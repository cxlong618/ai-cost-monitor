"""活跃账户的所有权检查，删除账户与不存在账户使用相同响应。"""
from fastapi import HTTPException
from sqlalchemy import select

from app.models.entities import Account


async def own_account(db, user, account_id):
    account = (await db.execute(select(Account).where(
        Account.id == account_id, Account.user_id == user.id, Account.status != 3,
    ))).scalar_one_or_none()
    if account is None:
        raise HTTPException(404, "账户不存在")
    return account
