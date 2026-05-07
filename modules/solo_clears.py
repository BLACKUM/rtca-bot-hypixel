import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
from core.logger import log_info, log_error
from core.ui import AuthorView
import math

PAGE_SIZE = 10

try:
    from core.secrets import SOLO_CLEAR_CHANNEL_ID
except ImportError:
    SOLO_CLEAR_CHANNEL_ID = None
import time

def parse_time(time_str: str) -> int:
    try:
        if ":" in time_str:
            parts = time_str.split(":")
            m = int(parts[0])
            s_parts = parts[1].split(".")
            s = int(s_parts[0])
            ms = int(s_parts[1]) if len(s_parts) > 1 else 0
            if len(s_parts) > 1 and len(s_parts[1]) == 2:
                ms *= 10
            return (m * 60 * 1000) + (s * 1000) + ms
        return int(time_str)
    except Exception:
        return -1

def format_time(ms: int) -> str:
    s, ms_rem = divmod(ms, 1000)
    m, s = divmod(s, 60)
    return f"{m:02d}:{s:02d}.{ms_rem:03d}"

class VerifyView(AuthorView):
    def __init__(self, bot, floor, uuid):
        super().__init__(timeout=None)
        self.bot = bot
        self.floor = floor
        self.uuid = uuid

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, custom_id="verify_approve")
    async def approve(self, interaction: discord.Interaction, button: Button):
        success, msg = await self.bot.solo_manager.verify_run(self.floor, self.uuid, True)
        if success:
            embed = interaction.message.embeds[0]
            embed.color = 0x00ff00
            embed.title = "✅ Solo Clear Approved"
            embed.set_footer(text=f"Approved by {interaction.user.name}")
            await interaction.message.edit(embed=embed, view=None)
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger, custom_id="verify_reject")
    async def reject(self, interaction: discord.Interaction, button: Button):
        success, msg = await self.bot.solo_manager.verify_run(self.floor, self.uuid, False)
        if success:
            embed = interaction.message.embeds[0]
            embed.color = 0xff0000
            embed.title = "❌ Solo Clear Rejected"
            embed.set_footer(text=f"Rejected by {interaction.user.name}")
            await interaction.message.edit(embed=embed, view=None)
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)

class SubmitModal(Modal):
    def __init__(self, bot, floor):
        super().__init__(title=f"Submit Solo Clear - {floor}")
        self.bot = bot
        self.floor = floor

        self.ign = TextInput(label="Your IGN", required=True, max_length=16)
        self.time = TextInput(label="Clear Time (MM:SS.ms)", placeholder="e.g. 4:20.50", required=True)
        self.proof = TextInput(
            label="Proof",
            style=discord.TextStyle.paragraph,
            placeholder="Video URL or screenshot link. High ranks may require video proof.",
            required=True,
            max_length=1000
        )

        self.add_item(self.ign)
        self.add_item(self.time)
        self.add_item(self.proof)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        ign_val = self.ign.value.strip()
        time_val = self.time.value.strip()
        proof_val = self.proof.value.strip()

        time_ms = parse_time(time_val)
        if time_ms <= 0:
            await interaction.followup.send("❌ Invalid time format. Please use `MM:SS` or `MM:SS.ms`.")
            return

        from services.api import get_uuid
        uuid = await get_uuid(ign_val)
        if not uuid:
            await interaction.followup.send("❌ Could not resolve UUID for that IGN.")
            return

        success, msg = await self.bot.solo_manager.submit_run(
            self.floor, ign_val, uuid, time_ms, proof_val, interaction.user.id
        )

        if not success:
            await interaction.followup.send(f"❌ {msg}")
            return

        view = VerifyView(self.bot, self.floor, uuid)
        embed = discord.Embed(title="New Solo Clear Submission", color=0x00ffff)
        embed.add_field(name="Player", value=f"`{ign_val}`\n<@{interaction.user.id}>", inline=True)
        embed.add_field(name="Floor", value=self.floor, inline=True)
        embed.add_field(name="Time", value=format_time(time_ms), inline=True)
        embed.add_field(name="Proof / Details", value=proof_val, inline=False)
        
        target_channel = interaction.channel
        if SOLO_CLEAR_CHANNEL_ID:
            solo_ch = interaction.client.get_channel(SOLO_CLEAR_CHANNEL_ID)
            if solo_ch:
                target_channel = solo_ch

        await target_channel.send(embed=embed, view=view)
        await interaction.followup.send(f"✅ {msg}")

class SoloSearchModal(Modal):
    def __init__(self, view):
        super().__init__(title="Search Solo Leaderboard")
        self.view = view
        self.ign_input = TextInput(label="IGN", placeholder="Enter IGN to find...", required=False, max_length=16)
        self.page_input = TextInput(label="Page Number", placeholder="Enter page number...", required=False, max_length=5)
        self.add_item(self.ign_input)
        self.add_item(self.page_input)

    async def on_submit(self, interaction: discord.Interaction):
        ign_val = self.ign_input.value.strip()
        page_val = self.page_input.value.strip()

        if page_val:
            try:
                page_num = int(page_val)
                if 1 <= page_num <= self.view.total_pages:
                    self.view.page = page_num
                    await self.view.update_message(interaction)
                else:
                    await interaction.response.send_message(f"❌ Page must be between 1 and {self.view.total_pages}.", ephemeral=True)
            except ValueError:
                await interaction.response.send_message("❌ Invalid page number.", ephemeral=True)
            return

        if ign_val:
            data = self.view.bot.solo_manager.get_leaderboard(self.view.floor, self.view.category)
            target = ign_val.lower()
            found_index = next((i for i, r in enumerate(data) if r.get("ign", "").lower() == target), -1)
            if found_index >= 0:
                self.view.page = (found_index // PAGE_SIZE) + 1
                await self.view.update_message(interaction)
            else:
                await interaction.response.send_message(f"❌ '{ign_val}' not found in this leaderboard.", ephemeral=True)
            return

        await interaction.response.send_message("❌ Please enter an IGN or page number.", ephemeral=True)


class RunSelect(Select):
    def __init__(self, view, runs, start_rank=1):
        self._lb_view = view
        options = []
        for i, run in enumerate(runs[:25], start_rank):
            ign = run.get('ign', 'Unknown')
            time_str = format_time(run.get('time_ms', 0))
            emoji = "✅" if run.get("verified") else "⏱️"
            options.append(discord.SelectOption(
                label=f"#{i} - {ign}",
                description=f"Time: {time_str}",
                value=run['uuid'],
                emoji=emoji
            ))
        
        super().__init__(placeholder="Inspect run details...", min_values=1, max_values=1, options=options, custom_id="run_inspect_select")

    async def callback(self, interaction: discord.Interaction):
        uuid = self.values[0]
        self._lb_view.inspect_uuid = uuid
        await self._lb_view.update_message(interaction)

class LeaderboardView(AuthorView):
    def __init__(self, bot, floor, category="all", ign=None):
        super().__init__(timeout=None)
        self.bot = bot
        self.floor = floor
        self.category = category
        self.ign = ign
        self.inspect_uuid = None
        self.page = 1
        self.total_pages = 1
        self.update_components()

    def update_components(self):
        self.clear_items()

        if self.inspect_uuid:
            btn = discord.ui.Button(label="⬅ Back to Leaderboard", style=discord.ButtonStyle.secondary, custom_id="lb_back")
            btn.callback = self.btn_back
            self.add_item(btn)
            return

        cat_ver = discord.ui.Button(label="Verified", style=discord.ButtonStyle.primary if self.category == "verified" else discord.ButtonStyle.secondary, row=0, custom_id="lb_cat_verified")
        cat_unver = discord.ui.Button(label="Unverified", style=discord.ButtonStyle.primary if self.category == "unverified" else discord.ButtonStyle.secondary, row=0, custom_id="lb_cat_unverified")
        cat_all = discord.ui.Button(label="All", style=discord.ButtonStyle.primary if self.category == "all" else discord.ButtonStyle.secondary, row=0, custom_id="lb_cat_all")
        cat_ver.callback = self.btn_verified
        cat_unver.callback = self.btn_unverified
        cat_all.callback = self.btn_all
        self.add_item(cat_ver)
        self.add_item(cat_unver)
        self.add_item(cat_all)

        prev_b = discord.ui.Button(emoji="⬅️", style=discord.ButtonStyle.secondary, row=1, custom_id="lb_prev", disabled=self.page <= 1)
        search_b = discord.ui.Button(emoji="🔍", style=discord.ButtonStyle.secondary, row=1, custom_id="lb_search")
        next_b = discord.ui.Button(emoji="➡️", style=discord.ButtonStyle.secondary, row=1, custom_id="lb_next", disabled=self.page >= self.total_pages)
        showme_b = discord.ui.Button(label="📍 Show Me", style=discord.ButtonStyle.primary, row=1, custom_id="lb_showme")
        prev_b.callback = self.prev_btn
        search_b.callback = self.search_btn
        next_b.callback = self.next_btn
        showme_b.callback = self.show_me_btn
        self.add_item(prev_b)
        self.add_item(search_b)
        self.add_item(next_b)
        self.add_item(showme_b)

        runs = self.bot.solo_manager.get_leaderboard(self.floor, self.category)
        if runs:
            start = (self.page - 1) * PAGE_SIZE
            page_runs = runs[start:start + PAGE_SIZE]
            if page_runs:
                self.add_item(RunSelect(self, page_runs, start_rank=start + 1))

    def build_embed(self):
        runs = self.bot.solo_manager.get_leaderboard(self.floor, self.category)
        
        if self.inspect_uuid:
            target_run = next((r for r in runs if r['uuid'] == self.inspect_uuid), None)
            if not target_run:
                self.inspect_uuid = None
                return self.build_embed()

            time_str = format_time(target_run.get('time_ms', 0))
            ts = target_run.get('date_achieved', 0)
            secrets = target_run.get('secrets', 0)
            puzzles = target_run.get('puzzles', [])
            prince = target_run.get('prince', False)
            mimic = target_run.get('mimic', False)
            proof = target_run.get('proof_text', 'None provided')
            
            emb = discord.Embed(title=f"Run Details - {target_run.get('ign')}", color=0x3498db)
            emb.add_field(name="Floor", value=self.floor, inline=True)
            emb.add_field(name="Time", value=time_str, inline=True)
            emb.add_field(name="Status", value="Verified ✅" if target_run.get('verified') else "Unverified ⏱️", inline=True)
            emb.add_field(name="Date", value=f"<t:{ts}:D> (<t:{ts}:R>)", inline=False)
            
            score = target_run.get('score', 0)
            deaths = target_run.get('deaths', 0)
            crypts = target_run.get('crypts', 0)

            if score == 0 and deaths == 0 and crypts == 0 and secrets == 0 and not puzzles and not prince and not mimic:
                emb.add_field(name="Run info", value="*Not provided (Manual Submission)*", inline=False)
            else:
                emb.add_field(name="Score", value=str(score) if score > 0 else "Unknown", inline=True)
                emb.add_field(name="Crypts", value=str(crypts), inline=True)
                emb.add_field(name="Deaths", value=str(deaths), inline=True)
                
                emb.add_field(name="Secrets", value=str(secrets), inline=True)
                emb.add_field(name="Puzzles", value=str(len(puzzles)), inline=True)
                emb.add_field(name="Objectives", value=f"Prince: {'✅' if prince else '❌'}  |  Mimic: {'✅' if mimic else '❌'}", inline=False)
                
                if puzzles:
                    emb.add_field(name="Puzzle List", value=", ".join(puzzles), inline=False)
                
            emb.add_field(name="Proof", value=proof, inline=False)
            return emb

        embed = discord.Embed(title=f"Solo Leaderboard - {self.floor} ({self.category.title()})", color=0x3498db)
        if not runs:
            self.total_pages = 1
            self.page = 1
            embed.description = "No clears found for this category."
            embed.set_footer(text=f"Page 1/1 • Your IGN: {self.ign or '—'}")
            return embed

        self.total_pages = max(1, math.ceil(len(runs) / PAGE_SIZE))
        if self.page > self.total_pages: self.page = self.total_pages
        if self.page < 1: self.page = 1

        start = (self.page - 1) * PAGE_SIZE
        end = start + PAGE_SIZE
        page_runs = runs[start:end]

        desc = ""
        for i, run in enumerate(page_runs, start + 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**#{i}**"
            ign = run.get("ign", "Unknown")

            user_id = self.bot.daily_manager.get_user_id_by_ign(ign)
            if ign.upper() == "BLACKUM":
                display_name = "<@679725029109399574>"
            elif user_id:
                display_name = f"<@{user_id}>"
            else:
                display_name = f"**{ign}**"

            time_str = format_time(run.get("time_ms", 0))
            ts = run.get("date_achieved", 0)
            ver_emoji = "✅" if run.get("verified") else "⏱️"
            line = f"{medal} {display_name} • `{time_str}` • {ver_emoji} <t:{ts}:R>"
            if self.ign and ign.lower() == self.ign.lower():
                line = f"{line} ← you"
            desc += line + "\n"
        embed.description = desc
        embed.set_footer(text=f"Page {self.page}/{self.total_pages} • Your IGN: {self.ign or '—'}")
        return embed

    async def update_message(self, interaction: discord.Interaction):
        embed = self.build_embed()
        self.update_components()
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def btn_back(self, interaction: discord.Interaction):
        self.inspect_uuid = None
        await self.update_message(interaction)

    async def btn_verified(self, interaction: discord.Interaction):
        self.category = "verified"
        self.inspect_uuid = None
        self.page = 1
        await self.update_message(interaction)

    async def btn_unverified(self, interaction: discord.Interaction):
        self.category = "unverified"
        self.inspect_uuid = None
        self.page = 1
        await self.update_message(interaction)

    async def btn_all(self, interaction: discord.Interaction):
        self.category = "all"
        self.inspect_uuid = None
        self.page = 1
        await self.update_message(interaction)

    async def prev_btn(self, interaction: discord.Interaction):
        self.page = max(1, self.page - 1)
        await self.update_message(interaction)

    async def next_btn(self, interaction: discord.Interaction):
        self.page = min(self.total_pages, self.page + 1)
        await self.update_message(interaction)

    async def search_btn(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SoloSearchModal(self))

    async def show_me_btn(self, interaction: discord.Interaction):
        ign = self.ign
        if not ign:
            ign = self.bot.link_manager.get_link(interaction.user.id)
            if not ign:
                await interaction.response.send_message("❌ Link your account first with `/link <ign>`.", ephemeral=True)
                return
            self.ign = ign

        runs = self.bot.solo_manager.get_leaderboard(self.floor, self.category)
        target = ign.lower()
        found_index = next((i for i, r in enumerate(runs) if r.get("ign", "").lower() == target), -1)
        if found_index < 0:
            await interaction.response.send_message("❌ You are not on this leaderboard yet.", ephemeral=True)
            return
        self.page = (found_index // PAGE_SIZE) + 1
        await self.update_message(interaction)

class SoloClears(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="submit_clear", description="Submit a fast solo dungeon clear.")
    @app_commands.describe(floor="The dungeon floor (default is F7)")
    async def submit_clear_cmd(self, interaction: discord.Interaction, floor: str = "F7"):
        floor = floor.upper()
        await interaction.response.send_modal(SubmitModal(self.bot, floor))

    @app_commands.command(name="solo_clears", description="View the solo clears leaderboard.")
    @app_commands.describe(floor="The dungeon floor (default is F7)")
    async def solo_leaderboard_cmd(self, interaction: discord.Interaction, floor: str = "F7"):
        floor = floor.upper()
        ign = None
        try:
            ign = self.bot.link_manager.get_link(interaction.user.id)
        except Exception:
            pass
        view = LeaderboardView(self.bot, floor, category="all", ign=ign)
        view.author_id = interaction.user.id
        embed = view.build_embed()
        view.update_components()
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(SoloClears(bot))
