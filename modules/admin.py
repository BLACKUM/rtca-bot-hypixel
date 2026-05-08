import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select, Modal, TextInput, Button
from core.config import config
from core.logger import log_info, log_error, get_latest_log_file
from core.ui import AuthorView
from services.api import get_uuid
from services.ban_manager import ban_manager
from services.request_log import request_log
from modules.dungeons import DefaultSelectView
import os
import sys
import json
import asyncio
import platform
import psutil

class EmbedPaginatorView(AuthorView):
    def __init__(self, embeds):
        super().__init__(timeout=180)
        self.embeds = embeds
        self.current_page = 0
        self._update_buttons()

    def _update_buttons(self):
        self.prev_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page == len(self.embeds) - 1)

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

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
            config.save()
            
            await interaction.response.send_message(f"✅ Updated `{self.key}` to `{converted_val}`", ephemeral=True)
            
        except ValueError:
             await interaction.response.send_message(f"❌ Invalid format for {self.key}.", ephemeral=True)
        except Exception as e:
             await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

class ConfigSelect(Select):
    def __init__(self, bot):
        self.bot = bot
        from core import config
        options = []
        
        keys = ["target_level", "debug_mode", "profile_cache_ttl", "prices_cache_ttl", "owner_ids", "congrats_gifs"]
        
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
        
        if key == "congrats_gifs":
             gif_view = GifManageView(self.bot)
             gif_view.author_id = getattr(self.view, "author_id", None)
             await interaction.response.send_message("🎉 **Manage Congratulation GIFs**", view=gif_view, ephemeral=True)
             return

        current_val = getattr(config, key, "Unknown")
        await interaction.response.send_modal(ConfigEditModal(key, current_val))

class GifManageView(AuthorView):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Add GIF", style=discord.ButtonStyle.success, emoji="➕")
    async def add_gif(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GifAddModal())

    @discord.ui.button(label="Remove Last GIF", style=discord.ButtonStyle.danger, emoji="➖")
    async def remove_gif(self, interaction: discord.Interaction, button: discord.ui.Button):
        from core import config
        if config.congrats_gifs:
            removed = config.congrats_gifs.pop()
            config.save()
            await interaction.response.send_message(f"🗑️ Removed last GIF: `{removed}`", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No GIFs to remove.", ephemeral=True)

    @discord.ui.button(label="List GIFs", style=discord.ButtonStyle.secondary, emoji="📜")
    async def list_gifs(self, interaction: discord.Interaction, button: discord.ui.Button):
        from core import config
        gifs = config.congrats_gifs
        
        if not gifs:
             await interaction.response.send_message("No GIFs configured.", ephemeral=True)
             return

        lines = [f"`{g}`" for g in gifs]
        chunks = [lines[i:i+10] for i in range(0, len(lines), 10)]
        
        embeds = []
        for i, chunk in enumerate(chunks):
            embed = discord.Embed(title=f"Configured GIFs ({len(gifs)}) - Page {i+1}/{len(chunks)}", color=0x9b59b6)
            embed.description = "\n".join(chunk)
            embeds.append(embed)

        view = EmbedPaginatorView(embeds)
        view.author_id = self.author_id
        await interaction.response.send_message(embed=embeds[0], view=view, ephemeral=True)


class GifAddModal(Modal):
    def __init__(self):
        super().__init__(title="Add Congratulation GIF")
        self.gif_url = TextInput(label="GIF URL", placeholder="https://media.tenor.com/...", required=True)
        self.add_item(self.gif_url)

    async def on_submit(self, interaction: discord.Interaction):
        url = self.gif_url.value.strip()
        from core import config
        if url not in config.congrats_gifs:
            config.congrats_gifs.append(url)
            config.save()
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
            discord.SelectOption(label="Update & Restart Loop", value="update_restart", description="Git pull + Restart (3s)", emoji="🚀"),
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

        elif val == "update_restart":
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
                
                await interaction.followup.send(f"📥 **Update & Restart Initiated**\n\n**Git Output:**\n```\n{output}\n```\n🔄 Restarting in 3 seconds (loop script)...")
                
                await asyncio.sleep(1)
                await self.bot.close()
                
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


class LeaderboardAdminView(AuthorView):
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

class DataAdminView(AuthorView):
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

    @discord.ui.button(label="GitHub Backup", style=discord.ButtonStyle.success, emoji="📤")
    async def github_backup(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.bot.github_manager.is_enabled():
            await interaction.response.send_message("❌ **GitHub Backup is not configured.** Please set up `core/github_secrets.py` to use this feature.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=False)
        try:
            msg = await interaction.followup.send("📤 **Initiating GitHub data backup...**")
            success, message = await self.bot.github_manager.backup_data()
            if success:
                await msg.edit(content=f"✅ **Backup Success:** {message}")
            else:
                await msg.edit(content=f"❌ **Backup Failed:** {message}")
        except Exception as e:
            from core.logger import log_error
            log_error(f"Manual GitHub backup failed: {e}")
            await interaction.followup.send("❌ Error during backup process.")


SOLO_FLOORS = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "M1", "M2", "M3", "M4", "M5", "M6", "M7"]


def _build_run_detail_embed(run: dict, floor: str, uuid: str):
    from modules.solo_clears import format_time
    ign = run.get("ign", "Unknown")
    time_str = format_time(run.get("time_ms", 0))
    is_verified = run.get("verified", False)
    ts = run.get("date_achieved", 0)
    discord_id = run.get("discord_id", "")
    proof = run.get("proof_text", "—")
    score = run.get("score", 0)
    deaths = run.get("deaths", 0)
    crypts = run.get("crypts", 0)
    secrets = run.get("secrets", 0)
    puzzles = run.get("puzzles", []) or []
    prince = run.get("prince", False)
    mimic = run.get("mimic", False)

    color = 0x00ff00 if is_verified else 0xffa500
    emb = discord.Embed(
        title=f"{'✅ Verified' if is_verified else '⏱️ Unverified'} — {ign} on {floor}",
        color=color,
    )
    emb.add_field(name="Time", value=f"`{time_str}`", inline=True)
    emb.add_field(name="Score", value=str(score) if score > 0 else "—", inline=True)
    emb.add_field(name="Date", value=f"<t:{ts}:F>\n<t:{ts}:R>" if ts else "—", inline=True)

    submitter = f"<@{discord_id}>" if discord_id and str(discord_id).isdigit() else f"`{discord_id}`"
    emb.add_field(name="Submitted by", value=submitter, inline=True)
    emb.add_field(name="UUID", value=f"`{uuid}`", inline=True)
    emb.add_field(name="​", value="​", inline=True)

    stats_str = (
        f"Secrets: **{secrets}**\n"
        f"Deaths: **{deaths}**\n"
        f"Crypts: **{crypts}**\n"
        f"Prince: {'✅' if prince else '❌'}\n"
        f"Mimic: {'✅' if mimic else '❌'}\n"
        f"Puzzles ({len(puzzles)}): {', '.join(puzzles) if puzzles else '—'}"
    )
    emb.add_field(name="Stats", value=stats_str, inline=False)

    verification = run.get("verification") or {}
    if verification:
        method = verification.get("method", "—")
        moj = verification.get("mojang_verified", False)
        ident = verification.get("is_verified_owner", False)
        dev = verification.get("is_dev_key", False)
        modern = verification.get("modern_client", None)
        missing = verification.get("missing_evidence_fields", []) or []
        verified_at = verification.get("verified_at", 0)
        v_str = (
            f"Method: `{method}`\n"
            f"Mojang: {'✅' if moj else '❌'}  Identity: {'✅' if ident else '❌'}  Dev key: {'✅' if dev else '❌'}\n"
            f"Modern client: {'✅' if modern else ('❌' if modern is False else '—')}\n"
            f"Missing fields: {', '.join(missing) if missing else 'none'}\n"
            f"Verified at: <t:{verified_at}:R>" if verified_at else ""
        )
        emb.add_field(name="Verification", value=v_str or "—", inline=False)

    evidence = run.get("evidence") or {}
    if evidence:
        sc = evidence.get("score_components") or {}
        sc_str = (
            f"skill={sc.get('skill', 0)}, explore={sc.get('explore', 0)}, "
            f"time={sc.get('time', 0)}, bonus={sc.get('bonus', 0)} → **{sc.get('total', 0)}**"
        ) if sc else "—"

        e_str = (
            f"Score components: {sc_str}\n"
            f"Enter tick: `{evidence.get('dungeon_enter_tick', '—')}`  Clear tick: `{evidence.get('clear_trigger_tick', '—')}`\n"
            f"Enter clock: `{evidence.get('client_clock_enter', '—')}`  Clear clock: `{evidence.get('client_clock_clear', '—')}`\n"
            f"Mojang server_id: `{(evidence.get('mojang_server_id') or '—')[:16]}...`\n"
            f"Map data: {'present (' + str(len(evidence.get('map_data', {}).get('rooms', []))) + ' rooms)' if evidence.get('map_data') else 'absent'}\n"
            f"Scoreboard lines: {len(evidence.get('scoreboard_lines', []) or [])}\n"
            f"Tablist lines: {len(evidence.get('tablist_lines', []) or [])}"
        )
        emb.add_field(name="Evidence", value=e_str, inline=False)

    emb.add_field(name="Proof", value=proof[:1000], inline=False)
    return emb


def _render_run_map_file(run: dict):
    evidence = run.get("evidence") or {}
    map_data = evidence.get("map_data")
    if not map_data:
        return None
    try:
        from services.map_renderer import render_map
        import io as _io
        png = render_map(map_data)
        if not png:
            return None
        return discord.File(_io.BytesIO(png), filename="minimap.png")
    except Exception as e:
        log_error(f"[Admin] map render failed: {e}")
        return None


class EditProofModal(Modal):
    def __init__(self, bot, floor: str, uuid: str, run: dict):
        super().__init__(title="Edit Proof")
        self.bot = bot
        self.floor = floor
        self.uuid = uuid
        self.run = run
        self.proof_input = TextInput(
            label="Proof",
            style=discord.TextStyle.paragraph,
            default=run.get("proof_text", ""),
            required=False,
            max_length=1000,
        )
        self.add_item(self.proof_input)

    async def on_submit(self, interaction: discord.Interaction):
        new_proof = self.proof_input.value.strip()
        floor_data = self.bot.solo_manager.data.get(self.floor.upper(), {})
        if self.uuid in floor_data:
            floor_data[self.uuid]["proof_text"] = new_proof
            await self.bot.solo_manager._save_data()
            self.run["proof_text"] = new_proof
        await interaction.response.send_message("\u2705 Proof updated.", ephemeral=True)


class SoloRunDetailView(AuthorView):
    def __init__(self, bot, floor: str, uuid: str, run: dict, all_runs: list, author_id=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.floor = floor
        self.uuid = uuid
        self.run = run
        self.all_runs = all_runs
        self.author_id = author_id
        self._build_buttons()

    def _build_buttons(self):
        self.clear_items()
        is_ver = self.run.get("verified", False)

        del_btn = discord.ui.Button(label="Delete", style=discord.ButtonStyle.danger, emoji="🗑️", row=0)
        del_btn.callback = self.delete_btn
        self.add_item(del_btn)

        if is_ver:
            unver_btn = discord.ui.Button(label="Unverify", style=discord.ButtonStyle.secondary, emoji="❌", row=0)
            unver_btn.callback = self.unverify_btn
            self.add_item(unver_btn)
        else:
            ver_btn = discord.ui.Button(label="Verify", style=discord.ButtonStyle.success, emoji="✅", row=0)
            ver_btn.callback = self.verify_btn
            self.add_item(ver_btn)

        edit_proof_btn = discord.ui.Button(label="Edit Proof", style=discord.ButtonStyle.secondary, emoji="✏️", row=0)
        edit_proof_btn.callback = self.edit_proof_btn
        self.add_item(edit_proof_btn)

        sb_btn = discord.ui.Button(label="Scoreboard", style=discord.ButtonStyle.secondary, emoji="📜", row=1)
        sb_btn.callback = self.show_scoreboard
        self.add_item(sb_btn)

        tab_btn = discord.ui.Button(label="Tablist", style=discord.ButtonStyle.secondary, emoji="📋", row=1)
        tab_btn.callback = self.show_tablist
        self.add_item(tab_btn)

        back_btn = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, emoji="⬅️", row=1)
        back_btn.callback = self.back_btn
        self.add_item(back_btn)

    async def _refresh(self, interaction: discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.defer()
        embed = _build_run_detail_embed(self.run, self.floor, self.uuid)
        map_file = _render_run_map_file(self.run)
        self._build_buttons()
        kwargs = {"content": None, "embed": embed, "view": self, "attachments": []}
        if map_file is not None:
            kwargs["attachments"] = [map_file]
            embed.set_image(url="attachment://minimap.png")
        await interaction.edit_original_response(**kwargs)

    async def delete_btn(self, interaction: discord.Interaction):
        await interaction.response.defer()
        view = SoloDeleteConfirmView(self.bot, self.floor, self.uuid, self.run, self.all_runs, author_id=self.author_id)
        embed = discord.Embed(
            title="⚠️ Confirm deletion",
            description=(
                f"Delete `{self.run.get('ign')}`'s **{self.floor}** run "
                f"(`{self.run.get('time_ms', 0)} ms`) permanently?\n\nThis cannot be undone."
            ),
            color=0xff0000,
        )
        await interaction.edit_original_response(content=None, embed=embed, view=view, attachments=[])

    async def verify_btn(self, interaction: discord.Interaction):
        success, _ = await self.bot.solo_manager.verify_run(self.floor, self.uuid, True, method="proof")
        if success:
            self.run["verified"] = True
            self.run["verified_method"] = "proof"
        await self._refresh(interaction)

    async def edit_proof_btn(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EditProofModal(self.bot, self.floor, self.uuid, self.run))

    async def unverify_btn(self, interaction: discord.Interaction):
        floor_data = self.bot.solo_manager.data.get(self.floor.upper(), {})
        rec = floor_data.get(self.uuid)
        if rec is not None:
            rec["verified"] = False
            await self.bot.solo_manager._save_data()
            self.run["verified"] = False
        await self._refresh(interaction)

    async def show_scoreboard(self, interaction: discord.Interaction):
        lines = (self.run.get("evidence") or {}).get("scoreboard_lines") or []
        if not lines:
            await interaction.response.send_message("*(No scoreboard data captured.)*", ephemeral=True)
            return
        body = "\n".join(lines)
        if len(body) > 1900:
            body = body[:1900] + "\n…"
        await interaction.response.send_message(f"```\n{body}\n```", ephemeral=True)

    async def show_tablist(self, interaction: discord.Interaction):
        lines = (self.run.get("evidence") or {}).get("tablist_lines") or []
        if not lines:
            await interaction.response.send_message("*(No tablist data captured.)*", ephemeral=True)
            return
        body = "\n".join(lines)
        if len(body) > 1900:
            body = body[:1900] + "\n…"
        await interaction.response.send_message(f"```\n{body}\n```", ephemeral=True)

    async def back_btn(self, interaction: discord.Interaction):
        await interaction.response.defer()
        view = SoloRunPickerView(self.bot, self.floor, self.all_runs, author_id=self.author_id)
        await interaction.edit_original_response(
            content=f"Select a run on **{self.floor}**:",
            embed=None,
            view=view,
            attachments=[],
        )


class SoloDeleteConfirmView(AuthorView):
    def __init__(self, bot, floor: str, uuid: str, run: dict, all_runs: list, author_id=None):
        super().__init__(timeout=120)
        self.bot = bot
        self.floor = floor
        self.uuid = uuid
        self.run = run
        self.all_runs = all_runs
        self.author_id = author_id

    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        success, msg = await self.bot.solo_manager.remove_run(self.floor, self.uuid)
        if success:
            self.all_runs[:] = [r for r in self.all_runs if r["uuid"] != self.uuid]
        embed = discord.Embed(
            title="✅ Deleted" if success else "❌ Delete failed",
            description=msg,
            color=0x00ff00 if success else 0xff0000,
        )
        if self.all_runs:
            view = SoloRunPickerView(self.bot, self.floor, self.all_runs, author_id=self.author_id)
            await interaction.edit_original_response(
                content=f"Select a run on **{self.floor}**:",
                embed=embed,
                view=view,
                attachments=[],
            )
        else:
            view = SoloFloorPickerView(self.bot, author_id=self.author_id)
            await interaction.edit_original_response(
                content="Pick a floor:",
                embed=embed,
                view=view,
                attachments=[],
            )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="↩️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        view = SoloRunDetailView(self.bot, self.floor, self.uuid, self.run, self.all_runs, author_id=self.author_id)
        embed = _build_run_detail_embed(self.run, self.floor, self.uuid)
        map_file = _render_run_map_file(self.run)
        kwargs = {"content": None, "embed": embed, "view": view, "attachments": []}
        if map_file is not None:
            kwargs["attachments"] = [map_file]
            embed.set_image(url="attachment://minimap.png")
        await interaction.edit_original_response(**kwargs)


class SoloRunPickerSelect(discord.ui.Select):
    def __init__(self, bot, floor: str, runs: list, author_id):
        from modules.solo_clears import format_time
        self.bot = bot
        self.floor = floor
        self.runs = runs
        self.author_id = author_id
        options = []
        for i, run in enumerate(runs[:25], 1):
            ign = run.get("ign", "Unknown")
            time_str = format_time(run.get("time_ms", 0))
            is_ver = run.get("verified", False)
            options.append(discord.SelectOption(
                label=f"#{i} {ign} — {time_str}",
                value=run["uuid"],
                description="Verified" if is_ver else "Unverified",
                emoji="✅" if is_ver else "⏱️",
            ))
        super().__init__(placeholder="Select a run to view…", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        try:
            uuid = self.values[0]
            run = next((r for r in self.runs if r["uuid"] == uuid), None)
            if not run:
                await interaction.response.send_message("Run no longer exists.", ephemeral=True)
                return
            await interaction.response.defer()
            view = SoloRunDetailView(self.bot, self.floor, uuid, run, self.runs, author_id=self.author_id)
            embed = _build_run_detail_embed(run, self.floor, uuid)
            map_file = _render_run_map_file(run)
            kwargs = {"embed": embed, "view": view, "content": None, "attachments": []}
            if map_file is not None:
                kwargs["attachments"] = [map_file]
                embed.set_image(url="attachment://minimap.png")
            await interaction.edit_original_response(**kwargs)
        except Exception as e:
            import traceback
            tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            log_error(f"[SoloAdmin] run picker failed: {tb}")
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(f"❌ Error:\n```py\n{tb[-1500:]}\n```", ephemeral=True)
                else:
                    await interaction.response.send_message(f"❌ Error:\n```py\n{tb[-1500:]}\n```", ephemeral=True)
            except Exception:
                pass


class SoloRunPickerView(AuthorView):
    def __init__(self, bot, floor: str, runs: list, author_id=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.floor = floor
        self.runs = runs
        self.author_id = author_id
        self.add_item(SoloRunPickerSelect(bot, floor, runs, author_id))

        back_btn = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, emoji="⬅️", row=1)
        back_btn.callback = self._back
        self.add_item(back_btn)

    async def _back(self, interaction: discord.Interaction):
        await interaction.response.defer()
        view = SoloFloorPickerView(self.bot, author_id=self.author_id)
        await interaction.edit_original_response(content="Pick a floor:", embed=None, view=view, attachments=[])


class SoloFloorPickerSelect(discord.ui.Select):
    def __init__(self, bot, author_id):
        self.bot = bot
        self.author_id = author_id
        floor_data = bot.solo_manager.data
        options = []
        for fl in SOLO_FLOORS:
            count = len(floor_data.get(fl, {}) or {})
            if count == 0:
                continue
            options.append(discord.SelectOption(
                label=fl,
                value=fl,
                description=f"{count} run{'s' if count != 1 else ''}",
            ))
        if not options:
            options.append(discord.SelectOption(label="(no clears recorded)", value="__none__"))
        super().__init__(placeholder="Pick a floor…", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        try:
            fl = self.values[0]
            if fl == "__none__":
                await interaction.response.send_message("No clears recorded yet.", ephemeral=True)
                return
            runs = self.bot.solo_manager.get_leaderboard(fl, "all")
            if not runs:
                await interaction.response.send_message(f"No clears on {fl}.", ephemeral=True)
                return
            if not interaction.response.is_done():
                await interaction.response.defer()
            view = SoloRunPickerView(self.bot, fl, runs, author_id=self.author_id)
            await interaction.edit_original_response(content=f"Select a run on **{fl}**:", embed=None, view=view, attachments=[])
        except Exception as e:
            import traceback
            tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            log_error(f"[SoloAdmin] floor picker failed: {tb}")
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(f"❌ Error:\n```py\n{tb[-1500:]}\n```", ephemeral=True)
                else:
                    await interaction.response.send_message(f"❌ Error:\n```py\n{tb[-1500:]}\n```", ephemeral=True)
            except Exception:
                pass


class SoloFloorPickerView(AuthorView):
    def __init__(self, bot, author_id=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.author_id = author_id
        self.add_item(SoloFloorPickerSelect(bot, author_id))

class ForceAddSoloClearModal(Modal):
    def __init__(self, bot):
        super().__init__(title="Force Add Solo Clear")
        self.bot = bot
        self.ign = TextInput(label="Minecraft IGN", required=True)
        self.floor = TextInput(label="Floor (e.g. M7)", required=True)
        self.time = TextInput(label="Time (MM:SS.ms)", placeholder="e.g. 4:20.50", required=True)
        self.add_item(self.ign)
        self.add_item(self.floor)
        self.add_item(self.time)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        from services.api import get_uuid
        from modules.solo_clears import parse_time
        
        time_ms = parse_time(self.time.value)
        if time_ms <= 0:
             await interaction.followup.send("❌ Invalid time format.")
             return

        uuid = await get_uuid(self.ign.value)
        if not uuid:
            await interaction.followup.send("❌ Player not found.")
            return
        
        success, msg = await self.bot.solo_manager.submit_run(
            self.floor.value, self.ign.value, uuid, time_ms, 
            "Force Added via Admin Panel", interaction.user.id, auto_verify=True
        )
        await interaction.followup.send(f"{'✅' if success else '❌'} {msg}")

class SoloClearsAdminView(AuthorView):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.bot = bot

    @discord.ui.button(label="Force Add Clear", style=discord.ButtonStyle.success, emoji="➕")
    async def force_add(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ForceAddSoloClearModal(self.bot))

    @discord.ui.button(label="Browse Clears", style=discord.ButtonStyle.primary, emoji="🔍")
    async def browse_clears(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SoloFloorPickerView(self.bot, author_id=self.author_id)
        await interaction.response.send_message("Pick a floor:", view=view, ephemeral=True)

class IpBanModal(Modal):
    def __init__(self):
        super().__init__(title="Ban IP from API")
        self.ip_input = TextInput(
            label="IP Address",
            placeholder="e.g. 1.2.3.4",
            required=True,
            max_length=64,
        )
        self.reason_input = TextInput(
            label="Reason",
            placeholder="e.g. Abusing API, spamming /v1/solo_clear",
            required=True,
            style=discord.TextStyle.paragraph,
            max_length=500,
        )
        self.add_item(self.ip_input)
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        ip = self.ip_input.value.strip()
        reason = self.reason_input.value.strip()

        if not ip:
            await interaction.response.send_message("❌ IP cannot be empty.", ephemeral=True)
            return

        ok = await ban_manager.ban(ip, reason, interaction.user.id)
        if not ok:
            await interaction.response.send_message("❌ Failed to ban IP.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"🚫 Banned `{ip}`\n**Reason:** {reason}",
            ephemeral=True,
        )


class IpUnbanModal(Modal):
    def __init__(self):
        super().__init__(title="Unban IP")
        self.ip_input = TextInput(
            label="IP Address",
            placeholder="e.g. 1.2.3.4",
            required=True,
            max_length=64,
        )
        self.add_item(self.ip_input)

    async def on_submit(self, interaction: discord.Interaction):
        ip = self.ip_input.value.strip()
        ok = await ban_manager.unban(ip)
        if ok:
            await interaction.response.send_message(f"✅ Unbanned `{ip}`.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ `{ip}` is not banned.", ephemeral=True)


class IpBansView(AuthorView):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.bot = bot

    @discord.ui.button(label="Ban IP", style=discord.ButtonStyle.danger, emoji="🚫")
    async def ban_ip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(IpBanModal())

    @discord.ui.button(label="Unban IP", style=discord.ButtonStyle.success, emoji="✅")
    async def unban_ip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(IpUnbanModal())

    @discord.ui.button(label="List Bans", style=discord.ButtonStyle.secondary, emoji="📜")
    async def list_bans(self, interaction: discord.Interaction, button: discord.ui.Button):
        bans = ban_manager.get_all()
        if not bans:
            await interaction.response.send_message("No banned IPs.", ephemeral=True)
            return

        lines = []
        for ip, entry in bans.items():
            reason = entry.get("reason", "No reason")
            banned_by = entry.get("banned_by", "?")
            ts = entry.get("banned_at", 0)
            when = f"<t:{ts}:R>" if ts else "unknown"
            lines.append(f"`{ip}` — {reason}\n └ by <@{banned_by}> {when}")

        chunks = [lines[i:i+10] for i in range(0, len(lines), 10)]
        embeds = []
        for i, chunk in enumerate(chunks):
            embed = discord.Embed(
                title=f"Banned IPs ({len(bans)}) - Page {i+1}/{len(chunks)}",
                color=0xE74C3C,
            )
            embed.description = "\n\n".join(chunk)
            embeds.append(embed)

        view = EmbedPaginatorView(embeds)
        view.author_id = self.author_id
        await interaction.response.send_message(embed=embeds[0], view=view, ephemeral=True)


def _format_log_line(entry: dict) -> str:
    status = entry.get("status", 0)
    if status == 0:
        status_emoji = "❔"
    elif 200 <= status < 300 or status == 101:
        status_emoji = "✅"
    elif status == 429:
        status_emoji = "🐢"
    elif status == 403:
        status_emoji = "🚫"
    elif 400 <= status < 500:
        status_emoji = "⚠️"
    else:
        status_emoji = "❌"

    path = entry.get("path", "")
    query = entry.get("query", "")
    target = f"{path}?{query}" if query else path
    if len(target) > 80:
        target = target[:77] + "..."

    ts = entry.get("ts", 0)
    when = f"<t:{ts}:T>" if ts else "?"
    return (
        f"{status_emoji} `{status}` {when} **{entry.get('method', '?')}** `{target}`\n"
        f" └ from `{entry.get('ip', '?')}`"
    )


def _build_log_embeds(entries: list, title_prefix: str) -> list:
    if not entries:
        return []
    chunks = [entries[i:i+10] for i in range(0, len(entries), 10)]
    embeds = []
    for i, chunk in enumerate(chunks):
        embed = discord.Embed(
            title=f"{title_prefix} ({len(entries)}) - Page {i+1}/{len(chunks)}",
            color=0x3498DB,
        )
        embed.description = "\n\n".join(_format_log_line(e) for e in chunk)
        embeds.append(embed)
    return embeds


class RequestLogFilterModal(Modal):
    def __init__(self, author_id=None):
        super().__init__(title="Filter API Log by IP")
        self.author_id = author_id
        self.ip_input = TextInput(
            label="IP Address",
            placeholder="e.g. 1.2.3.4",
            required=True,
            max_length=64,
        )
        self.add_item(self.ip_input)

    async def on_submit(self, interaction: discord.Interaction):
        ip = self.ip_input.value.strip()
        entries = request_log.get_recent(ip_filter=ip)
        if not entries:
            await interaction.response.send_message(f"No requests logged from `{ip}`.", ephemeral=True)
            return
        embeds = _build_log_embeds(entries, f"API Requests from {ip}")
        view = EmbedPaginatorView(embeds)
        view.author_id = self.author_id
        await interaction.response.send_message(embed=embeds[0], view=view, ephemeral=True)


class RequestLogView(AuthorView):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.bot = bot

    @discord.ui.button(label="View Recent", style=discord.ButtonStyle.primary, emoji="📜")
    async def view_recent(self, interaction: discord.Interaction, button: discord.ui.Button):
        entries = request_log.get_recent()
        if not entries:
            await interaction.response.send_message("No API requests logged yet.", ephemeral=True)
            return
        embeds = _build_log_embeds(entries, "Recent API Requests")
        view = EmbedPaginatorView(embeds)
        view.author_id = self.author_id
        await interaction.response.send_message(embed=embeds[0], view=view, ephemeral=True)

    @discord.ui.button(label="Filter by IP", style=discord.ButtonStyle.secondary, emoji="🔍")
    async def filter_by_ip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RequestLogFilterModal(author_id=self.author_id))

    @discord.ui.button(label="Clear Log", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def clear_log(self, interaction: discord.Interaction, button: discord.ui.Button):
        request_log.clear()
        await interaction.response.send_message("✅ API request log cleared.", ephemeral=True)


class AdminView(AuthorView):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Dungeons", style=discord.ButtonStyle.primary, emoji="🏰", row=0)
    async def dungeons(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = DefaultSelectView(self.bot)
        view.author_id = self.author_id
        embed = view._create_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

    @discord.ui.button(label="Leaderboard", style=discord.ButtonStyle.primary, emoji="🏆", row=0)
    async def leaderboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = LeaderboardAdminView(self.bot)
        view.author_id = self.author_id
        await interaction.response.send_message("🏆 **Leaderboard Admin**", view=view, ephemeral=True)

    @discord.ui.button(label="Data", style=discord.ButtonStyle.secondary, emoji="📁", row=0)
    async def data(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = DataAdminView(self.bot)
        view.author_id = self.author_id
        await interaction.response.send_message("📁 **Data Management**", view=view, ephemeral=True)

    @discord.ui.button(label="Force Link", style=discord.ButtonStyle.secondary, emoji="🔗", row=1)
    async def force_link(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ForceLinkModal(self.bot))

    @discord.ui.button(label="Config", style=discord.ButtonStyle.secondary, emoji="⚙️", row=1)
    async def config(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = AuthorView()
        view.author_id = self.author_id
        view.add_item(ConfigSelect(self.bot))
        await interaction.response.send_message("⚙️ **Configuration Editor**", view=view, ephemeral=True)

    @discord.ui.button(label="System", style=discord.ButtonStyle.secondary, emoji="🖥️", row=1)
    async def system(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = AuthorView()
        view.author_id = self.author_id
        view.add_item(SystemSelect(self.bot))
        await interaction.response.send_message("🖥️ **System Operations**", view=view, ephemeral=True)

    @discord.ui.button(label="Solo Clears", style=discord.ButtonStyle.primary, emoji="⚔️", row=2)
    async def solo_clears(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SoloClearsAdminView(self.bot)
        view.author_id = self.author_id
        await interaction.response.send_message("⚔️ **Solo Clears Admin**", view=view, ephemeral=True)

    @discord.ui.button(label="IP Bans", style=discord.ButtonStyle.danger, emoji="🚫", row=2)
    async def ip_bans(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = IpBansView(self.bot)
        view.author_id = self.author_id
        await interaction.response.send_message("🚫 **API IP Ban Management**", view=view, ephemeral=True)

    @discord.ui.button(label="API Logs", style=discord.ButtonStyle.secondary, emoji="📡", row=2)
    async def api_logs(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = RequestLogView(self.bot)
        view.author_id = self.author_id
        await interaction.response.send_message("📡 **API Request Log**", view=view, ephemeral=True)

    @discord.ui.button(label="Update & Restart", style=discord.ButtonStyle.danger, emoji="🚀", row=2)
    async def update_restart(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=False)
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
            
            await interaction.followup.send(f"📥 **Update & Restart Initiated**\n\n**Git Output:**\n```\n{output}\n```\n🔄 Restarting in 3 seconds (loop script)...")
            
            await asyncio.sleep(1)
            await self.bot.close()
            
        except Exception as e:
            await interaction.followup.send(f"❌ Update failed: {e}")


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="admin", description="Owner-only administration panel")
    async def admin(self, interaction: discord.Interaction):
        if interaction.user.id not in config.owner_ids:
            await interaction.response.send_message("❌ You do not have permission to access the admin panel.", ephemeral=True)
            return

        embed = discord.Embed(title="🛡️ Admin Panel", description="Select a category via buttons below.", color=0x2b2d31)
        view = AdminView(self.bot)
        view.author_id = interaction.user.id
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
