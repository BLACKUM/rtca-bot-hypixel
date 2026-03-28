import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from core.logger import log_info, log_error
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
            embed.title = "✅ Solo Run Approved"
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
            embed.title = "❌ Solo Run Rejected"
            embed.set_footer(text=f"Rejected by {interaction.user.name}")
            await interaction.message.edit(embed=embed, view=None)
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)

class SubmitModal(Modal):
    def __init__(self, bot, floor):
        super().__init__(title=f"Submit Solo Run - {floor}")
        self.bot = bot
        self.floor = floor

        self.ign = TextInput(label="Your IGN", required=True, max_length=16)
        self.time = TextInput(label="Clear Time (MM:SS.ms)", placeholder="e.g. 4:20.50", required=True)
        self.proof = TextInput(
            label="Proof",
            style=discord.TextStyle.paragraph,
            placeholder="You can put a video URL here or your Discord nickname so we can DM you and ask for proof.",
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
        embed = discord.Embed(title="New Solo Run Submission", color=0x00ffff)
        embed.add_field(name="Player", value=f"`{ign_val}`\n<@{interaction.user.id}>", inline=True)
        embed.add_field(name="Floor", value=self.floor, inline=True)
        embed.add_field(name="Time", value=format_time(time_ms), inline=True)
        embed.add_field(name="Proof / Details", value=proof_val, inline=False)
        
        await interaction.channel.send(embed=embed, view=view)
        await interaction.followup.send(f"✅ {msg}")

class SoloClears(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="submit_run", description="Submit a fast solo dungeon run.")
    @app_commands.describe(floor="The dungeon floor (e.g., M7, F6)")
    async def submit_run_cmd(self, interaction: discord.Interaction, floor: str):
        floor = floor.upper()
        await interaction.response.send_modal(SubmitModal(self.bot, floor))

    @app_commands.command(name="solo_leaderboard", description="View the solo clears leaderboard.")
    @app_commands.describe(floor="The dungeon floor (e.g., M7)", category="View verified, unverified, or all runs.")
    @app_commands.choices(category=[
        app_commands.Choice(name="Verified", value="verified"),
        app_commands.Choice(name="Unverified", value="unverified"),
        app_commands.Choice(name="All", value="all")
    ])
    async def solo_leaderboard_cmd(self, interaction: discord.Interaction, floor: str, category: str = "verified"):
        floor = floor.upper()
        runs = self.bot.solo_manager.get_leaderboard(floor, category)

        embed = discord.Embed(title=f"Solo Leaderboard - {floor} ({category.title()})", color=0x3498db)
        if not runs:
            embed.description = "No runs found for this category."
        else:
            desc = ""
            for i, run in enumerate(runs[:10], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                ign = run.get("ign", "Unknown")
                time_str = format_time(run.get("time_ms", 0))
                ts = run.get("date_achieved", 0)
                ver_emoji = "✅" if run.get("verified") else "⏱️"
                
                desc += f"{medal} **{ign}** • `{time_str}` • {ver_emoji} <t:{ts}:R>\\n"
            
            embed.description = desc
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(SoloClears(bot))
