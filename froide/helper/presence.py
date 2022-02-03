import time
from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from channels.db import database_sync_to_async

try:
    import aioredis
except ImportError:
    aioredis = None

User = get_user_model()

MAX_AGE_SECONDS = 60
MAX_AGE = timedelta(seconds=MAX_AGE_SECONDS)


class RedisContext:
    async def __aenter__(self):
        self.redis = await aioredis.create_redis(settings.REDIS_URL)
        return self.redis

    async def __aexit__(self, exc_type, exc, tb):
        self.redis.close()
        await self.redis.wait_closed()


def get_presence_manager(room):
    if aioredis is None or not getattr(settings, "REDIS_URL", None):
        return DummyUserPresenceManager(room)
    return RedisUserPresenceManager(room)


def get_expiring_keys_manager(prefix, timeout=10 * 60):
    if aioredis is None or not getattr(settings, "REDIS_URL", None):
        return DummyExpiringKeysManager(prefix, timeout=timeout)
    return RedisExpiringKeysManager(prefix, timeout=timeout)


class BaseUserPresenceManager:
    def __init__(self, room):
        self.room = room

    async def touch(self, user):
        raise NotImplementedError

    async def list_present(self):
        raise NotImplementedError

    async def is_present(self, user):
        raise NotImplementedError

    async def remove(self, user):
        raise NotImplementedError

    async def expire(self):
        raise NotImplementedError


class DummyUserPresenceManager(BaseUserPresenceManager):
    presence = defaultdict(dict)

    def __init__(self, room):
        super().__init__(room)

    async def touch(self, user):
        self.presence[self.room][user.id] = timezone.now()

    def _list_present_user_ids(self):
        self._expire()
        now = timezone.now()
        for user_id, timestamp in self.presence[self.room].items():
            if timestamp + MAX_AGE >= now:
                yield user_id

    def _list_present_users(self):
        return list(User.objects.filter(id__in=self._list_present_user_ids()))

    async def list_present(self):
        return await database_sync_to_async(self._list_present_users)()

    async def is_present(self, user):
        return user.id in self.presence[self.room]

    async def remove(self, user):
        if self.room in self.presence:
            if user.id in self.presence[self.room]:
                del self.presence[self.room][user.id]

    def _expire(self):
        now = timezone.now()
        self.presence[self.room] = {
            uid: timestamp
            for uid, timestamp in self.presence[self.room].items()
            if timestamp + MAX_AGE >= now
        }

    async def expire(self):
        self._expire()


class RedisUserPresenceManager(BaseUserPresenceManager):
    @property
    def key(self):
        return "froide_presence_{}".format(self.room)

    # Wait for Python 3.8
    # @asynccontextmanager
    # async def get_redis(self):
    #     redis = await aioredis.create_redis(settings.REDIS_URL)
    #     yield redis
    #     await redis.wait_closed()

    get_redis = RedisContext

    def get_time(self):
        return int(time.time())

    def _is_expired(self, score):
        return self.get_time() - int(score) > MAX_AGE_SECONDS

    async def touch(self, user):
        async with self.get_redis() as redis:
            await redis.zadd(self.key, self.get_time(), user.id)

    async def _list_present_user_ids(self):
        async with self.get_redis() as redis:
            has_expired = False
            async for user_id, score in redis.izscan(self.key):
                if self._is_expired(score):
                    has_expired = True
                    continue
                yield user_id
            if has_expired:
                await self._expire(redis)

    def _list_present_users(self, user_ids):
        return list(User.objects.filter(id__in=user_ids))

    async def list_present(self):
        user_ids = [x async for x in self._list_present_user_ids()]
        return await database_sync_to_async(self._list_present_users)(user_ids)

    async def is_present(self, user):
        async with self.get_redis() as redis:
            score = await redis.zscore(self.key, user.id)
        if score is None:
            return False
        is_expired = self._is_expired(score)
        if is_expired:
            await self._remove(user)
        return True

    async def _remove(self, redis, user):
        await redis.zrem(self.key, user.id)

    async def remove(self, user):
        async with self.get_redis() as redis:
            await self._remove(redis, user)

    async def _expire(self, redis):
        max_val = self.get_time() - MAX_AGE_SECONDS
        await redis.zremrangebyscore(self.key, max=max_val)

    async def expire(self):
        async with self.get_redis() as redis:
            await self._expire(redis)


class BaseExpiringKeysManager:
    def __init__(self, prefix, timeout=8 * 60):
        self.prefix = prefix
        self.timeout = timedelta(seconds=timeout)

    async def add_key_value(self, key, value):
        raise NotImplementedError

    async def list_key_value(self):
        raise NotImplementedError

    async def remove_key_value(self, key):
        raise NotImplementedError


class DummyExpiringKeysManager(BaseExpiringKeysManager):
    keys = defaultdict(dict)

    async def add_key_value(self, key, value):
        self.keys[self.prefix][key] = (timezone.now(), value)

    async def list_key_value(self):
        self._expire()
        for key, (_, value) in self.keys[self.prefix].items():
            yield key, value

    async def remove_key_value(self, key, value):
        try:
            if self.keys[self.prefix][key] == value:
                del self.keys[self.prefix][key]
        except KeyError:
            pass

    async def remove_key(self, key):
        try:
            del self.keys[self.prefix][key]
        except KeyError:
            pass

    def _expire(self):
        now = timezone.now()
        self.keys[self.prefix] = {
            key: (timestamp, value)
            for key, (timestamp, value) in self.keys[self.prefix].items()
            if timestamp + self.timeout >= now
        }


class RedisExpiringKeysManager(BaseExpiringKeysManager):
    """
    Stores key/value as expiring redis keys
    """

    KEY_PREFIX = "froide_expkeys_"
    SEPERATOR = "::"

    def make_prefix(self):
        return "{}_{}".format(self.KEY_PREFIX, self.prefix)

    def _make_redis_key(self, key):
        return "{prefix}{sep}{key}".format(
            prefix=self.make_prefix(), sep=self.SEPERATOR, key=key
        )

    def split_key(self, redis_key):
        return redis_key.split(self.SEPERATOR)[-1]

    get_redis = RedisContext

    async def add_key_value(self, key, value):
        redis_key = self._make_redis_key(key)
        async with self.get_redis() as redis:
            await redis.set(redis_key, value, expire=self.timeout.seconds)

    async def list_key_value(self):
        async with self.get_redis() as redis:
            async for redis_key in redis.iscan(match="{}*".format(self.make_prefix())):
                key = self.split_key(redis_key.decode("utf-8"))
                value = await redis.get(redis_key, encoding="utf-8")
                yield key, value

    async def remove_key_value(self, key, value):
        redis_key = self._make_redis_key(key)
        async with self.get_redis() as redis:
            redis_value = await redis.get(redis_key, encoding="utf-8")
            if redis_value == value:
                await redis.delete(redis_key)

    async def remove_key(self, key):
        redis_key = self._make_redis_key(key)
        async with self.get_redis() as redis:
            await redis.delete(redis_key)
