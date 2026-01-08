import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select, Modal, TextInput, Button
from core.config import OWNER_IDS, save_config, CONFIG_FILE
from core.logger import log_info, log_error, get_latest_log_file
from services.api import get_uuid
from modules.dungeons import DefaultSelectView
import os
import sys
import json
import asyncio

class AddUserModal(Modal):
    def __init__(self, bot):
        super().__init__(title="Add User to Daily Leaderboard")
        self.bot = bot
        
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


class ForceLinkModal(Modal):
    def __init__(self, bot):
        super().__init__(title="Force Link User")
        self.bot = bot
        
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
            int(user_id)
        except ValueError:
             await interaction.response.send_message("❌ Invalid Discord User ID.", ephemeral=True)
             return

        await interaction.response.defer(ephemeral=True)
        
        uuid = await get_uuid(ign)
        if not uuid:
             await interaction.followup.send(f"❌ Could not find UUID for IGN: `{ign}`")
             return
             
        await self.bot.link_manager.link_user(user_id, ign)
        await self.bot.daily_manager.register_user(user_id, ign, uuid)

        await interaction.followup.send(f"✅ Force linked <@{user_id}> to `{ign}`.")


class ConfigEditModal(Modal):
    def __init__(self, key, current_value):
        super().__init__(title=f"Edit Config: {key}")
        self.key = key
        
        self.value_input = TextInput(
            label="New Value",
            default=str(current_value),
            required=True
        )
        self.add_item(self.value_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            from core import config
            
            new_value = self.value_input.value
            
            if new_value.lower() == "true":
                new_value = True
            elif new_value.lower() == "false":
                new_value = False
            else:
                try:
                    if "." in new_value:
                        new_value = float(new_value)
                    else:
                        new_value = int(new_value)
                except ValueError:
                    pass
            
            setattr(config, self.key.upper(), new_value)
            config.save_config()
            
            await interaction.response.send_message(f"✅ Config `{self.key}` updated to `{new_value}`.", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to update config: {e}", ephemeral=True)

class ConfigSelect(Select):
    def __init__(self):
        from core import config
        options = []
        
        full_config = {}
        if os.path.exists(config.CONFIG_FILE):
            with open(config.CONFIG_FILE, 'r') as f:
                full_config = json.load(f)
        
        for key, value in full_config.items():
            options.append(discord.SelectOption(
                label=key, 
                description=f"Current: {value}",
                value=key
            ))

        super().__init__(placeholder="Select a setting to edit...", options=options)

    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        from core import config
        current_val = getattr(config, key.upper(), "Unknown")
        await interaction.response.send_modal(ConfigEditModal(key, current_val))


class SystemSelect(Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            discord.SelectOption(label="Update Bot (Git Pull)", value="update", description="Pull latest changes from GitHub", emoji="📥"),
            discord.SelectOption(label="Reload Extensions", value="reload", description="Reload all bot modules", emoji="🔄"),
            discord.SelectOption(label="Get Logs", value="logs", description="Upload the latest log file", emoji="📜"),
            discord.SelectOption(label="Restart Bot", value="restart", description="Restart the bot process", emoji="👋"),
        ]
        super().__init__(placeholder="Select a system action...", options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        
        if val == "update":
            await interaction.response.defer(ephemeral=True)
            try:
                proc = await asyncio.create_subprocess_shell(
                    "git pull",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                output = stdout.decode() + stderr.decode()
                
                if len(output) > 1900:
                    output = output[:1900] + "..."
                
                await interaction.followup.send(f"git pull output:\n```\n{output}\n```")
            except Exception as e:
                await interaction.followup.send(f"❌ Update failed: {e}")
                
        elif val == "reload":
            await interaction.response.defer(ephemeral=True)
            msg = []
            extensions = [
                "modules.dungeons",
                "modules.rng",
                "modules.leaderboard",
                "modules.settings",
                "modules.error_handler",
                "modules.admin"
            ]
            for ext in extensions:
                try:
                    await self.bot.reload_extension(ext)
                    msg.append(f"✅ Reloaded {ext}")
                except Exception as e:
                    msg.append(f"❌ Failed {ext}: {e}")
            
            await interaction.followup.send("\n".join(msg))
            
        elif val == "logs":
             await interaction.response.defer(ephemeral=True)
             log_file = get_latest_log_file()
             if log_file and os.path.exists(log_file):
                 await interaction.followup.send(file=discord.File(log_file))
             else:
                 await interaction.followup.send("❌ No log file found.")

        elif val == "restart":
            await interaction.response.send_message("👋 Restarting bot...", ephemeral=True)
            await self.bot.close()
            os.execv(sys.executable, ['python'] + sys.argv)


class LeaderboardAdminView(View):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.bot = bot
    
    @discord.ui.button(label="Add User", style=discord.ButtonStyle.success, emoji="➕")
    async def add_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddUserModal(self.bot))

    @discord.ui.button(label="Force Update", style=discord.ButtonStyle.danger, emoji="⚡")
    async def force_update(self, interaction: discord.Interaction, button: discord.ui.Button):
         await interaction.response.defer(ephemeral=False)
         try:
            base_msg = await interaction.followup.send("🔄 Starting Force Update...")
            updated, errors, total = await self.bot.daily_manager.force_update_all(base_msg, force=True)
            await base_msg.edit(content=f"✅ **Force Update Complete**\nTotal: {total}\nUpdated: {updated}\nErrors: {errors}")
         except Exception as e:
             log_error(f"Admin force update failed: {e}")
             await interaction.followup.send("❌ Error during update.")

class DataAdminView(View):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.bot = bot

    @discord.ui.button(label="Linked Users", style=discord.ButtonStyle.primary, emoji="🔗")
    async def linked_users(self, interaction: discord.Interaction, button: discord.ui.Button):
         links = self.bot.link_manager.links
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
             
         await interaction.response.send_message(embed=embeds[0], ephemeral=True)

    @discord.ui.button(label="Tracked Users", style=discord.ButtonStyle.primary, emoji="📊")
    async def tracked_users(self, interaction: discord.Interaction, button: discord.ui.Button):
         users = self.bot.daily_manager.get_tracked_users()
         daily_data = self.bot.daily_manager.data["users"]
         
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

    @discord.ui.button(label="Dungeons", style=discord.ButtonStyle.primary, emoji="🏰", row=0)
    async def dungeons(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = DefaultSelectView(self.bot)
        embed = view._create_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

    @discord.ui.button(label="Leaderboard", style=discord.ButtonStyle.primary, emoji="🏆", row=0)
    async def leaderboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🏆 **Leaderboard Admin**", view=LeaderboardAdminView(self.bot), ephemeral=True)

    @discord.ui.button(label="Data", style=discord.ButtonStyle.secondary, emoji="📁", row=0)
    async def data(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("📁 **Data Management**", view=DataAdminView(self.bot), ephemeral=True)

    @discord.ui.button(label="Force Link", style=discord.ButtonStyle.secondary, emoji="🔗", row=1)
    async def force_link(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ForceLinkModal(self.bot))

    @discord.ui.button(label="Config", style=discord.ButtonStyle.secondary, emoji="⚙️", row=1)
    async def config(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        view.add_item(ConfigSelect())
        await interaction.response.send_message("⚙️ **Configuration Editor**", view=view, ephemeral=True)

    @discord.ui.button(label="System", style=discord.ButtonStyle.danger, emoji="🖥️", row=1)
    async def system(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        view.add_item(SystemSelect(self.bot))
        await interaction.response.send_message("🖥️ **System Operations**", view=view, ephemeral=True)


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="admin", description="Owner-only administration panel")
    async def admin(self, interaction: discord.Interaction):
        if interaction.user.id not in OWNER_IDS:
            await interaction.response.send_message("❌ You do not have permission to access the admin panel.", ephemeral=True)
            return
            
        embed = discord.Embed(title="🛡️ Admin Panel", description="Select a category via buttons below.", color=0x2b2d31)
        await interaction.response.send_message(embed=embed, view=AdminView(self.bot), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
