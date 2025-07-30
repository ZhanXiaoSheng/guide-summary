from pydantic_settings import BaseSettings
from pathlib import Path
import os

class Settings(BaseSettings):
    APP_NAME: str = "Guide Summary Generator"
    API_PREFIX: str = "/api/v1"
    
    # 大模型配置
    API_KEY: str
    BASE_URL: str = "https://api.deepseek.com"
    LLM_MODEL: str = "deepseek-chat"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 500
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = 'forbid'  # 禁止额外字段

# 添加调试信息
print(f"当前工作目录: {os.getcwd()}")
print(f"环境配置目录: {Path('.env').absolute()}")

settings = Settings()
print(f"加载 API_KEY: {settings.API_KEY}")  # 确认是否加载成功