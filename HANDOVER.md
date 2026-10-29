# AI 成本监控 · 交接文档

> 2026-10-29 | 交接给 Codex 继续优化 | OpenClaw 玄策负责 pull + 部署

## 产品概述

接真实账单/用量的 AI 成本监控工具（订阅计算器为引流）。核心信任设计：**API Key 只存用户浏览器（IndexedDB + WebCrypto），服务端仅内存中转，永不落库**。

- 线上地址：http://45.144.136.180 （HTTP 明文，正式推广前需 HTTPS + 域名）
- 测试账号：qinxiao@test.com / test12345（上线前删除）

## 架构

```
nginx :80 ─┬── / → /var/www/ai-cost-monitor（Vue3 静态文件）
           └── /api/ → 127.0.0.1:8001（FastAPI，systemd: ai-cost-monitor）

同机另一服务：remote-file-manager（:8000，勿动端口）
数据库：PostgreSQL 14（原生安装），库 acm / 用户 acm，连接串在 backend/.env
```

## 目录结构

```
backend/
  app/
    api/        # 路由：auth(JWT) / accounts / alerts / trends / snapshots
    adapters/   # 厂商适配器（见下表）+ registry.py 注册表
    core/       # config(pydantic-settings) + database
    models/     # entities.py 全部 ORM（7 张表）
    services/   # collector(Key中转采集) + alert_engine(规则引擎)
  init_db.py    # 建表 + 播种 dev 用户
frontend/       # Vue3 + Vite + pinia + echarts + vue-router
docs/           # 设计文档（功能/数据库/API调研）
```

## 适配器状态（关键）

| 厂商 | billing_type | 端点 | 实测状态 |
|------|--------------|------|---------|
| deepseek | balance | GET /user/balance | ✅ 真 Key 全链路 |
| zai | quota | GET open.bigmodel.cn/api/monitor/usage/quota/limit（Authorization 头直接放 Key，无 Bearer；unit=3 五小时窗 / unit=6 周窗） | ✅ 真 Key 全链路 |
| openrouter | balance | GET /api/v1/credits | ⚠️ 未实测 |
| anthropic | cost | GET /v1/organizations/cost_report（需 Admin Key `sk-ant-admin`） | ⚠️ 未实测 |
| openai | cost | GET /v1/organization/usage + /costs（需 Admin Key；ChatGPT Plus ≠ API 账号，接不了） | ⚠️ 未实测 |
| siliconflow | balance | GET /v1/user/info（字段猜测） | ⚠️ 未实测 |

新增厂商：实现 `ProviderAdapter` 子类 → registry._bootstrap() 注册。

## 已知坑（Codex 必读）

1. **写文件工具会破坏代码**：正则/命令替换/`str` 类型注解可能被毁成 `***`。生成含敏感语法的脚本用 shell heredoc；每次改完 `python3 -m py_compile` 校验
2. **.env 新增变量必须在 Settings 类声明**，否则 pydantic 拒绝启动（已踩两次：DEEPSEEK_TEST_KEY / ZAI_TEST_KEY）
3. **部署目录要清空再拷贝**：`rm -rf /var/www/ai-cost-monitor/* && cp -r frontend/dist/* ...`，否则旧 chunk 混堆导致浏览器加载旧版
4. **8000 端口被 remote-file-manager 占用**，本项目固定 8001
5. `pkill -f` 匹配串会误杀自身 shell，按端口杀用 `fuser -k <port>/tcp`

## 常用命令

```bash
# 后端
systemctl restart ai-cost-monitor && journalctl -u ai-cost-monitor -f
cd backend && python3 -m py_compile $(git diff --name-only | grep '\.py$')

# 前端构建部署（一条龙）
cd frontend && npm run build && rm -rf /var/www/ai-cost-monitor/* && cp -r dist/* /var/www/ai-cost-monitor/

# 数据库
su - postgres -c "psql -d acm"
```

## 待办清单（按优先级）

1. **安全**：HTTPS（买域名 + Let's Encrypt）、注册正式账号删测试号、JWT_SECRET 换强随机（现 .env 里的 dev 值）
2. **功能**：burn_rate 速率告警接入趋势计算、邮件告警通道、报告页（purchases 表已建未用）
3. **适配器**：openrouter/anthropic/openai/siliconflow 真 Key 实测
4. **体验**：移动端适配检查、趋势图时间范围切换（现固定 30 天）
5. **运营**：订阅计算器实做（pricing_models 表空）、公众号引流文章

## 协作流程约定

- Codex 在 GitHub 仓库开发/优化 → 琴萧告知玄策 → 玄策 `git pull` → 构建 → 部署 → 回报结果
- 玄策不修改业务代码（只负责部署链路）；发现线上问题反馈给琴萧/Codex
