"""告警规则 API"""
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator, ConfigDict
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.core.database import get_db
from app.models.entities import AlertEvent, AlertRule, User
from app.services.alert_engine import can_add_rule
from app.services.ownership import own_account as _own_account

router = APIRouter(prefix="/alerts", tags=["alerts"])


class RuleIn(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    account_id: int
    type: int = Field(ge=0, le=2, description="0=余额阈值 1=配额阈值 2=速率异常")
    threshold: float = Field(ge=0, le=99999999)
    channel: Literal[0] = 0  # 尚未提供邮件投递，明确拒绝该通道

    @model_validator(mode="after")
    def validate_threshold(self):
        if self.type == 1 and self.threshold > 100:
            raise ValueError("配额阈值不能超过 100%")
        return self


class RuleUpdate(BaseModel):
    enabled: Literal[0, 1]


@router.get("/rules")
async def list_rules(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rules = (await db.execute(select(AlertRule).where(AlertRule.user_id == user.id))).scalars().all()
    return [
        {"id": r.id, "account_id": r.account_id, "type": r.type,
         "threshold": str(r.threshold), "channel": r.channel, "enabled": r.enabled}
        for r in rules
    ]


@router.post("/rules")
async def create_rule(body: RuleIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await _own_account(db, user, body.account_id)
    if not await can_add_rule(db, user, body.account_id):
        raise HTTPException(403, "已达规则数上限（免费版每账户 1 条，升级 Pro 解锁）")
    rule = AlertRule(
        account_id=body.account_id, user_id=user.id,
        type=body.type, threshold=body.threshold, channel=body.channel,
    )
    db.add(rule)
    await db.commit()
    return {"id": rule.id}


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rule = (await db.execute(select(AlertRule).where(AlertRule.id == rule_id))).scalar_one_or_none()
    if rule is None or rule.user_id != user.id:
        raise HTTPException(404, "规则不存在")
    await db.execute(delete(AlertEvent).where(AlertEvent.rule_id == rule.id))
    await db.delete(rule)
    await db.commit()
    return {"ok": True}


@router.patch("/rules/{rule_id}")
async def update_rule(rule_id: int, body: RuleUpdate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rule = await db.get(AlertRule, rule_id)
    if rule is None or rule.user_id != user.id:
        raise HTTPException(404, "规则不存在")
    await _own_account(db, user, rule.account_id)
    if body.enabled and not rule.enabled and not await can_add_rule(db, user, rule.account_id):
        raise HTTPException(403, "已达启用规则数上限")
    rule.enabled = body.enabled
    await db.commit()
    return {"ok": True}


@router.patch("/events/{event_id}/read")
async def read_event(event_id: int, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    event = (await db.execute(select(AlertEvent).join(AlertRule).where(
        AlertEvent.id == event_id, AlertRule.user_id == user.id,
    ))).scalar_one_or_none()
    if event is None:
        raise HTTPException(404, "事件不存在")
    if event.read_at is None:
        event.read_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


@router.get("/events")
async def list_events(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rules = (await db.execute(select(AlertRule).where(AlertRule.user_id == user.id))).scalars().all()
    out = []
    for r in rules:
        evs = (await db.execute(
            select(AlertEvent).where(AlertEvent.rule_id == r.id).order_by(AlertEvent.triggered_at.desc()).limit(50)
        )).scalars().all()
        out.extend(
            {"id": e.id, "rule_id": r.id, "kind": e.kind, "message": e.message,
             "triggered_at": e.triggered_at.isoformat(), "read": e.read_at is not None}
            for e in evs
        )
    out.sort(key=lambda x: x["triggered_at"], reverse=True)
    return out
