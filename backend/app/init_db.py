"""建表脚本：python -m app.init_db"""
import asyncio

from sqlalchemy import text

from app.core.database import engine
from app.models.entities import Base


async def main():
    async with engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        await conn.run_sync(Base.metadata.create_all)
    print("tables created:", ", ".join(Base.metadata.tables))


if __name__ == "__main__":
    asyncio.run(main())
