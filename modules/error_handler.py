import discord
from discord.ext import commands
from core.logger import log_error

class GlobalErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, 'on_error'):
            return

        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.send(f"You don't have permission to use this command.")
            return

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.2f}s.")
            return

        log_error(f"Unhandled exception in command {ctx.command}: {error}")
        
async def setup(bot):
    await bot.add_cog(GlobalErrorHandler(bot))
