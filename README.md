# AI Cost Monitor — AI 成本监控工具

> 接真实账单/用量的动态成本监控。Key 存用户浏览器本地，服务端仅内存中转、永不落库。

## 结构

```
backend/    FastAPI + SQLAlchemy 2.0 + PostgreSQL
frontend/   Vue 3 + Vite
docs/       设计文档（功能 / 数据库 / API 调研）
```

## 核心设计

- 三种计费形态统一快照：余额制（DeepSeek）/ 套餐制（智谱）/ 按量账单制（OpenAI/Anthropic）
- 适配器模式：`app/adapters/` 每厂商一个 Adapter
- Key 安全：浏览器 IndexedDB 存储 → 请求头携带 → 后端内存转发 → 用完即丢，日志禁打印

## 开发

```bash
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8001
cd frontend && npm i && npm run dev
```

Vite 开发代理会把 `/api` 请求转发到后端 8001 并剥离前缀。后端数据库与 JWT 参数仍通过 `backend/.env` 配置；正式部署必须替换开发 JWT 密钥并使用 HTTPS。本地 Key 模式需在账户页设置保险箱口令，旧版本本地 Key 需重新录入。

回归验证（项目根目录，PowerShell）：

```powershell
python -m venv .venv
python -m pip --python .venv/Scripts/python.exe install -r backend/requirements-dev.txt
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m compileall -q backend/app backend/tests
cd frontend
npm ci
npm test
npm run build
```

测试不连接生产数据库或真实厂商。当前能力及未完成项见 [功能设计中的审查记录](docs/01-功能设计.md)。
