import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
from core.logger import log_info, log_error

try:
    from core.secrets import ADMIN_CHANNEL_ID
except ImportError:
    ADMIN_CHANNEL_ID = None
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

class VerifyView(View):
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
            placeholder="You can put a video URL here or screenshot. Keep in mind that for high ranks we may ask for video proof.",
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
        if ADMIN_CHANNEL_ID:
            admin_ch = interaction.client.get_channel(ADMIN_CHANNEL_ID)
            if admin_ch:
                target_channel = admin_ch

        await target_channel.send(embed=embed, view=view)
        await interaction.followup.send(f"✅ {msg}")

class RunSelect(Select):
    def __init__(self, view, runs):
        self._lb_view = view
        options = []
        for i, run in enumerate(runs[:25], 1):
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

class LeaderboardView(View):
    def __init__(self, bot, floor, category="all"):
        super().__init__(timeout=None)
        self.bot = bot
        self.floor = floor
        self.category = category
        self.inspect_uuid = None
        self.update_components()

    def update_components(self):
        self.clear_items()

        if self.inspect_uuid:
            btn = discord.ui.Button(label="⬅ Back to Leaderboard", style=discord.ButtonStyle.secondary, custom_id="lb_back")
            btn.callback = self.btn_back
            self.add_item(btn)
        else:
            cat_ver = discord.ui.Button(label="Verified", style=discord.ButtonStyle.primary if self.category == "verified" else discord.ButtonStyle.secondary, custom_id="lb_cat_verified")
            cat_unver = discord.ui.Button(label="Unverified", style=discord.ButtonStyle.primary if self.category == "unverified" else discord.ButtonStyle.secondary, custom_id="lb_cat_unverified")
            cat_all = discord.ui.Button(label="All", style=discord.ButtonStyle.primary if self.category == "all" else discord.ButtonStyle.secondary, custom_id="lb_cat_all")
            
            cat_ver.callback = self.btn_verified
            cat_unver.callback = self.btn_unverified
            cat_all.callback = self.btn_all
            
            self.add_item(cat_ver)
            self.add_item(cat_unver)
            self.add_item(cat_all)

            runs = self.bot.solo_manager.get_leaderboard(self.floor, self.category)
            if runs:
                self.add_item(RunSelect(self, runs[:10]))

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
            embed.description = "No clears found for this category."
        else:
            desc = ""
            for i, run in enumerate(runs[:10], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                ign = run.get("ign", "Unknown")
                time_str = format_time(run.get("time_ms", 0))
                ts = run.get("date_achieved", 0)
                ver_emoji = "✅" if run.get("verified") else "⏱️"
                desc += f"{medal} **{ign}** • `{time_str}` • {ver_emoji} <t:{ts}:R>\n"
            embed.description = desc
        return embed

    async def update_message(self, interaction: discord.Interaction):
        self.update_components()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def btn_back(self, interaction: discord.Interaction):
        self.inspect_uuid = None
        await self.update_message(interaction)

    async def btn_verified(self, interaction: discord.Interaction):
        self.category = "verified"
        self.inspect_uuid = None
        await self.update_message(interaction)

    async def btn_unverified(self, interaction: discord.Interaction):
        self.category = "unverified"
        self.inspect_uuid = None
        await self.update_message(interaction)

    async def btn_all(self, interaction: discord.Interaction):
        self.category = "all"
        self.inspect_uuid = None
        await self.update_message(interaction)

class SoloClears(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="submit_clear", description="Submit a fast solo dungeon clear.")
    @app_commands.describe(floor="The dungeon floor (default is F7)")
    async def submit_clear_cmd(self, interaction: discord.Interaction, floor: str = "F7"):
        floor = floor.upper()
        await interaction.response.send_modal(SubmitModal(self.bot, floor))

    @app_commands.command(name="solo_leaderboard", description="View the solo clears leaderboard.")
    @app_commands.describe(floor="The dungeon floor (default is F7)")
    async def solo_leaderboard_cmd(self, interaction: discord.Interaction, floor: str = "F7"):
        floor = floor.upper()
        view = LeaderboardView(self.bot, floor, category="all")
        embed = view.build_embed()
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(SoloClears(bot))
