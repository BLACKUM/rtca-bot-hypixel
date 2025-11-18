import aiohttp
import asyncio
from utils.logging import log_debug, log_error
from cache import cache_get, cache_set


async def get_uuid(name: str):
    log_debug(f"Requesting UUID for {name}")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://playerdb.co/api/player/minecraft/{name}") as r:
            if r.status != 200:
                log_error(f"UUID request failed ({r.status})")
                return None
            data = await r.json()
            uuid = data["data"]["player"]["raw_id"]
            log_debug(f"UUID fetched: {uuid}")
            return uuid


async def get_profile_data(uuid: str):
    cached = cache_get(uuid)
    if cached:
        log_debug(f"Using cached data for {uuid}")
        return cached
    url = f"https://adjectilsbackend.adjectivenoun3215.workers.dev/v2/skyblock/profiles?uuid={uuid}"
    log_debug(f"Requesting profile data: {url}")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status != 200:
                    log_error(f"Profile request failed ({r.status})")
                    return None
                data = await r.json()
                cache_set(uuid, data)
                return data
        except asyncio.TimeoutError:
            log_error("Profile request timed out (15s)")
            return None
