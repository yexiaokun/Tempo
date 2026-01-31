from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.database import engine, async_session
from sqlmodel import SQLModel, select, text
from app.db import models
from app.routers import tasks, auth
from app.services.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        print("🚀 [Init] Checking database tables...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(SQLModel.metadata.create_all)
    
    #初始化默认用户
    async with async_session() as session:
        statement = select(models.User).where(models.User.username == "demo_user")
        result = await session.exec(statement)
        user = result.first()

        if not user:
            print("👤 [Init] Creating default demo user...")
            default_user = models.User(
                username="demo_user",
                email="demo@example.com",
                hashed_password="fake_hash_secret",
                default_city="Shanghai"
            )
            session.add(default_user)
            await session.commit()
        else:
            print("✅ [Init] Default user already exists.")
    # 启动定时任务
    start_scheduler()

    yield
    # --- 关闭时 (如果有清理工作写在这里) ---

app = FastAPI(title="Tempo AI Backend", lifespan=lifespan)

app.include_router(tasks.router)
app.include_router(auth.router)

@app.get("/")
async def root():
    return {"msg": "Tempo Backend is Running on PostgreSQL"}