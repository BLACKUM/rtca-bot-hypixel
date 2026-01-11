import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Modal, TextInput
import time
import math
from datetime import datetime, timedelta, timezone
from core.config import OWNER_IDS
from core.logger import log_info, log_error
from services.api import get_uuid, get_dungeon_xp, get_recent_runs

class SearchModal(Modal):
    def __init__(self, view):
        super().__init__(title="Search Leaderboard")
        self.view = view
        
        self.ign_input = TextInput(
            label="IGN",
            placeholder="Enter IGN to find...",
            required=False,
            max_length=16
        )
        self.page_input = TextInput(
            label="Page Number",
            placeholder="Enter page number...",
            required=False,
            max_length=5
        )
        
        self.add_item(self.ign_input)
        self.add_item(self.page_input)

    async def on_submit(self, interaction: discord.Interaction):
        ign_val = self.ign_input.value
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

        if ign_val:
            ign_val_lower = ign_val.lower()
            
            if "runs" in self.view.mode:
                 metric = f"runs_{self.view.floor_id}"
            else:
                 metric = "xp"
                 
            period = "daily" if "daily" in self.view.mode or self.view.mode == "leaderboard" else "monthly"
            
            data = self.view.bot.daily_manager.get_leaderboard(period, metric)
            
            found_index = -1
            for i, entry in enumerate(data):
                if entry["ign"].lower() == ign_val_lower:
                    found_index = i
                    break
            
            if found_index != -1:
                self.view.page = (found_index // 10) + 1
                await self.view.update_message(interaction)
                return
            else:
                await interaction.response.send_message(f"❌ User '{ign_val}' not found in leaderboard.", ephemeral=True)
                return

        await interaction.response.send_message("❌ Please enter an IGN or Page Number.", ephemeral=True)
        
class RunFloorSelect(discord.ui.Select):
    def __init__(self, view):
        self._view = view
        options = []
        
        for i in range(7, 0, -1):
             options.append(discord.SelectOption(label=f"Master Floor {i}", value=f"master_{i}", default=(f"master_{i}" == view.floor_id)))
             
        for i in range(7, 0, -1):
             options.append(discord.SelectOption(label=f"Floor {i}", value=f"normal_{i}", default=(f"normal_{i}" == view.floor_id)))
        
        options.append(discord.SelectOption(label=f"Entrance", value=f"normal_0", default=("normal_0" == view.floor_id)))
        
        super().__init__(placeholder="Select Floor...", min_values=1, max_values=1, options=options, row=2, custom_id="floor_select")

    async def callback(self, interaction: discord.Interaction):
        self._view.floor_id = self.values[0]
        self._view.page = 1
        
        for opt in self.options:
            opt.default = (opt.value == self._view.floor_id)
            
        await self._view.update_message(interaction)

class DailyView(View):
    def __init__(self, bot, user_id, ign):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = str(user_id)
        self.ign = ign
        self.mode = "leaderboard"
        self.floor_id = "master_7"
        self.msg = None
        self.page = 1
        self.total_pages = 1

        self.add_item(discord.ui.Button(label="Today", style=discord.ButtonStyle.primary, disabled=True, row=0, custom_id="daily_today"))
        self.children[0].callback = self.today_btn
        
        self.add_item(discord.ui.Button(label="Monthly", style=discord.ButtonStyle.secondary, row=0, custom_id="daily_monthly"))
        self.children[1].callback = self.monthly_btn
        
        self.add_item(discord.ui.Button(label="Personal", style=discord.ButtonStyle.success, row=0, custom_id="daily_personal"))
        self.children[2].callback = self.personal_btn
        
        self.add_item(discord.ui.Button(label="Runs", style=discord.ButtonStyle.primary, row=0, custom_id="daily_runs"))
        self.children[3].callback = self.runs_btn
        
        self.add_item(discord.ui.Button(emoji="⬅️", style=discord.ButtonStyle.secondary, row=1, custom_id="daily_prev"))
        self.children[4].callback = self.prev_btn
        
        self.add_item(discord.ui.Button(emoji="🔍", style=discord.ButtonStyle.secondary, row=1, custom_id="daily_search"))
        self.children[5].callback = self.search_btn
        
        self.add_item(discord.ui.Button(emoji="➡️", style=discord.ButtonStyle.secondary, row=1, custom_id="daily_next"))
        self.children[6].callback = self.next_btn
        
        self.add_item(discord.ui.Button(label="📍 Show Me", style=discord.ButtonStyle.primary, row=1, custom_id="daily_showme"))
        self.children[7].callback = self.show_me_btn

    def _get_leaderboard_embed(self, type="daily"):
        metric = "runs" if "runs" in type else "xp"
        period = "daily" if "daily" in type else "monthly"
        
        if metric == "runs":
            metric = f"runs_{self.floor_id}"
            floor_name = self.floor_id.replace("_", " ").title().replace("Master ", "M").replace("Normal ", "F").replace("Normal 0", "Entrance")
            title_p = "Daily" if period == "daily" else "Monthly"
            title = f"🏃 {title_p} {floor_name} Runs"
        else:
            title_p = "Daily" if period == "daily" else "Monthly"
            title = f"🏆 {title_p} Catacombs XP Leaderboard"
        
        data = self.bot.daily_manager.get_leaderboard(period, metric)
        
        embed = discord.Embed(title=title, color=0xffd700)
        
        last_updated = self.bot.daily_manager.get_last_updated()
        next_update_ts = int(last_updated) + 7200 if last_updated else None
        last_update_ts = int(last_updated) if last_updated else None
        update_str = f"<t:{next_update_ts}:R>" if next_update_ts else "Soon"
        last_update_str = f"<t:{last_update_ts}:R>" if last_update_ts else "Never"
        
        if not data:
            embed.description = "No data recorded yet."
            embed.set_footer(text=f"Updates every 2 hours • Your IGN: {self.ign}")
            return embed

        self.total_pages = math.ceil(len(data) / 10)
        if self.page > self.total_pages: self.page = self.total_pages
        if self.page < 1: self.page = 1
        
        start_idx = (self.page - 1) * 10
        end_idx = start_idx + 10
        current_data = data[start_idx:end_idx]
            
        desc = []
        for i, entry in enumerate(current_data, start_idx + 1):
            medal = ""
            if i == 1: medal = "🥇"
            elif i == 2: medal = "🥈"
            elif i == 3: medal = "🥉"
            else: medal = f"**#{i}**"
            
            if metric.startswith("runs"):
                suffix = "Run" if entry['gained'] == 1 else "Runs"
                val_str = f"+{entry['gained']:,.0f} {suffix}"
            else:
                val_str = f"+{entry['gained']:,.0f} XP"
                
            line = f"{medal} **{entry['ign']}**: {val_str}"
            if entry['ign'] == self.ign:
                line = f"{line} < you"
            desc.append(line)
            
        
        next_daily_ts, next_monthly_ts = self.bot.daily_manager.get_reset_timestamps()

        desc.append(f"\nResets: **Daily** <t:{next_daily_ts}:R> • **Monthly** <t:{next_monthly_ts}:R>\nNext global update: {update_str} • Last update: {last_update_str}")
        
        embed.description = "\n".join(desc)
        embed.set_footer(text=f"Page {self.page}/{self.total_pages} • Updates every 2 hours • Your IGN: {self.ign}")
        return embed

    def _get_personal_embed(self):
        daily_stats = self.bot.daily_manager.get_daily_stats(self.user_id)
        monthly_stats = self.bot.daily_manager.get_monthly_stats(self.user_id)
        
        embed = discord.Embed(title=f"📊 Personal Stats: {self.ign}", color=0x00ff99)
        
        if not daily_stats and not monthly_stats:
            embed.description = "No data tracked yet. Wait for the next update or click 'Force Update'!"
            return embed
            
        cata_val = ""
        if daily_stats:
             c_g = daily_stats['cata_gained']
             c_s = daily_stats['cata_start_lvl']
             c_c = daily_stats['cata_current_lvl']
             cata_val += f"**Daily**: +{c_g:,.0f} XP (`{c_s:.2f}` ➤ `{c_c:.2f}`)\n"
        else:
             cata_val += "**Daily**: No data\n"
             
        if monthly_stats:
             m_g = monthly_stats['cata_gained']
             m_s = monthly_stats['cata_start_lvl']
             m_c = monthly_stats['cata_current_lvl']
             cata_val += f"**Monthly**: +{m_g:,.0f} XP (`{m_s:.2f}` ➤ `{m_c:.2f}`)"
        else:
             cata_val += "**Monthly**: No data"
             
        embed.add_field(name="Catacombs", value=cata_val, inline=False)
        
        class_lines = []
        classes = ["archer", "berserk", "healer", "mage", "tank"]
        
        for cls in classes:
            d_gain = daily_stats["classes"][cls]["gained"] if daily_stats and cls in daily_stats["classes"] else 0
            m_gain = monthly_stats["classes"][cls]["gained"] if monthly_stats and cls in monthly_stats["classes"] else 0
            
            if d_gain > 0 or m_gain > 0:
                line = f"**{cls.title()}**:"
                if d_gain > 0:
                    d_s = daily_stats["classes"][cls]["start_lvl"]
                    d_c = daily_stats["classes"][cls]["current_lvl"]
                    line += f"\n  Day: +{d_gain:,.0f} XP (`{d_s:.2f}` ➤ `{d_c:.2f}`)"
                if m_gain > 0:
                    m_s = monthly_stats["classes"][cls]["start_lvl"]
                    m_c = monthly_stats["classes"][cls]["current_lvl"]
                    line += f"\n  Month: +{m_gain:,.0f} XP (`{m_s:.2f}` ➤ `{m_c:.2f}`)"
                class_lines.append(line)
                
        if class_lines:
            embed.add_field(name="Class Progress", value="\n".join(class_lines), inline=False)
        else:
            embed.add_field(name="Class Progress", value="No class XP gained recently.", inline=False)

        run_lines = []
        
        def format_runs(stats, period_label):
            if not stats or "runs" not in stats: return []
            lines = []
            
            n_runs = stats["runs"].get("normal", {})
            if n_runs:
                valid_tiers = {k: v for k, v in n_runs.items() if k.isdigit()}
                items = sorted(valid_tiers.items(), key=lambda x: int(x[0]))
                
                parts = []
                for tier, count in items:
                    name = f"F{tier}" if tier != "0" else "Entrance"
                    parts.append(f"{name} (+{count})")
                
                if parts:
                    lines.append(f"**{period_label} Normal**: {', '.join(parts)}")
            
            m_runs = stats["runs"].get("master", {})
            if m_runs:
                valid_tiers = {k: v for k, v in m_runs.items() if k.isdigit()}
                items = sorted(valid_tiers.items(), key=lambda x: int(x[0]))
                
                parts = []
                for tier, count in items:
                    name = f"M{tier}"
                    parts.append(f"{name} (+{count})")
                
                if parts:
                    lines.append(f"**{period_label} Master**: {', '.join(parts)}")
                    
            return lines

        run_lines.extend(format_runs(daily_stats, "Daily"))
        run_lines.extend(format_runs(monthly_stats, "Monthly"))
        
        if run_lines:
             embed.add_field(name="Runs Gained", value="\n".join(run_lines), inline=False)

        return embed

    def _update_buttons(self):
        is_lb = self.mode in ["leaderboard", "monthly"]
        is_runs = self.mode in ["runs_daily", "runs_monthly"]
        
        self.children[0].disabled = self.mode == "leaderboard" or self.mode == "runs_daily"
        self.children[1].disabled = self.mode == "monthly" or self.mode == "runs_monthly"
        self.children[2].disabled = self.mode == "personal"
        self.children[3].disabled = is_runs
        
        self.children[4].disabled = (not is_lb and not is_runs) or self.page <= 1
        self.children[5].disabled = (not is_lb and not is_runs)
        self.children[6].disabled = (not is_lb and not is_runs) or self.page >= self.total_pages
        self.children[7].disabled = (not is_lb and not is_runs)
        
        for item in self.children:
            if isinstance(item, RunFloorSelect):
                self.remove_item(item)
        
        if is_runs:
             self.add_item(RunFloorSelect(self))

    async def update_message(self, interaction):
        if not interaction.response.is_done():
             await interaction.response.defer()
        
        if self.mode == "leaderboard":
            embed = self._get_leaderboard_embed("daily")
        elif self.mode == "monthly":
             embed = self._get_leaderboard_embed("monthly")
        elif self.mode == "runs_daily":
             embed = self._get_leaderboard_embed("runs_daily")
        elif self.mode == "runs_monthly":
             embed = self._get_leaderboard_embed("runs_monthly")
        elif self.mode == "personal":
             embed = self._get_personal_embed()
        
        self._update_buttons()
        await interaction.edit_original_response(embed=embed, view=self)

    async def today_btn(self, interaction: discord.Interaction):
        if "runs" in self.mode:
             self.mode = "runs_daily"
        else:
             self.mode = "leaderboard"
        self.page = 1
        await self.update_message(interaction)

    async def monthly_btn(self, interaction: discord.Interaction):
        if "runs" in self.mode:
             self.mode = "runs_monthly"
        else:
             self.mode = "monthly"
        self.page = 1
        await self.update_message(interaction)

    async def personal_btn(self, interaction: discord.Interaction):
        self.mode = "personal"
        await self.update_message(interaction)

    async def runs_btn(self, interaction: discord.Interaction):
        if "monthly" in self.mode:
             self.mode = "runs_monthly"
        else:
             self.mode = "runs_daily"
        self.page = 1
        await self.update_message(interaction)

    async def prev_btn(self, interaction: discord.Interaction):
        self.page -= 1
        await self.update_message(interaction)

    async def search_btn(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SearchModal(self))

    async def next_btn(self, interaction: discord.Interaction):
        self.page += 1
        await self.update_message(interaction)
        
    async def show_me_btn(self, interaction: discord.Interaction):
        metric = "runs" if "runs" in self.mode else "xp"
        if metric == "runs": metric = f"runs_{self.floor_id}"
        
        period = "daily" if "daily" in self.mode or self.mode == "leaderboard" else "monthly"
        
        data = interaction.client.daily_manager.get_leaderboard(period, metric)
        
        found_index = -1
        for i, entry in enumerate(data):
            if entry["ign"].lower() == self.ign.lower():
                found_index = i
                break
        
        if found_index != -1:
            self.page = (found_index // 10) + 1
            await self.update_message(interaction)
        else:
            await interaction.response.send_message("❌ You are not on the leaderboard yet.", ephemeral=True)

class Leaderboard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="daily", description="View daily Dungeon XP leaderboards and stats")
    async def daily(self, interaction: discord.Interaction):
        ign = self.bot.link_manager.get_link(interaction.user.id)
        if not ign:
            await interaction.response.send_message("❌ You must link your account first using `/link <ign>`.", ephemeral=True)
            return

        try:
            uuid = await get_uuid(ign)
            if uuid:
                await self.bot.daily_manager.register_user(interaction.user.id, ign, uuid)
        except Exception:
            pass

        view = DailyView(self.bot, interaction.user.id, ign)
        embed = view._get_leaderboard_embed("daily")
        
        await interaction.response.send_message(embed=embed, view=view)

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
             
        runs = await get_recent_runs(uuid)
        if not runs:
             await interaction.followup.send(f"❌ No recent runs found for **{ign}** (or API disabled).")
             return
             
        teammates = {}
        
        for run in runs:
            d_type = run.get("dungeon_type", "catacombs")
            tier = run.get("dungeon_tier", 0)
            is_master = "master" in d_type
            floor_prefix = "M" if is_master else "F"
            floor_name = f"{floor_prefix}{tier}"
            if tier == 0 and not is_master: floor_name = "Entrance"
            
            ts = run.get("completion_ts", 0) / 1000
            
            for p in run.get("participants", []):
                p_uuid = p.get("player_uuid")
                if p_uuid == uuid: continue
                
                raw_name = p.get("display_name", "Unknown")
                p_ign = discord.utils.remove_markdown(raw_name.split(":")[0]).strip()
                if "§" in p_ign:
                    p_ign = "".join([c for i, c in enumerate(p_ign) if c != "§" and (i==0 or p_ign[i-1] != "§")])
                    import re
                    p_ign = re.sub(r'§.', '', raw_name.split(":")[0]).strip()
                
                if p_ign not in teammates:
                    teammates[p_ign] = {
                        "count": 0,
                        "last_floor": floor_name,
                        "last_ts": ts
                    }
                
                teammates[p_ign]["count"] += 1
                if ts > teammates[p_ign]["last_ts"]:
                    teammates[p_ign]["last_floor"] = floor_name
                    teammates[p_ign]["last_ts"] = ts

        sorted_mates = sorted(teammates.items(), key=lambda x: x[1]["count"], reverse=True)
        
        embed = discord.Embed(title=f"🤝 Recent Teammates: {ign}", color=0x3498db)
        embed.description = f"Analyzed **{len(runs)}** recent runs."
        
        lines = []
        for i, (name, data) in enumerate(sorted_mates[:15], 1):
             medal = ""
             if i == 1: medal = "🥇 "
             elif i == 2: medal = "🥈 "
             elif i == 3: medal = "🥉 "
             else: medal = f"**{i}.** "
             
             lines.append(f"{medal}**{name}**: {data['count']} runs (Last: {data['last_floor']})")
             
        if not lines:
            embed.description += "\nNo teammates found (Solo runs?)."
        else:
            embed.add_field(name="Most Played With", value="\n".join(lines), inline=False)
            
        embed.set_footer(text=f"Updates based on latest API data")
        await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Leaderboard(bot))
