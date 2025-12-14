import discord

try:
    from core.secrets import TOKEN
except ImportError:
    raise ImportError(
        "secrets.py not found! Please copy secrets.example.py to secrets.py and add your Discord bot token."
    )

XP_PER_RUN_DEFAULT = 300000.0
TARGET_LEVEL = 50
DEBUG_MODE = True
SKELETON_MASTER_CHESTPLATE_50 = "SKELETON_MASTER_CHESTPLATE_50"

OWNER_IDS = [
    377351386637271041, # BLACKUM
    679725029109399574, # ATK (TESTER)
]

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.dm_messages = True
INTENTS.members = True

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

PROFILE_CACHE_TTL = 60 # 1 minute
PRICES_CACHE_TTL = 3600 # 1 hour

GLOBAL_DROPS = [
    "Ice Spray"
]

RNG_DROPS = {
    "Floor 7 (Necron)": [
        "Necron's Handle",
        "Implosion",
        "Wither Shield",
        "Shadow Warp",
        "5th Master Star",
        "Master Skull - Tier 5",
        "50% M7 Skeleton Master Chestplate",
        "Thunderlord VII",
        "Dark Claymore"
    ],
    "Floor 6 (Sadan)": [
        "Giant's Sword",
        "Precursor Eye",
        "4th Master Star"
    ],
    "Floor 5 (Livid)": [
        "Shadow Fury",
        "3rd Master Star"
    ],
    "Floor 4 (Thorn)": [
        "Spirit Wing",
        "Spirit Bone",
        "Spirit Shortbow",
        "2nd Master Star"
    ],
    "Floor 3 (Professor)": [
        "1st Master Star"
    ],
    "Floor 2 (Scarf)": [
        "Scarf's Studies"
    ],
    "Floor 1 (Bonzo)": [
        "Bonzo's Staff",
        "Bonzo's Mask"
    ]
}

DROP_EMOJIS = {
    "Master Skull - Tier 5": "<:SkyBlock_items_master_skull:1448310369360809994>",
    "Thunderlord VII": "<a:SkyBlock_items_enchanted_book:1448310367653728336>",
    "Giant's Sword": "<:Minecraft_items_iron_sword:1448310365124563118>",
    "Precursor Eye": "<:SkyBlock_items_precursor_eye:1448310361890750517>",
    "Shadow Fury": "<:Minecraft_items_diamond_sword:1448310360003317911>",
    "Spirit Shortbow": "<:Minecraft_items_bow:1448311754164539462>",
    "Spirit Bone": "<:SkyBlock_items_spirit_bone:1448311755636736040>",
    "Spirit Wing": "<:SkyBlock_items_spirit_wing:1448311757087969311>",
    "Scarf's Studies": "<:SkyBlock_items_scarf_thesis:1448310358447231027>",
    "Dark Claymore": "<:Minecraft_items_stone_sword:1448310356781961297>",
    "Bonzo's Staff": "<:Minecraft_items_blaze_rod:1448310353166340248>",
    "Bonzo's Mask": "<:SkyBlock_items_bonzo_mask:1448310351631351929>",
    "1st Master Star": "<:SkyBlock_items_first_master_star:1448305520921411595>",
    "2nd Master Star": "<:SkyBlock_items_second_master_sta:1448305519021264987>",
    "3rd Master Star": "<:SkyBlock_items_third_master_star:1448305516605603921>",
    "4th Master Star": "<:SkyBlock_items_fourth_master_sta:1448305514776760520>",
    "5th Master Star": "<:SkyBlock_items_fifth_master_star:1448305512876609732>",
    "50% M7 Skeleton Master Chestplate": "<:SkyBlock_items_Skeleton_Master:1448305511488421968>",
    "Implosion": "<a:SkyBlock_items_scroll:1448304563923718194>",
    "Wither Shield": "<a:SkyBlock_items_scroll:1448304563923718194>",
    "Shadow Warp": "<a:SkyBlock_items_scroll:1448304563923718194>",
    "Necron's Handle": "<a:SkyBlock_items_necrons_handle:1448302537144008896>",
    "Ice Spray": "<a:SkyBlock_items_enchanted_stick:1449788369709039637>"
}

DROP_IDS = {
    "Bonzo's Staff": "BONZO_STAFF",
    "Bonzo's Mask": "BONZO_MASK",
    "Scarf's Studies": "SCARF_STUDIES",
    "1st Master Star": "FIRST_MASTER_STAR",
    "Spirit Wing": "SPIRIT_WING",
    "Spirit Bone": "SPIRIT_BONE", 
    "Spirit Shortbow": "ITEM_SPIRIT_BOW",
    "2nd Master Star": "SECOND_MASTER_STAR",
    "Shadow Fury": "SHADOW_FURY",
    "3rd Master Star": "THIRD_MASTER_STAR",
    "Giant's Sword": "GIANTS_SWORD", 
    "Precursor Eye": "PRECURSOR_EYEd",
    "4th Master Star": "FOURTH_MASTER_STAR",
    "Necron's Handle": "NECRON_HANDLE",
    "Implosion": "IMPLOSION_SCROLL",
    "Wither Shield": "WITHER_SHIELD_SCROLL",
    "Shadow Warp": "SHADOW_WARP_SCROLL",
    "5th Master Star": "FIFTH_MASTER_STAR",
    "Master Skull - Tier 5": "MASTER_SKULL_TIER_5",
    "Thunderlord VII": "ENCHANTMENT_THUNDERLORD_7",
    "Dark Claymore": "DARK_CLAYMORE",
    "50% M7 Skeleton Master Chestplate": "SKELETON_MASTER_CHESTPLATE_50",
    "Ice Spray": "ICE_SPRAY_WAND"
}

CHEST_COSTS = {
    # F7
    "Necron's Handle": 100_000_000,
    "Implosion": 50_000_000, 
    "Wither Shield": 50_000_000,
    "Shadow Warp": 50_000_000,
    "5th Master Star": 9_000_000,
    "Master Skull - Tier 5": 32_000_000,
    "Thunderlord VII": 2_000_000, 
    "Dark Claymore": 150_000_000,
    # F6
    "Giant's Sword": 25_000_000,
    "Precursor Eye": 30_000_000, 
    "4th Master Star": 8_000_000,
    # F5
    "Shadow Fury": 15_000_000,
    "3rd Master Star": 7_000_000,
    # F4
    "Spirit Wing": 2_000_000,
    "Spirit Bone": 1_500_000,
    "Spirit Shortbow": 4_000_000,
    "2nd Master Star": 6_000_000,
    # F3
    "1st Master Star": 5_000_000,
    # F2
    "Scarf's Studies": 500_000,
    # F1
    "Bonzo's Staff": 2_250_000,
    "Bonzo's Mask": 1_250_000,
    
    
    
    
    
    
}

def validate_config():
    if not TOKEN:
        raise ValueError("TOKEN is missing in secrets.py!")
    if not OWNER_IDS:
        print("Warning: OWNER_IDS is empty!")
