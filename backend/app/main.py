"""FastAPI 入口"""
import logging

from fastapi import FastAPI

from app.api.accounts import router as accounts_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="AI Cost Monitor", version="0.1.0")
app.include_router(accounts_router)


@app.get("/health")
async def health():
    return {"ok": True}
