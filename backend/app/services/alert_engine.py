"""告警规则引擎 — 每次快照入库后评估规则（F4）

规则类型 type: 0=余额阈值 1=配额阈值 2=速率异常
冷却：同一规则 12h 内不重复触发
免费版限制：1 条/账户
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Account, AlertEvent, AlertRule, Snapshot
from app.services.metrics import burn_rate

COOLDOWN = timedelta(hours=12)
FREE_RULES_PER_ACCOUNT = 1
PRO_RULES_PER_ACCOUNT = 20


async def can_add_rule(db: AsyncSession, user, account_id: int) -> bool:
    n = len(
        (await db.execute(
            select(AlertRule).where(AlertRule.account_id == account_id, AlertRule.enabled == 1)
        )).scalars().all()
    )
    limit = PRO_RULES_PER_ACCOUNT if user.is_pro else FREE_RULES_PER_ACCOUNT
    return n < limit


async def _in_cooldown(db: AsyncSession, rule_id: int) -> bool:
    since = datetime.now(timezone.utc) - COOLDOWN
    recent = (await db.execute(
            select(AlertEvent).where(AlertEvent.rule_id == rule_id, AlertEvent.triggered_at > since).limit(1)
    )).scalar_one_or_none()
    return recent is not None


def _evaluate(rule: AlertRule, snap: Snapshot, burn_rate: float | None) -> str | None:
    """返回告警消息；None=未触发"""
    if rule.type == 0 and snap.balance_total is not None:
        if snap.balance_total < rule.threshold:
            return f"余额低于 {rule.threshold}：当前 {snap.balance_total}"
    if rule.type == 1 and snap.quota_used_pct is not None:
        if snap.quota_used_pct > rule.threshold:
            return f"配额消耗超过 {rule.threshold}%：当前 {snap.quota_used_pct}%"
    if rule.type == 2 and burn_rate is not None and burn_rate > float(rule.threshold):
        return f"烧钱速率异常：日均 {burn_rate:.2f}，超阈值 {rule.threshold}"
    return None


async def evaluate_alerts(db: AsyncSession, account: Account, snap: Snapshot) -> list[AlertEvent]:
    """快照入库后调用：评估该账户全部启用规则"""
    rules = (await db.execute(
        select(AlertRule).where(AlertRule.account_id == account.id, AlertRule.enabled == 1)
    )).scalars().all()
    if account.status == 3:
        return []
    burn = None
    if any(rule.type == 2 for rule in rules):
        since = datetime.now(timezone.utc) - timedelta(days=30)
        snaps = (await db.execute(select(Snapshot).where(
            Snapshot.account_id == account.id, Snapshot.fetched_at >= since,
            Snapshot.currency == snap.currency,
        ).order_by(Snapshot.fetched_at))).scalars().all()
        burn = burn_rate(snaps)
    events = []
    for rule in rules:
        if await _in_cooldown(db, rule.id):
            continue
        msg = _evaluate(rule, snap, burn)
        if msg:
            ev = AlertEvent(rule_id=rule.id, snapshot_id=snap.id, kind=rule.type, message=msg)
            db.add(ev)
            events.append(ev)
    if events:
        await db.commit()
    return events
