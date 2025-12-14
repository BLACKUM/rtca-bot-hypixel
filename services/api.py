import aiohttp
import asyncio
from urllib.parse import quote
from core.config import PROFILE_CACHE_TTL, PRICES_CACHE_TTL, SKELETON_MASTER_CHESTPLATE_50
from core.logger import log_debug, log_error, log_info
from core.cache import cache_get, cache_set, get_cache_expiry


# cloudflare bypass, i hate i even have to do this
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.2; WOW64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


async def get_uuid(name: str):
    cached = cache_get(name.lower())
    if cached:
        log_debug(f"Using cached UUID for {name}")
        return cached

    log_debug(f"Requesting UUID for {name}")
    async with aiohttp.ClientSession() as session:
        if not name.replace("_", "").isalnum():
            log_error(f"Invalid name format: {name}")
            return None
            
        msg = quote(name)
        async with session.get(f"https://playerdb.co/api/player/minecraft/{msg}", headers=HEADERS) as r:
            if r.status != 200:
                log_error(f"UUID request failed ({r.status})")
                return None
            data = await r.json()
            uuid = data["data"]["player"]["raw_id"]
            log_debug(f"UUID fetched: {uuid}")
            cache_set(name.lower(), uuid, ttl=PROFILE_CACHE_TTL)
            return uuid


async def get_profile_data(uuid: str):
    cached = cache_get(uuid)
    if cached:
        log_debug(f"Using cached data for {uuid}")
        return cached
    if not uuid or len(uuid) != 32 or not all(c in '0123456789abcdefABCDEF' for c in uuid):
        log_error(f"Invalid UUID format: {uuid}")
        return None
        
    url = f"https://adjectilsbackend.adjectivenoun3215.workers.dev/v2/skyblock/profiles?uuid={uuid}"
    log_debug(f"Requesting profile data: {url}")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status != 200:
                    try:
                        text = await r.text()
                        log_error(f"Profile request failed ({r.status}): {text[:200]}")
                    except:
                        log_error(f"Profile request failed ({r.status})")
                    return None
                data = await r.json()
                cache_set(uuid, data, ttl=PROFILE_CACHE_TTL)
                return data
        except asyncio.TimeoutError:
            log_error("Profile request timed out (15s)")
            return None


async def get_bazaar_prices():
    cached = cache_get("bazaar_prices")
    if cached is not None:
        return cached
    
    url = "https://api.hypixel.net/skyblock/bazaar"
    log_debug("Fetching Bazaar prices")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    try:
                        text = await r.text()
                        log_error(f"Bazaar request failed ({r.status}): {text[:200]}")
                    except:
                        log_error(f"Bazaar request failed ({r.status})")
                    cache_set("bazaar_prices", {}, ttl=PRICES_CACHE_TTL)
                    return {}
                data = await r.json()
                products = data.get("products", {})
                prices = {
                    pid: info["quick_status"]["sellPrice"] 
                    for pid, info in products.items()
                }
                cache_set("bazaar_prices", prices, ttl=PRICES_CACHE_TTL)
                return prices
        except Exception as e:
            log_error(f"Failed to fetch Bazaar prices: {e}")
            cache_set("bazaar_prices", {}, ttl=PRICES_CACHE_TTL)
            return {}


async def get_ah_prices():
    cached = cache_get("ah_prices")
    if cached is not None:
        return cached
        
    url = "https://moulberry.codes/auction_averages_lbin/3day.json"
    log_debug("Fetching AH prices (3-day avg)")
    
    async with aiohttp.ClientSession() as session:
        log_debug(f"Requesting AH prices: {url}")
        try:
            async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    try:
                        text = await r.text()
                        log_error(f"AH request failed ({r.status}): {text[:200]}")
                    except:
                        log_error(f"AH request failed ({r.status})")
                    cache_set("ah_prices", {}, ttl=PRICES_CACHE_TTL)
                    return {}
                prices = await r.json()
                cache_set("ah_prices", prices, ttl=PRICES_CACHE_TTL)
                return prices
        except Exception as e:
            log_error(f"Failed to fetch AH prices: {e}")
            cache_set("ah_prices", {}, ttl=PRICES_CACHE_TTL)
            return {}

async def get_all_prices():
    bz_future = get_bazaar_prices()
    ah_future = get_ah_prices()
    
    bz_prices, ah_prices = await asyncio.gather(bz_future, ah_future)
    
    prices = bz_prices.copy()
    prices.update(ah_prices)
    
    # Yeah i really cba to make another price checker just for this thing
    prices[SKELETON_MASTER_CHESTPLATE_50] = 40_000_000
    
    return prices


def get_prices_expiry():
    return get_cache_expiry("ah_prices")


async def get_dungeon_runs(uuid: str):
    profile_data = await get_profile_data(uuid)
    if not profile_data:
        return {}
    
    profiles = profile_data.get("profiles")
    if not profiles:
        return {}
    
    best_profile = next((p for p in profiles if p.get("selected")), profiles[0])
    member = best_profile.get("members", {}).get(uuid, {})
    dungeons = member.get("dungeons", {})
    
    catacombs_data = dungeons.get("dungeon_types", {}).get("catacombs", {})
    master_catacombs_data = dungeons.get("dungeon_types", {}).get("master_catacombs", {})
    
    master_completions = master_catacombs_data.get("tier_completions", {})
    normal_completions = catacombs_data.get("tier_completions", {})
    
    log_debug(f"Master completions: {master_completions}")

    tier_to_floor = {
        '1': "Floor 1 (Bonzo)",
        '2': "Floor 2 (Scarf)",
        '3': "Floor 3 (Professor)",
        '4': "Floor 4 (Thorn)",
        '5': "Floor 5 (Livid)",
        '6': "Floor 6 (Sadan)",
        '7': "Floor 7 (Necron)",
    }
    
    run_counts = {}
    for tier_key, floor_name in tier_to_floor.items():
        master_runs = int(master_completions.get(tier_key, 0))
        normal_runs = int(normal_completions.get(tier_key, 0))
        run_counts[floor_name] = {
            "normal": normal_runs,
            "master": master_runs
        }
    
    log_debug(f"Fetched run counts for {uuid}: {run_counts}")
    return run_counts


async def get_dungeon_xp(uuid: str):
    profile_data = await get_profile_data(uuid)
    if not profile_data:
        return None
    
    profiles = profile_data.get("profiles")
    if not profiles:
        return None
    
    best_profile = next((p for p in profiles if p.get("selected")), profiles[0])
    member = best_profile.get("members", {}).get(uuid, {})
    dungeons = member.get("dungeons", {})
    
    catacombs = dungeons.get("dungeon_types", {}).get("catacombs", {})
    cata_xp = float(catacombs.get("experience", 0))
    
    classes = dungeons.get("player_classes", {})
    class_xp = {}
    
    for cls in ["archer", "berserk", "healer", "mage", "tank"]:
        cls_data = classes.get(cls, {})
        class_xp[cls] = float(cls_data.get("experience", 0))
        
    return {
        "catacombs": cata_xp,
        "classes": class_xp
    }
