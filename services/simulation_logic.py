import time
from core.logger import log_info, log_debug
from services.xp_calculations import get_dungeon_level, get_total_xp_for_level
from core.config import TARGET_LEVEL


def simulate_to_level_all50(dungeon_classes: dict, floor_xp: float, bonuses: dict,
                            target_level: int = TARGET_LEVEL, max_runs: int = 200000):
    start_time = time.perf_counter()
    log_info("▶ Starting simulation...")
    log_debug(f"Initial XP: {dungeon_classes}")
    log_debug(f"Bonuses: {bonuses}")

    classes = {k: float(v) for k, v in dungeon_classes.items()}
    runs_done = {k: 0 for k in classes}
    runs = 0

    hecatomb = bonuses.get("hecatomb", 0.02)
    scarf_accessory = bonuses.get("scarf_accessory", 0.06)
    scarf_attribute = bonuses.get("scarf_attribute", 0.2)
    global_mult = bonuses.get("global", 1.0)
    mayor_mult = bonuses.get("mayor", 1.0)
    class_boosts = bonuses.get("class_boosts", {})
    
    per_class_base = {}
    for cls in classes.keys():
        boost = class_boosts.get(cls, 0.0)
        base = floor_xp * (1.0 + (hecatomb * 2) + boost + scarf_accessory + scarf_attribute) * global_mult * mayor_mult
        per_class_base[cls] = base

    log_debug(f"Base XP per run: {per_class_base}")
    log_debug(f"Bonuses used: hecatomb={hecatomb} (x2={hecatomb*2}), scarf_accessory={scarf_accessory}, scarf_attribute={scarf_attribute}, global={global_mult}, mayor={mayor_mult}")
    log_debug(f"Class boosts: {class_boosts}")

    target_xp = get_total_xp_for_level(target_level)
    
    classxpsleft = {c: max(target_xp - classes[c], 0) for c in classes}
    
    log_debug(f"Target XP for level {target_level}: {target_xp}")
    log_debug(f"Initial remaining XP: {classxpsleft}")

    while runs < max_runs:
        allnegative = True
        for c in classes:
            if classxpsleft[c] > 0:
                allnegative = False
                break
        if allnegative:
            break
        
        runs += 1
        
        maxval = -1
        maxindex = None
        for c in classes:
            if classxpsleft[c] > maxval:
                maxval = classxpsleft[c]
                maxindex = c
        
        if maxindex is None:
            break
        
        for c in classes:
            if c == maxindex:
                classxpsleft[c] -= per_class_base[c]
                runs_done[c] += 1
            else:
                classxpsleft[c] -= per_class_base[c] * 0.25
        
        for c in classes:
            classes[c] = target_xp - classxpsleft[c]

        if runs % 5000 == 0:
            avg_lvl = {c: round(get_dungeon_level(xp), 2) for c, xp in classes.items()}
            log_debug(f"#{runs:,} runs → levels: {avg_lvl}")

    elapsed = time.perf_counter() - start_time
    log_debug(f"🏁 Simulation completed after {runs:,} runs ({elapsed*1000:.2f}ms)")

    results = {}
    for c, xp in classes.items():
        lvl = get_dungeon_level(xp)
        xp_for_target = get_total_xp_for_level(target_level)
        actual_remaining = classxpsleft.get(c, 0)
        remaining = max(0, actual_remaining)
        results[c] = {
            "current_level": lvl,
            "remaining_xp": int(remaining),
            "runs_done": runs_done.get(c, 0)
        }

    return runs, results
