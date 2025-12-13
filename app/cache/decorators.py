from functools import wraps
from typing import Callable
from app.cache.layer import cache_layer


def async_cached(key_builder: Callable[..., str], l2_ttl: int = None):
    """
    Decorator for async functions. key_builder receives same args/kwargs.
    Example:
      @async_cached(lambda task_id, **kw: f"Task:{task_id}")
      async def get_task(user_id): ...
    """

    def decorator(fn: Callable):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            key = key_builder(*args, **kwargs)

            # loader closure calls the original function
            async def loader():
                value = await fn(*args, **kwargs)
                if value is None:
                    return None
                if hasattr(value, "model_dump"):
                    return value.model_dump()
                return value

            return await cache_layer.get(key, loader=loader, l2_ttl=l2_ttl)

        return wrapper

    return decorator
