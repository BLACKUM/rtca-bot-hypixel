import time
from config import CACHE_TTL

_PROFILE_CACHE = {}


def cache_get(uuid: str):
    entry = _PROFILE_CACHE.get(uuid)
    if not entry:
        return None
    ts, data = entry
    if time.time() - ts > CACHE_TTL:
        del _PROFILE_CACHE[uuid]
        return None
    return data


def cache_set(uuid: str, data):
    _PROFILE_CACHE[uuid] = (time.time(), data)
