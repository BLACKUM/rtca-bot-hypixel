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
import platform
import psutil

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
    def __init__(self, key, current_val):
        super().__init__(title=f"Edit {key}")
        self.key = key
        default_val = str(current_val)
        if isinstance(current_val, list):
             default_val = ", ".join(map(str, current_val))
             
        self.value_input = TextInput(label="New Value", default=default_val, required=True, style=discord.TextStyle.paragraph)
        self.add_item(self.value_input)

    async def on_submit(self, interaction: discord.Interaction):
        from core import config
        new_val = self.value_input.value
        
        try:
            current_val = getattr(config, self.key)
            if isinstance(current_val, bool):
                 converted_val = new_val.lower() in ("true", "1", "yes")
            elif isinstance(current_val, int):
                converted_val = int(new_val)
            elif isinstance(current_val, float):
                converted_val = float(new_val)
            elif isinstance(current_val, list):
                items = [x.strip() for x in new_val.split(",") if x.strip()]
                if items and isinstance(current_val[0], int):
                     converted_val = [int(x) for x in items]
                else:
                     converted_val = items
            else:
                converted_val = new_val
                
            setattr(config, self.key, converted_val)
            config.save_config()
            
            await interaction.response.send_message(f"✅ Updated `{self.key}` to `{converted_val}`", ephemeral=True)
            
        except ValueError:
             await interaction.response.send_message(f"❌ Invalid format for {self.key}.", ephemeral=True)
        except Exception as e:
             await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

class ConfigSelect(Select):
    def __init__(self):
        from core import config
        options = []
        
        keys = ["TARGET_LEVEL", "DEBUG_MODE", "PROFILE_CACHE_TTL", "PRICES_CACHE_TTL", "OWNER_IDS", "CONGRATS_GIFS"]
        
        for key in keys:
            value = getattr(config, key, "Unknown")
            display_val = str(value)
            if isinstance(value, list):
                display_val = f"List [{len(value)} items]"

            options.append(discord.SelectOption(
                label=key, 
                description=f"Current: {display_val}",
                value=key
            ))

        super().__init__(placeholder="Select a setting to edit...", options=options)

    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        from core import config
        
        if key == "CONGRATS_GIFS":
             await interaction.response.send_message("🎉 **Manage Congratulation GIFs**", view=GifManageView(self.bot), ephemeral=True)
             return

        current_val = getattr(config, key.upper(), "Unknown")
        await interaction.response.send_modal(ConfigEditModal(key, current_val))

class GifManageView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Add GIF", style=discord.ButtonStyle.success, emoji="➕")
    async def add_gif(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GifAddModal())

    @discord.ui.button(label="Remove Last GIF", style=discord.ButtonStyle.danger, emoji="➖")
    async def remove_gif(self, interaction: discord.Interaction, button: discord.ui.Button):
        from core import config
        if config.CONGRATS_GIFS:
            removed = config.CONGRATS_GIFS.pop()
            config.save_config()
            await interaction.response.send_message(f"🗑️ Removed last GIF: `{removed}`", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No GIFs to remove.", ephemeral=True)

    @discord.ui.button(label="List GIFs", style=discord.ButtonStyle.secondary, emoji="📜")
    async def list_gifs(self, interaction: discord.Interaction, button: discord.ui.Button):
        from core import config
        gifs = "\n".join([f"`{g}`" for g in config.CONGRATS_GIFS])
        if len(gifs) > 1900:
             gifs = gifs[:1900] + "... (truncated)"
        if not gifs:
            gifs = "No GIFs configured."
            
        await interaction.response.send_message(f"**Configured GIFs:**\n{gifs}", ephemeral=True)

class GifAddModal(Modal):
    def __init__(self):
        super().__init__(title="Add Congratulation GIF")
        self.gif_url = TextInput(label="GIF URL", placeholder="https://media.tenor.com/...", required=True)
        self.add_item(self.gif_url)

    async def on_submit(self, interaction: discord.Interaction):
        url = self.gif_url.value.strip()
        from core import config
        if url not in config.CONGRATS_GIFS:
            config.CONGRATS_GIFS.append(url)
            config.save_config()
            await interaction.response.send_message(f"✅ Added GIF:\n`{url}`", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ GIF already exists.", ephemeral=True)

class SystemSelect(Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            discord.SelectOption(label="Update Bot (Git Pull)", value="update", description="Pull latest changes from GitHub", emoji="📥"),
            discord.SelectOption(label="Reload Extensions", value="reload", description="Reload all bot modules", emoji="🔄"),
            discord.SelectOption(label="Get Logs", value="logs", description="Upload the latest log file", emoji="📜"),
            discord.SelectOption(label="Host Info", value="host_info", description="View location and system stats", emoji="ℹ️"),
            discord.SelectOption(label="Restart (Internal)", value="restart", description="Restart via os.exec", emoji="🔄"),
            discord.SelectOption(label="Restart (Loop/Tmux)", value="restart_loop", description="Exit process (requires loop script)", emoji="🔁"),
            discord.SelectOption(label="Shutdown", value="shutdown", description="Turn off the bot", emoji="🛑"),
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
            await interaction.response.send_message("👋 Restarting bot (Internal)...", ephemeral=True)
            await self.bot.close()
            os.execv(sys.executable, ['python'] + sys.argv)

        elif val == "restart_loop":
            await interaction.response.send_message("🔁 Exiting process for Loop/Tmux restart...", ephemeral=True)
            await self.bot.close()
            sys.exit(0)

        elif val == "host_info":
             await interaction.response.defer(ephemeral=True)
             
             path = os.getcwd()
             system = f"{platform.system()} {platform.release()}"
             py_ver = sys.version.split()[0]
             
             mem = psutil.virtual_memory()
             mem_usage = f"{mem.used / (1024**3):.2f}/{mem.total / (1024**3):.2f} GB ({mem.percent}%)"
             
             cpu = psutil.cpu_percent(interval=None)
             
             embed = discord.Embed(title="ℹ️ Host System Info", color=0x3498db)
             embed.add_field(name="📂 Bot Location", value=f"`{path}`", inline=False)
             embed.add_field(name="💻 OS", value=f"`{system}`", inline=True)
             embed.add_field(name="🐍 Python", value=f"`{py_ver}`", inline=True)
             embed.add_field(name="🧠 Memory", value=f"`{mem_usage}`", inline=True)
             embed.add_field(name="⚙️ CPU Load", value=f"`{cpu}%`", inline=True)
             
             await interaction.followup.send(embed=embed)


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
