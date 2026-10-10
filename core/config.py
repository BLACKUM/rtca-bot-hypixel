import discord
try:
    from core.secrets import TOKEN, HYPIXEL_API_KEY
except ImportError:
    raise ImportError(
        "secrets.py not found or incomplete! Please copy secrets.example.py to secrets.py and add your Discord bot token and Hypixel API key."
    )

try:
    from core.github_secrets import GITHUB_BACKUP_REPO, GITHUB_BACKUP_TOKEN
except ImportError:
    GITHUB_BACKUP_REPO = ""
    GITHUB_BACKUP_TOKEN = ""

from core.configuration import BotConfig

config = BotConfig()

from core.logger import set_debug_mode
set_debug_mode(config.debug_mode)

INTENTS = discord.Intents.default()
INTENTS.dm_messages = True
INTENTS.members = True

def validate_config():
    if not TOKEN:
        raise ValueError("TOKEN is missing in secrets.py!")
    if not HYPIXEL_API_KEY:
        raise ValueError("HYPIXEL_API_KEY is missing in secrets.py!")
    if not config.owner_ids:
        print("Warning: OWNER_IDS is empty!")
