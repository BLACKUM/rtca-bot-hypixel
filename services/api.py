import aiohttp
import asyncio
from services import json_utils
from urllib.parse import quote
from core.config import config
from core.game_data import SKELETON_MASTER_CHESTPLATE_50

from core.logger import log_debug, log_error, log_info
from core.cache import cache_get, cache_set, get_cache_expiry
from typing import Optional


_SESSION: Optional[aiohttp.ClientSession] = None
_CONNECTOR: Optional[aiohttp.TCPConnector] = None

async def init_session():
    global _SESSION, _CONNECTOR
    if _SESSION is None:
        _CONNECTOR = aiohttp.TCPConnector(force_close=True)
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

    soopy_url = f"https://soopy.dev/api/v2/player_skyblock/{uuid}"
    log_debug(f"Requesting profile data (soopy.dev): {soopy_url}")
    try:
        async with _SESSION.get(soopy_url, timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status == 200:
                data = await r.json(loads=json_utils.loads)
                if data.get("success") and data.get("data"):
                    result = _normalize_soopy(data["data"], uuid)
                    await cache_set(uuid, result, ttl=config.profile_cache_ttl)
                    return result
                log_error(f"soopy.dev returned success=false for {uuid}")
            else:
                log_error(f"soopy.dev profile request failed ({r.status})")
    except Exception as e:
        log_error(f"soopy.dev profile request error: {e}")

    fallback_url = f"https://adjectilsbackend.adjectivenoun3215.workers.dev/v2/skyblock/profiles?uuid={uuid}"
    log_debug(f"Requesting profile data (adjectilsbackend fallback): {fallback_url}")
    try:
        async with _SESSION.get(fallback_url, timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status != 200:
                try:
                    text = await r.text()
                    log_error(f"Fallback profile request failed ({r.status}): {text[:200]}")
                except Exception:
                    log_error(f"Fallback profile request failed ({r.status})")
                return None
            data = await r.json(loads=json_utils.loads)
            await cache_set(uuid, data, ttl=config.profile_cache_ttl)
            return data
    except asyncio.TimeoutError:
        log_error("Fallback profile request timed out (15s)")
        return None
    except Exception as e:
        log_error(f"Fallback profile request error: {e}")
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


def _parse_soopy_dungeon_stats(member: dict) -> dict:
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
        floor_data = floor_stats_raw.get(raw_key, {})
        completions = int((floor_data or {}).get("completions", 0) or 0)
        s_raw = ((floor_data or {}).get("fastest_time_s") or {}).get("raw")
        s_plus_raw = ((floor_data or {}).get("fastest_time_s_plus") or {}).get("raw")
        floors[display_key] = {
            "runs": completions,
            "best_score": 0,
            "fastest_s": int(s_raw) if isinstance(s_raw, (int, float)) else 0,
            "fastest_s_plus": int(s_plus_raw) if isinstance(s_plus_raw, (int, float)) else 0,
        }

    kills = member.get("kills", {})
    blood_mob_kills = int((kills or {}).get("watcher_summon_undead", 0) or 0)

    return {
        "catacombs": cata_xp,
        "secrets": 0,
        "blood_mob_kills": blood_mob_kills,
        "classes": class_xp,
        "floors": floors,
    }


async def get_bazaar_prices():
    cached = await cache_get("bazaar_prices")
    if cached is not None:
        return cached
    
    url = "https://api.hypixel.net/skyblock/bazaar"
    log_debug("Fetching Bazaar prices")
    
    if not _SESSION:
        await init_session()

    try:
        async with _SESSION.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status != 200:
                try:
                    text = await r.text()
                    log_error(f"Bazaar request failed ({r.status}): {text[:200]}")
                except:
                    log_error(f"Bazaar request failed ({r.status})")
                await cache_set("bazaar_prices", {}, ttl=config.prices_cache_ttl)
                return {}
            data = await r.json(loads=json_utils.loads)
            products = data.get("products", {})
            prices = {
                pid: info["quick_status"]["sellPrice"] 
                for pid, info in products.items()
            }
            await cache_set("bazaar_prices", prices, ttl=config.prices_cache_ttl)
            return prices
    except Exception as e:
        log_error(f"Failed to fetch Bazaar prices: {e}")
        await cache_set("bazaar_prices", {}, ttl=config.prices_cache_ttl)
        return {}


async def get_ah_prices():
    cached = await cache_get("ah_prices")
    if cached is not None:
        return cached
        
    url = "https://moulberry.codes/auction_averages_lbin/3day.json"
    log_debug("Fetching AH prices (3-day avg)")
    
    if not _SESSION:
        await init_session()

    log_debug(f"Requesting AH prices: {url}")
    try:
        async with _SESSION.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status != 200:
                try:
                    text = await r.text()
                    log_error(f"AH request failed ({r.status}): {text[:200]}")
                except:
                    log_error(f"AH request failed ({r.status})")
                await cache_set("ah_prices", {}, ttl=config.prices_cache_ttl)
                return {}
            prices = await r.json(loads=json_utils.loads)
            await cache_set("ah_prices", prices, ttl=config.prices_cache_ttl)
            return prices
    except Exception as e:
        log_error(f"Failed to fetch AH prices: {e}")
        await cache_set("ah_prices", {}, ttl=config.prices_cache_ttl)
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

async def get_special_prices():
    urls = {
        "SHINY_NECRON_HANDLE": "https://sky.coflnet.com/api/item/price/NECRON_HANDLE?IsShiny=true",
        SKELETON_MASTER_CHESTPLATE_50: "https://sky.coflnet.com/api/item/price/SKELETON_MASTER_CHESTPLATE?ItemTier=10-10&NoOtherValuableEnchants=true&BaseStatBoost=50"
    }
    
    special_prices = {}
    
    if not _SESSION:
        await init_session()

    tasks = []
    for key, url in urls.items():
        tasks.append(fetch_special_price(_SESSION, key, url))
    
    results = await asyncio.gather(*tasks)
    for key, price in results:
        if price is not None:
            special_prices[key] = price
                
    return special_prices

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

async def get_all_prices():
    bz_future = get_bazaar_prices()
    ah_future = get_ah_prices()
    special_future = get_special_prices()
    
    bz_prices, ah_prices, special_prices = await asyncio.gather(bz_future, ah_future, special_future)
    
    prices = bz_prices.copy()
    prices.update(ah_prices)
    prices.update(special_prices)
    
    if SKELETON_MASTER_CHESTPLATE_50 not in prices:
        prices[SKELETON_MASTER_CHESTPLATE_50] = 40_000_000
    
    return prices


def get_prices_expiry():
    return get_cache_expiry("ah_prices")


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

    if "catacombs_xp" in dungeons:
        return _parse_soopy_dungeon_stats(member)

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
