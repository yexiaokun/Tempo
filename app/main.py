from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.database import engine
from sqlmodel import SQLModel
from app.db import models


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        print("正在检查并创建数据表...")
        await conn.run_sync(SQLModel.metadata.create_all)
    yield

app = FastAPI(title="Tempo AI Backend", lifespan=lifespan)

@app.get("/")
async def root():
    return {"msg": "Tempo Backend is Running on PostgreSQL"}