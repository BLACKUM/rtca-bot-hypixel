import time
import os
import asyncio
import aiofiles
from core.logger import log_info, log_error

try:
    import orjson as json_backend
    _USE_ORJSON = True
except ImportError:
    import json as json_backend
    _USE_ORJSON = False

CACHE_FILE = "data/cache.json"
_DATA_CACHE = {}
_DIRTY = False
_SAVE_INTERVAL_SECONDS = 30
MAX_CACHE_SIZE = 10000


def _serialize(data) -> bytes:
    if _USE_ORJSON:
        return json_backend.dumps(data)
    return json_backend.dumps(data).encode("utf-8")


def _deserialize(content: bytes) -> dict:
    if _USE_ORJSON:
        return json_backend.loads(content)
    return json_backend.loads(content.decode("utf-8"))


async def initialize():
    await _load_cache()
    asyncio.get_event_loop().create_task(_periodic_save_loop())


async def _load_cache():
    global _DATA_CACHE
    if not os.path.exists(CACHE_FILE):
        return
    try:
        async with aiofiles.open(CACHE_FILE, "rb") as f:
            content = await f.read()
            data = _deserialize(content)
            if isinstance(data, dict):
                _DATA_CACHE = data
                log_info(f"Loaded {len(_DATA_CACHE)} entries from cache.")
    except Exception as e:
        log_error(f"Failed to load cache: {e}")


async def _save_cache():
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        temp_path = CACHE_FILE + ".tmp"
        async with aiofiles.open(temp_path, "wb") as f:
            await f.write(_serialize(_DATA_CACHE))
        os.replace(temp_path, CACHE_FILE)
    except Exception as e:
        log_error(f"Failed to save cache: {e}")


async def _periodic_save_loop():
    global _DIRTY
    while True:
        await asyncio.sleep(_SAVE_INTERVAL_SECONDS)
        if _DIRTY:
            await _save_cache()
            _DIRTY = False


async def shutdown():
    if _DIRTY:
        await _save_cache()


async def cache_get(key: str):
    entry = _DATA_CACHE.get(key)
    if not entry:
        return None
    expiry, data = entry[0], entry[1]
    if time.time() > expiry:
        global _DIRTY
        del _DATA_CACHE[key]
        _DIRTY = True
        return None
    return data


async def _cleanup_cache():
    import heapq
    global _DIRTY
    now = time.time()
    expired_keys = [k for k, v in _DATA_CACHE.items() if now > v[0]]
    for k in expired_keys:
        del _DATA_CACHE[k]
    if len(_DATA_CACHE) >= MAX_CACHE_SIZE:
        overcount = len(_DATA_CACHE) - MAX_CACHE_SIZE + (MAX_CACHE_SIZE // 10)
        oldest = heapq.nsmallest(overcount, _DATA_CACHE.items(), key=lambda item: item[1][0])
        for k, _ in oldest:
            del _DATA_CACHE[k]
    _DIRTY = True


async def cache_set(key: str, data, ttl: int = 60):
    global _DIRTY
    if len(_DATA_CACHE) >= MAX_CACHE_SIZE:
        await _cleanup_cache()
    expiry = time.time() + ttl
    _DATA_CACHE[key] = (expiry, data)
    _DIRTY = True


def get_cache_expiry(key: str):
    entry = _DATA_CACHE.get(key)
    if not entry:
        return None
    expiry, _ = entry
    return expiry
