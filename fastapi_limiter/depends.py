from typing import Annotated, Callable, Optional
from pathlib import Path

import redis as pyredis
from pydantic import Field
from starlette.requests import Request

from fastapi_limiter import FastAPILimiter
from definitions import REDIS_SCRIPTS_PATH


class BaseRateLimiter:
    lua_script: str = ""
    lua_sha: str = ""

    def __init__(
            self,
            identifier: Optional[Callable] = None,
            callback: Optional[Callable] = None
    ):
        self.identifier = identifier
        self.callback = callback

    async def _check(self, key: str) -> int:
        pass

    @classmethod
    async def _update_lua_sha(cls):
        cls.lua_sha = await FastAPILimiter.redis.script_load(cls.lua_script)

    async def __call__(self, request: Request):
        if not FastAPILimiter.redis:
            raise Exception("You must call FastAPILimiter.init in startup event of fastapi!")

        identifier = self.identifier or FastAPILimiter.identifier
        callback = self.callback or FastAPILimiter.callback
        rate_key = await identifier(request)
        context_key = id(self)
        key = f"{FastAPILimiter.prefix}:{rate_key}:{context_key}"
        try:
            pexpire = await self._check(key)
        except pyredis.exceptions.NoScriptError:
            await self._update_lua_sha()
            pexpire = await self._check(key)
        if pexpire > 0:
            return await callback(request, pexpire)


class FixedWindowRateLimiter(BaseRateLimiter):
    lua_script = Path(REDIS_SCRIPTS_PATH, 'fixed_window.lua').read_text()

    def __init__(
            self,
            times: Annotated[int, Field(ge=0)] = 1,
            milliseconds: Annotated[int, Field(ge=-1)] = 0,
            seconds: Annotated[int, Field(ge=-1)] = 0,
            minutes: Annotated[int, Field(ge=-1)] = 0,
            hours: Annotated[int, Field(ge=-1)] = 0,
            identifier: Optional[Callable] = None,
            callback: Optional[Callable] = None
    ):
        super().__init__(
            identifier,
            callback
        )
        self.times = times
        self.milliseconds = milliseconds + 1000 * seconds + 60000 * minutes + 3600000 * hours

    async def _check(self, key: str) -> int:
        return await FastAPILimiter.redis.evalsha(self.lua_sha, 1, key, str(self.times), str(self.milliseconds))


class TokenBucketRateLimiter(BaseRateLimiter):
    lua_script = Path(REDIS_SCRIPTS_PATH, 'token_bucket.lua').read_text()

    def __init__(
            self,
            capacity: Annotated[int, Field(ge=1)] = 1,
            refill_rate: Annotated[int, Field(ge=1)] = 1,
            identifier: Optional[Callable] = None,
            callback: Optional[Callable] = None
    ):
        super().__init__(
            identifier,
            callback
        )
        self.capacity = capacity
        self.refill_rate = refill_rate

    async def _check(self, key: str) -> int:
        return await FastAPILimiter.redis.evalsha(self.lua_sha, 1, key, str(self.capacity), str(self.refill_rate))
