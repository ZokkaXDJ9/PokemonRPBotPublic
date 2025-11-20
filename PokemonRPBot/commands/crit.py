import discord
from discord import app_commands
from discord.ext import commands
import math
from typing import Literal

class CritCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="crit",
        description="Calculate the critical strike damage of a move."
    )
    async def crit(
        self,
        interaction: discord.Interaction,
        damage: int,  # Rolled damage
        stab: Literal["yes", "no", "double"] = "no",  # Whether STAB is applied
        item_bonus: int = 0,               # Items
        weather: int = 0,                  # Weather effects
        stat_boosts: int = 0,              # Stat boosts
        effective: Literal[
            "neutral",
            "super_effective",
            "double_effective",
            "not_effective",
            "double_not_effective",
        ] = "neutral",
        crit_multi: Literal["ignore defense (1.25x)", "normal (1.5x)", "sniper (2x)"] = "normal (1.5x)"  # Affects critical multiplier
    ):
        """
        Final Formula:
        Base Damage = (Rolled damage + STAB + SE + Items + Weather) x CritMultiplier + StatBoosts - NVE
        """

        # 1. Base additive damage
        base_damage = damage

        # Add STAB if applicable
        if stab == "yes":
            base_damage += 1
        elif stab == "double":
            base_damage +=2

        # Add super/double effective (additive portion)
        if effective == "super_effective":
            base_damage += 1
        elif effective == "double_effective":
            base_damage += 2

        # Add item bonus
        base_damage += item_bonus

        # Add weather effects
        base_damage += weather

        # 2. Critical multiplier
        if crit_multi == "ignore defense (1.25x)":
            crit_multiplier = 1.25 
        elif crit_multi == "normal (1.5x)":
            crit_multiplier = 1.5
        elif crit_multi == "sniper (2x)":
            crit_multiplier = 2
        
        total_damage = math.ceil(base_damage * crit_multiplier)

        # 3. Add stat boosts
        total_damage += stat_boosts

        # 4. Subtract not-very-effective reductions
        if effective == "not_effective":
            total_damage -= 1
        elif effective == "double_not_effective":
            total_damage -= 2

        # 5. Ensure damage doesn't fall below zero
        total_damage = max(total_damage, 0)

        await interaction.response.send_message(f"Base damage: {total_damage}")


async def setup(bot):
    await bot.add_cog(CritCommand(bot))
