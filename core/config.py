import discord
try:
    from core.secrets import TOKEN, IRC_WEBHOOK_URL, ADMIN_WEBHOOK_URL, IRC_CHANNEL_ID
except ImportError:
    raise ImportError(
        "secrets.py not found! Please copy secrets.example.py to secrets.py and add your Discord bot token."
    )

try:
    from core.secrets import SOLO_CLEAR_WEBHOOK_URL
except ImportError:
    SOLO_CLEAR_WEBHOOK_URL = ""

try:
    from core.github_secrets import GITHUB_BACKUP_REPO, GITHUB_BACKUP_TOKEN
except ImportError:
    GITHUB_BACKUP_REPO = ""
    GITHUB_BACKUP_TOKEN = ""

try:
    from core.secrets import HYPIXEL_API_KEY
except ImportError:
    HYPIXEL_API_KEY = ""

from core.configuration import BotConfig

config = BotConfig()

from core.logger import set_debug_mode
set_debug_mode(config.debug_mode)

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.dm_messages = True
INTENTS.members = True

def validate_config():
    if not TOKEN:
        raise ValueError("TOKEN is missing in secrets.py!")
    if not config.owner_ids:
        print("Warning: OWNER_IDS is empty!")
