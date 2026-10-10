import re


def clean_mc_formatting(text):
    if not text: return ""
    return re.sub(r'§.', '', text).strip()


# Built from the runs in the current API response only; teammate history is never stored.
def get_teammates(user_uuid, runs):
    user_uuid = str(user_uuid).replace("-", "")
    user_data = {}

    sorted_runs = sorted(runs or [], key=lambda x: x.get("completion_ts") or x.get("timestamp") or 0)

    for run in sorted_runs:
        raw_ts = run.get("completion_ts") or run.get("timestamp") or 0
        ts = raw_ts / 1000

        type_str = run.get("type", "").upper()
        d_type = "kuudra" if type_str == "KUUDRA" else run.get("dungeon_type", "catacombs")
        
        if d_type == "kuudra":
            tier_id = run.get("tier_id", "NONE").upper()
            kuudra_map = {"HOT": "Hot", "BURNING": "Burning", "FIERY": "Fiery", "INFERNAL": "Infernal"}
            floor_name = kuudra_map.get(tier_id, "Basic")
        else:
            tier = run.get("dungeon_tier", 0)
            is_master = "master" in d_type
            floor_prefix = "M" if is_master else "F"
            floor_name = f"{floor_prefix}{tier}"
            if tier == 0 and not is_master: floor_name = "Entrance"

        for p in run.get("participants", []):
            p_uuid = str(p.get("player_uuid", "")).replace("-", "")
            if not p_uuid or p_uuid == user_uuid: continue
            
            if p_uuid not in user_data:
                user_data[p_uuid] = {
                    "ign": "Unknown",
                    "count": 0,
                    "last_floor": floor_name,
                    "last_ts": ts,
                    "last_class": "Unknown",
                    "last_class_level": 0
                }
            
            tm = user_data[p_uuid]
            tm["count"] += 1
            
            tm["last_floor"] = floor_name
            tm["last_ts"] = ts
            
            raw_name = p.get("display_name", "Unknown")
            tm["ign"] = clean_mc_formatting(raw_name.split(":")[0])
            
            clean_display = clean_mc_formatting(raw_name)
            if ":" in clean_display:
                parts = clean_display.split(":")
                if len(parts) > 1:
                    class_part = parts[1].strip()
                    if "(" in class_part:
                        c_name = class_part.split("(")[0].strip()
                        try:
                            c_lvl = int(class_part.split("(")[1].replace(")", "").strip())
                        except ValueError:
                            c_lvl = 0
                        tm["last_class"] = c_name
                        tm["last_class_level"] = c_lvl
                    elif d_type == "kuudra":
                        tm["last_class"] = class_part
                        tm["last_class_level"] = -1

    teammates = [(data.get("ign", "Unknown"), data) for data in user_data.values()]
    teammates.sort(key=lambda x: x[1]["count"], reverse=True)
    return teammates
