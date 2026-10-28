"""智谱 zai 适配器 — GLM Coding Plan 用量端点（社区逆向，cc-switch #1038）
⚠️ 无官方 SLA，接口变更风险由适配器模式隔离；上线前需真实 Key 实测补录字段。
"""
from datetime import datetime, timezone

import httpx

from app.adapters.base import ProviderAdapter, ProviderSnapshot, QuotaInfo

BASE_URL = "https://open.bigmodel.cn"
USAGE_PATH = "/api/paas/usage"  # TODO: 用真实 Key 实测确认完整路径与响应结构


class ZaiAdapter(ProviderAdapter):
    provider = "zai"
    billing_type = "quota"

    async def _fetch(self, api_key: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{BASE_URL}{USAGE_PATH}",
                headers={"Authorization": api_key, "Accept-Language": "en-US,en"},
            )
            resp.raise_for_status()
            return resp.json()

    async def test_connection(self, api_key: str) -> bool:
        try:
            data = await self._fetch(api_key)
            return bool(data.get("success") and data.get("data"))
        except httpx.HTTPError:
            return False

    async def fetch_snapshot(self, api_key: str) -> ProviderSnapshot:
        data = await self._fetch(api_key)
        d = data.get("data", {})
        limits = d.get("limits", {}) or {}
        quota = QuotaInfo(
            used_pct=limits.get("used_pct"),
            limit=limits.get("limit"),
            remaining=limits.get("remaining"),
            window=limits.get("window"),
            plan_level=d.get("level"),
        )
        return ProviderSnapshot(
            provider=self.provider,
            fetched_at=datetime.now(timezone.utc),
            quota=quota,
            raw_payload=data,
        )
