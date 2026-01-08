import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select, Modal, TextInput, Button
from core.config import OWNER_IDS
from core.logger import log_info, log_error
from services.api import get_uuid
from modules.dungeons import DefaultSelectView

class AddUserModal(Modal):
    def __init__(self, bot, view):
        super().__init__(title="Add User to Daily Leaderboard")
        self.bot = bot
        self.view = view
        
        self.ign_input = TextInput(
            label="Minecraft IGN",
            placeholder="Enter IGN...",
            required=True,
            max_length=16
        )
        self.user_id_input = TextInput(
            label="Discord User ID",
            placeholder="Enter Discord User ID...",
            required=True,
             max_length=20
        )
        self.add_item(self.ign_input)
        self.add_item(self.user_id_input)

    async def on_submit(self, interaction: discord.Interaction):
        ign = self.ign_input.value
        user_id = self.user_id_input.value
        
        try:
             # Validate User ID format
            int(user_id)
        except ValueError:
             await interaction.response.send_message("❌ Invalid Discord User ID.", ephemeral=True)
             return

        await interaction.response.defer(ephemeral=True)
        
        uuid = await get_uuid(ign)
        if not uuid:
             await interaction.followup.send(f"❌ Could not find UUID for IGN: `{ign}`")
             return
             
        await self.bot.daily_manager.register_user(user_id, ign, uuid)
        await interaction.followup.send(f"✅ Manually registered User <@{user_id}> as `{ign}` for daily tracking.")


class RngDefaultUserModal(Modal):
    def __init__(self, bot, view):
        super().__init__(title="Set Default RNG Target")
        self.bot = bot
        self.view = view
        
        self.target_id_input = TextInput(
            label="Target Discord User ID",
            placeholder="User to manage...",
            required=True,
             max_length=20
        )
        self.add_item(self.target_id_input)

    async def on_submit(self, interaction: discord.Interaction):
        target_id = self.target_id_input.value
        
        try:
            int(target_id)
        except ValueError:
             await interaction.response.send_message("❌ Invalid Discord User ID.", ephemeral=True)
             return
             
        await self.bot.rng_manager.set_default_target(str(interaction.user.id), str(target_id))
        await interaction.response.send_message(f"✅ Default target for /rng set to <@{target_id}>.", ephemeral=True)

class AdminSelect(Select):
    def __init__(self, view):
        self.parent_view = view
        options = [
            discord.SelectOption(label="Dungeons: Defaults", value="dungeons_defaults", description="Configure default simulation bonuses"),
            discord.SelectOption(label="RNG: Set Default", value="rng_default", description="Set default user for RNG tracking"),
            discord.SelectOption(label="Leaderboard: Add User", value="lb_add", description="Manually register a user"),
            discord.SelectOption(label="Leaderboard: Force Update", value="lb_force", description="Force update daily stats"),
            discord.SelectOption(label="Data: Linked Users", value="data_linked", description="View all linked Discord accounts"),
            discord.SelectOption(label="Data: Tracked Users", value="data_tracked", description="View all users tracked in leaderboard"),
        ]
        super().__init__(placeholder="Select an admin action...", options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        
        if val == "dungeons_defaults":
            view = DefaultSelectView(self.parent_view.bot)
            embed = view._create_embed()
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            view.message = await interaction.original_response()
            
        elif val == "rng_default":
            await interaction.response.send_modal(RngDefaultUserModal(self.parent_view.bot, self.parent_view))
            
        elif val == "lb_add":
            await interaction.response.send_modal(AddUserModal(self.parent_view.bot, self.parent_view))
            
        elif val == "lb_force":
             await interaction.response.defer(ephemeral=False)
             try:
                base_msg = await interaction.followup.send("🔄 Starting Force Update...")
                updated, errors, total = await self.parent_view.bot.daily_manager.force_update_all(base_msg, force=True)
                await base_msg.edit(content=f"✅ **Force Update Complete**\nTotal: {total}\nUpdated: {updated}\nErrors: {errors}")
             except Exception as e:
                 log_error(f"Admin force update failed: {e}")
                 await interaction.followup.send("❌ Error during update.")
                 
        elif val == "data_linked":
             links = self.parent_view.bot.link_manager.links
             if not links:
                 await interaction.response.send_message("No linked users.", ephemeral=True)
                 return
             
             lines = [f"<@{uid}>: `{ign}`" for uid, ign in links.items()]
             chunks = [lines[i:i+20] for i in range(0, len(lines), 20)]
             
             embeds = []
             for i, chunk in enumerate(chunks):
                 embed = discord.Embed(title=f"Linked Users ({len(links)}) - Page {i+1}/{len(chunks)}", color=0x5865F2)
                 embed.description = "\n".join(chunk)
                 embeds.append(embed)
                 
             await interaction.response.send_message(embed=embeds[0], ephemeral=True) # Simple pagination could be added, sending page 1 for now
             
        elif val == "data_tracked":
             users = self.parent_view.bot.daily_manager.get_tracked_users() # returns list of tuples (uid, uuid)
             # Need to map UID to IGN from daily_manager data
             daily_data = self.parent_view.bot.daily_manager.data["users"]
             
             if not users:
                  await interaction.response.send_message("No tracked users.", ephemeral=True)
                  return

             lines = []
             for uid, _ in users:
                 ign = daily_data.get(uid, {}).get("ign", "Unknown")
                 lines.append(f"<@{uid}>: `{ign}`")
                 
             chunks = [lines[i:i+20] for i in range(0, len(lines), 20)]

             embeds = []
             for i, chunk in enumerate(chunks):
                 embed = discord.Embed(title=f"Tracked Users ({len(users)}) - Page {i+1}/{len(chunks)}", color=0xFFA500)
                 embed.description = "\n".join(chunk)
                 embeds.append(embed)

             await interaction.response.send_message(embed=embeds[0], ephemeral=True)


class AdminView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(AdminSelect(self))

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="admin", description="Owner-only administration panel")
    async def admin(self, interaction: discord.Interaction):
        if interaction.user.id not in OWNER_IDS:
            await interaction.response.send_message("❌ You do not have permission to access the admin panel.", ephemeral=True)
            return
            
        embed = discord.Embed(title="🛡️ Admin Panel", description="Select an action below.", color=0x2b2d31)
        await interaction.response.send_message(embed=embed, view=AdminView(self.bot), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
