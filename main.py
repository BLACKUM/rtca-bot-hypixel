from discord.ext import commands, tasks
from core.config import TOKEN, INTENTS, validate_config
from core.logger import log_info, log_error
from services.daily_manager import daily_manager
from services.api import get_dungeon_xp
import asyncio
import os

bot = commands.Bot(command_prefix="!", intents=INTENTS)

@tasks.loop(hours=2)
async def track_daily_stats():
    log_info("Running scheduled daily stats update...")
    
    await daily_manager.check_resets()
    
    users = daily_manager.get_tracked_users()
    if not users:
        return

    log_info(f"Updating stats for {len(users)} tracked users.")
    
    for user_id, uuid in users:
        try:
            xp_data = await get_dungeon_xp(uuid)
            if xp_data:
                await daily_manager.update_user_data(user_id, xp_data)
        except Exception as e:
            log_error(f"Error updating user {uuid}: {e}")
        
        await asyncio.sleep(10)
        
    log_info("Daily stats update completed.")

@bot.listen()
async def on_ready():
    await daily_manager.initialize()
    await daily_manager.sanitize_data()
    if not track_daily_stats.is_running():
        track_daily_stats.start()
    
    log_info(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        log_info(f"🔁 Synced {len(synced)} global commands")
    except Exception as e:
        log_error(f"❌ Sync failed: {e}")

async def load_extensions():
    extensions = [
        "modules.dungeons",
        "modules.rng",
        "modules.leaderboard",
        "modules.settings",
        "modules.error_handler"
    ]
    for ext in extensions:
        try:
            await bot.load_extension(ext)
            log_info(f"Loaded extension: {ext}")
        except Exception as e:
            log_error(f"Failed to load extension {ext}: {e}")

async def main():
    validate_config()
    log_info("Starting RTCA Discord Bot...")
    
    await load_extensions()
    
    try:
        await bot.start(TOKEN)
    except Exception as e:
        log_error(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
