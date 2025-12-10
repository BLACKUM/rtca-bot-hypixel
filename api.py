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


async def get_bazaar_prices():
    cached = cache_get("bazaar_prices")
    if cached:
        return cached
    
    url = "https://api.hypixel.net/skyblock/bazaar"
    log_debug("Fetching Bazaar prices")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    log_error(f"Bazaar request failed ({r.status})")
                    return {}
                data = await r.json()
                products = data.get("products", {})
                prices = {
                    pid: info["quick_status"]["sellPrice"] 
                    for pid, info in products.items()
                }
                cache_set("bazaar_prices", prices)
                return prices
        except Exception as e:
            log_error(f"Failed to fetch Bazaar prices: {e}")
            return {}


async def get_ah_prices():
    cached = cache_get("ah_prices")
    if cached:
        return cached
        
    url = "https://moulberry.codes/auction_averages_lbin/3day.json"
    log_debug("Fetching AH prices (3-day avg)")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    log_error(f"AH request failed ({r.status})")
                    return {}
                prices = await r.json()
                cache_set("ah_prices", prices)
                return prices
        except Exception as e:
            log_error(f"Failed to fetch AH prices: {e}")
            return {}


async def get_all_prices():
    bz_future = get_bazaar_prices()
    ah_future = get_ah_prices()
    
    bz_prices, ah_prices = await asyncio.gather(bz_future, ah_future)
    
    prices = bz_prices.copy()
    prices.update(ah_prices)
    return prices

