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
PRICES_CACHE_TTL = 259200 # 3 days

GLOBAL_DROPS = [
    "Ice Spray"
]

RNG_CATEGORIES = {
    "Dungeons": ["Floor 1 (Bonzo)", "Floor 2 (Scarf)", "Floor 3 (Professor)", "Floor 4 (Thorn)", "Floor 5 (Livid)", "Floor 6 (Sadan)", "Floor 7 (Necron)"],
    "Slayers": ["Revenant Horror", "Tarantula Broodfather", "Sven Packmaster", "Voidgloom Seraph", "Inferno Demonlord"],
    "Kuudra": ["Kuudra Drops"],
    "Dragons": ["Dragon Drops"],
    "Mining": ["Mining RNGs"],
    "Fishing": ["Fishing RNGs"],
    "Enchantments": ["Enchantments"],
    "Dyes": ["Dyes"],
    "Diana": ["Diana Drops"]
}

RNG_DROPS = {
    # --- DUNGEONS ---
    "Floor 7 (Necron)": [
        "Shiny Necron's Handle",
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
    "Floor 6 (Sadan)": ["Giant's Sword", "Precursor Eye", "4th Master Star"],
    "Floor 5 (Livid)": ["Shadow Fury", "3rd Master Star"],
    "Floor 4 (Thorn)": ["Spirit Wing", "Spirit Bone", "Spirit Shortbow", "2nd Master Star"],
    "Floor 3 (Professor)": ["1st Master Star"],
    "Floor 2 (Scarf)": ["Scarf's Studies"],
    "Floor 1 (Bonzo)": ["Bonzo's Staff", "Bonzo's Mask"],
    
    # --- SLAYERS ---
    "Revenant Horror": ["Scythe Blade", "Shard of the Shredded", "Warden Heart", "Beheaded Horror", "Snake Rune"],
    "Tarantula Broodfather": ["Digested Mosquito", "Tarantula Talisman", "Fly Swatter", "Tarantula Catalyst", "Shriveled Wasp", "Ensnared Snail", "Primordial Eye", "Vial of Venom"],
    "Sven Packmaster": ["Overflux Capacitor", "Red Claw Egg", "Grizzly Bait", "Couture Rune"],
    "Voidgloom Seraph": ["Judgement Core", "Exceedingly Rare Ender Artifact Upgrade", "Pocket Espresso Machine", "Handy Blood Chalice"],
    "Inferno Demonlord": ["High Class Archfiend Dice", "Wilson's Engineering Plans"],
    
    # --- KUUDRA ---
    "Kuudra Drops": ["Burning Kuudra Core", "Kuudra Mandible", "Wheel of Fate", "Enrager"],
    
    # --- DRAGONS ---
    "Dragon Drops": ["Dragon Horn", "Epic Ender Dragon", "Leg Ender Dragon"],
    
    # --- MINING ---
    "Mining RNGs": ["Divan's Alloy", "Jaderald", "Quick Claw", "Scatha Pet (Rare)", "Scatha Pet (Epic)", "Scatha Pet (Legendary)", "Shattered Locket"],
    
    # --- FISHING ---
    "Fishing RNGs": ["Radioactive Vial", "Deep Sea Orb", "Lucky Clover Core", "Flash Book"],
    
    # --- DIANA ---
    "Diana Drops": ["Chimera I", "Minos Relic", "Daedalus Stick", "Mythos Fragment", "Shimmering Wool", "Manti-core"],
    
    # --- ENCHANTS ---
    "Enchantments": [
        "First Strike V", "Life Steal V", "Looting V", "Triple-Strike V", "Chance V", "Drain (Syphon)", 
        "Syphon V", "Prosecute VI", "Cleave VI", "Execute VI", "Venomous VI",
        "Sharpness VII", "Protection VII", "Proj. Protection VII", "Power VII", "Blast Protection VII", 
        "Fire Protection VII", "Giant Killer VII", "Growth VII", "Cubism VI", "Ender Slayer VII", 
        "Smite VII", "Bane of Arthropods VII", "Luck VII", "Critical VII", "Titan Killer VII", 
        "Golden Bounty", "Pesthunting Guide", "Big Brain V"
    ],
    
    # --- DYES ---
    "Dyes": [
        "Aquamarine Dye", "Archfiend Dye", "Aurora Dye", "Bingo Blue Dye", "Black Ice Dye", "Bone Dye", 
        "Brick Red Dye", "Byzantium Dye", "Carmine Dye", "Celadon Dye", "Celeste Dye", "Chocolate Dye", 
        "Copper Dye", "Cyclamen Dye", "Dark Purple Dye", "Dung Dye", "Emerald Dye", "Flame Dye", 
        "Fossil Dye", "Frog Dye", "Frostbitten Dye", "Holly Dye", "Iceberg Dye", "Jade Dye", "Lava Dye", 
        "Livid Dye", "Lucky Dye", "Mango Dye", "Matcha Dye", "Marine Dye", "Midnight Dye", "Mocha Dye", 
        "Mythological Dye", "Nadeshiko Dye", "Necron Dye", "Nyanza Dye", "Oasis Dye", "Ocean Dye", 
        "Pastel Sky Dye", "Pearlescent Dye", "Pelt Dye", "Periwinkle Dye", "Portal Dye", "Pure Black Dye", 
        "Pure Blue Dye", "Pure White Dye", "Pure Yellow Dye", "Red Tulip Dye", "Rose Dye", "Sangria Dye", 
        "Secret Dye", "Snowflake Dye", "Spooky Dye", "Sunflower Dye", "Sunset Dye", "Treasure Dye", 
        "Warden Dye", "Wild Strawberry Dye", "Tentacle Dye"
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
    "2nd Master Star": "<:SkyBlock_items_second_master_star:1448305519021264987>",
    "3rd Master Star": "<:SkyBlock_items_third_master_star:1448305516605603921>",
    "4th Master Star": "<:SkyBlock_items_fourth_master_star:1448305514776760520>",
    "5th Master Star": "<:SkyBlock_items_fifth_master_star:1448305512876609732>",
    "50% M7 Skeleton Master Chestplate": "<:SkyBlock_items_Skeleton_Master:1448305511488421968>",
    "Implosion": "<a:SkyBlock_items_scroll:1448304563923718194>",
    "Wither Shield": "<a:SkyBlock_items_scroll:1448304563923718194>",
    "Shadow Warp": "<a:SkyBlock_items_scroll:1448304563923718194>",
    "Necron's Handle": "<a:SkyBlock_items_necrons_handle:1448302537144008896>",
    "Shiny Necron's Handle": "<a:SkyBlock_items_necrons_handle:1448302537144008896>",
    "Ice Spray": "<a:SkyBlock_items_enchanted_stick:1449788369709039637>"
}

DROP_IDS = {
    # --- DUNGEONS ---
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
    "Precursor Eye": "PRECURSOR_EYE",
    "4th Master Star": "FOURTH_MASTER_STAR",
    "Necron's Handle": "NECRON_HANDLE",
    "Shiny Necron's Handle": "SHINY_NECRON_HANDLE",
    "Implosion": "IMPLOSION_SCROLL",
    "Wither Shield": "WITHER_SHIELD_SCROLL",
    "Shadow Warp": "SHADOW_WARP_SCROLL",
    "5th Master Star": "FIFTH_MASTER_STAR",
    "Master Skull - Tier 5": "MASTER_SKULL_TIER_5",
    "Thunderlord VII": "ENCHANTMENT_THUNDERLORD_7",
    "Dark Claymore": "DARK_CLAYMORE",
    "50% M7 Skeleton Master Chestplate": "SKELETON_MASTER_CHESTPLATE_50",
    "Ice Spray": "ICE_SPRAY_WAND",
    
    # --- SLAYERS ---
    "Scythe Blade": "SCYTHE_BLADE",
    "Shard of the Shredded": "SHARD_OF_THE_SHREDDED",
    "Warden Heart": "WARDEN_HEART",
    "Beheaded Horror": "BEHEADED_HORROR",
    "Snake Rune": "SNAKE_RUNE;1",
    "Digested Mosquito": "DIGESTED_MOSQUITO",
    "Tarantula Talisman": "TARANTULA_TALISMAN",
    "Fly Swatter": "FLY_SWATTER",
    "Tarantula Catalyst": "SPIDER_CATALYST",
    "Shriveled Wasp": "SHRIVELED_WASP",
    "Ensnared Snail": "ENSNARED_SNAIL",
    "Primordial Eye": "PRIMORDIAL_EYE",
    "Vial of Venom": "VIAL_OF_VENOM",
    "Overflux Capacitor": "OVERFLUX_CAPACITOR",
    "Red Claw Egg": "RED_CLAW_EGG",
    "Grizzly Bait": "GRIZZLY_BAIT",
    "Couture Rune": "COUTURE_RUNE;1",
    "Judgement Core": "JUDGEMENT_CORE",
    "Exceedingly Rare Ender Artifact Upgrade": "EXCEEDINGLY_RARE_ENDER_ARTIFACT_UPGRADER",
    "Pocket Espresso Machine": "POCKET_ESPRESSO_MACHINE",
    "Handy Blood Chalice": "HANDY_BLOOD_CHALICE",
    "High Class Archfiend Dice": "HIGH_CLASS_ARCHFIEND_DICE",
    "Wilson's Engineering Plans": "WILSON_ENGINEERING_PLANS",

    # --- KUUDRA ---
    "Burning Kuudra Core": "BURNING_KUUDRA_CORE",
    "Kuudra Mandible": "KUUDRA_MANDIBLE",
    "Wheel of Fate": "WHEEL_OF_FATE",
    "Enrager": "ENRAGER",

    # --- DRAGONS ---
    "Dragon Horn": "DRAGON_HORN",
    "Epic Ender Dragon": "ENDER_DRAGON;3",
    "Leg Ender Dragon": "ENDER_DRAGON;4", 

    # --- MINING ---
    "Divan's Alloy": "DIVAN_ALLOY",
    "Jaderald": "JADERALD",
    "Quick Claw": "PET_ITEM_QUICK_CLAW",
    "Scatha Pet (Rare)": "SCATHA;2",
    "Scatha Pet (Epic)": "SCATHA;3",
    "Scatha Pet (Legendary)": "SCATHA;4",
    "Shattered Locket": "SHATTERED_PENDANT",

    # --- FISHING ---
    "Radioactive Vial": "RADIOACTIVE_VIAL",
    "Deep Sea Orb": "DEEP_SEA_ORB",
    "Lucky Clover Core": "PET_ITEM_LUCKY_CLOVER_DROP",
    "Flash Book": "ENCHANTMENT_ULTIMATE_FLASH_1",

    # --- DIANA ---
    "Chimera I": "ENCHANTMENT_ULTIMATE_CHIMERA_1",
    "Minos Relic": "MINOS_RELIC",
    "Daedalus Stick": "DAEDALUS_STICK",
    "Mythos Fragment": "MYTHOS_FRAGMENT",
    "Shimmering Wool": "SHIMMERING_WOOL",
    "Manti-core": "MANTI_CORE",

    # --- ENCHANTS ---
    "First Strike V": "ENCHANTMENT_FIRST_STRIKE_5",
    "Life Steal V": "ENCHANTMENT_LIFE_STEAL_5",
    "Looting V": "ENCHANTMENT_LOOTING_5",
    "Triple-Strike V": "ENCHANTMENT_TRIPLE_STRIKE_5",
    "Chance V": "ENCHANTMENT_CHANCE_5",
    "Drain (Syphon)": "ENCHANTMENT_SYPHON_5", 
    "Syphon V": "ENCHANTMENT_SYPHON_5",
    "Prosecute VI": "ENCHANTMENT_PROSECUTE_6",
    "Cleave VI": "ENCHANTMENT_CLEAVE_6",
    "Execute VI": "ENCHANTMENT_EXECUTE_6",
    "Venomous VI": "ENCHANTMENT_VENOMOUS_6",
    "Sharpness VII": "ENCHANTMENT_SHARPNESS_7",
    "Protection VII": "ENCHANTMENT_PROTECTION_7",
    "Proj. Protection VII": "ENCHANTMENT_PROJECTILE_PROTECTION_7",
    "Power VII": "ENCHANTMENT_POWER_7",
    "Blast Protection VII": "ENCHANTMENT_BLAST_PROTECTION_7",
    "Fire Protection VII": "ENCHANTMENT_FIRE_PROTECTION_7",
    "Giant Killer VII": "ENCHANTMENT_GIANT_KILLER_7",
    "Growth VII": "ENCHANTMENT_GROWTH_7",
    "Cubism VI": "ENCHANTMENT_CUBISM_6",
    "Ender Slayer VII": "ENDSTONE_IDOL",
    "Smite VII": "SEVERED_HAND",
    "Bane of Arthropods VII": "ENSNARED_SNAIL",
    "Luck VII": "ENCHANTMENT_LUCK_7",
    "Critical VII": "ENCHANTMENT_CRITICAL_7",
    "Titan Killer VII": "ENCHANTMENT_TITAN_KILLER_7",
    "Golden Bounty": "GOLDEN_BOUNTY",
    "Pesthunting Guide": "PESTHUNTING_GUIDE",
    "Big Brain V": "ENCHANTMENT_BIG_BRAIN_5",

    # --- DYES ---
    "Aquamarine Dye": "DYE_AQUAMARINE",
    "Archfiend Dye": "DYE_ARCHFIEND",
    "Aurora Dye": "DYE_AURORA",
    "Bingo Blue Dye": "DYE_BINGO_BLUE",
    "Black Ice Dye": "DYE_BLACK_ICE",
    "Bone Dye": "DYE_BONE",
    "Brick Red Dye": "DYE_BRICK_RED",
    "Byzantium Dye": "DYE_BYZANTIUM",
    "Carmine Dye": "DYE_CARMINE",
    "Celadon Dye": "DYE_CELADON",
    "Celeste Dye": "DYE_CELESTE",
    "Chocolate Dye": "DYE_CHOCOLATE",
    "Copper Dye": "DYE_COPPER",
    "Cyclamen Dye": "DYE_CYCLAMEN",
    "Dark Purple Dye": "DYE_DARK_PURPLE",
    "Dung Dye": "DYE_DUNG",
    "Emerald Dye": "DYE_EMERALD",
    "Flame Dye": "DYE_FLAME",
    "Fossil Dye": "DYE_FOSSIL",
    "Frog Dye": "DYE_FROG",
    "Frostbitten Dye": "DYE_FROSTBITTEN",
    "Holly Dye": "DYE_HOLLY",
    "Iceberg Dye": "DYE_ICEBERG",
    "Jade Dye": "DYE_JADE",
    "Lava Dye": "DYE_LAVA",
    "Livid Dye": "DYE_LIVID",
    "Lucky Dye": "DYE_LUCKY",
    "Mango Dye": "DYE_MANGO",
    "Matcha Dye": "DYE_MATCHA",
    "Marine Dye": "DYE_MARINE",
    "Midnight Dye": "DYE_MIDNIGHT",
    "Mocha Dye": "DYE_MOCHA",
    "Mythological Dye": "DYE_MYTHOLOGICAL",
    "Nadeshiko Dye": "DYE_NADESHIKO",
    "Necron Dye": "DYE_NECRON",
    "Nyanza Dye": "DYE_NYANZA",
    "Oasis Dye": "DYE_OASIS",
    "Ocean Dye": "DYE_OCEAN",
    "Pastel Sky Dye": "DYE_PASTEL_SKY",
    "Pearlescent Dye": "DYE_PEARLESCENT",
    "Pelt Dye": "DYE_PELT",
    "Periwinkle Dye": "DYE_PERIWINKLE",
    "Portal Dye": "DYE_PORTAL",
    "Pure Black Dye": "DYE_PURE_BLACK",
    "Pure Blue Dye": "DYE_PURE_BLUE",
    "Pure White Dye": "DYE_PURE_WHITE",
    "Pure Yellow Dye": "DYE_PURE_YELLOW",
    "Red Tulip Dye": "DYE_RED_TULIP",
    "Rose Dye": "DYE_ROSE",
    "Sangria Dye": "DYE_SANGRIA",
    "Secret Dye": "DYE_SECRET",
    "Snowflake Dye": "DYE_SNOWFLAKE",
    "Spooky Dye": "DYE_SPOOKY",
    "Sunflower Dye": "DYE_SUNFLOWER",
    "Sunset Dye": "DYE_SUNSET",
    "Tentacle Dye": "TENTACLE_DYE",
    "Treasure Dye": "DYE_TREASURE",
    "Warden Dye": "DYE_WARDEN",
    "Wild Strawberry Dye": "DYE_WILD_STRAWBERRY"
}

CHEST_COSTS = {
    # F7
    "Shiny Necron's Handle": 100_000_000,
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
    "Bonzo's Mask": 1_250_000
}

def validate_config():
    if not TOKEN:
        raise ValueError("TOKEN is missing in secrets.py!")
    if not OWNER_IDS:
        print("Warning: OWNER_IDS is empty!")

CONGRATS_GIFS = [
    "https://c.tenor.com/n5-r2F_JeGMAAAAd/tenor.gif",
    "https://c.tenor.com/xAW8c7Z8-3cAAAAd/tenor.gif",
    "https://c.tenor.com/4YDfECEyEtwAAAAd/tenor.gif",
    "https://c.tenor.com/8Zvt_ouixT8AAAAd/tenor.gif",
    "https://c.tenor.com/I5LkHI4yrRcAAAAd/tenor.gif",
    "https://c.tenor.com/JDUuuveDLeQAAAAd/tenor.gif",
    "https://c.tenor.com/Xqc4YXfCySEAAAAd/tenor.gif",
    "https://c.tenor.com/UgvKJP8OIHoAAAAd/tenor.gif",
    "https://c.tenor.com/O57p6KOsleoAAAAd/tenor.gif",
    "https://c.tenor.com/gdBh7nScJMYAAAAd/tenor.gif",
    "https://c.tenor.com/mamnZXgZxqIAAAAd/tenor.gif",
    "https://c.tenor.com/lfbOYamuNSoAAAAd/tenor.gif",
    "https://c.tenor.com/8WpxdEqUcWEAAAAd/tenor.gif",
    "https://c.tenor.com/jI79BCqsw68AAAAd/tenor.gif",
    "https://c.tenor.com/XgzhRq264JcAAAAd/tenor.gif",
    "https://c.tenor.com/VngFH2yD0RAAAAAC/tenor.gif",
    "https://c.tenor.com/JEFazVKAde0AAAAd/tenor.gif",
    "https://c.tenor.com/GEAz2m-SWAsAAAAd/tenor.gif",
    "https://c.tenor.com/LcsbStHRMCMAAAAC/tenor.gif",
    "https://c.tenor.com/Dgmg1Dzjq-oAAAAd/tenor.gif",
    "https://media.tenor.com/UlNu8AJREWwAAAAM/kermit-the-frog-go-the-fuck-outside-punk.gif",
    "https://i.imgflip.com/8axaft.gif",
    "https://media.tenor.com/0lsV1eolzSMAAAAM/shower-soap.gif",
    "https://media.tenor.com/jcG6b0cZgQEAAAAM/homer-bath.gif",
    "https://media.tenor.com/XX7CWmfJ8ZIAAAAM/shower-dogs.gif",
    "https://img1.picmix.com/output/pic/normal/2/8/0/6/11396082_40409.gif",
    "https://media.tenor.com/MMo4B6tp-GMAAAAM/job-application.gif",
    "https://media.tenor.com/Rs-PNa8EBFcAAAAM/job-jumpscare-job-application.gif",
    "https://media.tenor.com/JkMtMAjXHS8AAAAM/job-job-application.gif",
    "https://c.tenor.com/xyMEZ2xCttcAAAAC/tenor.gif",
    "https://media.tenor.com/Kp0_YKtqqXIAAAAe/job-application.png",
    "https://media.tenor.com/Gk2yr271HUsAAAAe/job-application.png",
    "https://media.tenor.com/UsDCL6bOIT4AAAAM/touch-grass-touch.gif",
    "https://i.imgflip.com/6f5788.gif",
    "https://media2.giphy.com/media/v1.Y2lkPTZjMDliOTUyODIyMXFzamljbm9sc2d1NnVzdDJvYXllN2Jjcm14Y25kYm00cGF5ZSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/bum2UBz4nR9IxZmWde/giphy-downsized.gif",
    "https://media3.giphy.com/media/v1.Y2lkPTZjMDliOTUyODVzb2JyeXpveng0Z2FocHdsczF6enZqbDN6NDBiZmhuaWlndXl1NiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/JyOtBwVBKFoeIQ14Po/200w_d.gif",
    "https://media.discordapp.net/attachments/1122856048374595647/1152961363614908497/JIXMersMo8xcnmXQ.gif?ex=69591b72&is=6957c9f2&hm=40759ab651245f54ba2e5f10640403b43806c1cfe5cbf542ec4be9d2a4607437&=&width=585&height=75",
    "https://media.discordapp.net/attachments/1263938847910269000/1276128862849339393/minus-infinite-social-credit-china.gif?ex=6958f21e&is=6957a09e&hm=34acdfe4c04a23c4d4e4256f908b7523d41670e382018038544bfc3aeb2823ff&=&width=800&height=450",
    "https://media.discordapp.net/attachments/1263938847910269000/1276125652730380349/gypsycrusadervshoke.gif?ex=6958ef20&is=69579da0&hm=545b63f83cb383740758971ca6940b9f9b22d1bd9d832ed09089d9246c15ffc0&=&width=800&height=503",
    "https://media.discordapp.net/attachments/1263938847910269000/1276130366847057950/redditsave.com_y2dkx7x76f481.gif?ex=6958f384&is=6957a204&hm=da6abb1ff3db36d77abaf35e8103173e849eb85297686fb2edcb1f1dec3cb57f&=&width=800&height=800",
    "https://media.discordapp.net/attachments/1236050415020277840/1267879801566269481/caption.gif?ex=69594214&is=6957f094&hm=2581bd92a3109cad09926351f8b69d6bc279a5003b64536ddb50684697b5eb5d&=&width=750&height=934",
    "https://media.discordapp.net/attachments/993269478060195950/1118188097222488104/ED6EFBC5-A68E-48C6-9103-B123B1ECC22D.gif?ex=69592a51&is=6957d8d1&hm=9b2954746a2d198cd8442724df3d8ccb09134436db77a0cdfdbc5b13cf79876e&=&width=254&height=60",
    "https://cdn.discordapp.com/attachments/982414624844554241/1185533720233508894/tM1qwcbNS15DWrFk.gif?ex=6958f3d1&is=6957a251&hm=9708f3e09cc4e9d50d986acaf7086d2177ba9e1c4bc09a6b96214851f9a9c28a",
    "https://media.discordapp.net/attachments/1255211359227084821/1269003922413060176/caption.gif?ex=6958bbc0&is=69576a40&hm=aec2497118642f46043347f8f462cc2f4e9fdd19d60cd0882d414949b84efcd8&=&width=294&height=375",
    "https://media.discordapp.net/attachments/773213826186739775/979470724098039878/puzzlehater.gif.gif?ex=6958c972&is=695777f2&hm=f9d81391304ff5749a3deeea31c77a76627bb1b7c14c872e148fe28afd26344a&=&width=168&height=168",
    "https://media.discordapp.net/attachments/1347938901825814592/1400962571082924132/MedalTVMinecraft20250731185114-1753971386_1.gif?ex=6958e9d1&is=69579851&hm=dcaf2ed25e77aca670c8f26e47e332c73c3d202af44bb5f5140369b7eda85757&=&width=865&height=485",
    "https://media.discordapp.net/attachments/1275995649988628574/1300897696269209681/wdhu.gif?ex=6958bf24&is=69576da4&hm=dc133d83ca5895f9975fee6ce031e2ad7bd4aad3cd84006b75de18ae3093abc7&=&width=658&height=849",
    "https://media.discordapp.net/attachments/1172235640117669921/1402064324805132479/a276ic.gif?ex=6958f768&is=6957a5e8&hm=01f61333a5246f22918ca0791a5ea7950a9470ce5d55f8e55491c423eab243ec&=&width=450&height=236",
    "https://media.discordapp.net/attachments/1397725617239363625/1403384070540365914/meowmeow.gif?ex=69592744&is=6957d5c4&hm=39de6c27bf9cca6fd7e61e2b61e8d232ce4bf1979e960d483204ba27e93b4605&=&width=445&height=445",
    "https://media.discordapp.net/attachments/1379474866725453988/1420884081176084551/togif.gif?ex=6958e0ab&is=69578f2b&hm=11c34bd40104687de43199b1e43539f6f8fa59083525b3736cf39d1f8d66fc70&=&width=1545&height=875",
    "https://media.discordapp.net/attachments/1160332174344597554/1228784996169552055/thirty11.gif?ex=695a12f4&is=6958c174&hm=3a08d3b7af929b028f99fe4eb0916043c3e1dc22425ca48940654ae46fe6febc&=&width=288&height=199",
    "https://media.discordapp.net/attachments/1423627182697086996/1424142662197317724/attachment.gif?ex=695a2f75&is=6958ddf5&hm=59a83af7929562b7a7cd568d4c21b00b58e260c703d787384661cf5683150c63&=&width=960&height=1075",
    "https://media.discordapp.net/attachments/1420147559011192924/1447572753149591592/togif.gif?ex=6959122e&is=6957c0ae&hm=b55333c72e8ef1c3e5b9cc6247a0b414412b0d1e6e49973edb9dd3919d74b401&=&width=1024&height=796"
]
