from math import ceil
from typing import Callable, Optional

from fastapi import HTTPException
from starlette.requests import Request
from starlette.status import HTTP_429_TOO_MANY_REQUESTS


async def default_identifier(request: Request):
    forwarded = request.headers.get("X-Forwarded-For")
    ip = forwarded.split(",")[0] if forwarded else request.client.host
    return ip


async def default_callback(request: Request, pexpire: int):
    """
    default callback when too many requests
    :param request:
    :param pexpire: The remaining milliseconds
    :return:
    """
    expire = ceil(pexpire / 1000)
    raise HTTPException(
        HTTP_429_TOO_MANY_REQUESTS, "Too Many Requests", headers={"Retry-After": str(expire)}
    )


class FastAPILimiter:
    redis = None
    prefix: Optional[str] = None
    identifier: Optional[Callable] = None
    callback: Optional[Callable] = None

    @classmethod
    async def init(
        cls,
        redis,
        prefix: str = "fastapi-limiter",
        identifier: Callable = default_identifier,
        callback: Callable = default_callback,
    ) -> None:
        cls.redis = redis
        cls.prefix = prefix
        cls.identifier = identifier
        cls.callback = callback

    @classmethod
    async def close(cls) -> None:
        await cls.redis.close()
