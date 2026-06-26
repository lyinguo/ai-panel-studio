from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.discussions import router as discussions_router
from app.db import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    # 启动时自动创建所有数据库表
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="AI Panel Studio", lifespan=lifespan)

# CORS — 允许前端开发服务器跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(discussions_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}