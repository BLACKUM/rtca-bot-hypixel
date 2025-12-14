import discord
from discord import app_commands
from discord.ext import commands
from services.link_manager import link_manager
from services.daily_manager import daily_manager
from services.api import get_uuid


class Settings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="link", description="Link your Discord account to a Hypixel IGN")
    @app_commands.describe(ign="Your Minecraft IGN")
    async def link(self, interaction: discord.Interaction, ign: str):
        uuid = await get_uuid(ign)
        if not uuid:
            await interaction.response.send_message(f"❌ Could not find player with IGN: {ign}", ephemeral=True)
            return

        link_manager.link_user(interaction.user.id, ign)
        await daily_manager.register_user(interaction.user.id, ign, uuid)
        await interaction.response.send_message(f"✅ Successfully linked your Discord account to **{ign}**!", ephemeral=True)

    @app_commands.command(name="unlink", description="Unlink your Discord account from any Hypixel IGN")
    async def unlink(self, interaction: discord.Interaction):
        if link_manager.unlink_user(interaction.user.id):
            await interaction.response.send_message("✅ Successfully unlinked your account.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ You do not have a linked account.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Settings(bot))
