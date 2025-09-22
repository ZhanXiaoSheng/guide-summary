from loguru import logger
import sys
from pathlib import Path
from config.settings import settings

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

"""
loguru的logger是一个全局单例
在任何一个模块中配置的handler和格式都会影响所有地方导入的logger
只需要在一个地方（如logging_conf.py）配置一次，所有模块都会生效
"""

# 移除默认配置
logger.remove()

# 定义loguru格式
loguru_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
log_format = settings.LOG_FORMAT or loguru_format
# 添加控制台输出
logger.add(
    sys.stdout,
    format=log_format,  # 使用log_format
    level=settings.LOG_LEVEL,
    enqueue=True,
    colorize=True,
)

# 添加文件输出 - 使用延迟初始化避免启动错误


def setup_file_logging():
    try:
        logger.add(
            LOG_DIR / "guide-summary.log",
            rotation="1 MB",
            retention="30 days",
            format=log_format,
            level=settings.LOG_LEVEL,
            encoding="utf-8",
            enqueue=True,
            catch=True,
        )
        logger.info("文件日志初始化成功")
    except Exception as e:
        logger.error(f"文件日志初始化失败: {e}")
        # 回退到只有控制台输出


# 在应用启动后调用
setup_file_logging()

# 可选：处理uvicorn日志

# def filter_uvicorn(record):
#     return "uvicorn" not in record["name"]


# logger.add(
#     LOG_DIR / "app.log",
#     rotation="10 MB",
#     retention="30 days",
#     format=loguru_format,
#     level=settings.LOG_LEVEL,
#     encoding="utf-8",
#     enqueue=True,
#     filter=filter_uvicorn  # 过滤掉uvicorn的日志
# )
