# AI 成本监控工具 · 厂商账单/用量 API 调研

> 版本 v0.2 | 2026-10-26 | 一期覆盖：DeepSeek、智谱、OpenRouter、Anthropic、OpenAI、硬基流动（硬基流动写法待修正）

## 总览

| 厂商 | 余额查询 | 用量明细 | 认证 | 稳定性 |
|------|---------|---------|------|--------|
| DeepSeek | ✅ 官方 `GET /user/balance` | ⚠️ 平台端点（非公开文档） | Bearer API Key | 高（官方文档） |
| 智谱 zai | ⚠️ Coding Plan 用量为社区逆向端点 | ✅ 返回 limits/level | Authorization: API Key | 中（接口可能变更，需适配器隔离） |
| OpenRouter | ✅ 官方 `GET /api/v1/credits` | ✅ `GET /api/v1/key` 额度/限额 | Bearer API Key（普通 Key） | 高（官方文档） |
| Anthropic | ✅ 官方 Admin API | ✅ cost_report 按日 USD + usage_report（可分组 workspace/model/key） | Admin Key `sk-ant-admin` | 高（官方文档） |
| OpenAI | ✅ 官方 Admin API | ✅ organization usage 按日分桶 | Admin Key（需管理权限 scope） | 高（官方文档） |
| 硬基流动 | ✅ 余额制（待验证） | 待验证 | Bearer API Key | 待验证 |

> v0.2 结论：**国外大厂（OpenAI/Anthropic/OpenRouter）接口比国内更规范**，均有正式文档。主要门栏：OpenAI/Anthropic 需用户在控制台创建专门的 Admin Key，普通 API Key 拉不了账单（产品内需引导文案）。

---

## 1. DeepSeek

### 1.1 官方余额接口（有正式文档）
```
GET https://api.deepseek.com/user/balance
Authorization: Bearer <DEEPSEEK_API_KEY>
```

响应：
```json
{
  "is_available": true,
  "balance_infos": [
    {
      "currency": "CNY",
      "total_balance": "110.00",
      "granted_balance": "10.00",     // 赠送余额
      "topped_up_balance": "100.00"   // 充值余额
    }
  ]
}
```

- 来源：官方文档 https://api-docs.deepseek.com/api/get-user-balance
- 直接映射 snapshots 表：balance_total / balance_granted / balance_topped_up / currency
- `is_available` 可用于 F1 连通性测试

### 1.2 用量明细端点（CodexBar 项目逆向，非官方）
开源项目 CodexBar（github.com/steipete/CodexBar）的 deepseek provider 文档披露：
- 按 Key 日用量：`GET .../by_api_key/cost?...`（与平台"用量"页面相同的日粒度数据）
- 备选：`GET .../usage/cost?...`
- 平台会话端点：无 API Key 时可用平台 session token 拉余额

**结论**：MVP 先只做官方余额接口（快照余额变化即可推算消耗 = 前后快照差值），用量明细端点作为增强项，接口不稳就靠差值法兜底。

---

## 2. 智谱 zai（GLM Coding Plan）

### 2.1 用量查询端点（社区逆向，cc-switch Discussion #1038）
```
GET https://open.bigmodel.cn/api/.../usage   (具体路径见 cc-switch 仓库脚本)
Authorization: <API Key>          // 注意：直接放 Key，非 Bearer 前缀
Accept-Language: en-US,en
```

响应结构（extractor 解析逻辑）：
```json
{
  "success": true,
  "data": {
    "level": "pro",               // 套餐等级
    "limits": {
      // 各周期配额窗口：used / limit / reset 时间等
    }
  }
}
```

- 来源：https://github.com/farion1231/cc-switch/discussions/1038
- 注意：Z.ai 海外站与 bigmodel 国内站的域名不同，脚本里可互换
- 官方还出了 Claude Code 用量插件 `glm-plan-usage`（zai-coding-plugins 仓库，仅个人版套餐）——可作为接口参考实现

### 2.2 映射
- `data.level` → 套餐名展示
- `data.limits.*` → quota_used_pct / quota_limit / quota_remaining / quota_window
- 无余额概念（套餐制），balance_* 字段留空

### 2.3 风险
- 社区逆向端点，无 SLA，可能随改版失效 → **采集层必须适配器模式**，接口挂了降级为 status=fetch_error 并告警用户
- 待办：开发期用琴萧自己的 Key 实测一次完整响应，把 limits 的确切字段结构补进本文档

---

## 3. OpenRouter（最易接入，优先实现）

### 3.1 剩余额度（官方文档）
```
GET https://openrouter.ai/api/v1/credits
Authorization: Bearer <OPENROUTER_API_KEY>   // 普通 Key 即可
```
响应：
```json
{ "data": { "total_credits": 100.5, "total_usage": 25.75 } }
```
- 剩余 = total_credits - total_usage，直接映射余额制快照

### 3.2 Key 额度/限额监控
```
GET https://openrouter.ai/api/v1/key
```
- 返回 `limit_remaining`、budgets（key 自身限额 / 预算限制），可做 Key 级告警
- 来源：https://openrouter.ai/docs/api/api-reference/credits/get-remaining-credits

**战略价值**：国内用户大量通过 OpenRouter 用海外模型，接入它等于间接覆盖一大批海外账户。

---

## 4. Anthropic（官方 Admin API，粒度最好）

```
GET https://api.anthropic.com/v1/organizations/cost_report      // 按日 USD，可按 workspace/line-item 分组
GET https://api.anthropic.com/v1/organizations/usage_report/messages  // token 用量，可按 key/workspace/model/service tier 分组
Authorization: x-api-key: sk-ant-admin0619-...   // 必须是 Admin Key
```

**要点**：
- 必须用 Admin Key（`sk-ant-admin` 开头），组织管理员在 Console Settings 创建；普通 `sk-ant-api` Key 调不通
- cost_report 是与发票对账的 USD 金额；usage_report 区分 uncached input / cached input / cache creation / output 四类 token（费率差好几倍）
- 类型：按量账单制（无余额概念）→ 映射为「日消耗累计」，与套餐/余额制统一到消耗趋势视图

---

## 5. OpenAI（官方 Admin API）

```
GET https://api.openai.com/v1/organization/usage?start_time=...&end_time=...&bucket=1d
GET https://api.openai.com/v1/organization/costs    // 成本版
Authorization: Bearer <OPENAI_ADMIN_KEY>   // Admin 权限 scope
```
- 官方 Cookbook 示例：developers.openai.com/cookbook/examples/completions_usage_api
- 需 Admin API Key（管理 scope）；项目级 sk-proj Key 拉不了组织总账单
- 同为按量账单制，与 Anthropic 同一适配器抽象：`BillingReportAdapter`（拉日消耗而非余额）
- 历史端点 `/v1/dashboard/billing/*` 已旧化，新实现直接用 organization usage/costs

---

## 6. 硬基流动 SiliconFlow

- 预计余额制（账户钱包），官方 API 文档化程度高，具体端点开发期实测补录

---

## 7. 适配器接口约定（后端）

```python
class ProviderAdapter(ABC):
    provider: str  # "zai" / "deepseek"

    async def test_connection(self, api_key: str) -> bool: ...
    async def fetch_snapshot(self, api_key: str) -> ProviderSnapshot: ...

@dataclass
class ProviderSnapshot:
    raw_payload: dict
    balance: BalanceInfo | None      # 充值型
    quota: QuotaInfo | None          # 套餐型
    fetched_at: datetime
```

新增厂商 = 实现一个 Adapter + 注册，不动核心逻辑。二期加厂商（硅基流动、Kimi、MiniMax）按此扩展。

## 8. 采集调度

- APScheduler / Celery beat，每账户默认 6h，Pro 用户 1h
- 每次采集后：写 snapshot → 跑告警规则引擎 → 更新 account.last_fetch_at
- 失败处理：连续 2 次失败置 status=key_invalid，触发站内告警

## 9. 待验证清单（开发第一周完成）

- [ ] 用真实 Key 实测智谱用量端点完整响应（补文档）
- [ ] 实测 DeepSeek /user/balance（文档已全，验证即可）
- [ ] 确认智谱端点限频策略（避免高频采集被封 Key）
- [ ] 差值法验证：连续快照差值 vs 平台页面显示消耗是否一致
