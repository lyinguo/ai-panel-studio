from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.discussions import router as discussions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    yield


app = FastAPI(title="AI Panel Studio", lifespan=lifespan)

# 注册路由
app.include_router(discussions_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}