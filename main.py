from contextlib import asynccontextmanager
from fastapi import FastAPI
from config.settings import settings
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("开始启动指引总结生成器")
    yield
    logger.info("关闭指引总结生成器")


def create_app() -> FastAPI:

    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
        lifespan=lifespan,
        redirect_slashes=False  # 关闭自动重定向
    )

    # summary 路由
    from routers.summary import router as summary_router
    app.include_router(summary_router, prefix=settings.API_PREFIX)

    # panorama 路由
    from routers.panorama import router as panorama_router
    app.include_router(panorama_router, prefix=settings.API_PREFIX)

    # 路由列表
    @app.get(f"{settings.API_PREFIX}/routes")
    async def list_all_routes():
        routes = []
        for route in app.routes:
            if hasattr(route, "methods") and hasattr(route, "path"):
                routes.append({
                    "path": route.path,
                    "methods": sorted(list(route.methods)),
                    "name": getattr(route, "name", "N/A")
                })
        return {"routes": routes}

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app


# 供 uvicorn main:app 使用
app = create_app()

if __name__ == "__main__":
    import uvicorn
    # logger.info("=== 通过 python main.py 启动 ===")
    # 用 "main:app" 形式配合 --reload 更稳（热重载子进程也会正确 import）
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
