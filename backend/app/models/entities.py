"""ORM 模型 — 对应 docs/02-数据库设计.md v0.4
约定：状态/类型字段一律 SMALLINT（0/1/2），减少存储。
Key 安全：api_key 不入库（浏览器本地存储，请求头携带，内存中转）。
"""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_pro: Mapped[int] = mapped_column(SmallInteger, default=0)  # 0/1
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(30))  # zai/deepseek/openrouter/anthropic/openai/siliconflow
    mode: Mapped[int] = mapped_column(SmallInteger, default=1)  # 0=本地Key 1=手动录入
    name: Mapped[str] = mapped_column(String(100))
    status: Mapped[int] = mapped_column(SmallInteger, default=0)  # 0=active 1=key_invalid 2=fetch_error 3=deleted
    last_fetch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # v0.4: 无 api_key_encrypted —— Key 永不上服务器


class Snapshot(Base):
    __tablename__ = "snapshots"
    __table_args__ = (Index("ix_snapshots_account_time", "account_id", "fetched_at"), )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source: Mapped[int] = mapped_column(SmallInteger, default=0)  # 0=自动采集 1=手动录入
    raw_payload_key: Mapped[str] = mapped_column(String(50))  # raw JSON 存对象存储/文件，表里只存键
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    # 余额制（DeepSeek/OpenRouter/硅基流动）
    balance_total: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    balance_granted: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    balance_topped_up: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 套餐制（智谱 coding plan）
    quota_used_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    quota_limit: Mapped[int | None] = mapped_column(Numeric(18, 0), nullable=True)
    quota_remaining: Mapped[float | None] = mapped_column(Numeric(18, 0), nullable=True)
    quota_window: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # 按量账单制（OpenAI/Anthropic）：当日消耗累计
    cost_today: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    cost_month: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[int] = mapped_column(SmallInteger)  # 0=余额阈值 1=配额阈值 2=速率异常
    threshold: Mapped[float] = mapped_column(Numeric(12, 4))
    channel: Mapped[int] = mapped_column(SmallInteger, default=0)  # 0=站内 1=邮件
    enabled: Mapped[int] = mapped_column(SmallInteger, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AlertEvent(Base):
    __tablename__ = "alert_events"
    __table_args__ = (Index("ix_alert_events_rule_time", "rule_id", "triggered_at"), )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("alert_rules.id", ondelete="CASCADE"))
    snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("snapshots.id"), nullable=True)
    kind: Mapped[int] = mapped_column(SmallInteger)  # 0=余额 1=配额 2=速率 3=采集失败
    message: Mapped[str] = mapped_column(Text)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Purchase(Base):
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[int] = mapped_column(SmallInteger)  # 0=Pro买断 1=报告次数
    amount_cents: Mapped[int] = mapped_column(Integer)
    credits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider: Mapped[int] = mapped_column(SmallInteger)  # 0=微信Native 1=微信JSAPI
    external_order_id: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[int] = mapped_column(SmallInteger, default=0)  # 0=pending 1=paid 2=refunded
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PricingModel(Base):
    __tablename__ = "pricing_models"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(30))
    model_id: Mapped[str] = mapped_column(String(64))
    plan_type: Mapped[int] = mapped_column(SmallInteger)  # 0=API按量 1=订阅
    plan_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    price_input: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)   # ¥/M tokens
    price_output: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
