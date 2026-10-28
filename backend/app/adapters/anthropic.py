"""Anthropic 适配器 — 官方 Admin API cost_report（按量账单制）
文档: https://docs.claude.com/en/api/admin-api
认证: Admin API Key（sk-ant-admin...），普通 sk-ant-api Key 不可用
"""
from datetime import datetime, timedelta, timezone

import httpx

from app.adapters.base import CostInfo, ProviderAdapter, ProviderSnapshot

BASE_URL = "https://api.anthropic.com"
ADMIN_KEY_PREFIX = "sk-ant-admin"


class AnthropicAdapter(ProviderAdapter):
    provider = "anthropic"
    billing_type = "cost"

    def _headers(self, api_key: str) -> dict:
        if not api_key.startswith(ADMIN_KEY_PREFIX):
            raise ValueError("需要 Admin API Key（sk-ant-admin 开头），普通 API Key 无法查询账单")
        return {"x-api-key": api_key, "anthropic-version": "2023-06-01"}

    async def _cost_report(self, api_key: str) -> dict:
        now = datetime.now(timezone.utc)
        params = {
            "start_time": int((now - timedelta(days=31)).timestamp()),
            "end_time": int(now.timestamp()),
            "limit": 100,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"{BASE_URL}/v1/organizations/cost_report",
                headers=self._headers(api_key),
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    async def test_connection(self, api_key: str) -> bool:
        try:
            data = await self._cost_report(api_key)
            return "data" in data or "results" in data
        except (httpx.HTTPError, ValueError):
            return False

    async def fetch_snapshot(self, api_key: str) -> ProviderSnapshot:
        data = await self._cost_report(api_key)
        # 按日分桶响应：取今日 / 本月累计
        today = datetime.now(timezone.utc).date()
        rows = data.get("results", []) or data.get("data", [])
        cost_today = cost_month = 0.0
        for r in rows:
            d = r.get("date") or r.get("start_time", "")
            amt = float(r.get("amount", 0) or r.get("cost", 0) or 0)
            try:
                d = d[:10] if isinstance(d, str) else datetime.fromtimestamp(int(d), timezone.utc).date().isoformat()
            except (ValueError, OSError):
                continue
            if d[:7] == today.strftime("%Y-%m"):
                cost_month += amt
                if d == today.isoformat():
                    cost_today += amt
        return ProviderSnapshot(
            provider=self.provider,
            fetched_at=datetime.now(timezone.utc),
            cost=CostInfo(today=round(cost_today, 4), month=round(cost_month, 4)),
            raw_payload=data,
        )
