"""手动快照 API — mode=1（不传 Key）用户的核心路径
用户从厂商控制台看到余额/配额，录入一条快照；或粘贴文本自动解析。
"""
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.api.trends import _own_account
from app.core.database import get_db
from app.models.entities import Account, Snapshot, User
from app.services.alert_engine import evaluate_alerts

router = APIRouter(prefix="/snapshots", tags=["snapshots"])


class ManualSnapshotIn(BaseModel):
    balance_total: float | None = None
    quota_used_pct: float | None = Field(default=None, ge=0, le=100)
    currency: str = "CNY"
    raw_text: str | None = Field(default=None, description="可选：粘贴的控制台文本，服务端自动解析兜底")


# 常见控制台文案模式："余额 9.55 元" / "总余额：$12.30" / "已用 35%"
PATTERNS = [
    (re.compile(r"总?余额[：:\s]*[¥￥$]?\s*([0-9]+(?:\.[0-9]+)?)"), "balance_total"),
    (re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*元"), "balance_total"),
    (re.compile(r"已用[：:\s]*([0-9]+(?:\.[0-9]+)?)\s*%"), "quota_used_pct"),
]


def parse_text(text: str) -> dict:
    found = {}
    for pat, field in PATTERNS:
        m = pat.search(text)
        if m and field not in found:
            found[field] = float(m.group(1))
    return found


@router.post("/manual")
async def manual_snapshot(
    body: ManualSnapshotIn,
    account_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    acc = await _own_account(db, user, account_id)
    if acc.mode == 0:
        raise HTTPException(400, "本地 Key 模式账户走自动采集，无需手动录入")

    # 粘贴文本解析兜底
    if body.raw_text and body.balance_total is None and body.quota_used_pct is None:
        parsed = parse_text(body.raw_text)
        if not parsed:
            raise HTTPException(422, "未能从粘贴文本中识别出余额或配额，请检查格式或手动填数字")
        body.balance_total = parsed.get("balance_total")
        body.quota_used_pct = parsed.get("quota_used_pct")
    elif body.balance_total is None and body.quota_used_pct is None:
        raise HTTPException(422, "请填写余额、配额或粘贴文本")

    row = Snapshot(
        account_id=account_id,
        source=1,  # 手动录入
        raw_payload_key=f"manual/{account_id}",
        currency=body.currency if body.balance_total is not None else None,
        balance_total=body.balance_total,
        quota_used_pct=body.quota_used_pct,
    )
    acc.last_fetch_at = row.fetched_at
    db.add(row)
    await db.commit()
    await evaluate_alerts(db, acc, row)
    return {"snapshot_id": row.id, "parsed_balance": body.balance_total, "parsed_quota_pct": body.quota_used_pct}
