"""OpenAI 适配器 — 官方 Admin API organization usage/costs（按量账单制）
认证: Admin API Key（管理权限 scope），项目级 sk-proj Key 拉不了组织账单
"""
from datetime import datetime, timedelta, timezone

import httpx

from app.adapters.base import CostInfo, ProviderAdapter, ProviderSnapshot

BASE_URL = "https://api.openai.com/v1/organization"


class OpenAIAdapter(ProviderAdapter):
    provider = "openai"
    billing_type = "cost"

    async def _usage(self, api_key: str) -> dict:
        now = datetime.now(timezone.utc)
        params = {
            "start_time": int((now - timedelta(days=31)).timestamp()),
            "end_time": int(now.timestamp()),
            "bucket": "1d",
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"{BASE_URL}/usage",
                headers={"Authorization": f"Bearer {api_key}"},
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    async def _costs(self, api_key: str) -> dict:
        now = datetime.now(timezone.utc)
        params = {
            "start_time": int((now - timedelta(days=31)).timestamp()),
            "end_time": int(now.timestamp()),
            "bucket": "1d",
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"{BASE_URL}/costs",
                headers={"Authorization": f"Bearer {api_key}"},
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    async def test_connection(self, api_key: str) -> bool:
        try:
            data = await self._usage(api_key)
            return "data" in data
        except httpx.HTTPError:
            return False

    async def fetch_snapshot(self, api_key: str) -> ProviderSnapshot:
        usage, costs = await self._usage(api_key), await self._costs(api_key)
        today = datetime.now(timezone.utc).date()
        cost_today = cost_month = 0.0
        for r in costs.get("data", []):
            # snapshot_id 形如 cost_day_YYYY_MM_DD；amount {value, currency_code}
            sid = r.get("snapshot_id", "")
            amount = r.get("amount", {}) or {}
            amt = float(amount.get("value", 0) or 0)
            if sid.startswith("cost_day_"):
                d = sid.replace("cost_day_", "").replace("_", "-")
                if d[:7] == today.strftime("%Y-%m"):
                    cost_month += amt
                    if d == today.isoformat():
                        cost_today += amt
        merged = {"usage": usage, "costs": costs}
        return ProviderSnapshot(
            provider=self.provider,
            fetched_at=datetime.now(timezone.utc),
            cost=CostInfo(today=round(cost_today, 4), month=round(cost_month, 4)),
            raw_payload=merged,
        )
