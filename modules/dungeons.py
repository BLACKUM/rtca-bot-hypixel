import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Select, View
import time
import math
from core.config import TARGET_LEVEL, FLOOR_XP_MAP, XP_PER_RUN_DEFAULT, OWNER_IDS
from core.logger import log_info, log_debug, log_error
from services.api import get_uuid, get_profile_data
from services.simulation_logic import simulate_to_level_all50
from services.daily_manager import daily_manager
from services.link_manager import link_manager

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
        
        try:
            await interaction.edit_original_response(embed=embed, view=self.parent_view)
        except Exception as e:
            log_error(f"Failed to edit message: {e}")
            try:
                await interaction.edit_original_response(embed=embed, view=self.parent_view)
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
            await interaction.edit_original_response(view=self.parent_view)
        except Exception as e:
            log_error(f"Failed to edit message in MainSelect: {e}")



def _create_option_list(option: str, current_val: float) -> list[discord.SelectOption]:
    if option == "ring":
        return [
            discord.SelectOption(label="Yes", value="0.1", description="10% bonus", default=(abs(current_val - 0.1) < 0.0001)),
            discord.SelectOption(label="No", value="0", description="No bonus", default=(abs(current_val - 0.0) < 0.0001)),
        ]
    elif option == "hecatomb":
        return [
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
        return [
            discord.SelectOption(label="Grimoire (6%)", value="0.06", description="6% bonus", default=(abs(current_val - 0.06) < 0.0001)),
            discord.SelectOption(label="Thesis (4%)", value="0.04", description="4% bonus", default=(abs(current_val - 0.04) < 0.0001)),
            discord.SelectOption(label="Studies (2%)", value="0.02", description="2% bonus", default=(abs(current_val - 0.02) < 0.0001)),
            discord.SelectOption(label="None", value="0.0", description="No scarf accessory", default=(abs(current_val - 0.0) < 0.0001)),
        ]
    elif option == "scarf_attribute":
        return [
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
        return [
            discord.SelectOption(label="0%", value="1", description="No boost", default=(abs(current_val - 1.0) < 0.0001)),
            discord.SelectOption(label="5%", value="1.05", description="5% boost", default=(abs(current_val - 1.05) < 0.0001)),
            discord.SelectOption(label="10%", value="1.1", description="10% boost", default=(abs(current_val - 1.1) < 0.0001)),
            discord.SelectOption(label="15%", value="1.15", description="15% boost", default=(abs(current_val - 1.15) < 0.0001)),
            discord.SelectOption(label="20%", value="1.2", description="20% boost", default=(abs(current_val - 1.2) < 0.0001)),
            discord.SelectOption(label="30%", value="1.3", description="30% boost", default=(abs(current_val - 1.3) < 0.0001)),
        ]
    elif option == "mayor":
        return [
            discord.SelectOption(label="0%", value="1", description="No boost", default=(abs(current_val - 1.0) < 0.0001)),
            discord.SelectOption(label="Derpy (50%)", value="1.5", description="50% boost", default=(abs(current_val - 1.5) < 0.0001)),
            discord.SelectOption(label="Aura (55%, probably bugged. select Derpy)", value="1.55", description="55% boost", default=(abs(current_val - 1.55) < 0.0001)),
        ]
    return None

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
        current_val = self.bonuses.get(option, default_bonuses.get(option, 0))
        options = _create_option_list(option, current_val)
        
        if options:
            return ValueSelect(self, option, options)
        return None
    
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
        
        try:
            await interaction.edit_original_response(embed=embed, view=self.parent_view)
        except Exception as e:
            log_error(f"Failed to edit message: {e}")
            try:
                await interaction.edit_original_response(embed=embed, view=self.parent_view)
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
            await interaction.edit_original_response(view=self.parent_view)
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
        current_val = default_bonuses.get(option, 0)
        options = _create_option_list(option, current_val)
        
        if options:
            return DefaultValueSelect(self, option, options)
        return None
    
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

class Dungeons(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(ign="Minecraft IGN (optional if linked)", floor="Dungeon floor (M7, M6, etc.)")
    @app_commands.command(name="rtca", description="Simulate runs until all dungeon classes reach level 50")
    async def rtca(self, interaction: discord.Interaction, ign: str = None, floor: str = "M7"):
        start_time = time.perf_counter()
        await interaction.response.defer(thinking=True)
        log_debug(f"Defer sent after {(time.perf_counter() - start_time):.2f}s")
        
        log_info(f"Command /rtca called by {interaction.user} → {ign if ign else '[Linked]'}")
        
        if ign is None:
            ign = link_manager.get_link(interaction.user.id)
            if not ign:
                await interaction.followup.send("❌ You must provide an IGN or link your account first using `/link <ign>`.", ephemeral=True)
                return
            
            try:
                uuid_check = await get_uuid(ign)
                if uuid_check:
                    await daily_manager.register_user(interaction.user.id, ign, uuid_check)
            except:
                pass
        
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
        
        view = BonusSelectView(self.bot, dungeon_classes, base_floor, bonuses, ign, floor, dungeon_xp)
        
        embed = view._create_embed(results, runs_total)
        
        message = await interaction.followup.send(embed=embed, view=view)
        view.message = message
        
        log_info(f"✅ Simulation finished: {ign} → {runs_total:,} total runs")

    @app_commands.command(name="setdefault", description="Change default bonus values (owner only)")
    async def setdefault(self, interaction: discord.Interaction):
        if interaction.user.id not in OWNER_IDS:
             await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
             return

        view = DefaultSelectView(self.bot)
        embed = view._create_embed()
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
        view.message = await interaction.original_response()

async def setup(bot: commands.Bot):
    await bot.add_cog(Dungeons(bot))
