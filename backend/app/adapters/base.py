"""厂商适配器基类 — 对应 docs/03-API账单接口调研.md

三种计费形态统一为 ProviderSnapshot：
- 余额制（DeepSeek/OpenRouter/硅基流动）→ balance 字段
- 套餐制（智谱 coding plan）→ quota 字段
- 按量账单制（OpenAI/Anthropic）→ cost 字段

Key 安全铁律：
- Adapter 收到的 key 仅存在于请求生命周期内存中
- 严禁写入日志/数据库/任何持久化介质
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BalanceInfo:
    total: float
    granted: float | None = None
    topped_up: float | None = None
    currency: str = "CNY"


@dataclass
class QuotaInfo:
    used_pct: float | None = None
    limit: float | None = None
    remaining: float | None = None
    window: str | None = None  # daily/weekly/monthly
    plan_level: str | None = None


@dataclass
class CostInfo:
    today: float | None = None
    month: float | None = None
    currency: str = "USD"


@dataclass
class ProviderSnapshot:
    provider: str
    fetched_at: datetime
    balance: BalanceInfo | None = None
    quota: QuotaInfo | None = None
    cost: CostInfo | None = None
    raw_payload: dict = field(default_factory=dict)


class ProviderAdapter(ABC):
    provider: str
    billing_type: str  # "balance" / "quota" / "cost"

    @abstractmethod
    async def test_connection(self, api_key: str) -> bool:
        """验证 Key 有效性（F1 连通性测试）"""

    @abstractmethod
    async def fetch_snapshot(self, api_key: str) -> ProviderSnapshot:
        """拉取一次快照。key 用完即丢，不得保存。"""
