import math
from core.config import DUNGEON_XP


def get_total_xp_for_level(level: float) -> float:
    total = 0.0
    level_int = math.floor(level)
    for i in range(1, min(level_int + 1, len(DUNGEON_XP))):
        total += DUNGEON_XP[i]
    if level_int + 1 < len(DUNGEON_XP):
        frac = level - level_int
        if frac > 0:
            total += DUNGEON_XP[level_int + 1] * frac
        return total
    base_levels = len(DUNGEON_XP) - 1
    total = sum(DUNGEON_XP[1:base_levels + 1])
    if level > base_levels:
        extra_levels = level - base_levels
        extra_whole = math.floor(extra_levels)
        total += extra_whole * DUNGEON_XP[-1]
        frac = extra_levels - extra_whole
        if frac > 0:
            total += DUNGEON_XP[-1] * frac
    return total


def get_dungeon_level(xp: float) -> float:
    total = 0.0
    for i in range(1, len(DUNGEON_XP)):
        total += DUNGEON_XP[i]
        if xp < total:
            prev = total - DUNGEON_XP[i]
            progress = (xp - prev) / DUNGEON_XP[i]
            return round(i - 1 + progress, 2)
    extra = xp - total
    extra_levels = extra / DUNGEON_XP[-1]
    return round((len(DUNGEON_XP) - 1) + extra_levels, 2)
