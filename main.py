#!/usr/bin/env python3

from discord.ext import commands
from config import TOKEN, INTENTS
from commands import setup_commands
from utils.logging import log_info, log_error


def main():
    log_info("Starting RTCA Discord Bot...")
    
    bot = commands.Bot(command_prefix="!", intents=INTENTS)
    setup_commands(bot)
    
    try:
        bot.run(TOKEN)
    except Exception as e:
        log_error(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    main()
