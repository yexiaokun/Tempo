from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.database import engine, async_session
from sqlmodel import SQLModel, select, text
from app.db import models
from app.routers import tasks, auth


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

    yield
    # --- 关闭时 (如果有清理工作写在这里) ---

app = FastAPI(title="Tempo AI Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许所有来源，上线时可改为 ["http://localhost:5500"]
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法 (GET, POST, PATCH...)
    allow_headers=["*"],  # 允许所有 Header
)

app.include_router(tasks.router)
app.include_router(auth.router)

@app.get("/")
async def root():
    return {"msg": "Tempo Backend is Running on PostgreSQL"}


#全局异常捕获
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"❌ 全局错误捕获: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "服务器开了点小差，请稍后重试", "detail": str(exc)}
    )