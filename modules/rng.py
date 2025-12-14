import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Select, View, Modal, TextInput, Button
import time
from core.config import RNG_DROPS, DROP_EMOJIS, DROP_IDS, CHEST_COSTS, GLOBAL_DROPS, OWNER_IDS
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
                
            rng_manager.set_drop_count(
                self.parent_view.target_user_id, 
                self.parent_view.current_floor, 
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

class RngFloorSelect(Select):
    def __init__(self, parent_view):
        options = [
            discord.SelectOption(label=floor, value=floor)
            for floor in RNG_DROPS.keys()
        ]
        super().__init__(placeholder="Select a Floor...", options=options, custom_id="rng_floor_select")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.invoker_id:
             await interaction.response.send_message("❌ This is not your menu.", ephemeral=True)
             return

        self.parent_view.current_floor = self.values[0]
        self.parent_view.current_item = None
        self.parent_view.update_view()
        log_info(f"RNG View ({self.parent_view.target_user_name}): Selected floor {self.parent_view.current_floor}")
        await interaction.response.edit_message(embed=await self.parent_view.get_embed(), view=self.parent_view)


class RngItemSelect(Select):
    def __init__(self, parent_view, floor):
        options = []
        
        for item in RNG_DROPS[floor]:
            opt = discord.SelectOption(label=item, value=item)
            emoji = DROP_EMOJIS.get(item)
            if emoji:
                opt.emoji = discord.PartialEmoji.from_str(emoji)
            options.append(opt)
            
        for item in GLOBAL_DROPS:
            opt = discord.SelectOption(label=item, value=item)
            emoji = DROP_EMOJIS.get(item)
            if emoji:
                opt.emoji = discord.PartialEmoji.from_str(emoji)
            options.append(opt)
            
        super().__init__(placeholder="Select a Drop...", options=options, custom_id="rng_item_select")
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
            floor_key = self.parent_view.current_floor
            if self.parent_view.current_item in GLOBAL_DROPS:
                floor_key = "Global"
            
            rng_manager.update_drop(self.parent_view.target_user_id, floor_key, self.parent_view.current_item, 1)
            log_info(f"RNG View ({self.parent_view.target_user_name}): Added {self.parent_view.current_item}")
        elif self.action == "subtract":
            floor_key = self.parent_view.current_floor
            if self.parent_view.current_item in GLOBAL_DROPS:
                floor_key = "Global"

            rng_manager.update_drop(self.parent_view.target_user_id, floor_key, self.parent_view.current_item, -1)
            log_info(f"RNG View ({self.parent_view.target_user_name}): Removed {self.parent_view.current_item}")
        elif self.action == "back":
            log_info(f"RNG View ({self.parent_view.target_user_name}): Go back")
            if self.parent_view.current_item:
                self.parent_view.current_item = None
            elif self.parent_view.current_floor:
                self.parent_view.current_floor = None
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

        self.parent_view.update_view()
        await interaction.response.edit_message(embed=await self.parent_view.get_embed(), view=self.parent_view)

class RngView(View):
    def __init__(self, target_user_id, target_user_name, invoker_id, run_counts=None, target_ign=None):
        super().__init__(timeout=300)
        self.target_user_id = str(target_user_id)
        self.target_user_name = target_user_name
        self.invoker_id = invoker_id
        self.current_floor = None
        self.current_item = None
        self.run_counts = run_counts or {}
        self.target_ign = target_ign
        self.filter_mode = "COMBINED"
        self.update_view()

    def update_view(self):
        self.clear_items()
        
        if self.current_item:
            self.add_item(RngActionButton(self, "-", discord.ButtonStyle.danger, "rng_sub", "subtract"))
            self.add_item(RngActionButton(self, "+", discord.ButtonStyle.success, "rng_add", "add"))
            self.add_item(RngActionButton(self, "Set", discord.ButtonStyle.primary, "rng_set", "set"))
            self.add_item(RngActionButton(self, "Back", discord.ButtonStyle.secondary, "rng_back", "back"))
        elif self.current_floor:
            self.add_item(RngItemSelect(self, self.current_floor))
            self.add_item(RngActionButton(self, "Back", discord.ButtonStyle.secondary, "rng_back", "back"))

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
        else:
            self.add_item(RngFloorSelect(self))
            
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
            floor_key = self.current_floor
            if self.current_item in GLOBAL_DROPS:
                floor_key = "Global"
                
            count = rng_manager.get_floor_stats(self.target_user_id, floor_key).get(self.current_item, 0)
            
            total_val, label, price, chest_cost, profit = self._calculate_item_details(self.current_item, count, prices)
            
            embed.title = label
            
            price_text = format_trunc(price) if price > 0 else "?"
            val_text = format_trunc(total_val)
            
            desc_lines = [f"**Current Count:** {count}", f"**Avg Price:** {price_text}", f"**Chest Cost:** {format_trunc(chest_cost)}", f"**Total Profit:** {val_text}"]
            
            floor_runs_data = self.run_counts.get(self.current_floor, {"normal": 0, "master": 0})
            runs = self._calculate_runs_for_filter(floor_runs_data)

            if runs > 0:
                if count > 0:
                    profit_per_run = total_val / runs
                    desc_lines.append(f"**Profit/Run:** {format_trunc(profit_per_run)}")
                desc_lines.append(f"**Total Runs:** {runs:,} ({self.filter_mode.title()})")
            
            embed.description = "\n".join(desc_lines)
            embed.set_footer(text=f"{self.current_floor} • {self.target_user_name}")
            
        elif self.current_floor:
            embed.title = f"{self.current_floor} Drops"
            stats = rng_manager.get_floor_stats(self.target_user_id, self.current_floor)
            desc = []
            floor_total_val = 0
            
            for item in RNG_DROPS[self.current_floor]:
                count = stats.get(item, 0)
                val, label, price, chest_cost, profit = self._calculate_item_details(item, count, prices)
                floor_total_val += val
                
                price_str = f"({format_trunc(profit)})" if price > 0 else ""

                if count > 0:
                     desc.append(f"**{label}:** {count} {price_str}")
                else:
                     desc.append(f"{label}: {count}")
            
            floor_runs_data = self.run_counts.get(self.current_floor, {"normal": 0, "master": 0})
            runs = self._calculate_runs_for_filter(floor_runs_data)

            log_debug(f"Floor {self.current_floor}: Runs={runs}, Profit={floor_total_val}")
            
            if floor_total_val > 0:
                desc.append(f"\n**Floor Profit:** {format_trunc(floor_total_val)}")
                if runs > 0:
                    profit_per_run = floor_total_val / runs
                    desc.append(f"**Profit/Run:** {format_trunc(profit_per_run)}")
            
            if runs > 0:
                desc.append(f"**Total Runs:** {runs:,} ({self.filter_mode.title()})")
                
            embed.description = "\n".join(desc)
            if not desc:
                embed.description = "No drops recorded yet."
            embed.set_footer(text=f"Select a drop to update • {self.target_user_name}")
 
        else:
            embed.title = f"RNG Tracker - {self.target_user_name}"
            user_stats = rng_manager.get_user_stats(self.target_user_id)
            desc = []
            
            total_drops_found = False
            grand_total = 0
            
            for floor_name in RNG_DROPS.keys():
                floor_stats = user_stats.get(floor_name, {})
                for item_name in RNG_DROPS[floor_name]:
                    count = floor_stats.get(item_name, 0)
                    if count > 0:
                        total_drops_found = True
                        val, label, price, chest_cost, profit = self._calculate_item_details(item_name, count, prices)
                        grand_total += val
                        desc.append(f"**{label}:** {count}")

            global_stats = user_stats.get("Global", {})
            has_global = False
            global_desc = []
            
            for item_name in GLOBAL_DROPS:
                count = global_stats.get(item_name, 0)
                if count > 0:
                    has_global = True
                    total_drops_found = True
                    val, label, price, chest_cost, profit = self._calculate_item_details(item_name, count, prices)
                    grand_total += val
                    global_desc.append(f"**{label}:** {count}")
            
            if has_global:
                 desc.append("\n**Global Drops**")
                 desc.extend(global_desc)

            total_runs = 0
            for floor_data in self.run_counts.values():
                total_runs += self._calculate_runs_for_filter(floor_data)
            
            if not total_drops_found:
                 desc.append("No drops recorded yet.")
            else:
                 desc.append(f"\n**Total Profile Profit:** {format_trunc(grand_total)}")
                 
                 if total_runs > 0:
                     avg_profit_per_run = grand_total / total_runs
                     desc.append(f"**Avg Profit/Run:** {format_trunc(avg_profit_per_run)}")
            
            if total_runs > 0:
                desc.append(f"**Total Runs:** {total_runs:,} ({self.filter_mode.title()})")
                 
            desc.append("\nSelect a floor to view or edit drops.")
            embed.description = "\n".join(desc)
            
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
            
        rng_manager.set_default_target(str(interaction.user.id), str(user.id))
        
        await interaction.response.send_message(f"✅ Default target for /rng set to **{user.mention}**.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Rng(bot))
