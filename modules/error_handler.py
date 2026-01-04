import discord
from discord import app_commands
from discord.ext import commands
from core.logger import log_error

class GlobalErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Register the app command error handler
        bot.tree.on_error = self.on_app_command_error

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏳ Command is on cooldown. Try again in {error.retry_after:.2f}s.", ephemeral=True)
            return
            
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        log_error(f"App Command Error in {interaction.command.name if interaction.command else 'Unknown'}: {error}")
        
        if interaction.response.is_done():
            await interaction.followup.send("❌ An unexpected error occurred.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ An unexpected error occurred.", ephemeral=True)

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

        log_error(f"Text Command Error in {ctx.command}: {error}")
        
async def setup(bot):
    await bot.add_cog(GlobalErrorHandler(bot))
