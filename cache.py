import time

_DATA_CACHE = {}


def cache_get(key: str):
    entry = _DATA_CACHE.get(key)
    if not entry:
        return None
    expiry, data = entry
    if time.time() > expiry:
        del _DATA_CACHE[key]
        return None
    return data


def cache_set(key: str, data, ttl: int = 60):
    expiry = time.time() + ttl
    _DATA_CACHE[key] = (expiry, data)


def get_cache_expiry(key: str):
    entry = _DATA_CACHE.get(key)
    if not entry:
        return None
    expiry, _ = entry
    return expiry
