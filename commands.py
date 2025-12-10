import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Select, View, Modal, TextInput
from discord import app_commands, TextStyle
import time
import math

from config import TARGET_LEVEL, FLOOR_XP_MAP, XP_PER_RUN_DEFAULT, OWNER_IDS, RNG_DROPS, DROP_EMOJIS, DROP_IDS, CHEST_COSTS
from utils.logging import log_info, log_debug, log_error
from api import get_uuid, get_profile_data, get_all_prices
from simulation import simulate_to_level_all50
from rng_manager import rng_manager

default_bonuses = {
    "ring": 0.1,
    "hecatomb": 0.02,
    "scarf_accessory": 0.06,
    "scarf_attribute": 0.2,
    "global": 1.0,
    "mayor": 1.0
}


def calculate_dungeon_xp_per_run(base_floor: float, ring: float, hecatomb: float, global_mult: float, mayor_mult: float) -> float:
    if base_floor >= 15000:
        maxcomps = 26
    elif base_floor == 4880:
        maxcomps = 51
    else:
        maxcomps = 76
    
    if ring > 0 and mayor_mult > 1:
        cataperrun = base_floor * (0.95 + ((mayor_mult - 1) + (maxcomps - 1) / 100) + ring + hecatomb + (maxcomps - 1) * (0.024 + hecatomb / 50))
    elif ring > 0:
        cataperrun = base_floor * (0.95 + ring + hecatomb + (maxcomps - 1) * (0.024 + hecatomb / 50))
    else:
        cataperrun = base_floor * (0.95 + hecatomb + (maxcomps - 1) * (0.022 + hecatomb / 50))
    
    cataperrun *= global_mult
    return math.ceil(cataperrun)


class ValueSelect(Select):
    
    def __init__(self, parent_view: 'BonusSelectView', option: str, options: list):
        self.parent_view = parent_view
        self.option = option
        super().__init__(placeholder=f"{option.replace('_', ' ').title()}...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.response.is_done():
            log_error("Interaction already responded to in ValueSelect")
            return
        
        message = interaction.message
        
        try:
            await interaction.response.defer(ephemeral=False)
        except discord.errors.NotFound:
            log_error("Interaction expired or not found in ValueSelect - cannot respond")
            return
        except Exception as e:
            log_error(f"Failed to defer interaction in ValueSelect: {e}")
            return
        
        value = float(self.values[0])
        
        self.parent_view.bonuses[self.option] = value
        
        log_debug(f"Recalculating with bonuses: {self.parent_view.bonuses}")
        
        ring = self.parent_view.bonuses.get("ring", default_bonuses["ring"])
        hecatomb = self.parent_view.bonuses.get("hecatomb", default_bonuses["hecatomb"])
        global_mult = self.parent_view.bonuses.get("global", default_bonuses["global"])
        mayor_mult = self.parent_view.bonuses.get("mayor", default_bonuses["mayor"])
        
        dungeon_xp = calculate_dungeon_xp_per_run(self.parent_view.base_floor, ring, hecatomb, global_mult, mayor_mult)
        
        self.parent_view.xp_per_run = dungeon_xp
        log_debug(f"Dungeon XP per run: {dungeon_xp:,.0f}")
        
        runs_total, results = simulate_to_level_all50(
            self.parent_view.dungeon_classes, 
            self.parent_view.base_floor, 
            self.parent_view.bonuses
        )
        
        embed = self.parent_view._create_embed(results, runs_total)
        
        self.parent_view._reset_view()
        
        target_message = self.parent_view.message if self.parent_view.message else message
        try:
            await target_message.edit(embed=embed, view=self.parent_view)
            self.parent_view.message = target_message
        except Exception as e:
            log_error(f"Failed to edit message: {e}")
            try:
                await interaction.message.edit(embed=embed, view=self.parent_view)
                self.parent_view.message = interaction.message
            except Exception as e2:
                log_error(f"Failed to edit message with interaction.message: {e2}")
        
        log_info(f"✅ Simulation recalculated: {self.parent_view.ign} → {runs_total:,} total runs")


class MainSelect(Select):
    
    def __init__(self, parent_view: 'BonusSelectView'):
        self.parent_view = parent_view
        super().__init__(
            placeholder="Select what to modify...",
            options=[
                discord.SelectOption(label="Catacombs Expert Ring", value="ring", description="Toggle ring bonus"),
                discord.SelectOption(label="Hecatomb", value="hecatomb", description="Set Hecatomb level"),
                discord.SelectOption(label="Scarf accessory", value="scarf_accessory", description="Set scarf accessory type"),
                discord.SelectOption(label="Scarf attribute", value="scarf_attribute", description="Set scarf attribute level"),
                discord.SelectOption(label="Global boost", value="global", description="Set global boost percentage"),
                discord.SelectOption(label="Mayor boost", value="mayor", description="Set mayor boost"),
            ]
        )
    
    async def callback(self, interaction: discord.Interaction):
        option = self.values[0]
        
        message = interaction.message
        
        try:
            await interaction.response.defer(ephemeral=False)
        except (discord.errors.NotFound, discord.errors.InteractionResponded) as e:
            log_error(f"Interaction error in MainSelect (defer failed): {type(e).__name__}: {e}")
            return
        except Exception as e:
            log_error(f"Unexpected error deferring in MainSelect: {e}")
            return
        
        if len(self.parent_view.children) > 1:
            self.parent_view.remove_item(self.parent_view.children[1])
        
        value_select = self.parent_view._create_value_select(option)
        if value_select:
            self.parent_view.add_item(value_select)
        
        try:
            await message.edit(view=self.parent_view)
            self.parent_view.message = message
        except Exception as e:
            log_error(f"Failed to edit message in MainSelect: {e}")


class BonusSelectView(View):
    
    def __init__(self, bot: commands.Bot, dungeon_classes: dict, base_floor: float, 
                 initial_bonuses: dict, ign: str, floor: str, xp_per_run: float):
        super().__init__(timeout=300)
        self.bot = bot
        self.dungeon_classes = dungeon_classes
        self.base_floor = base_floor
        self.bonuses = initial_bonuses.copy()
        self.ign = ign
        self.floor = floor
        self.message = None
        self.xp_per_run = xp_per_run
        
        self.main_select = MainSelect(self)
        self.add_item(self.main_select)
    
    def _create_value_select(self, option: str) -> ValueSelect:
        if option == "ring":
            current_val = self.bonuses.get("ring", default_bonuses["ring"])
            options = [
                discord.SelectOption(label="Yes", value="0.1", description="10% bonus", default=(abs(current_val - 0.1) < 0.0001)),
                discord.SelectOption(label="No", value="0", description="No bonus", default=(abs(current_val - 0.0) < 0.0001)),
            ]
        elif option == "hecatomb":
            current_val = self.bonuses.get("hecatomb", default_bonuses["hecatomb"])
            options = [
                discord.SelectOption(label="X", value="0.02", description="2% (default)", default=(abs(current_val - 0.02) < 0.0001)),
                discord.SelectOption(label="IX", value="0.0184", description="1.84%", default=(abs(current_val - 0.0184) < 0.0001)),
                discord.SelectOption(label="VIII", value="0.0168", description="1.68%", default=(abs(current_val - 0.0168) < 0.0001)),
                discord.SelectOption(label="VII", value="0.0152", description="1.52%", default=(abs(current_val - 0.0152) < 0.0001)),
                discord.SelectOption(label="VI", value="0.0136", description="1.36%", default=(abs(current_val - 0.0136) < 0.0001)),
                discord.SelectOption(label="V", value="0.012", description="1.2%", default=(abs(current_val - 0.012) < 0.0001)),
                discord.SelectOption(label="IV", value="0.0104", description="1.04%", default=(abs(current_val - 0.0104) < 0.0001)),
                discord.SelectOption(label="III", value="0.0088", description="0.88%", default=(abs(current_val - 0.0088) < 0.0001)),
                discord.SelectOption(label="II", value="0.0072", description="0.72%", default=(abs(current_val - 0.0072) < 0.0001)),
                discord.SelectOption(label="I", value="0.0056", description="0.56%", default=(abs(current_val - 0.0056) < 0.0001)),
                discord.SelectOption(label="0", value="0", description="No Hecatomb", default=(abs(current_val - 0.0) < 0.0001)),
            ]
        elif option == "scarf_accessory":
            current_val = self.bonuses.get("scarf_accessory", default_bonuses["scarf_accessory"])
            options = [
                discord.SelectOption(label="Grimoire (6%)", value="0.06", description="6% bonus", default=(abs(current_val - 0.06) < 0.0001)),
                discord.SelectOption(label="Thesis (4%)", value="0.04", description="4% bonus", default=(abs(current_val - 0.04) < 0.0001)),
                discord.SelectOption(label="Studies (2%)", value="0.02", description="2% bonus", default=(abs(current_val - 0.02) < 0.0001)),
                discord.SelectOption(label="None", value="0.0", description="No scarf accessory", default=(abs(current_val - 0.0) < 0.0001)),
            ]
        elif option == "scarf_attribute":
            current_val = self.bonuses.get("scarf_attribute", default_bonuses["scarf_attribute"])
            options = [
                discord.SelectOption(label="0 (0%)", value="0", description="No attribute", default=(abs(current_val - 0.0) < 0.0001)),
                discord.SelectOption(label="I (2%)", value="0.02", description="2% bonus", default=(abs(current_val - 0.02) < 0.0001)),
                discord.SelectOption(label="II (4%)", value="0.04", description="4% bonus", default=(abs(current_val - 0.04) < 0.0001)),
                discord.SelectOption(label="III (6%)", value="0.06", description="6% bonus", default=(abs(current_val - 0.06) < 0.0001)),
                discord.SelectOption(label="IV (8%)", value="0.08", description="8% bonus", default=(abs(current_val - 0.08) < 0.0001)),
                discord.SelectOption(label="V (10%)", value="0.1", description="10% bonus", default=(abs(current_val - 0.1) < 0.0001)),
                discord.SelectOption(label="VI (12%)", value="0.12", description="12% bonus", default=(abs(current_val - 0.12) < 0.0001)),
                discord.SelectOption(label="VII (14%)", value="0.14", description="14% bonus", default=(abs(current_val - 0.14) < 0.0001)),
                discord.SelectOption(label="VIII (16%)", value="0.16", description="16% bonus", default=(abs(current_val - 0.16) < 0.0001)),
                discord.SelectOption(label="IX (18%)", value="0.18", description="18% bonus", default=(abs(current_val - 0.18) < 0.0001)),
                discord.SelectOption(label="X (20%)", value="0.2", description="20% bonus", default=(abs(current_val - 0.2) < 0.0001)),
            ]
        elif option == "global":
            current_val = self.bonuses.get("global", default_bonuses["global"])
            options = [
                discord.SelectOption(label="0%", value="1", description="No boost", default=(abs(current_val - 1.0) < 0.0001)),
                discord.SelectOption(label="5%", value="1.05", description="5% boost", default=(abs(current_val - 1.05) < 0.0001)),
                discord.SelectOption(label="10%", value="1.1", description="10% boost", default=(abs(current_val - 1.1) < 0.0001)),
                discord.SelectOption(label="15%", value="1.15", description="15% boost", default=(abs(current_val - 1.15) < 0.0001)),
                discord.SelectOption(label="20%", value="1.2", description="20% boost", default=(abs(current_val - 1.2) < 0.0001)),
                discord.SelectOption(label="30%", value="1.3", description="30% boost", default=(abs(current_val - 1.3) < 0.0001)),
            ]
        elif option == "mayor":
            current_val = self.bonuses.get("mayor", default_bonuses["mayor"])
            options = [
                discord.SelectOption(label="0%", value="1", description="No boost", default=(abs(current_val - 1.0) < 0.0001)),
                discord.SelectOption(label="Derpy (50%)", value="1.5", description="50% boost", default=(abs(current_val - 1.5) < 0.0001)),
                discord.SelectOption(label="Aura (55%, probably bugged. select Derpy)", value="1.55", description="55% boost", default=(abs(current_val - 1.55) < 0.0001)),
            ]
        else:
            return None
        
        return ValueSelect(self, option, options)
    
    def _reset_view(self):
        self.clear_items()
        self.main_select = MainSelect(self)
        self.add_item(self.main_select)
    
    def _create_embed(self, results: dict, runs_total: int) -> discord.Embed:
        xp_description = f"Dungeon XP per run: {self.xp_per_run:,.0f}"
        
        embed = discord.Embed(
            title=f"Simulation — reach Level {TARGET_LEVEL} for all classes ({self.ign})",
            description=f"Floor: {self.floor} ({self.base_floor:,} base XP)\n{xp_description}",
            color=0x00ff99
        )
        
        for cls in ["archer", "berserk", "healer", "mage", "tank"]:
            info = results.get(cls, {"current_level": 0.0, "remaining_xp": 0, "runs_done": 0})
            lvl = info["current_level"]
            rem = info["remaining_xp"]
            runs_for_class = info["runs_done"]
            rem_text = "\n(✅ reached)" if runs_for_class == 0 and lvl >= TARGET_LEVEL else "\n(❌ not yet)"
            embed.add_field(
                name=cls.title(),
                value=f"Expected Level {lvl:.2f} {rem_text}\n({runs_for_class} runs)",
                inline=True
            )
        
        embed.set_footer(text=f"Total simulated runs: {runs_total:,} \nDM @BLACKUM if you want to report an issue.")
        return embed


class DefaultValueSelect(Select):
    
    def __init__(self, parent_view: 'DefaultSelectView', option: str, options: list):
        self.parent_view = parent_view
        self.option = option
        super().__init__(placeholder=f"{option.replace('_', ' ').title()}...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id not in OWNER_IDS:
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return
        
        if interaction.response.is_done():
            log_error("Interaction already responded to in DefaultValueSelect")
            return
        
        message = interaction.message
        
        try:
            await interaction.response.defer(ephemeral=False)
        except discord.errors.NotFound:
            log_error("Interaction expired or not found in DefaultValueSelect - cannot respond")
            return
        except Exception as e:
            log_error(f"Failed to defer interaction in DefaultValueSelect: {e}")
            return
        
        value = float(self.values[0])
        
        old_value = default_bonuses[self.option]
        default_bonuses[self.option] = value
        
        log_info(f"Default {self.option} changed from {old_value} to {value} by {interaction.user}")
        
        embed = self.parent_view._create_embed()
        
        self.parent_view._reset_view()
        
        target_message = self.parent_view.message if self.parent_view.message else message
        try:
            await target_message.edit(embed=embed, view=self.parent_view)
            self.parent_view.message = target_message
        except Exception as e:
            log_error(f"Failed to edit message: {e}")
            try:
                await interaction.message.edit(embed=embed, view=self.parent_view)
                self.parent_view.message = interaction.message
            except Exception as e2:
                log_error(f"Failed to edit message with interaction.message: {e2}")


class DefaultMainSelect(Select):
    
    def __init__(self, parent_view: 'DefaultSelectView'):
        self.parent_view = parent_view
        super().__init__(
            placeholder="Select what to modify...",
            options=[
                discord.SelectOption(label="Catacombs Expert Ring", value="ring", description="Toggle ring bonus"),
                discord.SelectOption(label="Hecatomb", value="hecatomb", description="Set Hecatomb level"),
                discord.SelectOption(label="Scarf accessory", value="scarf_accessory", description="Set scarf accessory type"),
                discord.SelectOption(label="Scarf attribute", value="scarf_attribute", description="Set scarf attribute level"),
                discord.SelectOption(label="Global boost", value="global", description="Set global boost percentage"),
                discord.SelectOption(label="Mayor boost", value="mayor", description="Set mayor boost"),
            ]
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id not in OWNER_IDS:
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return
        
        option = self.values[0]
        
        message = interaction.message
        
        try:
            await interaction.response.defer(ephemeral=False)
        except (discord.errors.NotFound, discord.errors.InteractionResponded) as e:
            log_error(f"Interaction error in DefaultMainSelect (defer failed): {type(e).__name__}: {e}")
            return
        except Exception as e:
            log_error(f"Unexpected error deferring in DefaultMainSelect: {e}")
            return
        
        if len(self.parent_view.children) > 1:
            self.parent_view.remove_item(self.parent_view.children[1])
        
        value_select = self.parent_view._create_value_select(option)
        if value_select:
            self.parent_view.add_item(value_select)
        
        try:
            await message.edit(view=self.parent_view)
            self.parent_view.message = message
        except Exception as e:
            log_error(f"Failed to edit message in DefaultMainSelect: {e}")


class DefaultSelectView(View):
    
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=300)
        self.bot = bot
        self.message = None
        
        self.main_select = DefaultMainSelect(self)
        self.add_item(self.main_select)
    
    def _create_value_select(self, option: str) -> DefaultValueSelect:
        if option == "ring":
            current_val = default_bonuses.get("ring", 0.1)
            options = [
                discord.SelectOption(label="Yes", value="0.1", description="10% bonus", default=(abs(current_val - 0.1) < 0.0001)),
                discord.SelectOption(label="No", value="0", description="No bonus", default=(abs(current_val - 0.0) < 0.0001)),
            ]
        elif option == "hecatomb":
            current_val = default_bonuses.get("hecatomb", 0.02)
            options = [
                discord.SelectOption(label="X", value="0.02", description="2% (default)", default=(abs(current_val - 0.02) < 0.0001)),
                discord.SelectOption(label="IX", value="0.0184", description="1.84%", default=(abs(current_val - 0.0184) < 0.0001)),
                discord.SelectOption(label="VIII", value="0.0168", description="1.68%", default=(abs(current_val - 0.0168) < 0.0001)),
                discord.SelectOption(label="VII", value="0.0152", description="1.52%", default=(abs(current_val - 0.0152) < 0.0001)),
                discord.SelectOption(label="VI", value="0.0136", description="1.36%", default=(abs(current_val - 0.0136) < 0.0001)),
                discord.SelectOption(label="V", value="0.012", description="1.2%", default=(abs(current_val - 0.012) < 0.0001)),
                discord.SelectOption(label="IV", value="0.0104", description="1.04%", default=(abs(current_val - 0.0104) < 0.0001)),
                discord.SelectOption(label="III", value="0.0088", description="0.88%", default=(abs(current_val - 0.0088) < 0.0001)),
                discord.SelectOption(label="II", value="0.0072", description="0.72%", default=(abs(current_val - 0.0072) < 0.0001)),
                discord.SelectOption(label="I", value="0.0056", description="0.56%", default=(abs(current_val - 0.0056) < 0.0001)),
                discord.SelectOption(label="0", value="0", description="No Hecatomb", default=(abs(current_val - 0.0) < 0.0001)),
            ]
        elif option == "scarf_accessory":
            current_val = default_bonuses.get("scarf_accessory", 0.06)
            options = [
                discord.SelectOption(label="Grimoire (6%)", value="0.06", description="6% bonus", default=(abs(current_val - 0.06) < 0.0001)),
                discord.SelectOption(label="Thesis (4%)", value="0.04", description="4% bonus", default=(abs(current_val - 0.04) < 0.0001)),
                discord.SelectOption(label="Studies (2%)", value="0.02", description="2% bonus", default=(abs(current_val - 0.02) < 0.0001)),
                discord.SelectOption(label="None", value="0.0", description="No scarf accessory", default=(abs(current_val - 0.0) < 0.0001)),
            ]
        elif option == "scarf_attribute":
            current_val = default_bonuses.get("scarf_attribute", 0.0)
            options = [
                discord.SelectOption(label="0 (0%)", value="0", description="No attribute", default=(abs(current_val - 0.0) < 0.0001)),
                discord.SelectOption(label="I (2%)", value="0.02", description="2% bonus", default=(abs(current_val - 0.02) < 0.0001)),
                discord.SelectOption(label="II (4%)", value="0.04", description="4% bonus", default=(abs(current_val - 0.04) < 0.0001)),
                discord.SelectOption(label="III (6%)", value="0.06", description="6% bonus", default=(abs(current_val - 0.06) < 0.0001)),
                discord.SelectOption(label="IV (8%)", value="0.08", description="8% bonus", default=(abs(current_val - 0.08) < 0.0001)),
                discord.SelectOption(label="V (10%)", value="0.1", description="10% bonus", default=(abs(current_val - 0.1) < 0.0001)),
                discord.SelectOption(label="VI (12%)", value="0.12", description="12% bonus", default=(abs(current_val - 0.12) < 0.0001)),
                discord.SelectOption(label="VII (14%)", value="0.14", description="14% bonus", default=(abs(current_val - 0.14) < 0.0001)),
                discord.SelectOption(label="VIII (16%)", value="0.16", description="16% bonus", default=(abs(current_val - 0.16) < 0.0001)),
                discord.SelectOption(label="IX (18%)", value="0.18", description="18% bonus", default=(abs(current_val - 0.18) < 0.0001)),
                discord.SelectOption(label="X (20%)", value="0.2", description="20% bonus", default=(abs(current_val - 0.2) < 0.0001)),
            ]
        elif option == "global":
            current_val = default_bonuses.get("global", 1.0)
            options = [
                discord.SelectOption(label="0%", value="1", description="No boost", default=(abs(current_val - 1.0) < 0.0001)),
                discord.SelectOption(label="5%", value="1.05", description="5% boost", default=(abs(current_val - 1.05) < 0.0001)),
                discord.SelectOption(label="10%", value="1.1", description="10% boost", default=(abs(current_val - 1.1) < 0.0001)),
                discord.SelectOption(label="15%", value="1.15", description="15% boost", default=(abs(current_val - 1.15) < 0.0001)),
                discord.SelectOption(label="20%", value="1.2", description="20% boost", default=(abs(current_val - 1.2) < 0.0001)),
                discord.SelectOption(label="30%", value="1.3", description="30% boost", default=(abs(current_val - 1.3) < 0.0001)),
            ]
        elif option == "mayor":
            current_val = default_bonuses.get("mayor", 1.0)
            options = [
                discord.SelectOption(label="0%", value="1", description="No boost", default=(abs(current_val - 1.0) < 0.0001)),
                discord.SelectOption(label="Derpy (50%)", value="1.5", description="50% boost", default=(abs(current_val - 1.5) < 0.0001)),
                discord.SelectOption(label="Aura (55%, probably bugged. select Derpy)", value="1.55", description="55% boost", default=(abs(current_val - 1.55) < 0.0001)),
            ]
        else:
            return None
        
        return DefaultValueSelect(self, option, options)
    
    def _reset_view(self):
        self.clear_items()
        self.main_select = DefaultMainSelect(self)
        self.add_item(self.main_select)
    
    def _create_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="Default Bonus Values",
            description="Current default values used for new simulations:",
            color=0x00ff99
        )
        
        embed.add_field(
            name="Catacombs Expert Ring",
            value=f"`{default_bonuses['ring']}` ({'Yes' if default_bonuses['ring'] > 0 else 'No'})",
            inline=True
        )
        embed.add_field(
            name="Hecatomb",
            value=f"`{default_bonuses['hecatomb']}`",
            inline=True
        )
        embed.add_field(
            name="Scarf Accessory",
            value=f"`{default_bonuses['scarf_accessory']}`",
            inline=True
        )
        embed.add_field(
            name="Scarf Attribute",
            value=f"`{default_bonuses['scarf_attribute']}`",
            inline=True
        )
        embed.add_field(
            name="Global Boost",
            value=f"`{default_bonuses['global']}` ({((default_bonuses['global'] - 1) * 100):.0f}%)",
            inline=True
        )
        embed.add_field(
            name="Mayor Boost",
            value=f"`{default_bonuses['mayor']}` ({((default_bonuses['mayor'] - 1) * 100):.0f}%)",
            inline=True
        )
        
        embed.set_footer(text="Select an option above to change its default value")
        return embed



class RngAmountModal(Modal):
    def __init__(self, parent_view):
        super().__init__(title="Set Drop Count")
        self.parent_view = parent_view
        
        self.amount_input = TextInput(
            label="Amount",
            placeholder="Enter new count",
            style=TextStyle.short,
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
            rng_manager.update_drop(self.parent_view.target_user_id, self.parent_view.current_floor, self.parent_view.current_item, 1)
            log_info(f"RNG View ({self.parent_view.target_user_name}): Added {self.parent_view.current_item}")
        elif self.action == "subtract":
            rng_manager.update_drop(self.parent_view.target_user_id, self.parent_view.current_floor, self.parent_view.current_item, -1)
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

        self.parent_view.update_view()
        await interaction.response.edit_message(embed=await self.parent_view.get_embed(), view=self.parent_view)

def format_trunc(value: float) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.0f}k"
    else:
        return f"{value:,.0f}"

class RngView(View):
    def __init__(self, target_user_id, target_user_name, invoker_id):
        super().__init__(timeout=300)
        self.target_user_id = str(target_user_id)
        self.target_user_name = target_user_name
        self.invoker_id = invoker_id
        self.current_floor = None
        self.current_item = None
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
        else:
            self.add_item(RngFloorSelect(self))

    async def get_embed(self):
        embed = discord.Embed(color=0x00ff99)
        prices = await get_all_prices()
        
        if self.current_item:
            emoji = DROP_EMOJIS.get(self.current_item)
            label = f"{emoji} {self.current_item}" if emoji else self.current_item
            embed.title = label
            count = rng_manager.get_floor_stats(self.target_user_id, self.current_floor).get(self.current_item, 0)
            
            item_id = DROP_IDS.get(self.current_item)
            price = float(prices.get(item_id, 0))
            chest_cost = CHEST_COSTS.get(self.current_item, 0)
            profit = max(0, price - chest_cost)
            
            total_val = profit * count
            
            price_text = format_trunc(price) if price > 0 else "?"
            val_text = format_trunc(total_val)
            
            embed.description = f"**Current Count:** {count}\n**Avg Price:** {price_text}\n**Chest Cost:** {format_trunc(chest_cost)}\n**Total Profit:** {val_text}"
            embed.set_footer(text=f"{self.current_floor} • {self.target_user_name}")
            
        elif self.current_floor:
            embed.title = f"{self.current_floor} Drops"
            stats = rng_manager.get_floor_stats(self.target_user_id, self.current_floor)
            desc = []
            floor_total_val = 0
            
            for item in RNG_DROPS[self.current_floor]:
                count = stats.get(item, 0)
                emoji = DROP_EMOJIS.get(item)
                label = f"{emoji} {item}" if emoji else item
                
                item_id = DROP_IDS.get(item)
                price = float(prices.get(item_id, 0))
                chest_cost = CHEST_COSTS.get(item, 0)
                profit = max(0, price - chest_cost)
                
                val = profit * count
                floor_total_val += val
                
                price_str = f"({format_trunc(profit)})" if price > 0 else ""

                if count > 0:
                     desc.append(f"**{label}:** {count} {price_str}")
                else:
                     desc.append(f"{label}: {count}")
            
            if floor_total_val > 0:
                desc.append(f"\n**Floor Profit:** {format_trunc(floor_total_val)}")
                
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
                        emoji = DROP_EMOJIS.get(item_name)
                        label = f"{emoji} {item_name}" if emoji else item_name
                        
                        item_id = DROP_IDS.get(item_name)
                        price = float(prices.get(item_id, 0))
                        chest_cost = CHEST_COSTS.get(item_name, 0)
                        profit = max(0, price - chest_cost)
                        
                        val = profit * count
                        grand_total += val
                        
                        desc.append(f"**{label}:** {count}")
                        total_drops_found = True

            if not total_drops_found:
                 desc.append("No drops recorded yet.")
            else:
                 desc.append(f"\n**Total Profile Profit:** {format_trunc(grand_total)}")
                 
            desc.append("\nSelect a floor to view or edit drops.")
            embed.description = "\n".join(desc)
            embed.set_footer(text="Manage your RNG collection")
 
        return embed


def setup_commands(bot: commands.Bot):
    
    @bot.event
    async def on_ready():
        log_info(f"✅ Logged in as {bot.user}")
        try:
            synced = await bot.tree.sync()
            log_info(f"🔁 Synced {len(synced)} global commands")
        except Exception as e:
            log_error(f"❌ Sync failed: {e}")

    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(ign="Minecraft IGN", floor="Dungeon floor (M7, M6, etc.)")
    @bot.tree.command(name="rtca", description="Simulate runs until all dungeon classes reach level 50")
    async def rtca(interaction: discord.Interaction, ign: str, floor: str = "M7"):
        start_time = time.perf_counter()
        await interaction.response.defer(thinking=True)
        log_debug(f"Defer sent after {(time.perf_counter() - start_time):.2f}s")

        log_info(f"Command /rtca called by {interaction.user} → {ign}")

        base_floor = FLOOR_XP_MAP.get(floor.upper(), XP_PER_RUN_DEFAULT)

        uuid = await get_uuid(ign)
        if not uuid:
            await interaction.followup.send("❌ Could not find that username.")
            return

        profile_data = await get_profile_data(uuid)
        if not profile_data:
            await interaction.followup.send("❌ Failed to fetch SkyBlock data.")
            return

        profiles = profile_data.get("profiles")
        if not profiles:
            await interaction.followup.send("❌ No SkyBlock profile found.")
            return

        best_profile = next((p for p in profiles if p.get("selected")), profiles[0])
        member = best_profile["members"][uuid]
        dungeons = member.get("dungeons", {})
        player_classes = dungeons.get("player_classes", {})

        dungeon_classes = {
            cls: data["experience"]
            for cls, data in player_classes.items()
            if cls in ["archer", "berserk", "healer", "mage", "tank"]
        }

        if not dungeon_classes:
            await interaction.followup.send("❌ This player has no dungeon data.")
            return

        player_data = member.get("player_data", {})
        perks = player_data.get("perks", {})
        class_boosts = {
            "archer": perks.get("toxophilite", 0) * 0.02,
            "berserk": perks.get("unbridled_rage", 0) * 0.02,
            "healer": perks.get("heart_of_gold", 0) * 0.02,
            "mage": perks.get("cold_efficiency", 0) * 0.02,
            "tank": perks.get("diamond_in_the_rough", 0) * 0.02,
        }

        ring_bonus = default_bonuses["ring"]
        hecatomb_value = default_bonuses["hecatomb"]
        scarf_accessory_value = default_bonuses["scarf_accessory"]
        scarf_attribute_value = default_bonuses["scarf_attribute"]

        global_mult = default_bonuses["global"]
        mayor_mult = default_bonuses["mayor"]

        bonuses = {
            "ring": ring_bonus,
            "hecatomb": hecatomb_value,
            "scarf_accessory": scarf_accessory_value,
            "scarf_attribute": scarf_attribute_value,
            "global": global_mult,
            "mayor": mayor_mult,
            "class_boosts": class_boosts
        }

        log_debug(f"Detected bonuses: {bonuses}")

        ring = bonuses.get("ring", default_bonuses["ring"])
        hecatomb = bonuses.get("hecatomb", default_bonuses["hecatomb"])
        global_mult = bonuses.get("global", default_bonuses["global"])
        mayor_mult = bonuses.get("mayor", default_bonuses["mayor"])
        
        dungeon_xp = calculate_dungeon_xp_per_run(base_floor, ring, hecatomb, global_mult, mayor_mult)
        
        log_debug(f"Dungeon XP per run: {dungeon_xp:,.0f}")

        runs_total, results = simulate_to_level_all50(dungeon_classes, base_floor, bonuses)

        view = BonusSelectView(bot, dungeon_classes, base_floor, bonuses, ign, floor, dungeon_xp)
        
        embed = view._create_embed(results, runs_total)
        
        message = await interaction.followup.send(embed=embed, view=view)
        view.message = message

        log_info(f"✅ Simulation finished: {ign} → {runs_total:,} total runs")

    @bot.tree.command(name="setdefault", description="Change default bonus values (owner only)")
    async def setdefault(interaction: discord.Interaction):
        view = DefaultSelectView(bot)
        embed = view._create_embed()
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
        view.message = await interaction.original_response()

    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @bot.tree.command(name="rng", description="Track and manage your Skyblock RNG drops")
    async def rng(interaction: discord.Interaction):
        
        log_info(f"Command /rng called by {interaction.user}")
        
        target_user = interaction.user
        
        default_target_id = rng_manager.get_default_target(str(interaction.user.id))
        if default_target_id:
            try:
                fetched = await bot.fetch_user(int(default_target_id))
                if fetched:
                        target_user = fetched
            except:
                pass
        
        view = RngView(target_user.id, target_user.display_name, interaction.user.id)
        embed = await view.get_embed()
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.describe(user="Default user to manage")
    @bot.tree.command(name="rngdefault", description="Set default User Account to manage (Owner Only)")
    async def rngdefault(interaction: discord.Interaction, user: discord.User):
        if interaction.user.id not in OWNER_IDS:
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return
            
        rng_manager.set_default_target(str(interaction.user.id), str(user.id))
        
        await interaction.response.send_message(f"✅ Default target for /rng set to **{user.mention}**.", ephemeral=True)
