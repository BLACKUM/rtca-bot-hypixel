from discord.ext import commands, tasks
from config import TOKEN, INTENTS
from commands import setup_commands
from utils.logging import log_info, log_error
from daily_manager import daily_manager
from api import get_dungeon_xp
import asyncio


bot = commands.Bot(command_prefix="!", intents=INTENTS)

@tasks.loop(hours=2)
async def track_daily_stats():
    log_info("Running scheduled daily stats update...")
    
    daily_manager.check_resets()
    
    users = daily_manager.get_tracked_users()
    if not users:
        return

    log_info(f"Updating stats for {len(users)} tracked users.")
    
    for user_id, uuid in users:
        try:
            xp_data = await get_dungeon_xp(uuid)
            if xp_data:
                daily_manager.update_user_data(user_id, xp_data)
        except Exception as e:
            log_error(f"Error updating user {uuid}: {e}")
        
        await asyncio.sleep(10)
        
    log_info("Daily stats update completed.")

@bot.listen()
async def on_ready():
    await daily_manager.sanitize_data()
    if not track_daily_stats.is_running():
        track_daily_stats.start()

def main():
    log_info("Starting RTCA Discord Bot...")
    
    setup_commands(bot)
    
    try:
        bot.run(TOKEN)
    except Exception as e:
        log_error(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    main()
