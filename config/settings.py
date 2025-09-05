from decouple import config, Csv


class Settings:
    # 应用配置
    APP_NAME = config('APP_NAME', default='Guide Summary Generator')
    API_PREFIX = config('API_PREFIX', default='/api/v1')

    # 大模型配置
    API_KEY = config('API_KEY', default='')
    BASE_URL = config('BASE_URL', default='https://api.deepseek.com')
    LLM_MODEL = config('LLM_MODEL', default='deepseek-chat')
    LLM_TEMPERATURE = config('LLM_TEMPERATURE', default=0.3, cast=float)
    LLM_MAX_TOKENS = config('LLM_MAX_TOKENS', default=500, cast=int)

    # 日志配置
    LOG_LEVEL = config('LOG_LEVEL', default='INFO')
    LOG_FORMAT = config(
        'LOG_FORMAT', default='{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{line} - {message}')

    # 百度全景图配置
    PANORAMA_API_URL = config(
        'PANORAMA_API_URL', default='https://api.map.baidu.com/panorama/v2')
    PANORAMA_API_KEY = config('PANORAMA_API_KEY', default='')

    # 动态获取任何配置
    @staticmethod
    def get(key: str, default=None, cast=None):
        return config(key, default=default, cast=cast)


settings = Settings()
