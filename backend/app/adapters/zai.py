"""智谱 zai 适配器 — GLM Coding Plan 官方监控端点（已实测 2026-10-29）

GET https://open.bigmodel.cn/api/monitor/usage/quota/limit
Header: Authorization: <key>（无 Bearer 前缀）
响应: {code:200, data:{limits:[{type,unit,number,percentage,nextResetTime,...}], level:"pro"}}

unit 语义（实测推断）: 3=5小时窗口 6=周窗口 5=次数型工具限额(TIME_LIMIT)
适配器取 unit=6（周窗口）为主配额，unit=3（5小时窗口）为辅。
来源: zai-org/zai-coding-plugins glm-plan-usage 插件源码
"""
from datetime import datetime, timezone

import httpx

from app.adapters.base import ProviderAdapter, ProviderSnapshot, QuotaInfo

BASE_URL = "https://open.bigmodel.cn"
QUOTA_PATH = "/api/monitor/usage/quota/limit"


class ZaiAdapter(ProviderAdapter):
    provider = "zai"
    billing_type = "quota"

    async def _fetch(self, api_key: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{BASE_URL}{QUOTA_PATH}",
                headers={"Authorization": api_key, "Accept-Language": "en-US,en"},
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success"):
                raise ValueError(data.get("msg") or "zai 接口返回失败")
            return data["data"]

    async def test_connection(self, api_key: str) -> bool:
        try:
            await self._fetch(api_key)
            return True
        except (httpx.HTTPError, ValueError, KeyError):
            return False

    async def fetch_snapshot(self, api_key: str) -> ProviderSnapshot:
        d = await self._fetch(api_key)
        limits = d.get("limits", [])
        weekly = next((x for x in limits if x.get("unit") == 6 and x.get("type") == "TOKENS_LIMIT"), None)
        hourly = next((x for x in limits if x.get("unit") == 3 and x.get("type") == "TOKENS_LIMIT"), None)
        main = weekly or hourly or (limits[0] if limits else None)
        quota = None
        if main:
            quota = QuotaInfo(
                used_pct=main.get("percentage"),
                remaining=None,
                window="weekly" if main is weekly else "5h",
                plan_level=d.get("level"),
            )
        return ProviderSnapshot(
            provider=self.provider,
            fetched_at=datetime.now(timezone.utc),
            quota=quota,
            raw_payload=d,
        )
