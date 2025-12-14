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


MAX_CACHE_SIZE = 10000

def _cleanup_cache():
    now = time.time()
    expired_keys = [k for k, v in _DATA_CACHE.items() if now > v[0]]
    for k in expired_keys:
        del _DATA_CACHE[k]
    
    if len(_DATA_CACHE) >= MAX_CACHE_SIZE:
        sorted_cache = sorted(_DATA_CACHE.items(), key=lambda item: item[1][0])
        to_remove = len(_DATA_CACHE) - MAX_CACHE_SIZE + 1
        for i in range(to_remove):
            del _DATA_CACHE[sorted_cache[i][0]]


def cache_set(key: str, data, ttl: int = 60):
    if len(_DATA_CACHE) >= MAX_CACHE_SIZE:
        _cleanup_cache()
    
    expiry = time.time() + ttl
    _DATA_CACHE[key] = (expiry, data)


def get_cache_expiry(key: str):
    entry = _DATA_CACHE.get(key)
    if not entry:
        return None
    expiry, _ = entry
    return expiry
