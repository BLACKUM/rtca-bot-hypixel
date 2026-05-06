import time
from typing import Dict, Optional, Tuple
from urllib.parse import quote

from core.logger import log_error, log_info
from services import api as api_service
from services import json_utils

HAS_JOINED_URL = "https://sessionserver.mojang.com/session/minecraft/hasJoined"

_session_cache: Dict[str, Tuple[str, float]] = {}
_CACHE_TTL_S = 60.0


def _normalize_uuid(value: str) -> str:
    return value.replace("-", "").lower()


def _cache_set(server_id: str, norm_uuid: str) -> None:
    _session_cache[server_id.lower()] = (norm_uuid, time.monotonic() + _CACHE_TTL_S)


def _cache_check(server_id: str, expected_uuid: Optional[str]) -> Optional[bool]:
    entry = _session_cache.get(server_id.lower())
    if not entry:
        return None
    norm_uuid, expires = entry
    if time.monotonic() > expires:
        del _session_cache[server_id.lower()]
        return None
    if expected_uuid and _normalize_uuid(norm_uuid) != _normalize_uuid(expected_uuid):
        return False
    return True


async def verify_session(ign: str, server_id: str, expected_uuid: Optional[str] = None) -> bool:
    if not ign or not server_id:
        return False

    cached = _cache_check(server_id, expected_uuid)
    if cached is not None:
        log_info(f"[Mojang] Cache {'hit' if cached else 'hit (uuid mismatch)'} for {ign} server_id={server_id[:8]}...")
        return cached

    if not api_service._SESSION:
        await api_service.init_session()

    url = f"{HAS_JOINED_URL}?username={quote(ign)}&serverId={quote(server_id)}"

    try:
        async with api_service._SESSION.get(url) as resp:
            if resp.status == 204:
                log_error(f"[Mojang] hasJoined returned 204 (not authenticated) for {ign}")
                return False
            if resp.status != 200:
                log_error(f"[Mojang] hasJoined unexpected status {resp.status} for {ign}")
                return False

            data = await resp.json(loads=json_utils.loads)
            returned_id = data.get("id", "")
            returned_name = data.get("name", "")

            if not returned_id:
                log_error(f"[Mojang] hasJoined response missing id for {ign}")
                return False

            _cache_set(server_id, returned_id)

            if expected_uuid and _normalize_uuid(returned_id) != _normalize_uuid(expected_uuid):
                log_error(
                    f"[Mojang] UUID mismatch for {ign}: "
                    f"returned={returned_id} expected={expected_uuid}"
                )
                return False

            log_info(f"[Mojang] Session verified for {returned_name} ({returned_id})")
            return True

    except Exception as e:
        log_error(f"[Mojang] hasJoined call failed for {ign}: {e}")
        return False
