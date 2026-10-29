"""离线 API 回归：隔离内存数据库，不访问线上服务或真实厂商。"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import BigInteger, event, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.main import app
from app.api.auth import current_user, hash_password, verify_password
from app.core.database import get_db
from app.models.entities import Base, User, Account, Snapshot, AlertEvent
from app.adapters.base import ProviderSnapshot, BalanceInfo
from app.services.metrics import burn_rate


@compiles(BigInteger, "sqlite")
def sqlite_bigint(element, compiler, **kw):
    return "INTEGER"


@pytest_asyncio.fixture
async def setup():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as db:
        users = [User(id=1, email="one@example.com", password_hash="unused"), User(id=2, email="two@example.com", password_hash="unused")]
        db.add_all(users)
        await db.commit()
        db.add_all([Account(id=1, user_id=1, provider="deepseek", name="手动", mode=1), Account(id=2, user_id=2, provider="deepseek", name="他人", mode=1), Account(id=3, user_id=1, provider="deepseek", name="Key", mode=0)])
        await db.commit()
    identity = SimpleNamespace(id=1, is_pro=0)

    async def user():
        return identity

    async def database():
        async with sessions() as db:
            yield db

    app.dependency_overrides[current_user] = user
    app.dependency_overrides[get_db] = database
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client, sessions, identity
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_account_lifecycle_and_ownership(setup):
    client, sessions, _ = setup
    assert (await client.patch('/accounts/2', json={"name": "侵入"})).status_code == 404
    assert (await client.post('/accounts', json={"provider": "deepseek", "name": "x", "mode": 9})).status_code == 422
    assert (await client.post('/accounts', json={"provider": "deepseek", "name": "   "})).status_code == 422
    assert (await client.patch('/accounts/1', json={"name": "新别名"})).status_code == 200
    assert (await client.delete('/accounts/1')).status_code == 200
    assert [a['id'] for a in (await client.get('/accounts')).json()] == [3]
    assert (await client.get('/trends/1')).status_code == 404
    assert (await client.post('/snapshots/manual?account_id=1', json={"balance_total": 1})).status_code == 404
    assert (await client.post('/accounts/1/collect', headers={"X-Provider-Key": "dummy"})).status_code == 404
    assert (await client.post('/accounts', json={"provider": "deepseek", "name": "新增", "mode": 0})).status_code == 200
    assert (await client.post('/accounts', json={"provider": "deepseek", "name": "超限"})).status_code == 403


@pytest.mark.asyncio
async def test_manual_validation_currency_and_time(setup):
    client, sessions, _ = setup
    for body in [{"raw_text": "已用 150%"}, {"balance_total": "NaN"}, {}, {"quota_used_pct": -1}]:
        assert (await client.post('/snapshots/manual?account_id=1', json=body)).status_code == 422
    assert (await client.post('/snapshots/manual?account_id=2', json={"balance_total": 10})).status_code == 404
    assert (await client.post('/snapshots/manual?account_id=3', json={"balance_total": 10})).status_code == 400
    response = await client.post('/snapshots/manual?account_id=1', json={"raw_text": "总余额：$12.30，已用 35%"})
    assert response.status_code == 200
    async with sessions() as db:
        account = await db.get(Account, 1)
        assert account.last_fetch_at is not None
    data = (await client.get('/trends/1?days=7')).json()
    assert data['currency'] == 'USD'
    assert data['latest_balance'] == 12.3
    assert data['latest_quota_pct'] == 35
    assert (await client.get('/trends/1?days=-1')).status_code == 422


def test_burn_rate_recharge_and_currency():
    now = datetime.now(timezone.utc)
    snaps = [SimpleNamespace(fetched_at=now + timedelta(days=i), balance_total=b, currency="CNY") for i, b in enumerate([100, 90, 150, 130])]
    assert burn_rate(snaps) == 10
    assert burn_rate(snaps[:1]) is None
    snaps[1].currency = "USD"
    assert burn_rate(snaps[:2]) is None


@pytest.mark.asyncio
async def test_rate_alert_read_cooldown_and_delete(setup):
    client, sessions, identity = setup
    rule = await client.post('/alerts/rules', json={"account_id": 1, "type": 2, "threshold": 5})
    assert rule.status_code == 200
    rule_id = rule.json()['id']
    async with sessions() as db:
        db.add(Snapshot(account_id=1, fetched_at=datetime.now(timezone.utc) - timedelta(days=1), raw_payload_key="test", currency="CNY", balance_total=100))
        await db.commit()
    for balance in [90, 89]:
        assert (await client.post('/snapshots/manual?account_id=1', json={"balance_total": balance})).status_code == 200
    events = (await client.get('/alerts/events')).json()
    assert len(events) == 1
    event_id = events[0]['id']
    identity.id = 2
    assert (await client.patch(f'/alerts/events/{event_id}/read')).status_code == 404
    assert (await client.patch(f'/alerts/rules/{rule_id}', json={"enabled": 0})).status_code == 404
    identity.id = 1
    assert (await client.patch(f'/alerts/events/{event_id}/read')).status_code == 200
    assert (await client.get('/alerts/events')).json()[0]['read'] is True
    assert (await client.patch(f'/alerts/rules/{rule_id}', json={"enabled": 0})).status_code == 200
    assert (await client.patch(f'/alerts/rules/{rule_id}', json={"enabled": 1})).status_code == 200
    assert (await client.delete(f'/alerts/rules/{rule_id}')).status_code == 200
    assert (await client.get('/alerts/events')).json() == []


@pytest.mark.asyncio
async def test_rule_validation_and_limits(setup):
    client, _, _ = setup
    for fields in [{"channel": 1}, {"threshold": "Infinity"}, {"type": 1, "threshold": 101}]:
        assert (await client.post('/alerts/rules', json={"account_id": 1, "type": 0, "threshold": 5, **fields})).status_code == 422
    assert (await client.post('/alerts/rules', json={"account_id": 2, "type": 0, "threshold": 5})).status_code == 404
    body = {"account_id": 1, "type": 0, "threshold": 5}
    assert (await client.post('/alerts/rules', json=body)).status_code == 200
    assert (await client.post('/alerts/rules', json=body)).status_code == 403


@pytest.mark.asyncio
async def test_collect_time_mode_and_failure(setup, monkeypatch):
    client, sessions, _ = setup
    fetched = datetime.now(timezone.utc) - timedelta(minutes=1)

    class Adapter:
        async def fetch_snapshot(self, key):
            return ProviderSnapshot(provider="deepseek", fetched_at=fetched, balance=BalanceInfo(total=42))

    monkeypatch.setattr('app.services.collector.get_adapter', lambda _: Adapter())
    headers = {"X-Provider-Key": "dummy-not-a-real-key"}
    assert (await client.post('/accounts/1/collect', headers=headers)).status_code == 400
    response = await client.post('/accounts/3/collect', headers=headers)
    assert response.status_code == 200
    assert response.json()['quota_used_pct'] is None
    async with sessions() as db:
        account = await db.get(Account, 3)
        assert account.last_fetch_at.replace(tzinfo=timezone.utc) == fetched
        snap = (await db.execute(select(Snapshot).where(Snapshot.account_id == 3))).scalar_one()
        assert snap.fetched_at.replace(tzinfo=timezone.utc) == fetched

    class FailedAdapter:
        async def fetch_snapshot(self, key):
            raise ValueError(f"sensitive={key}")

    monkeypatch.setattr('app.services.collector.get_adapter', lambda _: FailedAdapter())
    response = await client.post('/accounts/3/collect', headers=headers)
    assert response.status_code == 502
    assert 'dummy-not-a-real-key' not in response.text
    async with sessions() as db:
        assert (await db.get(Account, 3)).status == 2


def test_password_hash_compatibility():
    hashed = hash_password('test-password')
    assert verify_password('test-password', hashed)
    assert not verify_password('incorrect-password', hashed)
    assert not verify_password('长' * 40, hashed)


@pytest.mark.asyncio
async def test_register_login_and_password_limits(setup):
    client, _, _ = setup
    body = {"email": "new@example.com", "password": "new-test-password"}
    response = await client.post('/auth/register', json=body)
    assert response.status_code == 200
    assert response.json()['token']
    assert (await client.post('/auth/login', json=body)).status_code == 200
    assert (await client.post('/auth/login', json={**body, "password": "incorrect"})).status_code == 401
    assert (await client.post('/auth/register', json={**body, "password": "长" * 30})).status_code == 422
