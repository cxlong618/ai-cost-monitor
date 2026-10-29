"""趋势 API — 快照曲线 / 烧钱速率 / 额度还剩 N 天预测（F3 核心）"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.core.database import get_db
from app.models.entities import Snapshot, User
from app.services.ownership import own_account as _own_account
from app.services.metrics import burn_rate as _burn_rate

router = APIRouter(prefix="/trends", tags=["trends"])


def _days_left(burn: float | None, latest: Snapshot | None) -> float | None:
    if not burn or latest is None or latest.balance_total is None:
        return None
    return round(float(latest.balance_total) / burn, 1)


@router.get("/{account_id}")
async def trend(
    account_id: int,
    days: int = Query(default=30, ge=1, le=365),
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

    latest = snaps[-1] if snaps else None
    burn = _burn_rate([s for s in snaps if latest and s.currency == latest.currency])
    return {
        "points": [
            {
                "t": s.fetched_at.isoformat(),
                "balance": float(s.balance_total) if s.balance_total is not None else None,
                "quota_pct": float(s.quota_used_pct) if s.quota_used_pct is not None else None,
                "cost_today": float(s.cost_today) if s.cost_today is not None else None,
                "cost_month": float(s.cost_month) if s.cost_month is not None else None,
                "currency": s.currency,
            }
            for s in snaps
        ],
        "burn_rate_per_day": burn,
        "currency": latest.currency if latest else None,
        "latest_cost_today": float(latest.cost_today) if latest and latest.cost_today is not None else None,
        "latest_cost_month": float(latest.cost_month) if latest and latest.cost_month is not None else None,
        "days_left": _days_left(burn, latest),
        "latest_balance": float(latest.balance_total) if latest and latest.balance_total is not None else None,
        "latest_quota_pct": float(latest.quota_used_pct) if latest and latest.quota_used_pct is not None else None,
    }
