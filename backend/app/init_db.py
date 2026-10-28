"""建表脚本：python -m app.init_db"""
import asyncio

from sqlalchemy import text

from app.core.database import engine
from app.models.entities import Base


async def main():
    async with engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        await conn.run_sync(Base.metadata.create_all)
    # 开发期播种用户 id=1（JWT 登录上线后移除）
    from sqlalchemy import insert
    from app.core.database import SessionLocal
    from app.models.entities import User
    async with SessionLocal() as s:
        exists = (await s.execute(text("SELECT 1 FROM users WHERE id=1"))).scalar()
        if not exists:
            s.add(User(id=1, email="dev@local", password_hash="dev"))
            await s.commit()
            print("seeded dev user id=1")
    print("tables created:", ", ".join(Base.metadata.tables))


if __name__ == "__main__":
    asyncio.run(main())
