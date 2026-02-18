import discord
try:
    from core.secrets import TOKEN, IRC_WEBHOOK_URL, IRC_CHANNEL_ID
except ImportError:
    raise ImportError(
        "secrets.py not found! Please copy secrets.example.py to secrets.py and add your Discord bot token."
    )

from core.configuration import BotConfig

config = BotConfig()

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.dm_messages = True
INTENTS.members = True

def validate_config():
    if not TOKEN:
        raise ValueError("TOKEN is missing in secrets.py!")
    if not config.owner_ids:
        print("Warning: OWNER_IDS is empty!")
