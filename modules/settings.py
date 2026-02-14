import discord
from discord import app_commands
from discord.ext import commands
from services.api import get_uuid, get_profile_data
from typing import List


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

        await self.bot.link_manager.link_user(interaction.user.id, ign)
        await self.bot.daily_manager.register_user(interaction.user.id, ign, uuid)
        await interaction.response.send_message(f"✅ Successfully linked your Discord account to **{ign}**!", ephemeral=True)

    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="unlink", description="Unlink your Discord account from any Hypixel IGN")
    async def unlink(self, interaction: discord.Interaction):
        if await self.bot.link_manager.unlink_user(interaction.user.id):
            await interaction.response.send_message("✅ Successfully unlinked your account.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ You do not have a linked account.", ephemeral=True)

    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="profile", description="Select which SkyBlock profile to track for leaderboards")
    @app_commands.describe(profile="Select a profile name (or 'Auto' to use currently selected)")
    async def profile(self, interaction: discord.Interaction, profile: str):
        ign = self.bot.link_manager.get_link(interaction.user.id)
        if not ign:
            await interaction.response.send_message("❌ You must link your account first using `/link`!", ephemeral=True)
            return

        if profile.lower() == "auto":
            await self.bot.daily_manager.set_user_profile(interaction.user.id, None)
            await interaction.response.send_message("✅ Profile tracking set to **Auto** (currently selected profile).", ephemeral=True)
            return

        await self.bot.daily_manager.set_user_profile(interaction.user.id, profile)
        
        warning = "\n\n> [!WARNING]\n> Your daily and monthly leaderboard progress for this period has been **reset** to avoid corrupted stats."
        await interaction.response.send_message(f"✅ Successfully set your tracked profile to **{profile}**! {warning}", ephemeral=True)

    @profile.autocomplete("profile")
    async def profile_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        ign = self.bot.link_manager.get_link(interaction.user.id)
        if not ign:
            return []

        uuid = await get_uuid(ign)
        if not uuid:
            return []

        data = await get_profile_data(uuid)
        if not data or "profiles" not in data:
            return []

        profiles = [p.get("cute_name") for p in data["profiles"] if p.get("cute_name")]
        
        choices = [app_commands.Choice(name="Auto (Selected Profile)", value="Auto")]
        for p in profiles:
            if current.lower() in p.lower():
                choices.append(app_commands.Choice(name=p, value=p))
        
        return choices[:25]


async def setup(bot: commands.Bot):
    await bot.add_cog(Settings(bot))
