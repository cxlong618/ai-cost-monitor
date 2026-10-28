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
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
cd frontend && npm i && npm run dev
```
