"""OpenRouter 适配器 — 官方 GET /api/v1/credits（充值积分制，映射为余额制）
文档: https://openrouter.ai/docs/api/api-reference/credits/get-remaining-credits
"""
from datetime import datetime, timezone

import httpx

from app.adapters.base import BalanceInfo, ProviderAdapter, ProviderSnapshot

BASE_URL = "https://openrouter.ai"


class OpenRouterAdapter(ProviderAdapter):
    provider = "openrouter"
    billing_type = "balance"

    async def _get_credits(self, api_key: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{BASE_URL}/api/v1/credits",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            return resp.json()

    async def test_connection(self, api_key: str) -> bool:
        try:
            data = await self._get_credits(api_key)
            return "data" in data
        except httpx.HTTPError:
            return False

    async def fetch_snapshot(self, api_key: str) -> ProviderSnapshot:
        data = await self._get_credits(api_key)
        d = data.get("data", {})
        total = float(d.get("total_credits", 0))
        used = float(d.get("total_usage", 0))
        balance = BalanceInfo(total=round(total - used, 4), currency="USD")
        return ProviderSnapshot(
            provider=self.provider,
            fetched_at=datetime.now(timezone.utc),
            balance=balance,
            raw_payload=data,
        )
