from discord.ext import commands, tasks
from core.config import TOKEN, INTENTS, validate_config
from core.logger import log_info, log_error
from services.daily_manager import DailyManager
from services.rng_manager import RngManager
from services.link_manager import LinkManager
from services.recent_manager import RecentManager
from services.solo_manager import SoloManager
from services.api import get_dungeon_xp, init_session, close_session
from services.irc_handler import init_irc_handler
from services.name_manager import name_manager
from services.github_manager import GithubManager
from core.cache import initialize as init_cache, shutdown as shutdown_cache
import asyncio
import os
import traceback

class RTCABot(commands.Bot):
    async def setup_hook(self):
        await load_extensions()
        await init_session()
        await init_cache()
        await self.link_manager.initialize()
        await self.daily_manager.initialize()
        await self.rng_manager.initialize()
        await self.recent_manager.initialize()
        await self.solo_manager.initialize()
        await name_manager.initialize()
        await self.irc_handler.initialize()
        await self.daily_manager.sanitize_data()

bot = RTCABot(command_prefix="!", intents=INTENTS)

bot.daily_manager = DailyManager()
bot.rng_manager = RngManager()
bot.link_manager = LinkManager()
bot.recent_manager = RecentManager()
bot.solo_manager = SoloManager()
bot.github_manager = GithubManager()
bot.irc_handler = init_irc_handler(bot)

@bot.listen()
async def on_message(message):
    await bot.irc_handler.on_discord_message(message)

@tasks.loop(hours=2)
async def track_daily_stats():
    try:
        log_info("Running scheduled daily stats update...")
        
        await bot.daily_manager.check_resets()
        
        users = bot.daily_manager.get_tracked_users()
        if not users:
            return

        updated, errors, total = await bot.daily_manager.force_update_all()
        
        if updated > 0:
            log_info(f"Daily stats update completed: {updated}/{total} updated, {errors} errors.")
        else:
            log_info("Daily stats update skipped or completed with no changes.")
    except Exception as e:
        log_error(f"Unhandled exception in track_daily_stats loop: {e}")
        import traceback
        log_error(traceback.format_exc())

@tasks.loop(hours=24)
async def backup_github():
    try:
        log_info("Running scheduled GitHub data backup...")
        success, message = await bot.github_manager.backup_data()
        if success:
            log_info(f"GitHub backup: {message}")
        else:
            log_error(f"GitHub backup failed: {message}")
    except Exception as e:
        log_error(f"Unhandled exception in backup_github loop: {e}")
        import traceback
        log_error(traceback.format_exc())

@bot.listen()
async def on_ready():
    if not track_daily_stats.is_running():
        track_daily_stats.start()
    
    if bot.github_manager.is_enabled() and not backup_github.is_running():
        backup_github.start()
    
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
        "modules.error_handler",
        "modules.admin",
        "modules.api",
        "modules.solo_clears"
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
    
    
    try:
        await bot.start(TOKEN)
    except Exception as e:
        log_error(f"Failed to start bot: {e}")
        raise
    finally:
        await shutdown_cache()
        await bot.irc_handler.close()
        await close_session()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception:
        if not os.path.exists("logs"):
            os.makedirs("logs")
        with open("logs/crash.log", "w") as f:
            f.write(traceback.format_exc())
        print("\n❌ Bot crashed on startup! Error details saved to logs/crash.log")
        log_error(f"Startup crash detected: {traceback.format_exc()}")
