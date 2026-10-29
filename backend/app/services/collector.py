"""采集服务 — Key 内存中转（浏览器请求头 → 适配器 → 快照入库，key 用完即丢）

铁律：本模块任何日志不得包含 api_key。
"""
from loguru import logger

from fastapi import Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.registry import get_adapter
from app.models.entities import Account, Snapshot
from app.services.alert_engine import evaluate_alerts

async def collect_snapshot(
    db: AsyncSession,
    account: Account,
    x_provider_key: str = Header(..., description="用户浏览器本地存储的 Key，仅本次请求内存使用"),
) -> Snapshot:
    """用请求头携带的 Key 拉一次快照并入库。"""
    adapter = get_adapter(account.provider)
    try:
        snap = await adapter.fetch_snapshot(x_provider_key)
    except Exception as e:
        logger.warning("provider={} account={} fetch failed: {}", account.provider, account.id, type(e).__name__)
        account.status = 2  # fetch_error
        await db.commit()
        raise HTTPException(status_code=502, detail=f"厂商接口请求失败: {type(e).__name__}")

    balance, quota, cost = snap.balance, snap.quota, snap.cost
    row = Snapshot(
        account_id=account.id,
        fetched_at=snap.fetched_at,
        source=0,  # 自动采集
        raw_payload_key=f"raw/{account.provider}/{snap.fetched_at:%Y%m%dT%H%M%S}",
        currency=(balance.currency if balance else (cost.currency if cost else None)),
        balance_total=balance.total if balance else None,
        balance_granted=balance.granted if balance else None,
        balance_topped_up=balance.topped_up if balance else None,
        quota_used_pct=quota.used_pct if quota else None,
        quota_limit=quota.limit if quota else None,
        quota_remaining=quota.remaining if quota else None,
        quota_window=quota.window if quota else None,
        cost_today=cost.today if cost else None,
        cost_month=cost.month if cost else None,
    )
    account.status = 0
    account.last_fetch_at = snap.fetched_at
    db.add(row)
    await db.commit()
    await evaluate_alerts(db, account, row)  # F4: 快照入库后评估告警
    return row
