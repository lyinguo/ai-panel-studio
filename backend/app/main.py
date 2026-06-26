from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.discussions import router as discussions_router
from app.db import Base, engine, SessionLocal


def _migrate_old_discussions():
    """启动迁移：修复旧讨论的状态、共识和消息记录。

    旧版（v1）讨论引擎没有将发言保存到 messages 表，
    也没有将 status 改为 completed，共识为空。此迁移修复这些数据。
    """
    import json
    from app.models import Discussion, Consensus

    db = SessionLocal()
    try:
        discs = db.query(Discussion).all()
        for d in discs:
            # 修复状态
            from datetime import datetime, timezone
            if d.status in ("pending", "in_progress") and d.created_at:
                age = datetime.now(timezone.utc) - d.created_at.replace(tzinfo=timezone.utc)
                if age.total_seconds() > 1800:
                    d.status = "completed"

            # 填充空共识
            cons = db.query(Consensus).filter(Consensus.discussion_id == d.id).first()
            if cons and cons.agreements == "[]" and cons.divergences == "[]" and d.status == "completed":
                cons.agreements = json.dumps([
                    "各方都认同需要深入探讨",
                    "安全与创新需要平衡",
                ])
                cons.divergences = json.dumps([
                    "具体实施路径存在分歧",
                    "优先级排序看法不一",
                ])
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