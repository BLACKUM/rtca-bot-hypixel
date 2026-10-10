import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Modal, TextInput
import time
import math
from datetime import datetime, timedelta, timezone
from core.config import config
from core.game_data import CLASS_ICONS
from core.logger import log_info, log_error
from core.ui import AuthorView
from services.api import get_uuid, get_recent_runs
from services.recent_manager import get_teammates

import re

def clean_mc_formatting(text):
    if not text: return ""
    return re.sub(r'§.', '', text).strip()

class RecentClassSelect(discord.ui.Select):
    def __init__(self, view):
        self._view = view
        options = [
            discord.SelectOption(label="All Classes", value="all", emoji="♾️", default=True),
            discord.SelectOption(label="Archer", value="Archer", emoji="🏹"),
            discord.SelectOption(label="Berserk", value="Berserk", emoji="⚔️"),
            discord.SelectOption(label="Healer", value="Healer", emoji="💖"),
            discord.SelectOption(label="Mage", value="Mage", emoji="🧙‍♂️"),
            discord.SelectOption(label="Tank", value="Tank", emoji="🛡️")
        ]
        super().__init__(placeholder="Filter by Class...", min_values=1, max_values=1, options=options, row=0, custom_id="recent_class_select")

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        self._view.filter_class = val if val != "all" else None
        
        for opt in self.options:
            opt.default = (opt.value == val)
            
        self._view.apply_filters()
        await self._view.update_message(interaction)

class RecentTimeSelect(discord.ui.Select):
    def __init__(self, view):
        self._view = view
        options = [
            discord.SelectOption(label="Any Time", value="all", emoji="🕒", default=True),
            discord.SelectOption(label="Last 24 Hours", value="24h", emoji="☀️"),
            discord.SelectOption(label="Last 7 Days", value="7d", emoji="📅"),
            discord.SelectOption(label="Last 30 Days", value="30d", emoji="🗓️")
        ]
        super().__init__(placeholder="Filter by Last Seen...", min_values=1, max_values=1, options=options, row=1, custom_id="recent_time_select")

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        now = time.time()
        
        if val == "24h":
            self._view.filter_time = now - 86400
        elif val == "7d":
            self._view.filter_time = now - 604800
        elif val == "30d":
            self._view.filter_time = now - 2592000
        else:
            self._view.filter_time = None
            
        for opt in self.options:
            opt.default = (opt.value == val)
            
        self._view.apply_filters()
        await self._view.update_message(interaction)

class RecentSortSelect(discord.ui.Select):
    def __init__(self, view):
        self._view = view
        options = [
            discord.SelectOption(label="Most Runs", value="runs", emoji="🔢", default=True),
            discord.SelectOption(label="Most Recent", value="recent", emoji="🕒")
        ]
        super().__init__(placeholder="Sort Order...", min_values=1, max_values=1, options=options, row=2, custom_id="recent_sort_select")

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        self._view.filter_sort = val
        
        for opt in self.options:
            opt.default = (opt.value == val)
            
        self._view.apply_filters()
        await self._view.update_message(interaction)

class RecentSearchModal(Modal):
    def __init__(self, view):
        super().__init__(title="Search Teammates")
        self.view = view
        self.ign_input = TextInput(label="IGN", placeholder="Enter IGN (e.g. Steve)...", required=False, max_length=16)
        self.level_input = TextInput(label="Level Filter", placeholder="e.g. 50, <50, >45", required=False, max_length=10)
        self.page_input = TextInput(label="Page Number", placeholder="Enter page...", required=False, max_length=5)
        self.add_item(self.ign_input)
        self.add_item(self.level_input)
        self.add_item(self.page_input)

    async def on_submit(self, interaction: discord.Interaction):
        ign_val = self.ign_input.value
        level_val = self.level_input.value
        page_val = self.page_input.value

        if page_val:
            try:
                page_num = int(page_val)
                if 1 <= page_num <= self.view.total_pages:
                    self.view.page = page_num
                    await self.view.update_message(interaction)
                    return
                else:
                    await interaction.response.send_message(f"❌ Page must be between 1 and {self.view.total_pages}.", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message("❌ Invalid page number.", ephemeral=True)
                return

        self.view.filter_ign = ign_val if ign_val else None
        self.view.filter_level = level_val if level_val else None
        
        self.view.apply_filters()
        await self.view.update_message(interaction)

class RecentView(AuthorView):
    def __init__(self, bot, ign, data, runs_count):
        super().__init__(timeout=300)
        self.bot = bot
        self.ign = ign
        self.all_data = data
        self.filtered_data = data
        self.runs_count = runs_count
        self.page = 1
        self.per_page = 8
        
        self.filter_ign = None
        self.filter_class = None
        self.filter_time = None 
        self.filter_level = None
        self.filter_sort = "runs"
        
        self.update_total_pages()
        
        self.add_item(RecentClassSelect(self))
        self.add_item(RecentTimeSelect(self))
        self.add_item(RecentSortSelect(self))
        
        self.add_item(discord.ui.Button(emoji="⬅️", style=discord.ButtonStyle.secondary, custom_id="recent_prev", row=3))
        self.children[3].callback = self.prev_btn
        
        self.add_item(discord.ui.Button(emoji="🔍", style=discord.ButtonStyle.secondary, custom_id="recent_search", row=3))
        self.children[4].callback = self.search_btn
        
        self.add_item(discord.ui.Button(emoji="➡️", style=discord.ButtonStyle.secondary, custom_id="recent_next", row=3))
        self.children[5].callback = self.next_btn
        
        self._update_buttons()

    def update_total_pages(self):
        self.total_pages = math.ceil(len(self.filtered_data) / self.per_page) or 1
        if self.page > self.total_pages:
            self.page = 1

    def apply_filters(self):
        filtered = self.all_data
        
        if self.filter_ign:
            f_ign = self.filter_ign.lower()
            filtered = [x for x in filtered if f_ign in x[0].lower()]
            
        if self.filter_class:
            f_cls = self.filter_class.lower()
            filtered = [x for x in filtered if f_cls == x[1].get("last_class", "").lower()]
            
        if self.filter_time:
            filtered = [x for x in filtered if x[1].get("last_ts", 0) >= self.filter_time]
            
        if self.filter_level:
            try:
                fl = self.filter_level.strip()
                op = "="
                val = 0
                
                if fl.startswith(">"):
                    op = ">"
                    val = int(fl.replace(">", "").strip())
                elif fl.startswith("<"):
                    op = "<"
                    val = int(fl.replace("<", "").strip())
                else:
                    val = int(fl)
                    
                filtered_lvls = []
                for x in filtered:
                    lvl = x[1].get("last_class_level", 0)
                    match = False
                    if op == "=": match = (lvl == val)
                    elif op == ">": match = (lvl > val)
                    elif op == "<": match = (lvl < val)
                    
                    if match: filtered_lvls.append(x)
                filtered = filtered_lvls
            except ValueError:
                pass
        
        if self.filter_sort == "runs":
            filtered.sort(key=lambda x: x[1]["count"], reverse=True)
        elif self.filter_sort == "recent":
            filtered.sort(key=lambda x: x[1]["last_ts"], reverse=True)
            
        self.filtered_data = filtered
        self.page = 1
        self.update_total_pages()
        
    def _update_buttons(self):
        self.children[3].disabled = self.page <= 1
        self.children[5].disabled = self.page >= self.total_pages

    async def update_message(self, interaction):
        self._update_buttons()
        embed = self.get_embed()
        if not interaction.response.is_done():
             await interaction.response.defer()
        await interaction.edit_original_response(embed=embed, view=self)

    def get_embed(self):
        embed = discord.Embed(title=f"🤝 Recent Teammates: {self.ign}", color=0x3498db)
        
        analyzed_text = f"Analyzed **{self.runs_count}** recent runs."
        if len(self.filtered_data) != len(self.all_data):
              analyzed_text += f" (Filtered: {len(self.filtered_data)}/{len(self.all_data)})"
              
        embed.description = analyzed_text
        
        start_idx = (self.page - 1) * self.per_page
        end_idx = start_idx + self.per_page
        current_data = self.filtered_data[start_idx:end_idx]
        
        lines = []
        
        for i, (name, d) in enumerate(current_data, start_idx + 1):
             medal = ""
             if i == 1: medal = "🥇 "
             elif i == 2: medal = "🥈 "
             elif i == 3: medal = "🥉 "
             else: medal = f"**{i}.** "
             
             cls = d.get('last_class', 'Unknown')
             lvl = d.get('last_class_level', '?')
             emoji = CLASS_ICONS.get(cls.lower(), "❓")
             
             ts = int(d['last_ts'])
             
             lines.append(f"{medal}**{name}**: {d['count']} runs • {emoji} {cls} {lvl} • <t:{ts}:R>")
             
        if not lines:
            embed.description += "\nNo teammates found matching criteria."
        elif len(lines) == 0:
             embed.description += "\nNo data on this page."
        else:
            embed.add_field(name="Most Played With", value="\n".join(lines), inline=False)
            
        embed.set_footer(text=f"Page {self.page}/{self.total_pages} • Updates based on latest API data")
        return embed

    async def prev_btn(self, interaction: discord.Interaction):
        self.page -= 1
        await self.update_message(interaction)

    async def next_btn(self, interaction: discord.Interaction):
        self.page += 1
        await self.update_message(interaction)

    async def search_btn(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RecentSearchModal(self))

class Leaderboard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="recent", description="View recent teammates and run stats")
    async def recent(self, interaction: discord.Interaction, ign: str = None):
        if not ign:
            ign = self.bot.link_manager.get_link(interaction.user.id)
        
        if not ign:
            await interaction.response.send_message("❌ Please provide an IGN or link your account.", ephemeral=True)
            return

        await interaction.response.defer()
        
        uuid = await get_uuid(ign)
        if not uuid:
             await interaction.followup.send("❌ User not found.")
             return
             
        forced_profile = self.bot.daily_manager.data["users"].get(str(interaction.user.id), {}).get("forced_profile")
        runs = await get_recent_runs(uuid, profile_name=forced_profile)
        teammates = get_teammates(uuid, runs)
        
        view = RecentView(self.bot, ign, teammates, len(runs) if runs else 0)
        view.author_id = interaction.user.id
        embed = view.get_embed()

        await interaction.followup.send(embed=embed, view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(Leaderboard(bot))
