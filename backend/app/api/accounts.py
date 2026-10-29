"""账户 API — 添加/采集"""
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.core.database import get_db
from app.models.entities import Account, AlertRule, User
from app.services.ownership import own_account as _own_account
from app.adapters.registry import available_providers
from app.services.collector import collect_snapshot

router = APIRouter(prefix="/accounts", tags=["accounts"])


class AccountCreate(BaseModel):
    provider: str = Field(..., description="厂商名，见 /meta/providers")
    name: str = Field(min_length=1, max_length=100, pattern=r"\S")
    mode: Literal[0, 1] = 1


class AccountUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100, pattern=r"\S")


@router.get("/meta/providers")
async def list_providers():
    """支持的厂商列表（前端接入引导用）"""
    return {"providers": available_providers()}


@router.get("")
async def list_accounts(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Account).where(Account.user_id == user.id, Account.status != 3))).scalars().all()
    return [{"id": r.id, "provider": r.provider, "mode": r.mode, "name": r.name, "status": r.status} for r in rows]


@router.post("")
async def create_account(body: AccountCreate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if body.provider not in available_providers():
        raise HTTPException(400, f"不支持的厂商: {body.provider}")
    if not user.is_pro:
        count = (await db.execute(select(func.count()).select_from(Account).where(
            Account.user_id == user.id, Account.status != 3,
        ))).scalar_one()
        if count >= 2:
            raise HTTPException(403, "免费版最多接入 2 个账户")
    acc = Account(user_id=user.id, provider=body.provider, name=body.name.strip(), mode=body.mode)
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
    if acc.mode != 0 or not x_provider_key.strip():
        raise HTTPException(400, "仅本地 Key 模式且提供有效 Key 时可采集")
    snap = await collect_snapshot(db, acc, x_provider_key=x_provider_key)
    return {"snapshot_id": snap.id, "balance_total": snap.balance_total, "quota_used_pct": snap.quota_used_pct}


@router.patch("/{account_id}")
async def update_account(account_id: int, body: AccountUpdate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    account = await _own_account(db, user, account_id)
    account.name = body.name.strip()
    await db.commit()
    return {"ok": True}


@router.delete("/{account_id}")
async def delete_account(account_id: int, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    account = await _own_account(db, user, account_id)
    account.status = 3
    await db.execute(update(AlertRule).where(AlertRule.account_id == account_id).values(enabled=0))
    await db.commit()
    return {"ok": True}
