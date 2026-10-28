"""硅基流动 SiliconFlow 适配器 — 余额制（TODO: 端点实测补录）"""
from datetime import datetime, timezone

import httpx

from app.adapters.base import BalanceInfo, ProviderAdapter, ProviderSnapshot

BASE_URL = "https://api.siliconflow.cn"
USER_INFO_PATH = "/v1/user/info"  # 预计返回 balance 字段，待实测


class SiliconFlowAdapter(ProviderAdapter):
    provider = "siliconflow"
    billing_type = "balance"

    async def _fetch(self, api_key: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{BASE_URL}{USER_INFO_PATH}",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            return resp.json()

    async def test_connection(self, api_key: str) -> bool:
        try:
            await self._fetch(api_key)
            return True
        except httpx.HTTPError:
            return False

    async def fetch_snapshot(self, api_key: str) -> ProviderSnapshot:
        data = await self._fetch(api_key)
        d = data.get("data", data)
        balance = None
        if d.get("balance") is not None:
            balance = BalanceInfo(total=float(d["balance"]), currency="CNY")
        return ProviderSnapshot(
            provider=self.provider,
            fetched_at=datetime.now(timezone.utc),
            balance=balance,
            raw_payload=data,
        )
