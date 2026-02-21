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
    if isinstance(val, str):
        try:
            return float(val)
        except ValueError:
            return default
    if isinstance(val, dict):
        for key in ["networth", "milestone", "last_milestone", "experience", "total", "level", "amount", "value", "current"]:
            if key in val:
                return get_num(val[key], default)
    return default


def get_minion_slots(unique: int) -> int:
    thresholds = [
        5, 15, 25, 35, 45, 55, 65, 75, 85, 95,
        125, 160, 200, 250, 310, 390, 480, 590, 720, 880
    ]
    slots = 5
    for t in thresholds:
        if unique >= t:
            slots += 1
        else:
            break
    return slots


def parse_profile_stats(member: dict, profile: dict) -> dict:
    # Skill Average
    skills_data = member.get("skills", {})
    if not skills_data:
        # Check in player_data.skills
        skills_data = member.get("player_data", {}).get("skills", {})
    if not skills_data:
        # Check in experience (legacy or specific proxy formats)
        skills_data = member.get("experience", {})

    total_skill_lvl = 0
    skills_count = 0
    for s in SKILLS:
        # try member.skill_farming_level
        lvl = member.get(f"skill_{s}_level")
        if lvl is None:
            # try skills_data.farming.level
            lvl = skills_data.get(s, {}).get("level")
        if lvl is None:
            # try skills_data.farming.current
             lvl = skills_data.get(s, {}).get("current")
        if lvl is None:
            # try member.experience_skill_farming (calculating from XP would be complex, but let's see if there's a level there)
            lvl = member.get(f"experience_skill_{s}_level")

        total_skill_lvl += get_num(lvl)
        skills_count += 1

    skill_avg = total_skill_lvl / skills_count if skills_count > 0 else 0

    # Dungeons
    dungeons = member.get("dungeons", {})
    cata_xp = get_num(dungeons.get("d_types", {}).get("catacombs", {}).get("experience", 0))
    if cata_xp == 0:
        cata_xp = get_num(dungeons.get("dungeon_types", {}).get("catacombs", {}).get("experience", 0))
    cata_lvl = get_dungeon_level(cata_xp)

    classes = dungeons.get("player_classes", {})
    best_class = "None"
    best_xp = -1
    for cls, data in classes.items():
        xp = get_num(data.get("experience", 0))
        if xp > best_xp:
            best_xp = xp
            best_class = cls

    best_class_lvl = get_dungeon_level(best_xp) if best_xp != -1 else 0

    # Networth
    nw_data = member.get("networth", {})
    networth = get_num(nw_data.get("networth", 0))
    if networth == 0:
        networth = get_num(member.get("nw", 0))

    bank = get_num(profile.get("banking", {}).get("balance", 0))
    purse = get_num(member.get("currencies", {}).get("coin_purse", 0))

    if networth == 0:
        networth = purse + bank

    # Slayers
    slayers_data = member.get("slayer", {}).get("slayer_bosses", {})
    slayer_levels = []
    for s_type in SLAYER_TYPES:
        xp = get_num(slayers_data.get(s_type, {}).get("xp", 0))
        slayer_levels.append(str(get_slayer_level(xp, s_type)))

    slayer_str = " / ".join(slayer_levels)

    # Fairy Souls
    fairy_souls = get_num(member.get("fairy_soul", {}).get("total_collected", 0))
    if fairy_souls == 0:
         fairy_souls = get_num(member.get("fairy_souls_collected", 0))
    if fairy_souls == 0:
         fairy_souls = get_num(member.get("fairy_souls", {}).get("collected", 0))

    # Skyblock Level
    sb_exp = get_num(member.get("leveling", {}).get("experience", 0))
    sb_level = sb_exp / SB_LEVEL_DIVISOR

    # Bestiary
    bestiary = member.get("bestiary", {})
    bestiary_lvl = get_num(bestiary.get("milestone", 0))
    if bestiary_lvl == 0:
        bestiary_lvl = get_num(bestiary.get("level", 0))
    if bestiary_lvl == 0 and "milestone" in bestiary and isinstance(bestiary["milestone"], dict):
        bestiary_lvl = get_num(bestiary["milestone"].get("last_milestone", 0))

    # Minions
    unique_minions = len(member.get("player_data", {}).get("crafted_generators", []))
    minion_slots = get_minion_slots(unique_minions)

    # Powders
    mining_core = member.get("mining_core", {})
    powders = mining_core.get("powders", {})

    def get_total_powder(p_type: str) -> float:
        data = powders.get(p_type, {})
        if data:
            return get_num(data.get("total", data.get("current", 0) + data.get("spent", 0)))
        total = get_num(mining_core.get(f"powder_{p_type}_total", 0))
        if total == 0:
            total = get_num(mining_core.get(f"powder_{p_type}", 0)) + get_num(mining_core.get(f"powder_spent_{p_type}", 0))
        if total == 0:
            total = get_num(mining_core.get(f"{p_type}_powder", 0))
        return total

    mithril_powder = get_total_powder("mithril")
    gemstone_powder = get_total_powder("gemstone")
    glacite_powder = get_total_powder("glacite")

    maxwell = member.get("accessory_bag_storage", {})
    magical_power = get_num(maxwell.get("highest_magical_power", 0))

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
        "glacite_powder": glacite_powder,
        "magical_power": magical_power
    }
