from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.database import engine
from sqlmodel import SQLModel
from app.db import models
from app.routers import tasks
from app.services.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        print("正在检查并创建数据表...")
        await conn.run_sync(SQLModel.metadata.create_all)
    
    # 启动定时任务
    start_scheduler()

    yield
    # --- 关闭时 (如果有清理工作写在这里) ---

app = FastAPI(title="Tempo AI Backend", lifespan=lifespan)

app.include_router(tasks.router)

@app.get("/")
async def root():
    return {"msg": "Tempo Backend is Running on PostgreSQL"}