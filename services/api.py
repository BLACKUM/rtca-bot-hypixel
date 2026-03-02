import aiohttp
import asyncio
import os
import time
import aiofiles
from services import json_utils
from urllib.parse import quote
from core.config import config
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
        async with _SESSION.get(f"https://playerdb.co/api/player/minecraft/{msg}") as r:
            if r.status != 200:
                log_error(f"UUID request failed ({r.status})")
                return None
            data = await r.json(loads=json_utils.loads)
            uuid = data["data"]["player"]["raw_id"]
            log_debug(f"UUID fetched: {uuid}")
            await cache_set(name.lower(), uuid, ttl=config.profile_cache_ttl)
            return uuid
    except Exception as e:
         log_error(f"UUID fetch error: {e}")
         return None


async def get_soopy_player_data(uuid: str):
    cached = await cache_get(f"soopy_player:{uuid}")
    if cached:
        return cached

    if not _SESSION:
        await init_session()

    url = f"https://soopy.dev/api/v2/player/{uuid}"
    log_debug(f"Requesting player data (soopy.dev): {url}")
    try:
        async with _SESSION.get(url, timeout=aiohttp.ClientTimeout(total=20)) as r:
            if r.status == 200:
                data = await r.json(loads=json_utils.loads)
                if data.get("success") and data.get("data"):
                    result = data["data"]
                    await cache_set(f"soopy_player:{uuid}", result, ttl=config.profile_cache_ttl)
                    return result
    except Exception as e:
        log_error(f"soopy.dev player request error: {e}")
    return None


async def get_profile_data(uuid: str):

    cached = await cache_get(uuid)
    if cached:
        log_debug(f"Using cached data for {uuid}")
        return cached
    if not uuid or len(uuid) != 32 or not all(c in '0123456789abcdefABCDEF' for c in uuid):
        log_error(f"Invalid UUID format: {uuid}")
        return None

async def fetch_soopy_profile(uuid: str):
    url = f"https://soopy.dev/api/v2/player_skyblock/{uuid}"
    log_debug(f"Requesting profile data (soopy.dev): {url}")
    try:
        async with _SESSION.get(url, timeout=aiohttp.ClientTimeout(total=20)) as r:
            if r.status == 200:
                data = await r.json(loads=json_utils.loads)
                if data.get("success") and data.get("data"):
                    return _normalize_soopy(data["data"], uuid)
                log_error(f"soopy.dev returned success=false for {uuid}")
            else:
                log_error(f"soopy.dev profile request failed ({r.status})")
    except Exception as e:
        log_error(f"soopy.dev profile request error: {e}")
    return None


async def fetch_adjectils_profile(uuid: str):
    url = f"https://adjectilsbackend.adjectivenoun3215.workers.dev/v2/skyblock/profiles?uuid={uuid}"
    log_debug(f"Requesting profile data (adjectilsbackend): {url}")
    try:
        async with _SESSION.get(url, timeout=aiohttp.ClientTimeout(total=20)) as r:
            if r.status == 200:
                data = await r.json(loads=json_utils.loads)
                if data:
                    data["_source"] = "adjectils"
                    return data
            else:
                try:
                    text = await r.text()
                    log_error(f"Adjectils profile request failed ({r.status}): {text[:200]}")
                except Exception:
                    log_error(f"Adjectils profile request failed ({r.status})")
    except asyncio.TimeoutError:
        log_error("Adjectils profile request timed out (15s)")
    except Exception as e:
        log_error(f"Adjectils profile request error: {e}")
    return None


async def fetch_skycrypt_shiiyu_profile(uuid: str):
    from services.skycrypt_service import get_skycrypt_profile
    ign = await get_ign(uuid)
    if not ign:
        return None
    
    url = f"https://sky.shiiyu.moe/api/stats/{ign}"
    log_debug(f"Requesting profile data (sky.shiiyu.moe): {url}")
    try:
        async with _SESSION.get(url, timeout=aiohttp.ClientTimeout(total=20)) as r:
            if r.status == 200:
                data = await r.json(content_type=None)
                if data and "profiles" in data:
                    data["_source"] = "skycrypt"
                    return data
            else:
                log_error(f"sky.shiiyu.moe profile request failed ({r.status})")
    except Exception as e:
        log_error(f"sky.shiiyu.moe profile request error: {e}")
    return None


async def get_ign(uuid: str) -> Optional[str]:
    url = f"https://playerdb.co/api/player/minecraft/{uuid}"
    try:
        async with _SESSION.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status == 200:
                data = await r.json()
                return data.get("data", {}).get("player", {}).get("username")
    except Exception:
        pass
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

    result = await fetch_adjectils_profile(uuid)
    if not result:
        result = await fetch_soopy_profile(uuid)
    if not result:
        result = await fetch_skycrypt_shiiyu_profile(uuid)

    if result:
        await cache_set(uuid, result, ttl=config.profile_cache_ttl)
        return result
    
    return None


def _normalize_soopy(data: dict, uuid: str) -> dict:
    profiles_raw = data.get("profiles", {})
    current_profile_id = data.get("stats", {}).get("currentProfileId", "")
    profiles = []
    for profile_id, profile_info in profiles_raw.items():
        stats = profile_info.get("stats", {})
        members_raw = profile_info.get("members", {})
        members = {}
        for member_uuid, member_data in members_raw.items():
            formatted_uuid = (
                f"{member_uuid[:8]}-{member_uuid[8:12]}-{member_uuid[12:16]}-{member_uuid[16:20]}-{member_uuid[20:]}"
                if len(member_uuid) == 32 and "-" not in member_uuid else member_uuid
            )
            members[formatted_uuid] = member_data
            members[member_uuid] = member_data
        profiles.append({
            "profile_id": profile_id,
            "cute_name": stats.get("cute_name", ""),
            "selected": profile_id == current_profile_id,
            "members": members,
            "_soopy": True,
        })
    return {"profiles": profiles, "_source": "soopy"}


def _parse_soopy_dungeon_stats(member: dict, player_data: dict = None) -> dict:
    dungeons = member.get("dungeons", {})
    cata_xp = float(dungeons.get("catacombs_xp", 0) or 0)

    class_levels = dungeons.get("class_levels", {})
    class_xp = {}
    for cls in ["archer", "berserk", "healer", "mage", "tank"]:
        cls_data = class_levels.get(cls, {})
        class_xp[cls.capitalize()] = float((cls_data or {}).get("xp", 0) or 0)

    floor_stats_raw = dungeons.get("floorStats", {})
    floors = {}
    floor_key_map = {
        "e": "Entrance",
        "f1": "F1", "f2": "F2", "f3": "F3", "f4": "F4",
        "f5": "F5", "f6": "F6", "f7": "F7",
        "m1": "M1", "m2": "M2", "m3": "M3", "m4": "M4",
        "m5": "M5", "m6": "M6", "m7": "M7",
    }
    for raw_key, display_key in floor_key_map.items():
        floor_data = floor_stats_raw.get(raw_key) or {}
        completions = int(floor_data.get("completions") or 0)
        s_raw = (floor_data.get("fastest_time_s") or {}).get("raw")
        s_plus_raw = (floor_data.get("fastest_time_s_plus") or {}).get("raw")
        floors[display_key] = {
            "runs": completions,
            "best_score": int(floor_data.get("best_score") or 0),
            "fastest_s": int(s_raw) if isinstance(s_raw, (int, float)) and not isinstance(s_raw, bool) else 0,
            "fastest_s_plus": int(s_plus_raw) if isinstance(s_plus_raw, (int, float)) and not isinstance(s_plus_raw, bool) else 0,
        }

    kills = member.get("kills", {})
    blood_mob_kills = int((kills or {}).get("watcher_summon_undead", 0) or 0)
    
    secrets = -1
    if player_data:
        achievements = player_data.get("stats", {}).get("achievements", {}).get("skyblock", {})
        secrets = achievements.get("dungeon_secrets", -1)

    accessory_reforge = member.get("accessory_reforge", {})
    magical_power = int((accessory_reforge or {}).get("highest_magical_power", 0) or 0)

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
    url = "https://api.hypixel.net/skyblock/bazaar"
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

    url = f"https://adjectilsbackend.adjectivenoun3215.workers.dev/v2/player?uuid={uuid}"
    try:
        async with _SESSION.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
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


async def fetch_special_price(session, key, url):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
            if r.status == 200:
                data = await r.json(loads=json_utils.loads)
                price = data.get("median", data.get("min", 0))
                return key, price
    except Exception as e:
        log_error(f"Failed to fetch special price for {key}: {e}")
    return key, None


async def get_special_prices() -> dict:
    if not _SESSION:
        await init_session()
    tasks = [
        fetch_special_price(_SESSION, "SHINY_NECRON_HANDLE",
            "https://sky.coflnet.com/api/item/price/NECRON_HANDLE?IsShiny=true"),
        fetch_special_price(_SESSION, SKELETON_MASTER_CHESTPLATE_50,
            "https://sky.coflnet.com/api/item/price/SKELETON_MASTER_CHESTPLATE?ItemTier=10-10&NoOtherValuableEnchants=true&BaseStatBoost=50"),
    ]
    results = await asyncio.gather(*tasks)
    return {k: v for k, v in results if v is not None}


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

    bz, ah, special = await asyncio.gather(
        _fetch_bazaar_prices(),
        _fetch_ah_prices(),
        get_special_prices(),
    )
    prices = bz.copy()
    prices.update(ah)
    prices.update(special)
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

    if "floorStats" in dungeons:
        floor_stats = dungeons.get("floorStats", {})
        tier_to_floor_soopy = {
            "f1": "Floor 1 (Bonzo)", "f2": "Floor 2 (Scarf)",
            "f3": "Floor 3 (Professor)", "f4": "Floor 4 (Thorn)",
            "f5": "Floor 5 (Livid)", "f6": "Floor 6 (Sadan)",
            "f7": "Floor 7 (Necron)",
        }
        run_counts = {}
        for floor_key, floor_name in tier_to_floor_soopy.items():
            normal_runs = int((floor_stats.get(floor_key) or {}).get("completions", 0) or 0)
            master_key = floor_key.replace("f", "m")
            master_runs = int((floor_stats.get(master_key) or {}).get("completions", 0) or 0)
            run_counts[floor_name] = {"normal": normal_runs, "master": master_runs}
        return run_counts

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

    if "catacombs_xp" in dungeons:
        class_levels = dungeons.get("class_levels", {})
        class_xp = {
            cls: float((class_levels.get(cls) or {}).get("xp", 0) or 0)
            for cls in ["archer", "berserk", "healer", "mage", "tank"]
        }
        floor_stats = dungeons.get("floorStats", {})
        normal_runs = {
            str(i): int((floor_stats.get(f"f{i}") or {}).get("completions", 0) or 0)
            for i in range(1, 8)
        }
        master_runs = {
            str(i): int((floor_stats.get(f"m{i}") or {}).get("completions", 0) or 0)
            for i in range(1, 8)
        }
        return {
            "catacombs": float(dungeons.get("catacombs_xp", 0) or 0),
            "classes": class_xp,
            "runs": {"normal": normal_runs, "master": master_runs},
        }

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

    if profile_data.get("_source") == "skycrypt":
        from services.skycrypt_service import get_dungeon_stats_skycrypt
        ign = await get_ign(uuid)
        if ign:
            return await get_dungeon_stats_skycrypt(ign, profile_name)

    if profile_data.get("_source") == "soopy" or "catacombs_xp" in dungeons:
        player_data = await get_soopy_player_data(uuid)
        return _parse_soopy_dungeon_stats(member, player_data)


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

    if isinstance(dungeons.get("treasures"), list):
        return dungeons.get("treasures", [])

    treasures = dungeons.get("treasures", {})
    return treasures.get("runs", [])
