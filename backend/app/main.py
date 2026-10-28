"""FastAPI 入口"""
import logging

from fastapi import FastAPI

from app.api.accounts import router as accounts_router
from app.api.auth import router as auth_router
from app.api.alerts import router as alerts_router
from app.api.trends import router as trends_router
from app.api.snapshots import router as snapshots_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="AI Cost Monitor", version="0.1.0")
app.include_router(accounts_router)
app.include_router(auth_router)
app.include_router(alerts_router)
app.include_router(trends_router)
app.include_router(snapshots_router)


@app.get("/health")
async def health():
    return {"ok": True}
