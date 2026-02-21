import discord
from discord import app_commands
from discord.ext import commands
from services.api import get_uuid, get_profile_data, get_player_discord
from services.profile_parser import parse_profile_stats, format_number
from core.config import config
from typing import List, Optional


class ProfileSelect(discord.ui.Select):
    def __init__(self, profiles: List[dict], current_profile: Optional[str], tracked_profile: Optional[str]):
        options = []
        current_lower = current_profile.lower() if current_profile else None
        tracked_lower = tracked_profile.lower() if tracked_profile else None
        
        for p in profiles:
            name = p.get("cute_name", "Unknown")
            is_viewing = current_lower == name.lower() if current_lower else False
            is_tracked = tracked_lower == name.lower() if tracked_lower else False
            is_game_selected = p.get("selected", False)
            
            label = f"{name}"
            if is_game_selected:
                label += " (Selected)"
            
            desc = []
            if is_tracked:
                desc.append("Currently Tracking")
            
            options.append(discord.SelectOption(
                label=label,
                value=name,
                description=" • ".join(desc) if desc else None,
                default=is_viewing
            ))

        super().__init__(
            placeholder=f"Viewing: {current_profile}" if current_profile else "Select a profile to view",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        view: 'ProfileSelectView' = self.view
        selected = self.values[0]

        view.selected_profile = selected
        view.update_view()
        
        embed = view.create_embed(selected)
        await interaction.response.edit_message(embed=embed, view=view)


class TrackProfileButton(discord.ui.Button):
    def __init__(self, profile_name: str):
        super().__init__(label=f"Track '{profile_name}'", style=discord.ButtonStyle.success, custom_id="track_profile")
        self.profile_name = profile_name

    async def callback(self, interaction: discord.Interaction):
        view: 'ProfileSelectView' = self.view
        
        viewer_ign = view.bot.link_manager.get_link(interaction.user.id)
        if not viewer_ign:
             await interaction.response.send_message("❌ You must link your account to track profiles.", ephemeral=True)
             return
             
        viewer_uuid = await get_uuid(viewer_ign)
        
        if viewer_uuid != view.uuid:
             await interaction.response.send_message("❌ You can only track your own profiles.", ephemeral=True)
             return

        await view.bot.daily_manager.set_user_profile(interaction.user.id, self.profile_name)
        
        await interaction.response.send_message(f"✅ Now tracking profile **{self.profile_name}** for leaderboards and daily stats!", ephemeral=True)
        
        view.forced_profile = self.profile_name
        view.update_view()
        embed = view.create_embed(view.selected_profile)
        await interaction.edit_original_response(embed=embed, view=view)


class ProfileSelectView(discord.ui.View):
    def __init__(self, bot: commands.Bot, uuid: str, ign: str, profile_data: dict, forced_profile: Optional[str], selected_profile: Optional[str] = None):
        super().__init__(timeout=300)
        self.bot = bot
        self.uuid = uuid
        self.ign = ign
        self.profile_data = profile_data
        self.forced_profile = forced_profile
        self.selected_profile = selected_profile or forced_profile
        
        if not self.selected_profile:
             self.selected_profile = next((p.get("cute_name") for p in profile_data.get("profiles", []) if p.get("selected")), None)
             if not self.selected_profile and profile_data.get("profiles"):
                 self.selected_profile = profile_data.get("profiles")[0].get("cute_name")

        self.update_view()

    def update_view(self):
        self.clear_items()
        
        self.add_item(ProfileSelect(self.profile_data.get("profiles", []), self.selected_profile, self.forced_profile))
        
        if self.selected_profile and self.selected_profile != self.forced_profile:
            self.add_item(TrackProfileButton(self.selected_profile))


    def create_embed(self, selected_profile_name: Optional[str]) -> discord.Embed:
        profiles = self.profile_data.get("profiles", [])

        profile = None
        if selected_profile_name:
            profile = next((p for p in profiles if p.get("cute_name") == selected_profile_name), None)

        if not profile:
            profile = next((p for p in profiles if p.get("selected")), profiles[0])

        if not profile:
            return discord.Embed(title="Error", description="Could not find profile.", color=discord.Color.red())

        member = profile.get("members", {}).get(self.uuid, {})
        stats = parse_profile_stats(member, profile)
        
        cute_name = profile.get("cute_name", "Unknown")
        title = f"{self.ign}'s Profile on {cute_name}"
        
        embed = discord.Embed(title=title, color=discord.Color.blue())
        
        description = [
            f"Catacombs\n**{stats['catacombs']:.2f}**",
            f"Most Played Class\n**{stats['class_name']} ({stats['class_level']:.1f})**",
            f"Magical Power\n**{format_number(stats['magical_power'])}**",
            f"Bank\n**{format_number(stats['bank'])}**",
            f"Purse\n**{format_number(stats['purse'])}**",
            f"Slayers\n**{stats['slayers']}**",
            f"Fairy Souls\n**{stats['fairy_souls']}**",
            f"Skyblock Level\n**{stats['sb_level']:.2f}**",
            f"Minion Slots\n**{stats['unique_minions']} ({stats['minion_slots']} slots)**"
        ]
        
        embed.description = "\n".join(description)
        
        items_footer = []
        if self.forced_profile:
            items_footer.append(f"Currently tracking: {self.forced_profile}")
        
        if self.forced_profile != cute_name:
             items_footer.append(f"Viewing: {cute_name}")
             
        if not self.forced_profile:
            items_footer.append("⚠️ No profile selected for tracking.")
            
        embed.set_footer(text=" • ".join(items_footer))
            
        return embed


class Settings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="link", description="Link your Discord account to a Hypixel IGN")
    @app_commands.describe(ign="Your Minecraft IGN")
    async def link(self, interaction: discord.Interaction, ign: str):
        await interaction.response.defer(ephemeral=True)

        uuid = await get_uuid(ign)
        if not uuid:
            await interaction.followup.send(f"❌ Could not find player with IGN: {ign}")
            return

        is_owner = interaction.user.id in config.owner_ids
        
        if not is_owner:
            discord_link = await get_player_discord(uuid)
            if not discord_link:
                 await interaction.followup.send(
                    f"❌ **{ign}** does not have a Discord account linked on Hypixel!\n\n"
                    "**How to link:**\n"
                    "1. Go to Hypixel Lobby\n"
                    "2. Right-click **My Profile** (Head) -> **Social Media** -> **Discord**\n"
                    "3. Paste your Discord username/tag and confirm."
                )
                 return
    
            user_tag = str(interaction.user)
            user_name = interaction.user.name
            
            msg_discord = discord_link.lower().strip()
            
            normalized_tag = user_tag.lower().strip()
            normalized_name = user_name.lower().strip()
            
            if msg_discord != normalized_tag and msg_discord != normalized_name:
                 await interaction.followup.send(
                    f"❌ The Discord account linked to **{ign}** is `{discord_link}`, but your account is **{user_tag}**.\n"
                    "Please update your social media on Hypixel to match your current Discord account."
                )
                 return
        else:
            await interaction.followup.send(f"⚠️ **Admin Bypass Activated**: Skipping verification for **{ign}**.")

        await self.bot.link_manager.link_user(interaction.user.id, ign)
        await self.bot.daily_manager.register_user(interaction.user.id, ign, uuid)
        
        data = await get_profile_data(uuid)
        if data and "profiles" in data:
            selected_in_game = next((p.get("cute_name") for p in data.get("profiles", []) if p.get("selected")), None)
            if selected_in_game:
                await self.bot.daily_manager.set_user_profile(interaction.user.id, selected_in_game)

        await interaction.followup.send(f"✅ Successfully linked your Discord account to **{ign}**!")

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
    @app_commands.describe(ign="Minecraft IGN (optional if linked)")
    async def profile(self, interaction: discord.Interaction, ign: str = None):
        if ign is None:
            ign = self.bot.link_manager.get_link(interaction.user.id)
            if not ign:
                await interaction.response.send_message("❌ You must link your account first using `/link` or provide an IGN!", ephemeral=True)
                return
        
        await interaction.response.defer(ephemeral=False)
        
        uuid = await get_uuid(ign)
        if not uuid:
            await interaction.followup.send(f"❌ Could not find UUID for {ign}.")
            return

        data = await get_profile_data(uuid)
        if not data or "profiles" not in data:
            await interaction.followup.send(f"❌ Failed to fetch SkyBlock data for {ign}.")
            return

        viewer_ign = self.bot.link_manager.get_link(interaction.user.id)
        viewer_uuid = await get_uuid(viewer_ign) if viewer_ign else None
        
        forced_profile = None
        if viewer_uuid == uuid:
             forced_profile = self.bot.daily_manager.data["users"].get(str(interaction.user.id), {}).get("forced_profile")
        
             if not forced_profile:
                selected_in_game = next((p.get("cute_name") for p in data.get("profiles", []) if p.get("selected")), None)
                if selected_in_game:
                    await self.bot.daily_manager.set_user_profile(interaction.user.id, selected_in_game)
                    forced_profile = selected_in_game
        
        view = ProfileSelectView(self.bot, uuid, ign, data, forced_profile)
        embed = view.create_embed(view.selected_profile)
        
        await interaction.followup.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Settings(bot))
