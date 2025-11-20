import discord
from discord import app_commands
from discord.ext import commands
import os
import random
from typing import List
from helpers import load_move
from emojis import get_type_emoji, get_category_emoji
from cache_helper import load_or_build_cache

# Directories for move files
MOVES_DIRECTORY = os.path.join(os.path.dirname(__file__), "../Data/moves")

def get_move_field(move: dict, field: str, alt_field: str = None):
    """
    Retrieve a value from the move dict, trying both the provided key and an alternate version.
    If alt_field is not provided, defaults to the lowercase version of field.
    """
    if alt_field is None:
        alt_field = field.lower()
    return move.get(field) or move.get(alt_field)

class CreateMoveCardCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cache move names at startup
        self.move_cache: List[str] = []
        self.move_cache_lower: List[str] = []
        self.load_move_cache()
        # Global lists for randomization
        self.random_types = ["Rock", "Ice", "Fire", "Electric", "Grass", "Water", "Psychic", "Fairy", "Steel", "Dark", "Dragon", "Poison", "Flying", "Bug", "Ghost", "Ground", "Fighting", "Normal"]
        self.random_categories = ["Physical", "Special"]
        self.status_category = "Support"
        self.random_accuracy_stats = ["Dexterity", "Insight", "Special", "Strength", "Vitality", "Will"]
        self.random_targets = [
            "Foe",
            "All Foes",
            "User",
            "Ally",
            "All Allies",
            "Battlefield",
            "Random Target",
            "Random Foe",
            "Random Ally",
            "Area"
        ]

        # Cost configuration (edit these values to change cost logic)
        self.BASE_COST = 6
        self.TYPE_RANDOMIZER_COST = 3 # Cost if type is randomized
        self.CATEGORY_RANDOMIZER_COST = 3 # Cost if category is randomized
        self.ACCURACY_RANDOMIZER_COST = 3 # Cost if accuracy is randomized
        self.POWER_RANDOMIZER_COST = 3  # Cost per point of power above reference
        self.POWER_RANDOMIZER_DISCOUNT = 3  # Discount per point of power below reference
        self.TARGET_RANDOMIZER_COST = 6  # Cost if target is randomized
        # Add more cost variables as needed
    
    def load_move_cache(self):
        """Load all move names into memory for fast autocomplete"""
        self.move_cache, self.move_cache_lower = load_or_build_cache(
            "moves.json",
            MOVES_DIRECTORY,
            "[Create Movecard] moves"
        )

    async def move_name_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Fast autocomplete using cached move names"""
        if not current:
            return [app_commands.Choice(name=name, value=name) for name in self.move_cache[:25]]
        
        current_lower = current.lower()
        matches = []
        
        for name, name_lower in zip(self.move_cache, self.move_cache_lower):
            if current_lower in name_lower:
                matches.append(app_commands.Choice(name=name, value=name))
                if len(matches) >= 25:
                    break
        
        return matches

    async def bool_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        options = ["True", "False"]
        return [app_commands.Choice(name=opt, value=opt) for opt in options if current.lower() in opt.lower()]

    @app_commands.command(
        name="create_movecard", 
        description="Generate a Move Card for a given Move with the option to randomize different fields."
    )
    @app_commands.describe(
        move="The move to generate a card for.",
        allow_type_randomization="Randomize type? Default: False",
        allow_category_randomization="Randomize category? Default: False",
        allow_accuracy_randomization="Randomize accuracy? Default: False",
        allow_power_randomization="Randomize power? Default: False",
        allow_target_randomization="Randomize target? Default: False"
    )
    @app_commands.autocomplete(
        move=move_name_autocomplete,
        allow_type_randomization=bool_autocomplete,
        allow_category_randomization=bool_autocomplete,
        allow_accuracy_randomization=bool_autocomplete,
        allow_power_randomization=bool_autocomplete,
        allow_target_randomization=bool_autocomplete
    )
    async def move(
        self,
        interaction: discord.Interaction,
        move: str,
        allow_type_randomization: str = "False",
        allow_category_randomization: str = "False",
        allow_accuracy_randomization: str = "False",
        allow_power_randomization: str = "False",
        allow_target_randomization: str = "False"
    ):
        """
        allow_type_randomization: Randomize type? Default: False
        allow_category_randomization: Randomize category? Default: False
        allow_accuracy_randomization: Randomize accuracy? Default: False
        allow_power_randomization: Randomize power? Default: False
        allow_target_randomization: Randomize target? Default: False
        """
        move_data = load_move(move)
        if move_data is None:
            await interaction.response.send_message(
                f"Move '{move}' not found.", ephemeral=True
            )
            return

        # Convert string flags to booleans
        allow_type_randomization = allow_type_randomization == "True"
        allow_category_randomization = allow_category_randomization == "True"
        allow_accuracy_randomization = allow_accuracy_randomization == "True"
        allow_power_randomization = allow_power_randomization == "True"
        allow_target_randomization = allow_target_randomization == "True"

        # Pick random values only if allowed
        type_field = random.choice(self.random_types) if allow_type_randomization else get_move_field(move_data, "Type")
        move_category = get_move_field(move_data, "Category")
        is_status = move_category == self.status_category
        if is_status:
            category_field = self.status_category
        else:
            category_field = random.choice(self.random_categories) if allow_category_randomization else move_category
        description_field = get_move_field(move_data, "Description")
        effect_field = get_move_field(move_data, "Effect")
        original_target = get_move_field(move_data, "Target")
        foe_targets = ["Foe", "All Foes", "Area", "Random Foe"]
        if not allow_target_randomization:
            target_field = original_target
        elif original_target in foe_targets:
            target_field = random.choice(foe_targets)
        else:
            target_field = random.choice(self.random_targets)
        power_field = str(random.randint(0, 5)) if allow_power_randomization else get_move_field(move_data, "Power", "power")
        accuracy_field = random.choice(self.random_accuracy_stats) if allow_accuracy_randomization else get_move_field(move_data, "Accuracy1", "accuracy")

        # Set damage field based on category
        if category_field == "Physical":
            damage_field = "Physical"
        elif category_field == "Special":
            damage_field = "Special"
        else:
            damage_field = get_move_field(move_data, "Damage1", "damage")

        # Calculate cost
        base_cost = self.BASE_COST
        reference_power = get_move_field(move_data, "Power", "power")
        try:
            reference_power_int = int(reference_power) if reference_power is not None else 0
            current_power_int = int(power_field) if power_field is not None else 0
        except ValueError:
            reference_power_int = 0
            current_power_int = 0
        # Cost for power difference
        power_cost = max(0, current_power_int - reference_power_int) * self.POWER_RANDOMIZER_COST
        power_discount = max(0, reference_power_int - current_power_int) * self.POWER_RANDOMIZER_DISCOUNT

        # Add cost for each randomizer used
        type_cost = self.TYPE_RANDOMIZER_COST if allow_type_randomization else 0
        category_cost = self.CATEGORY_RANDOMIZER_COST if allow_category_randomization else 0
        accuracy_cost = self.ACCURACY_RANDOMIZER_COST if allow_accuracy_randomization else 0
        target_cost = self.TARGET_RANDOMIZER_COST if allow_target_randomization else 0

        cost = base_cost + power_cost - power_discount + type_cost + category_cost + accuracy_cost + target_cost

        type_icon = get_type_emoji(type_field)
        category_icon = get_category_emoji(category_field)

        move_description = f"""
## New Move Card just dropped!
### {move}
*{description_field}*
**Type**: {type_icon} {type_field} — **{category_icon} {category_field}**
**Target**: {target_field}
"""
        if damage_field:
            move_description += f"**Damage Dice**: {damage_field} + {power_field}\n"
        move_description += f"**Accuracy Dice**: {accuracy_field} + Rank\n"
        move_description += f"**Effect**: {effect_field}\n"
        move_description += f"**Cost**: {cost} <:battlepoint:1272533678714519612>\n"

        await interaction.response.send_message(move_description)

async def setup(bot):
    await bot.add_cog(CreateMoveCardCommand(bot))
