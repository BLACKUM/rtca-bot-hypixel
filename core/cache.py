import time
import json
import os
import aiofiles
import asyncio
from core.logger import log_info, log_error

CACHE_FILE = "data/cache.json"
_DATA_CACHE = {}

async def initialize():
    await _load_cache()

async def _load_cache():
    global _DATA_CACHE
    if not os.path.exists(CACHE_FILE):
        return
    try:
        async with aiofiles.open(CACHE_FILE, 'r', encoding='utf-8') as f:
            content = await f.read()
            data = json.loads(content)
            if isinstance(data, dict):
                _DATA_CACHE = data
                log_info(f"Loaded {len(_DATA_CACHE)} entries from cache file.")
    except Exception as e:
        log_error(f"Failed to load cache: {e}")

async def _save_cache():
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        async with aiofiles.open(CACHE_FILE, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(_DATA_CACHE))
    except Exception as e:
        log_error(f"Failed to save cache: {e}")

async def cache_get(key: str):
    entry = _DATA_CACHE.get(key)
    if not entry:
        return None
    
    expiry = entry[0]
    data = entry[1]
    
    if time.time() > expiry:
        del _DATA_CACHE[key]
        await _save_cache()
        return None
    return data


MAX_CACHE_SIZE = 10000

async def _cleanup_cache():
    now = time.time()
    expired_keys = [k for k, v in _DATA_CACHE.items() if now > v[0]]
    for k in expired_keys:
        del _DATA_CACHE[k]
    
    if len(_DATA_CACHE) >= MAX_CACHE_SIZE:
        sorted_cache = sorted(_DATA_CACHE.items(), key=lambda item: item[1][0])
        to_remove = len(_DATA_CACHE) - MAX_CACHE_SIZE + 1
        for i in range(to_remove):
            del _DATA_CACHE[sorted_cache[i][0]]
            
    await _save_cache()

async def cache_set(key: str, data, ttl: int = 60):
    if len(_DATA_CACHE) >= MAX_CACHE_SIZE:
        await _cleanup_cache()
    
    expiry = time.time() + ttl
    _DATA_CACHE[key] = (expiry, data)
    await _save_cache()

def get_cache_expiry(key: str):
    entry = _DATA_CACHE.get(key)
    if not entry:
        return None
    expiry, _ = entry
    return expiry
