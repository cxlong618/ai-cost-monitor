"""趋势 API — 快照曲线 / 烧钱速率 / 额度还剩 N 天预测（F3 核心）"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.core.database import get_db
from app.models.entities import Account, Snapshot, User

router = APIRouter(prefix="/trends", tags=["trends"])


async def _own_account(db: AsyncSession, user: User, account_id: int) -> Account:
    acc = (await db.execute(select(Account).where(Account.id == account_id))).scalar_one_or_none()
    if acc is None or acc.user_id != user.id:
        raise HTTPException(404, "账户不存在")
    return acc


def _burn_rate(snaps: list[Snapshot]) -> float | None:
    """日均消耗：余额制用首尾差值 / 天数（充值会拉低消耗估计，MVP 接受）"""
    bal = [(s.fetched_at, float(s.balance_total)) for s in snaps if s.balance_total is not None]
    if len(bal) < 2:
        return None
    bal.sort(key=lambda x: x[0])
    (t0, b0), (t1, b1) = bal[0], bal[-1]
    days = max((t1 - t0).total_seconds() / 86400, 1 / 24)
    if b1 >= b0:  # 没消耗或充值过
        return 0.0
    return (b0 - b1) / days


def _days_left(burn: float | None, latest: Snapshot | None) -> float | None:
    if not burn or latest is None or latest.balance_total is None:
        return None
    return round(float(latest.balance_total) / burn, 1)


@router.get("/{account_id}")
async def trend(
    account_id: int,
    days: int = 30,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    await _own_account(db, user, account_id)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    snaps = (await db.execute(
        select(Snapshot)
        .where(Snapshot.account_id == account_id, Snapshot.fetched_at > since)
        .order_by(Snapshot.fetched_at.asc())
    )).scalars().all()

    burn = _burn_rate(list(snaps))
    latest = snaps[-1] if snaps else None
    return {
        "points": [
            {
                "t": s.fetched_at.isoformat(),
                "balance": float(s.balance_total) if s.balance_total is not None else None,
                "quota_pct": float(s.quota_used_pct) if s.quota_used_pct is not None else None,
                "cost_today": float(s.cost_today) if s.cost_today is not None else None,
            }
            for s in snaps
        ],
        "burn_rate_per_day": burn,
        "days_left": _days_left(burn, latest),
        "latest_balance": float(latest.balance_total) if latest and latest.balance_total is not None else None,
        "latest_quota_pct": float(latest.quota_used_pct) if latest and latest.quota_used_pct is not None else None,
    }
