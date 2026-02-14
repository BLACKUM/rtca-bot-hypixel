from services.xp_calculations import get_dungeon_level

TRILLION = 1_000_000_000_000
BILLION = 1_000_000_000
MILLION = 1_000_000
THOUSAND = 1_000

SLAYER_THRESHOLDS = {
    "zombie": [5, 15, 200, 1000, 5000, 20000, 100000, 400000, 1000000],
    "spider": [5, 25, 200, 1000, 5000, 20000, 100000, 400000, 1000000],
    "wolf": [10, 30, 250, 1500, 5000, 20000, 100000, 400000, 1000000],
    "enderman": [10, 30, 250, 1500, 5000, 20000, 100000, 400000, 1000000],
    "blaze": [10, 30, 250, 1500, 5000, 20000, 100000, 400000, 1000000],
    "vampire": [20, 75, 240, 840, 2400, 6400, 15400, 38400, 100000],
}

SKILLS = ["farming", "mining", "combat", "foraging", "fishing", "enchanting", "alchemy", "taming"]
SLAYER_TYPES = ["zombie", "spider", "wolf", "enderman", "blaze", "vampire"]
SB_LEVEL_DIVISOR = 100
MINION_SLOT_BASE = 5
MINION_SLOT_DIVISOR = 25


def format_number(num: float) -> str:
    if num >= TRILLION:
        return f"{num / TRILLION:.2f}t"
    if num >= BILLION:
        return f"{num / BILLION:.2f}b"
    if num >= MILLION:
        return f"{num / MILLION:.2f}m"
    if num >= THOUSAND:
        return f"{num / THOUSAND:.2f}k"
    return f"{num:,.2f}"


def get_slayer_level(xp: int, slayer_type: str) -> int:
    thresholds = SLAYER_THRESHOLDS.get(slayer_type, SLAYER_THRESHOLDS["zombie"])
    for i, threshold in enumerate(thresholds):
        if xp < threshold:
            return i
    return len(thresholds)


def get_num(val, default=0):
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, dict):
        for key in ["networth", "milestone", "last_milestone", "experience", "total", "level", "amount", "value"]:
            if key in val:
                return get_num(val[key], default)
    return default


def parse_profile_stats(member: dict, profile: dict) -> dict:
    skills_data = member.get("skills", {})
    total_skill_lvl = 0
    skills_count = 0
    for s in SKILLS:
        lvl = member.get(f"skill_{s}_level")
        if lvl is None:
            lvl = skills_data.get(s, {}).get("level", 0)
        
        total_skill_lvl += get_num(lvl)
        skills_count += 1
    
    skill_avg = total_skill_lvl / skills_count if skills_count > 0 else 0
    
    cata_xp = get_num(member.get("dungeons", {}).get("dungeon_types", {}).get("catacombs", {}).get("experience", 0))
    cata_lvl = get_dungeon_level(cata_xp)
    
    classes = member.get("dungeons", {}).get("player_classes", {})
    best_class = "None"
    best_xp = -1
    for cls, data in classes.items():
        xp = get_num(data.get("experience", 0))
        if xp > best_xp:
            best_xp = xp
            best_class = cls
    
    best_class_lvl = get_dungeon_level(best_xp) if best_xp != -1 else 0
    
    nw_data = member.get("networth", {})
    networth = get_num(nw_data.get("networth", 0))
    bank = get_num(profile.get("banking", {}).get("balance", 0))
    purse = get_num(member.get("currencies", {}).get("coin_purse", 0))
    
    if networth == 0:
        networth = purse + bank
    
    slayers_data = member.get("slayer", {}).get("slayer_bosses", {})
    slayer_levels = []
    for s_type in SLAYER_TYPES:
        xp = get_num(slayers_data.get(s_type, {}).get("xp", 0))
        slayer_levels.append(str(get_slayer_level(xp, s_type)))
    
    slayer_str = " / ".join(slayer_levels)
    
    fairy_souls = get_num(member.get("fairy_soul", {}).get("total_collected", 0))
    if fairy_souls == 0:
         fairy_souls = get_num(member.get("fairy_souls_collected", 0))
    
    sb_exp = get_num(member.get("leveling", {}).get("experience", 0))
    sb_level = sb_exp / SB_LEVEL_DIVISOR
    
    bestiary_lvl = get_num(member.get("bestiary", {}).get("milestone", 0))
    
    unique_minions = len(member.get("player_data", {}).get("crafted_generators", []))
    minion_slots = MINION_SLOT_BASE + (unique_minions // MINION_SLOT_DIVISOR)
    
    mining_core = member.get("mining_core", {})
    mithril_powder = get_num(mining_core.get("powder_mithril_total", 0))
    if mithril_powder == 0:
        mithril_powder = get_num(mining_core.get("powder_mithril", 0)) + get_num(mining_core.get("powder_spent_mithril", 0))
        
    gemstone_powder = get_num(mining_core.get("powder_gemstone_total", 0))
    if gemstone_powder == 0:
        gemstone_powder = get_num(mining_core.get("powder_gemstone", 0)) + get_num(mining_core.get("powder_spent_gemstone", 0))

    glacite_powder = get_num(mining_core.get("powder_glacite_total", 0))
    if glacite_powder == 0:
        glacite_powder = get_num(mining_core.get("powder_glacite", 0)) + get_num(mining_core.get("powder_spent_glacite", 0))
    
    return {
        "skill_avg": skill_avg,
        "catacombs": cata_lvl,
        "class_name": best_class.capitalize(),
        "class_level": best_class_lvl,
        "networth": networth,
        "bank": bank,
        "purse": purse,
        "slayers": slayer_str,
        "fairy_souls": fairy_souls,
        "sb_level": sb_level,
        "bestiary": float(bestiary_lvl),
        "unique_minions": unique_minions,
        "minion_slots": minion_slots,
        "mithril_powder": mithril_powder,
        "gemstone_powder": gemstone_powder,
        "glacite_powder": glacite_powder
    }
