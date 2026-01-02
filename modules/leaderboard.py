import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Modal, TextInput
import time
import math
from datetime import datetime, timedelta, timezone
from core.config import OWNER_IDS
from core.logger import log_info, log_error
from services.api import get_uuid, get_dungeon_xp
from services.daily_manager import daily_manager
from services.link_manager import link_manager

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
            data = daily_manager.get_leaderboard("daily" if self.view.mode == "leaderboard" else "monthly")
            
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

class DailyView(View):
    def __init__(self, user_id, ign):
        super().__init__(timeout=300)
        self.user_id = str(user_id)
        self.ign = ign
        self.mode = "leaderboard"
        self.msg = None
        self.page = 1
        self.total_pages = 1

        self.add_item(discord.ui.Button(label="Today", style=discord.ButtonStyle.primary, disabled=True, row=0, custom_id="daily_today"))
        self.children[0].callback = self.today_btn
        
        self.add_item(discord.ui.Button(label="Monthly", style=discord.ButtonStyle.secondary, row=0, custom_id="daily_monthly"))
        self.children[1].callback = self.monthly_btn
        
        self.add_item(discord.ui.Button(label="Personal", style=discord.ButtonStyle.success, row=0, custom_id="daily_personal"))
        self.children[2].callback = self.personal_btn
        
        self.add_item(discord.ui.Button(label="Force Update", style=discord.ButtonStyle.danger, row=0, custom_id="daily_force"))
        self.children[3].callback = self.force_update_btn
        
        self.add_item(discord.ui.Button(emoji="⬅️", style=discord.ButtonStyle.secondary, row=1, custom_id="daily_prev"))
        self.children[4].callback = self.prev_btn
        
        self.add_item(discord.ui.Button(emoji="🔍", style=discord.ButtonStyle.secondary, row=1, custom_id="daily_search"))
        self.children[5].callback = self.search_btn
        
        self.add_item(discord.ui.Button(emoji="➡️", style=discord.ButtonStyle.secondary, row=1, custom_id="daily_next"))
        self.children[6].callback = self.next_btn
        
        self.add_item(discord.ui.Button(label="📍 Show Me", style=discord.ButtonStyle.primary, row=1, custom_id="daily_showme"))
        self.children[7].callback = self.show_me_btn


    def _get_leaderboard_embed(self, type="daily"):
        data = daily_manager.get_leaderboard(type)
        title = "🏆 Daily Catacombs XP Leaderboard" if type == "daily" else "🏆 Monthly Catacombs XP Leaderboard"
        
        embed = discord.Embed(title=title, color=0xffd700)
        
        last_updated = daily_manager.get_last_updated()
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
            
            line = f"{medal} **{entry['ign']}**: +{entry['gained']:,.0f} XP"
            if entry['ign'] == self.ign:
                line = f"{line} < you"
            desc.append(line)
            
        
        next_daily_ts, next_monthly_ts = daily_manager.get_reset_timestamps()

        desc.append(f"\nResets: **Daily** <t:{next_daily_ts}:R> • **Monthly** <t:{next_monthly_ts}:R>\nNext global update: {update_str} • Last update: {last_update_str}")
        
        embed.description = "\n".join(desc)
        embed.set_footer(text=f"Page {self.page}/{self.total_pages} • Updates every 2 hours • Your IGN: {self.ign}")
        return embed

    def _get_personal_embed(self):
        daily_stats = daily_manager.get_daily_stats(self.user_id)
        monthly_stats = daily_manager.get_monthly_stats(self.user_id)
        
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

        return embed

    def _update_buttons(self):
        is_lb = self.mode in ["leaderboard", "monthly"]
        
        self.children[0].disabled = self.mode == "leaderboard"
        self.children[1].disabled = self.mode == "monthly"
        self.children[2].disabled = self.mode == "personal"
        
        self.children[4].disabled = not is_lb or self.page <= 1
        self.children[5].disabled = not is_lb
        self.children[6].disabled = not is_lb or self.page >= self.total_pages
        self.children[7].disabled = not is_lb

    async def update_message(self, interaction):
        if not interaction.response.is_done():
             await interaction.response.defer()
        
        if self.mode == "leaderboard":
            embed = self._get_leaderboard_embed("daily")
        elif self.mode == "monthly":
             embed = self._get_leaderboard_embed("monthly")
        elif self.mode == "personal":
             embed = self._get_personal_embed()
        
        self._update_buttons()
        await interaction.edit_original_response(embed=embed, view=self)

    async def today_btn(self, interaction: discord.Interaction):
        self.mode = "leaderboard"
        self.page = 1
        await self.update_message(interaction)

    async def monthly_btn(self, interaction: discord.Interaction):
        self.mode = "monthly"
        self.page = 1
        await self.update_message(interaction)

    async def personal_btn(self, interaction: discord.Interaction):
        self.mode = "personal"
        await self.update_message(interaction)

    async def force_update_btn(self, interaction: discord.Interaction):
        if interaction.user.id not in OWNER_IDS:
             await interaction.response.send_message("❌ This command is restricted to bot owners.", ephemeral=True)
             return

        await interaction.response.defer(ephemeral=False)
        
        try:
            tracked_users = daily_manager.get_tracked_users()
            if not tracked_users:
                await interaction.followup.send("❌ No users to update.", ephemeral=True)
                return

            status_msg = await interaction.followup.send(f"🔄 **Force Update Started**\nQueue: {len(tracked_users)} users...")
            
            updated_count, errors, total_users = await daily_manager.force_update_all(status_msg)
            
            await status_msg.edit(content=f"✅ **Force Update Complete**\nTotal: {total_users}\nUpdated: {updated_count}\nErrors: {errors}")
            
            await self.update_message(interaction)
             
        except Exception as e:
            log_error(f"Force update failed: {e}")
            await interaction.followup.send("❌ An error occurred during global update.", ephemeral=True)

    async def prev_btn(self, interaction: discord.Interaction):
        self.page -= 1
        await self.update_message(interaction)

    async def search_btn(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SearchModal(self))

    async def next_btn(self, interaction: discord.Interaction):
        self.page += 1
        await self.update_message(interaction)
        
    async def show_me_btn(self, interaction: discord.Interaction):
        data = daily_manager.get_leaderboard("daily" if self.mode == "leaderboard" else "monthly")
        
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
        ign = link_manager.get_link(interaction.user.id)
        if not ign:
            await interaction.response.send_message("❌ You must link your account first using `/link <ign>`.", ephemeral=True)
            return

        try:
            uuid = await get_uuid(ign)
            if uuid:
                await daily_manager.register_user(interaction.user.id, ign, uuid)
        except Exception:
            pass

        view = DailyView(interaction.user.id, ign)
        embed = view._get_leaderboard_embed("daily")
        
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="adddaily", description="[OWNER] Manually add a user to the daily leaderboard")
    @app_commands.describe(user="The Discord user to link", ign="The Minecraft IGN")
    async def adddaily(self, interaction: discord.Interaction, user: discord.User, ign: str):
        if interaction.user.id not in OWNER_IDS:
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        
        uuid = await get_uuid(ign)
        
        if not uuid:
             await interaction.followup.send(f"❌ Could not find UUID for IGN: `{ign}`")
             return
             
        daily_manager.register_user(str(user.id), ign, uuid)
        await interaction.followup.send(f"✅ Manually registered {user.mention} as `{ign}` for daily tracking.")

async def setup(bot: commands.Bot):
    await bot.add_cog(Leaderboard(bot))
