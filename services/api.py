import aiohttp
import asyncio
import os
import time
import aiofiles
from services import json_utils
from urllib.parse import quote
from core.config import config, HYPIXEL_API_KEY
from core.game_data import SKELETON_MASTER_CHESTPLATE_50

from core.logger import log_debug, log_error, log_info
from core.cache import cache_get, cache_set, get_cache_expiry
from typing import Optional

PRICES_CACHE_FILE = "data/prices_cache.json"
_prices_memory: Optional[dict] = None
_prices_fetched_at: float = 0.0


_SESSION: Optional[aiohttp.ClientSession] = None
_CONNECTOR: Optional[aiohttp.TCPConnector] = None

async def init_session():
    global _SESSION, _CONNECTOR
    if _SESSION is None:
        _CONNECTOR = aiohttp.TCPConnector(limit=10)
        _SESSION = aiohttp.ClientSession(headers=HEADERS, connector=_CONNECTOR)
        log_info("Global API Session initialized.")

async def close_session():
    global _SESSION, _CONNECTOR
    if _SESSION:
        await _SESSION.close()
    
    if _CONNECTOR and not _CONNECTOR.closed:
        await _CONNECTOR.close()

    await asyncio.sleep(0.5)
    _SESSION = None
    _CONNECTOR = None
    log_info("Global API Session closed.")


MOJANG_PROFILE_URL = "https://api.mojang.com/users/profiles/minecraft"
HYPIXEL_BASE_URL = "https://api.hypixel.net/v2"

# cloudflare bypass, i hate i even have to do this
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
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
    cached = await cache_get(name.lower())
    if cached:
        log_debug(f"Using cached UUID for {name}")
        return cached

    log_debug(f"Requesting UUID for {name}")
    
    if not _SESSION:
        await init_session()
        
    if not name.replace("_", "").isalnum():
        log_error(f"Invalid name format: {name}")
        return None
        
    msg = quote(name)
    try:
        async with _SESSION.get(f"{MOJANG_PROFILE_URL}/{msg}", timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status != 200:
                log_error(f"UUID request failed ({r.status})")
                return None
            data = await r.json(content_type=None, loads=json_utils.loads)
            uuid = data["id"]
            log_debug(f"UUID fetched: {uuid}")
            await cache_set(name.lower(), uuid, ttl=config.profile_cache_ttl)
            return uuid
    except Exception as e:
         log_error(f"UUID fetch error: {e}")
         return None


COOLDOWN_FIRST_429 = 5
COOLDOWN_SUBSEQUENT_429 = 60
COOLDOWN_SERVER_ERROR = 30

class _ApiCooldownTracker:
    def __init__(self):
        self._cooldowns: dict[str, float] = {}
        self._consecutive_failures: dict[str, int] = {}

    def is_cooling_down(self, api_name: str) -> bool:
        return time.time() < self._cooldowns.get(api_name, 0.0)

    def record_failure(self, api_name: str, status: int, retry_after: int = 0):
        self._consecutive_failures[api_name] = self._consecutive_failures.get(api_name, 0) + 1
        fails = self._consecutive_failures[api_name]
        
        if status == 429:
             duration = COOLDOWN_FIRST_429 if fails == 1 else COOLDOWN_SUBSEQUENT_429
        else:
             duration = COOLDOWN_SERVER_ERROR
             
        duration = max(duration, retry_after)
        self._cooldowns[api_name] = time.time() + duration
        log_error(f"API '{api_name}' failed ({status}). On cooldown for {duration}s (Failure #{fails})")

    def record_success(self, api_name: str):
        if api_name in self._consecutive_failures:
            del self._consecutive_failures[api_name]

_api_cooldown = _ApiCooldownTracker()

async def fetch_hypixel_profile(uuid: str):
    url = f"{HYPIXEL_BASE_URL}/skyblock/profiles?uuid={uuid}"
    log_debug(f"Requesting profile data (Hypixel API): {url}")
    headers = {
        "API-Key": HYPIXEL_API_KEY
    }
    try:
        async with _SESSION.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as r:
            if r.status == 200:
                _api_cooldown.record_success("hypixel")
                data = await r.json(content_type=None, loads=json_utils.loads)
                if data and data.get("success") and "profiles" in data:
                    data["_source"] = "hypixel"
                    return data
                else:
                    log_error(f"Hypixel API returned success=False or no profiles: {data}")
            else:
                retry_after = int(r.headers.get("Retry-After", 0))
                _api_cooldown.record_failure("hypixel", r.status, retry_after)
    except asyncio.TimeoutError:
        _api_cooldown.record_failure("hypixel", 408)
        log_error("Hypixel API profile request timed out")
    except Exception as e:
        _api_cooldown.record_failure("hypixel", 500)
        log_error(f"Hypixel API profile request error: {e}")
    return None


async def get_profile_data(uuid: str):
    cached = await cache_get(uuid)
    if cached:
        log_debug(f"Using cached data for {uuid}")
        return cached

    if not uuid or len(uuid) != 32 or not all(c in '0123456789abcdefABCDEF' for c in uuid):
        log_error(f"Invalid UUID format: {uuid}")
        return None

    if not _SESSION:
        await init_session()

    if _api_cooldown.is_cooling_down("hypixel"):
        log_debug("Skipping Hypixel API (on cooldown)")
        return None

    result = await fetch_hypixel_profile(uuid)
    if result:
        await cache_set(uuid, result, ttl=config.profile_cache_ttl)
        return result
    
    return None


async def _load_prices_from_disk() -> Optional[dict]:
    if not os.path.exists(PRICES_CACHE_FILE):
        return None
    try:
        async with aiofiles.open(PRICES_CACHE_FILE, "rb") as f:
            content = await f.read()
        data = json_utils.loads(content)
        fetched_at = data.get("_fetched_at", 0)
        if time.time() - fetched_at > config.prices_cache_ttl:
            log_info("Prices cache file is expired, will re-fetch.")
            return None
        log_info(f"Loaded prices from disk (age: {int(time.time() - fetched_at)}s).")
        prices = {k: v for k, v in data.items() if k != "_fetched_at"}
        return prices
    except Exception as e:
        log_error(f"Failed to load prices from disk: {e}")
        return None


async def _save_prices_to_disk(prices: dict):
    try:
        os.makedirs(os.path.dirname(PRICES_CACHE_FILE), exist_ok=True)
        payload = dict(prices)
        payload["_fetched_at"] = time.time()
        temp_path = PRICES_CACHE_FILE + ".tmp"
        async with aiofiles.open(temp_path, "wb") as f:
            await f.write(json_utils.dumps(payload))
        os.replace(temp_path, PRICES_CACHE_FILE)
        log_info("Prices saved to disk.")
    except Exception as e:
        log_error(f"Failed to save prices to disk: {e}")


async def _fetch_bazaar_prices() -> dict:
    url = f"{HYPIXEL_BASE_URL}/skyblock/bazaar"
    log_info("Fetching Bazaar prices from API...")
    if not _SESSION:
        await init_session()
    try:
        async with _SESSION.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status != 200:
                log_error(f"Bazaar request failed ({r.status})")
                return {}
            data = await r.json(loads=json_utils.loads)
            products = data.get("products", {})
            return {
                pid: info["quick_status"]["sellPrice"]
                for pid, info in products.items()
            }
    except Exception as e:
        log_error(f"Failed to fetch Bazaar prices: {e}")
        return {}


async def _fetch_ah_prices() -> dict:
    url = "https://moulberry.codes/auction_averages_lbin/3day.json"
    log_info("Fetching AH prices from API...")
    if not _SESSION:
        await init_session()
    try:
        async with _SESSION.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status != 200:
                log_error(f"AH request failed ({r.status})")
                return {}
            return await r.json(loads=json_utils.loads)
    except Exception as e:
        log_error(f"Failed to fetch AH prices: {e}")
        return {}


async def get_player_discord(uuid: str) -> Optional[str]:
    log_debug(f"Requesting player Discord for {uuid}")

    if not _SESSION:
        await init_session()

    url = f"{HYPIXEL_BASE_URL}/player?uuid={uuid}"
    headers = {"API-Key": HYPIXEL_API_KEY}
    try:
        async with _SESSION.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status != 200:
                log_error(f"Player request failed ({r.status})")
                return None
            data = await r.json(loads=json_utils.loads)
            player = data.get("player", {})
            if not player:
                return None
            social = player.get("socialMedia", {})
            links = social.get("links", {})
            return links.get("DISCORD")
    except Exception as e:
        log_error(f"Player request error: {e}")
        return None


async def get_all_prices() -> dict:
    global _prices_memory, _prices_fetched_at

    if _prices_memory is not None:
        age = time.time() - _prices_fetched_at
        if age < config.prices_cache_ttl:
            return _prices_memory

    from_disk = await _load_prices_from_disk()
    if from_disk is not None:
        _prices_memory = from_disk
        _prices_fetched_at = time.time()
        return _prices_memory

    bz, ah = await asyncio.gather(
        _fetch_bazaar_prices(),
        _fetch_ah_prices(),
    )
    prices = bz.copy()
    prices.update(ah)
    if SKELETON_MASTER_CHESTPLATE_50 not in prices:
        prices[SKELETON_MASTER_CHESTPLATE_50] = 40_000_000

    _prices_memory = prices
    _prices_fetched_at = time.time()
    await _save_prices_to_disk(prices)
    return prices


def get_prices_expiry() -> float:
    if not os.path.exists(PRICES_CACHE_FILE):
        return 0.0
    return os.path.getmtime(PRICES_CACHE_FILE) + config.prices_cache_ttl


def _select_member(profile_data, uuid, profile_name=None):
    profiles = profile_data.get("profiles")
    if not profiles:
        return None

    if profile_name:
        profile = next((p for p in profiles if p.get("cute_name", "").lower() == profile_name.lower()), None)
    else:
        profile = next((p for p in profiles if p.get("selected")), profiles[0])

    if not profile:
        profile = next((p for p in profiles if p.get("selected")), profiles[0])

    uuid_no_dashes = uuid.replace("-", "")
    members = profile.get("members", {})
    return members.get(uuid) or members.get(uuid_no_dashes) or {}

async def get_dungeon_runs(uuid: str, profile_name: str = None):
    profile_data = await get_profile_data(uuid)
    if not profile_data:
        return {}

    member = _select_member(profile_data, uuid, profile_name)
    if not member:
        return {}

    dungeons = member.get("dungeons", {})

    catacombs_data = dungeons.get("dungeon_types", {}).get("catacombs", {})
    master_catacombs_data = dungeons.get("dungeon_types", {}).get("master_catacombs", {})
    master_completions = master_catacombs_data.get("tier_completions", {})
    normal_completions = catacombs_data.get("tier_completions", {})

    tier_to_floor = {
        "1": "Floor 1 (Bonzo)", "2": "Floor 2 (Scarf)",
        "3": "Floor 3 (Professor)", "4": "Floor 4 (Thorn)",
        "5": "Floor 5 (Livid)", "6": "Floor 6 (Sadan)",
        "7": "Floor 7 (Necron)",
    }
    run_counts = {}
    for tier_key, floor_name in tier_to_floor.items():
        master_runs = int(master_completions.get(tier_key, 0))
        normal_runs = int(normal_completions.get(tier_key, 0))
        run_counts[floor_name] = {"normal": normal_runs, "master": master_runs}

    log_debug(f"Fetched run counts for {uuid}: {run_counts}")
    return run_counts


async def get_dungeon_xp(uuid: str, profile_name: str = None):
    profile_data = await get_profile_data(uuid)
    if not profile_data:
        return None

    member = _select_member(profile_data, uuid, profile_name)
    if not member:
        return None

    dungeons = member.get("dungeons", {})

    catacombs = dungeons.get("dungeon_types", {}).get("catacombs", {})
    master_catacombs = dungeons.get("dungeon_types", {}).get("master_catacombs", {})
    cata_xp = float(catacombs.get("experience", 0))
    normal_runs = catacombs.get("tier_completions", {})
    master_runs = master_catacombs.get("tier_completions", {})
    classes = dungeons.get("player_classes", {})
    class_xp = {
        cls: float((classes.get(cls) or {}).get("experience", 0))
        for cls in ["archer", "berserk", "healer", "mage", "tank"]
    }
    return {
        "catacombs": cata_xp,
        "classes": class_xp,
        "runs": {"normal": normal_runs, "master": master_runs},
    }


async def get_dungeon_stats(uuid: str, profile_name: str = None):
    profile_data = await get_profile_data(uuid)
    if not profile_data:
        return None

    member = _select_member(profile_data, uuid, profile_name)
    if not member:
        return None

    dungeons = member.get("dungeons", {})

    catacombs = dungeons.get("dungeon_types", {}).get("catacombs", {})
    master_catacombs = dungeons.get("dungeon_types", {}).get("master_catacombs", {})

    cata_xp = float(catacombs.get("experience", 0))

    secrets = int(dungeons.get("secrets", 0))
    if secrets == 0:
        secrets = int(member.get("achievements", {}).get("skyblock_treasure_hunter", 0))

    player_classes = dungeons.get("player_classes", {})
    class_xp = {}
    for cls in ["archer", "berserk", "healer", "mage", "tank"]:
        cls_data = player_classes.get(cls, {})
        class_xp[cls.capitalize()] = float(cls_data.get("experience", 0))

    player_stats = member.get("player_stats", {})
    kills = player_stats.get("kills", {})
    blood_mob_kills = kills.get("watcher_summon_undead", 0)

    accessory_bag = member.get("accessory_bag_storage", {})
    magical_power = int((accessory_bag or {}).get("highest_magical_power", 0) or 0)

    floors = {}

    def process_tier(tier_data, prefix="F"):
        times_s_plus = tier_data.get("fastest_time_s_plus", {})
        times_s = tier_data.get("fastest_time_s", {})
        runs = tier_data.get("tier_completions", {})
        best_score = tier_data.get("best_score", {})

        for tier in runs.keys():
            if tier == "total":
                continue
            if tier == "0":
                floor_name = "Entrance" if prefix == "F" else "M0"
            else:
                floor_name = f"{prefix}{tier}"

            ms_s_plus = times_s_plus.get(tier, 0)
            ms_s = times_s.get(tier, 0)
            score = best_score.get(tier, 0)
            count = runs.get(tier, 0)

            floors[floor_name] = {
                "runs": count,
                "best_score": score,
                "fastest_s_plus": ms_s_plus,
                "fastest_s": ms_s,
            }

    process_tier(catacombs, "F")
    process_tier(master_catacombs, "M")

    return {
        "catacombs": cata_xp,
        "secrets": secrets,
        "blood_mob_kills": blood_mob_kills,
        "classes": class_xp,
        "floors": floors,
        "magical_power": magical_power,
        "accessory_bag_storage": {
            "highest_magical_power": magical_power
        }
    }

async def get_recent_runs(uuid: str, profile_name: str = None):
    profile_data = await get_profile_data(uuid)
    if not profile_data:
        return []

    member = _select_member(profile_data, uuid, profile_name)
    if not member:
        return []

    dungeons = member.get("dungeons", {})
    treasures = dungeons.get("treasures", {})
    return treasures.get("runs", [])
