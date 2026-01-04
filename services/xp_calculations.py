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
    
    for cls in ["archer", "berserk", "healer", "mage", "tank"]:
        xp = float(classes_data.get(cls, 0))
        level = get_dungeon_level(xp)
        total_level += level
        count += 1
        
    return round(total_level / count, 2) if count > 0 else 0.0

def calculate_dungeon_xp_per_run(base_floor: float, ring: float, hecatomb: float, global_mult: float, mayor_mult: float) -> float:
    if base_floor >= 15000:
        maxcomps = 26
    elif base_floor == 4880:
        maxcomps = 51
    else:
        maxcomps = 76
    
    if ring > 0 and mayor_mult > 1:
        cataperrun = base_floor * (0.95 + ((mayor_mult - 1) + (maxcomps - 1) / 100) + ring + hecatomb + (maxcomps - 1) * (0.024 + hecatomb / 50))
    elif ring > 0:
        cataperrun = base_floor * (0.95 + ring + hecatomb + (maxcomps - 1) * (0.024 + hecatomb / 50))
    else:
        cataperrun = base_floor * (0.95 + hecatomb + (maxcomps - 1) * (0.022 + hecatomb / 50))
    
    cataperrun *= global_mult
    return math.ceil(cataperrun)