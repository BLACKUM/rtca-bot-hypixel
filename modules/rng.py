import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Select, View, Modal, TextInput, Button
import time
from core.config import RNG_DROPS, DROP_EMOJIS, DROP_IDS, CHEST_COSTS, GLOBAL_DROPS, OWNER_IDS, RNG_CATEGORIES
from core.logger import log_info, log_debug, log_error
from services.api import get_uuid, get_all_prices, get_dungeon_runs, get_prices_expiry
from services.rng_manager import rng_manager
from services.link_manager import link_manager

def format_trunc(value: float) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.0f}k"
    else:
        return f"{value:,.0f}"

class RngAmountModal(Modal):
    def __init__(self, parent_view):
        super().__init__(title="Set Drop Count")
        self.parent_view = parent_view
        
        self.amount_input = TextInput(
            label="Amount",
            placeholder="Enter new count",
            style=discord.TextStyle.short,
            min_length=1,
            max_length=5,
            required=True
        )
        self.add_item(self.amount_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount_input.value)
            if amount < 0:
                raise ValueError("Amount must be non-negative")
                
            await rng_manager.set_drop_count(
                self.parent_view.target_user_id, 
                self.parent_view.current_subcategory, 
                self.parent_view.current_item, 
                amount
            )
            
            self.parent_view.update_view()
            await interaction.response.edit_message(embed=await self.parent_view.get_embed(), view=self.parent_view)
            
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid non-negative number.", ephemeral=True)
        except Exception as e:
            log_error(f"Error in RngAmountModal: {e}")
            await interaction.response.send_message("❌ An error occurred.", ephemeral=True)

class RngCategorySelect(Select):
    def __init__(self, parent_view):
        options = [
            discord.SelectOption(label=cat, value=cat)
            for cat in RNG_CATEGORIES.keys()
        ]
        super().__init__(placeholder="Select a Category...", options=options, custom_id="rng_category_select")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.invoker_id:
             await interaction.response.send_message("❌ This is not your menu.", ephemeral=True)
             return

        self.parent_view.current_category = self.values[0]
        self.parent_view.current_subcategory = None
        self.parent_view.current_item = None
        self.parent_view.page = 0
        
        subcats = RNG_CATEGORIES.get(self.parent_view.current_category, [])
        if len(subcats) == 1:
            self.parent_view.current_subcategory = subcats[0]
            
        self.parent_view.update_view()
        await interaction.response.edit_message(embed=await self.parent_view.get_embed(), view=self.parent_view)

class RngSubCategorySelect(Select):
    def __init__(self, parent_view, category):
        options = []
        for sub in RNG_CATEGORIES.get(category, []):
             options.append(discord.SelectOption(label=sub, value=sub))
             
        super().__init__(placeholder=f"Select {category}...", options=options, custom_id="rng_sub_select")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.invoker_id:
             await interaction.response.send_message("❌ This is not your menu.", ephemeral=True)
             return

        self.parent_view.current_subcategory = self.values[0]
        self.parent_view.current_item = None
        self.parent_view.page = 0
        self.parent_view.update_view()
        log_info(f"RNG View ({self.parent_view.target_user_name}): Selected sub {self.parent_view.current_subcategory}")
        await interaction.response.edit_message(embed=await self.parent_view.get_embed(), view=self.parent_view)


class RngItemSelect(Select):
    def __init__(self, parent_view, subcategory):
        options = []
        
        all_items = []
        for item in RNG_DROPS.get(subcategory, []):
            all_items.append(item)
            
        if parent_view.current_category == "Dungeons":
             for item in GLOBAL_DROPS:
                 if item not in all_items:
                      all_items.append(item)
        
        start = parent_view.page * 25
        end = start + 25
        page_items = all_items[start:end]
        
        for item in page_items:
            opt = discord.SelectOption(label=item, value=item)
            emoji = DROP_EMOJIS.get(item)
            if emoji:
                opt.emoji = discord.PartialEmoji.from_str(emoji)
            options.append(opt)
            
        placeholder = f"Select Drop ({start+1}-{min(end, len(all_items))})..." if len(all_items) > 25 else "Select a Drop..."
        super().__init__(placeholder=placeholder, options=options, custom_id="rng_item_select")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.invoker_id:
             await interaction.response.send_message("❌ This is not your menu.", ephemeral=True)
             return
             
        self.parent_view.current_item = self.values[0]
        self.parent_view.update_view()
        log_info(f"RNG View ({self.parent_view.target_user_name}): Selected item {self.parent_view.current_item}")
        await interaction.response.edit_message(embed=await self.parent_view.get_embed(), view=self.parent_view)

class RngActionButton(discord.ui.Button):
    def __init__(self, parent_view, label, style, custom_id, action):
        super().__init__(label=label, style=style, custom_id=custom_id)
        self.parent_view = parent_view
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.invoker_id:
             await interaction.response.send_message("❌ This is not your menu.", ephemeral=True)
             return

        if self.action == "add":
            key = self.parent_view.current_subcategory
            if self.parent_view.current_item in GLOBAL_DROPS:
                key = "Global"
            
            await rng_manager.update_drop(self.parent_view.target_user_id, key, self.parent_view.current_item, 1)
            log_info(f"RNG View ({self.parent_view.target_user_name}): Added {self.parent_view.current_item}")
        elif self.action == "subtract":
            key = self.parent_view.current_subcategory
            if self.parent_view.current_item in GLOBAL_DROPS:
                key = "Global"

            await rng_manager.update_drop(self.parent_view.target_user_id, key, self.parent_view.current_item, -1)
            log_info(f"RNG View ({self.parent_view.target_user_name}): Removed {self.parent_view.current_item}")
        elif self.action == "back":
            log_info(f"RNG View ({self.parent_view.target_user_name}): Go back")
            if self.parent_view.current_item:
                self.parent_view.current_item = None
            elif self.parent_view.current_subcategory:
                subcats = RNG_CATEGORIES.get(self.parent_view.current_category, [])
                if len(subcats) == 1:
                    self.parent_view.current_subcategory = None
                    self.parent_view.current_category = None
                else:
                    self.parent_view.current_subcategory = None
            elif self.parent_view.current_category:
                self.parent_view.current_category = None
                
            self.parent_view.update_view()
            await interaction.response.edit_message(embed=await self.parent_view.get_embed(), view=self.parent_view)
            return
            
        elif self.action == "set":
             modal = RngAmountModal(self.parent_view)
             await interaction.response.send_modal(modal)
             return
             
        elif self.action == "filter_combined":
             self.parent_view.filter_mode = "COMBINED"
        elif self.action == "filter_master":
             self.parent_view.filter_mode = "MASTER"
        elif self.action == "filter_normal":
             self.parent_view.filter_mode = "NORMAL"
        elif self.action == "prev_page":
             self.parent_view.page = max(0, self.parent_view.page - 1)
        elif self.action == "next_page":
             self.parent_view.page += 1

        self.parent_view.update_view()
        await interaction.response.edit_message(embed=await self.parent_view.get_embed(), view=self.parent_view)

class RngView(View):
    def __init__(self, target_user_id, target_user_name, invoker_id, run_counts=None, target_ign=None):
        super().__init__(timeout=300)
        self.target_user_id = str(target_user_id)
        self.target_user_name = target_user_name
        self.invoker_id = invoker_id
        
        self.current_category = None
        self.current_subcategory = None
        self.current_item = None
        
        self.run_counts = run_counts or {}
        self.target_ign = target_ign
        self.filter_mode = "COMBINED"
        self.page = 0
        self.update_view()

    def update_view(self):
        self.clear_items()
        
        if self.current_item:
            self.add_item(RngActionButton(self, "-", discord.ButtonStyle.danger, "rng_sub", "subtract"))
            self.add_item(RngActionButton(self, "+", discord.ButtonStyle.success, "rng_add", "add"))
            self.add_item(RngActionButton(self, "Set", discord.ButtonStyle.primary, "rng_set", "set"))
            self.add_item(RngActionButton(self, "Back", discord.ButtonStyle.secondary, "rng_back", "back"))
            
        elif self.current_subcategory:
            self.add_item(RngItemSelect(self, self.current_subcategory))
            self.add_item(RngActionButton(self, "Back", discord.ButtonStyle.secondary, "rng_back", "back"))

            if self.current_category == "Dungeons":
                style_combined = discord.ButtonStyle.success if self.filter_mode == "COMBINED" else discord.ButtonStyle.secondary
                style_master = discord.ButtonStyle.success if self.filter_mode == "MASTER" else discord.ButtonStyle.secondary
                style_normal = discord.ButtonStyle.success if self.filter_mode == "NORMAL" else discord.ButtonStyle.secondary
                
                self.add_item(RngActionButton(self, "Combined", style_combined, "rng_filter_combined", "filter_combined"))
                self.add_item(RngActionButton(self, None, style_master, "rng_filter_master", "filter_master"))
                self.children[-1].emoji = discord.PartialEmoji.from_str("<:SkyBlock_items_master:1448690270366335087>")
                self.children[-1].label = None
    
                self.add_item(RngActionButton(self, None, style_normal, "rng_filter_normal", "filter_normal"))
                self.children[-1].emoji = discord.PartialEmoji.from_str("<:SkyBlock_items_catacombs:1448690272786448545>")
                self.children[-1].label = None
                
            all_items = RNG_DROPS.get(self.current_subcategory, []) + (GLOBAL_DROPS if self.current_category == "Dungeons" else [])
            total_items = len(all_items)
            
            if total_items > 25:
                 if self.page > 0:
                     self.add_item(RngActionButton(self, "Previous", discord.ButtonStyle.primary, "rng_prev", "prev_page"))
                 
                 if (self.page + 1) * 25 < total_items:
                     self.add_item(RngActionButton(self, "Next", discord.ButtonStyle.primary, "rng_next", "next_page"))
                
        elif self.current_category:
            self.add_item(RngSubCategorySelect(self, self.current_category))
            self.add_item(RngActionButton(self, "Back", discord.ButtonStyle.secondary, "rng_back", "back"))
            
        else:
            self.add_item(RngCategorySelect(self))

    def _calculate_item_details(self, item_name: str, count: int, prices: dict) -> tuple[float, list[str]]:
        emoji = DROP_EMOJIS.get(item_name)
        label = f"{emoji} {item_name}" if emoji else item_name
        
        item_id = DROP_IDS.get(item_name)
        price = float(prices.get(item_id, 0))
        chest_cost = CHEST_COSTS.get(item_name, 0)
        profit = max(0, price - chest_cost)
        
        val = profit * count
        
        return val, label, price, chest_cost, profit

    def _calculate_runs_for_filter(self, floor_runs_data: dict | int):
        if isinstance(floor_runs_data, int):
             floor_runs_data = {"normal": 0, "master": floor_runs_data}
             
        if self.filter_mode == "COMBINED":
            return floor_runs_data.get("normal", 0) + floor_runs_data.get("master", 0)
        elif self.filter_mode == "MASTER":
            return floor_runs_data.get("master", 0)
        elif self.filter_mode == "NORMAL":
            return floor_runs_data.get("normal", 0)
        return 0

    async def get_embed(self):
        embed = discord.Embed(color=0x00ff99)
        prices = await get_all_prices()
        
        if self.current_item:
            key = self.current_subcategory
            if self.current_item in GLOBAL_DROPS:
                key = "Global"
                
            count = rng_manager.get_floor_stats(self.target_user_id, key).get(self.current_item, 0)
            
            total_val, label, price, chest_cost, profit = self._calculate_item_details(self.current_item, count, prices)
            
            embed.title = label
            
            price_text = format_trunc(price) if price > 0 else "?"
            val_text = format_trunc(total_val)
            
            desc_lines = [f"**Current Count:** {count}", f"**Avg Price:** {price_text}", f"**Chest Cost:** {format_trunc(chest_cost)}", f"**Total Profit:** {val_text}"]
            
            if self.current_category == "Dungeons":
                 floor_map = {
                    "Floor 7 (Necron)": "F7", "Floor 6 (Sadan)": "F6", "Floor 5 (Livid)": "F5",
                    "Floor 4 (Thorn)": "F4", "Floor 3 (Professor)": "F3", "Floor 2 (Scarf)": "F2",
                    "Floor 1 (Bonzo)": "F1"
                 }
                 short_key = floor_map.get(self.current_subcategory, self.current_subcategory)
                 floor_runs_data = self.run_counts.get(short_key, {"normal": 0, "master": 0})
                 runs = self._calculate_runs_for_filter(floor_runs_data)
    
                 if runs > 0:
                     if count > 0:
                         profit_per_run = total_val / runs
                         desc_lines.append(f"**Profit/Run:** {format_trunc(profit_per_run)}")
                     desc_lines.append(f"**Total Runs:** {runs:,} ({self.filter_mode.title()})")
            
            embed.description = "\n".join(desc_lines)
            embed.set_footer(text=f"{self.current_subcategory} • {self.target_user_name}")
            
        elif self.current_subcategory:
            embed.title = f"{self.current_subcategory} Drops"
            stats = rng_manager.get_floor_stats(self.target_user_id, self.current_subcategory)
            desc = []
            sub_total_val = 0
            
            items = RNG_DROPS.get(self.current_subcategory, [])
            
            for item in items:
                count = stats.get(item, 0)
                val, label, price, chest_cost, profit = self._calculate_item_details(item, count, prices)
                sub_total_val += val
                
                price_str = f"({format_trunc(val)})" if val > 0 else ""

                if count > 0:
                     desc.append(f"**{label}:** {count} {price_str}")
                else:
                     desc.append(f"{label}: {count}")
            
            if self.current_category == "Dungeons":
                 floor_map = {
                    "Floor 7 (Necron)": "F7", "Floor 6 (Sadan)": "F6", "Floor 5 (Livid)": "F5",
                    "Floor 4 (Thorn)": "F4", "Floor 3 (Professor)": "F3", "Floor 2 (Scarf)": "F2",
                    "Floor 1 (Bonzo)": "F1"
                 }
                 short_key = floor_map.get(self.current_subcategory, self.current_subcategory)
                 floor_runs_data = self.run_counts.get(short_key, {"normal": 0, "master": 0})
                 runs = self._calculate_runs_for_filter(floor_runs_data)
                 
                 if sub_total_val > 0:
                     desc.append(f"\n**Total Profit:** {format_trunc(sub_total_val)}")
                     if runs > 0:
                         profit_per_run = sub_total_val / runs
                         desc.append(f"**Profit/Run:** {format_trunc(profit_per_run)}")
                 
                 if runs > 0:
                     desc.append(f"**Total Runs:** {runs:,} ({self.filter_mode.title()})")
            else:
                 if sub_total_val > 0:
                     desc.append(f"\n**Total Profit:** {format_trunc(sub_total_val)}")

            embed.description = "\n".join(desc)
            if not desc:
                embed.description = "No drops found."
            embed.set_footer(text=f"Select a drop to update • {self.target_user_name}")

        elif self.current_category:
             embed.title = f"{self.current_category} Overview"
             desc = []
             cat_total = 0
             
             for sub in RNG_CATEGORIES.get(self.current_category, []):
                 stats = rng_manager.get_floor_stats(self.target_user_id, sub)
                 sub_val = 0
                 sub_count = 0
                 for item in RNG_DROPS.get(sub, []):
                      c = stats.get(item, 0)
                      if c > 0:
                           v, _, _, _, _ = self._calculate_item_details(item, c, prices)
                           sub_val += v
                           sub_count += c
                 
                 cat_total += sub_val
                 if sub_val > 0:
                      desc.append(f"**{sub}:** {format_trunc(sub_val)} ({sub_count} drops)")
                 else:
                      desc.append(f"{sub}")
             
             if cat_total > 0:
                  desc.append(f"\n**Category Total:** {format_trunc(cat_total)}")
             
             embed.description = "\n".join(desc)
             embed.set_footer(text=f"Select a subcategory • {self.target_user_name}")

        else:
            embed.title = f"RNG Tracker - {self.target_user_name}"
            desc = ["**Select a Category:**\n"]
            grand_total = 0
            
            user_stats = rng_manager.get_user_stats(self.target_user_id)
            for floor_name in RNG_DROPS.keys():
                 floor_stats = user_stats.get(floor_name, {})
                 for item_name in RNG_DROPS[floor_name]:
                      count = floor_stats.get(item_name, 0)
                      if count > 0:
                           v, _, _, _, _ = self._calculate_item_details(item_name, count, prices)
                           grand_total += v

            for cat in RNG_CATEGORIES.keys():
                 cat_val = 0
                 for sub in RNG_CATEGORIES[cat]:
                      stats = user_stats.get(sub, {})
                      for item in RNG_DROPS.get(sub, []):
                           c = stats.get(item, 0)
                           if c > 0:
                                v, _, _, _, _ = self._calculate_item_details(item, c, prices)
                                cat_val += v
                 
                 if cat_val > 0:
                      desc.append(f"**{cat}**: {format_trunc(cat_val)}")
                 else:
                      desc.append(f"{cat}")

            if grand_total > 0:
                 desc.append(f"\n**Total Profile Profit:** {format_trunc(grand_total)}")
            
            expiry = get_prices_expiry()
            if expiry:
                desc.append(f"\n(Prices cached • Updates <t:{int(expiry)}:R>)")

            embed.description = "\n".join(desc)
            
            footer_text = "Manage your RNG collection"
            if self.target_ign:
                footer_text += f" • {self.target_ign}"
                
            embed.set_footer(text=footer_text)
 
        return embed

class Rng(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="rng", description="Track and manage your Skyblock RNG drops")
    async def rng(self, interaction: discord.Interaction):
        
        log_info(f"Command /rng called by {interaction.user}")
        
        target_ign = link_manager.get_link(interaction.user.id)
        default_target_id = rng_manager.get_default_target(str(interaction.user.id))
        
        if target_ign or default_target_id:
            await interaction.response.defer(thinking=True)
        
        target_user = interaction.user
        
        if default_target_id:
            try:
                fetched = await self.bot.fetch_user(int(default_target_id))
                if fetched:
                    target_user = fetched
                    target_ign = link_manager.get_link(target_user.id)
            except:
                pass
        
        run_counts = {}
        
        if target_ign:
            uuid = await get_uuid(target_ign)
            if uuid:
                run_counts = await get_dungeon_runs(uuid)
                log_debug(f"Fetched run counts for {target_ign}: {run_counts}")
        
        view = RngView(target_user.id, target_user.display_name, interaction.user.id, run_counts, target_ign)
        embed = await view.get_embed()
        
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)

    @app_commands.describe(user="Default user to manage")
    @app_commands.command(name="rngdefault", description="Set default User Account to manage (Owner Only)")
    async def rngdefault(self, interaction: discord.Interaction, user: discord.User):
        if interaction.user.id not in OWNER_IDS:
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return
            
        await rng_manager.set_default_target(str(interaction.user.id), str(user.id))
        
        await interaction.response.send_message(f"✅ Default target for /rng set to **{user.mention}**.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Rng(bot))
