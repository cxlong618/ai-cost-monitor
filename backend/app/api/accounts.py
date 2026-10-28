"""账户 API — 添加/采集"""
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.core.database import get_db
from app.models.entities import Account, User
from app.adapters.registry import available_providers, get_adapter
from app.services.collector import collect_snapshot

router = APIRouter(prefix="/accounts", tags=["accounts"])


class AccountCreate(BaseModel):
    provider: str = Field(..., description="厂商名，见 /meta/providers")
    name: str
    mode: int = 1  # 0=本地Key 1=手动录入


@router.get("/meta/providers")
async def list_providers():
    """支持的厂商列表（前端接入引导用）"""
    return {"providers": available_providers()}


async def _own_account(db: AsyncSession, user: User, account_id: int) -> Account:
    acc = (await db.execute(select(Account).where(Account.id == account_id))).scalar_one_or_none()
    if acc is None or acc.user_id != user.id:
        raise HTTPException(404, "账户不存在")
    return acc


@router.get("")
async def list_accounts(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Account).where(Account.user_id == user.id, Account.status != 3))).scalars().all()
    return [{"id": r.id, "provider": r.provider, "mode": r.mode, "name": r.name, "status": r.status} for r in rows]


@router.post("")
async def create_account(body: AccountCreate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if body.provider not in available_providers():
        raise HTTPException(400, f"不支持的厂商: {body.provider}")
    acc = Account(user_id=user.id, provider=body.provider, name=body.name, mode=body.mode)
    db.add(acc)
    await db.commit()
    return {"id": acc.id, "provider": acc.provider, "mode": acc.mode}


@router.post("/{account_id}/collect")
async def collect(
    account_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    x_provider_key: str = Header(...),
):
    """用户打开页面时触发：前端从浏览器本地取 Key 放请求头，后端内存中转采集。"""
    acc = await _own_account(db, user, account_id)
    snap = await collect_snapshot(db, acc, x_provider_key=x_provider_key)
    return {"snapshot_id": snap.id, "balance_total": str(snap.balance_total), "quota_used_pct": str(snap.quota_used_pct)}
