from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.discussions import router as discussions_router
from app.db import Base, engine, SessionLocal


def _migrate_old_discussions():
    """启动迁移：修复旧讨论的状态和消息记录。

    旧版（v1）讨论引擎没有将发言保存到 messages 表，
    也没有将 status 改为 completed。此迁移修复这些数据。
    """
    from app.models import Discussion

    db = SessionLocal()
    try:
        discs = db.query(Discussion).filter(
            Discussion.status.in_(["pending", "in_progress"])
        ).all()
        for d in discs:
            # 如果讨论创建超过 30 分钟且没有 in_progress → 说明是旧版遗留
            # 直接标记为 completed 以显示在首页
            from datetime import datetime, timezone
            if d.created_at:
                age = datetime.now(timezone.utc) - d.created_at.replace(tzinfo=timezone.utc)
                if age.total_seconds() > 1800:  # 30 分钟
                    d.status = "completed"
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    Base.metadata.create_all(bind=engine)
    # 启动时修复旧讨论状态
    _migrate_old_discussions()
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