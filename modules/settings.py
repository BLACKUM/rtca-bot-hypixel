import discord
from discord import app_commands
from discord.ext import commands
from services.api import get_uuid, get_profile_data
from services.profile_parser import parse_profile_stats, format_number
from typing import List, Optional


class ProfileSelect(discord.ui.Select):
    def __init__(self, profiles: List[dict]):
        options = [discord.SelectOption(label="Auto (Selected)", value="auto", description="Use currently selected profile on Hypixel")]
        for p in profiles:
            name = p.get("cute_name", "Unknown")
            options.append(discord.SelectOption(label=name, value=name))
        
        super().__init__(placeholder="Select a profile...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        view: 'ProfileSelectView' = self.view
        selected = self.values[0]
        
        if selected == "auto":
            await view.bot.daily_manager.set_user_profile(interaction.user.id, None)
            embed = view.create_embed(None)
            await interaction.response.edit_message(embed=embed, view=view)
            return

        await view.bot.daily_manager.set_user_profile(interaction.user.id, selected)
        embed = view.create_embed(selected)
        await interaction.response.edit_message(embed=embed, view=view)


class ProfileSelectView(discord.ui.View):
    def __init__(self, bot: commands.Bot, uuid: str, ign: str, profile_data: dict, selected_profile: Optional[str]):
        super().__init__(timeout=300)
        self.bot = bot
        self.uuid = uuid
        self.ign = ign
        self.profile_data = profile_data
        
        self.add_item(ProfileSelect(profile_data.get("profiles", [])))

    def create_embed(self, selected_profile_name: Optional[str]) -> discord.Embed:
        profiles = self.profile_data.get("profiles", [])
        
        if selected_profile_name:
            profile = next((p for p in profiles if p.get("cute_name") == selected_profile_name), None)
        else:
            profile = next((p for p in profiles if p.get("selected")), profiles[0])

        if not profile:
            return discord.Embed(title="Error", description="Could not find profile.", color=discord.Color.red())

        member = profile.get("members", {}).get(self.uuid, {})
        stats = parse_profile_stats(member, profile)
        
        cute_name = profile.get("cute_name", "Unknown")
        title = f"{self.ign}'s Profile on {cute_name}"
        
        embed = discord.Embed(title=title, color=discord.Color.blue())
        
        description = [
            f"Skill Average\n**{stats['skill_avg']:.2f}**",
            f"Catacombs\n**{stats['catacombs']:.2f}**",
            f"Most Played Class\n**{stats['class_name']} ({stats['class_level']:.1f})**",
            f"Networth\n**{format_number(stats['networth'])}**",
            f"Bank\n**{format_number(stats['bank'])}**",
            f"Purse\n**{format_number(stats['purse'])}**",
            f"Slayers\n**{stats['slayers']}**",
            f"Fairy Souls\n**{stats['fairy_souls']}**",
            f"Skyblock Level\n**{stats['sb_level']:.2f}**",
            f"Bestiary\n**{stats['bestiary']:.1f}**",
            f"Minion Slots\n**{stats['unique_minions']} ({stats['minion_slots']} slots)**",
            f"Heart of the Mountain\nCurrently Hypixel has removed this from the API, so it's not available, look at powders and have a guess?",
            f"Mithril Powder\n**{format_number(stats['mithril_powder'])}**",
            f"Gemstone Powder\n**{format_number(stats['gemstone_powder'])}**",
            f"Glacite Powder\n**{format_number(stats['glacite_powder'])}**"
        ]
        
        embed.description = "\n".join(description)
        
        status = f"Tracking: **{selected_profile_name if selected_profile_name else 'Auto'}**"
        if selected_profile_name:
            status += "\n\n**Note**: Changing profile resets leaderboard progress for this period."
        
        embed.set_footer(text=status)
        return embed


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
    @app_commands.command(name="profile", description="View profile stats and select which profile to track")
    async def profile(self, interaction: discord.Interaction):
        ign = self.bot.link_manager.get_link(interaction.user.id)
        if not ign:
            await interaction.response.send_message("❌ You must link your account first using `/link`!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        
        uuid = await get_uuid(ign)
        if not uuid:
            await interaction.followup.send("❌ Could not find your UUID.")
            return

        data = await get_profile_data(uuid)
        if not data or "profiles" not in data:
            await interaction.followup.send("❌ Failed to fetch SkyBlock data.")
            return

        forced_profile = self.bot.daily_manager.data["users"].get(str(interaction.user.id), {}).get("forced_profile")
        
        view = ProfileSelectView(self.bot, uuid, ign, data, forced_profile)
        embed = view.create_embed(forced_profile)
        
        await interaction.followup.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Settings(bot))
