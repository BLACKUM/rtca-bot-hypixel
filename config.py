import discord

try:
    from secrets import TOKEN
except ImportError:
    raise ImportError(
        "secrets.py not found! Please copy secrets.example.py to secrets.py and add your Discord bot token."
    )

XP_PER_RUN_DEFAULT = 300000.0
TARGET_LEVEL = 50
DEBUG_MODE = True

OWNER_IDS = [
    377351386637271041, # BLACKUM
    679725029109399574, # ATK (TESTER)
]

INTENTS = discord.Intents.default()
INTENTS.message_content = True

DUNGEON_XP = [
    0, 50, 75, 110, 160, 230, 330, 470, 670, 950, 1340,
    1890, 2665, 3760, 5260, 7380, 10300, 14400, 20000, 27600,
    38000, 52500, 71500, 97000, 132000, 180000, 243000, 328000,
    445000, 600000, 800000, 1065000, 1410000, 1900000, 2500000,
    3300000, 4300000, 5600000, 7200000, 9200000, 12000000, 15000000,
    19000000, 24000000, 30000000, 38000000, 48000000, 60000000, 75000000,
    93000000, 116250000, 200000000
]

FLOOR_XP_MAP = {
    "M7": 300000, "M6": 100000, "M5": 70000, "M4": 55000, 
    "M3": 35000, "M2": 20000, "M1": 15000,
    "F7": 28000, "F6": 4880, "F5": 2400, "F4": 1420, 
    "F3": 560, "F2": 220, "F1": 110, "ENTRANCE": 55
}

CACHE_TTL = 60 # 1 minute
