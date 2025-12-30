from pydantic_settings import BaseSettings
from functools import lru_cache
from fastapi import Depends
from typing_extensions import Annotated


class Settings(BaseSettings):
    redis_dsn: str = "redis://localhost:6379/0"
    l1_maxsize: int = 2048
    l1_ttl_seconds: int = 60  # default L1 TTL
    l2_ttl_seconds: int = 300  # default Redis TTL
    cache_namespace: str = "appcache:"
    redis_pool_size: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
