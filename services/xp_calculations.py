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


def get_class_average(classes_data: dict) -> float:
    if not classes_data:
        return 0.0
    
    total_level = 0.0
    count = 0
    
    # Standard 5 classes
    for cls in ["archer", "berserk", "healer", "mage", "tank"]:
        xp = float(classes_data.get(cls, 0))
        level = get_dungeon_level(xp)
        total_level += level
        count += 1
        
    return round(total_level / count, 2) if count > 0 else 0.0
