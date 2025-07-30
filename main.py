import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from config.settings import settings
from config.logging_conf import logger
from routers.summary import router as summary_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时运行
    logger.info("开始启动指引总结生成器")
    yield
    # 关闭时运行
    logger.info("关闭指引总结生成器")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    lifespan=lifespan  # 使用新的生命周期处理
)

app.include_router(summary_router, prefix=settings.API_PREFIX)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)