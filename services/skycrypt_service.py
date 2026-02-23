import json
import re
import base64
from typing import Optional
from core.logger import log_debug, log_error
from core.cache import cache_get, cache_set

SKYCRYPT_BASE = "https://sky.shiiyu.moe"
BUILD_ID_CACHE_KEY = "skycrypt_build_id"
BUILD_ID_TTL = 3600
PROFILE_TTL = 120
DUNGEON_TTL = 120
BUILD_ID_PATTERN = re.compile(r'"([a-zA-Z0-9]+)/get[A-Z]')
FLOOR_NAME_PATTERN = re.compile(r"^(Entrance|Floor [1-7])$")
CLASS_NAMES = {"archer", "berserk", "healer", "mage", "tank"}


async def _get_session():
    from services.api import _SESSION, init_session
    if not _SESSION:
        await init_session()
    from services.api import _SESSION
    return _SESSION


async def _get_build_id() -> Optional[str]:
    cached = await cache_get(BUILD_ID_CACHE_KEY)
    if cached:
        return cached

    session = await _get_session()
    try:
        import aiohttp
        async with session.get(SKYCRYPT_BASE, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                log_error(f"SkyCrypt HTML fetch failed: {resp.status}")
                return None
            html = await resp.text()
    except Exception as e:
        log_error(f"SkyCrypt HTML fetch error: {e}")
        return None

    match = BUILD_ID_PATTERN.search(html)
    if not match:
        log_error("Could not extract SkyCrypt build ID from HTML")
        return None

    build_id = match.group(1)
    log_debug(f"SkyCrypt build ID discovered: {build_id}")
    await cache_set(BUILD_ID_CACHE_KEY, build_id, ttl=BUILD_ID_TTL)
    return build_id


async def get_skycrypt_profile(ign: str, profile_name: Optional[str] = None) -> Optional[tuple]:
    cache_key = f"skycrypt_profile_{ign.lower()}_{(profile_name or '').lower()}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    session = await _get_session()
    url = f"{SKYCRYPT_BASE}/api/stats/{ign}"
    try:
        import aiohttp
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                log_error(f"SkyCrypt profile fetch failed ({resp.status}) for {ign}")
                return None
            data = await resp.json(content_type=None)
    except Exception as e:
        log_error(f"SkyCrypt profile fetch error for {ign}: {e}")
        return None

    uuid = data.get("uuid")
    if not uuid:
        log_error(f"No UUID in SkyCrypt response for {ign}")
        return None

    profiles = data.get("profiles", [])
    if not profiles:
        return None

    if profile_name:
        profile = next((p for p in profiles if p.get("cute_name", "").lower() == profile_name.lower()), None)
    else:
        profile = next((p for p in profiles if p.get("selected")), profiles[0])

    if not profile:
        return None

    result = (uuid, profile.get("profile_id"), profile.get("cute_name"))
    await cache_set(cache_key, result, ttl=PROFILE_TTL)
    return result


def _resolve_rjson(raw: list) -> list:
    resolved_cache = {}

    def resolve(node):
        if isinstance(node, int) and not isinstance(node, bool) and 0 < node < len(raw):
            if node not in resolved_cache:
                resolved_cache[node] = None
                resolved_cache[node] = resolve(raw[node])
            return resolved_cache[node]
        if isinstance(node, dict):
            return {k: resolve(v) for k, v in node.items()}
        if isinstance(node, list):
            return [resolve(item) for item in node]
        return node

    return [resolve(item) for item in raw]


def _safe_int(val) -> int:
    if isinstance(val, bool):
        return 0
    if isinstance(val, (int, float)):
        return int(val)
    return 0


def _parse_dungeon_data(raw: list) -> dict:
    resolved = _resolve_rjson(raw)

    cata_xp = 0.0
    secrets = 0
    blood_mob_kills = 0
    classes = {}
    floors = {}

    template = resolved[0] if resolved else {}
    if not isinstance(template, dict):
        return {"catacombs": 0.0, "secrets": 0, "blood_mob_kills": 0, "classes": {}, "floors": {}}

    level_obj = template.get("level", {})
    if isinstance(level_obj, dict):
        cata_xp = float(level_obj.get("xp", 0) or 0)

    classes_obj = template.get("classes", {})
    if isinstance(classes_obj, dict):
        classes_dict = classes_obj.get("classes", {})
        if isinstance(classes_dict, dict):
            for cls_name, cls_info in classes_dict.items():
                if cls_name in CLASS_NAMES and isinstance(cls_info, dict):
                    xp = cls_info.get("xp")
                    if isinstance(xp, (int, float)) and not isinstance(xp, bool):
                        classes[cls_name.capitalize()] = float(xp)

    stats_obj = template.get("stats", {})
    if isinstance(stats_obj, dict):
        secrets_info = stats_obj.get("secrets", {})
        if isinstance(secrets_info, dict):
            secrets = _safe_int(secrets_info.get("found", 0))
        blood_mob_kills = _safe_int(stats_obj.get("bloodMobKills", 0))

    cata_list = template.get("catacombs", [])
    master_list = template.get("master_catacombs", [])
    if isinstance(cata_list, list):
        for floor_obj in cata_list:
            _extract_floor(floor_obj, is_master=False, floors=floors)
    if isinstance(master_list, list):
        for floor_obj in master_list:
            _extract_floor(floor_obj, is_master=True, floors=floors)

    return {
        "catacombs": cata_xp,
        "secrets": secrets,
        "blood_mob_kills": blood_mob_kills,
        "classes": classes,
        "floors": floors,
    }


def _extract_floor(floor_obj: dict, is_master: bool, floors: dict):
    if not isinstance(floor_obj, dict):
        return
    name = floor_obj.get("name")
    if not isinstance(name, str) or not FLOOR_NAME_PATTERN.match(name):
        return
    stats = floor_obj.get("stats", {})
    if not isinstance(stats, dict):
        return

    floor_key = _make_floor_key(name, is_master)
    if not floor_key:
        return

    floors[floor_key] = {
        "runs": _safe_int(stats.get("tier_completions", 0)),
        "best_score": _safe_int(stats.get("best_score", 0)),
        "fastest_s": _safe_int(stats.get("fastest_time_s", 0)),
        "fastest_s_plus": _safe_int(stats.get("fastest_time_s_plus", 0)),
    }


def _make_floor_key(name: str, is_master: bool) -> Optional[str]:
    if name == "Entrance":
        return "Entrance" if not is_master else None
    match = re.match(r"Floor (\d+)", name)
    if match:
        return f"M{match.group(1)}" if is_master else f"F{match.group(1)}"
    return None


async def _call_dungeon_endpoint(session, build_id: str, uuid_no_dashes: str, profile_id: str) -> Optional[dict]:
    import aiohttp
    payload_data = [{"uuid": 1, "profileId": 2}, uuid_no_dashes, profile_id]
    payload_b64 = base64.b64encode(json.dumps(payload_data, separators=(",", ":")).encode()).decode()
    url = f"{SKYCRYPT_BASE}/_app/remote/{build_id}/getDungeonsSection?payload={payload_b64}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return None, resp.status
            envelope = await resp.json(content_type=None)
            return envelope, 200
    except Exception as e:
        log_error(f"SkyCrypt dungeon endpoint error: {e}")
        return None, 0


async def get_dungeon_stats_skycrypt(ign: str, profile_name: Optional[str] = None) -> Optional[dict]:
    cache_key = f"skycrypt_dungeons_{ign.lower()}_{(profile_name or '').lower()}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    profile_info = await get_skycrypt_profile(ign, profile_name)
    if not profile_info:
        log_error(f"Could not get SkyCrypt profile for {ign}")
        return None

    uuid, profile_id, profile_cute_name = profile_info
    uuid_no_dashes = uuid.replace("-", "")

    build_id = await _get_build_id()
    if not build_id:
        return None

    session = await _get_session()
    envelope, status = await _call_dungeon_endpoint(session, build_id, uuid_no_dashes, profile_id)

    if status == 404:
        log_debug("SkyCrypt build ID stale, invalidating and retrying")
        await cache_set(BUILD_ID_CACHE_KEY, None, ttl=1)
        build_id = await _get_build_id()
        if not build_id:
            return None
        envelope, status = await _call_dungeon_endpoint(session, build_id, uuid_no_dashes, profile_id)

    if status != 200 or envelope is None:
        log_error(f"SkyCrypt dungeon fetch failed (status={status}) for {ign}")
        return None

    if envelope.get("type") != "result":
        log_error(f"Unexpected SkyCrypt dungeon response type: {envelope.get('type')}")
        return None

    try:
        raw = json.loads(envelope["result"])
        result = _parse_dungeon_data(raw)
        await cache_set(cache_key, result, ttl=DUNGEON_TTL)
        return result
    except Exception as e:
        log_error(f"Failed to parse SkyCrypt dungeon data for {ign}: {e}")
        return None
