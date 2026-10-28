"""DeepSeek 适配器 — 官方 GET /user/balance（余额制）
文档: https://api-docs.deepseek.com/api/get-user-balance
"""
from datetime import datetime, timezone

import httpx

from app.adapters.base import BalanceInfo, ProviderAdapter, ProviderSnapshot

BASE_URL = "https://api.deepseek.com"


class DeepSeekAdapter(ProviderAdapter):
    provider = "deepseek"
    billing_type = "balance"

    async def _get_balance(self, api_key: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{BASE_URL}/user/balance",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            return resp.json()

    async def test_connection(self, api_key: str) -> bool:
        try:
            data = await self._get_balance(api_key)
            return data.get("is_available") is True or bool(data.get("balance_infos"))
        except httpx.HTTPError:
            return False

    async def fetch_snapshot(self, api_key: str) -> ProviderSnapshot:
        data = await self._get_balance(api_key)
        info = next(iter(data.get("balance_infos", [])), None)
        balance = None
        if info:
            balance = BalanceInfo(
                total=float(info["total_balance"]),
                granted=float(info.get("granted_balance") or 0) or None,
                topped_up=float(info.get("topped_up_balance") or 0) or None,
                currency=info.get("currency", "CNY"),
            )
        return ProviderSnapshot(
            provider=self.provider,
            fetched_at=datetime.now(timezone.utc),
            balance=balance,
            raw_payload=data,
        )
