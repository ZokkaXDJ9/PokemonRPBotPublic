import discord
from discord import app_commands
from discord.ext import commands
import os
import json
from typing import List
from helpers import load_move, ParsedRollQuery
from emojis import get_type_emoji, get_category_emoji
from cache_helper import load_or_build_cache

# Directories for move files and character files
MOVECARD_DIRECTORY = os.path.join(os.path.dirname(__file__), "../Data/movecards")
CHARACTERS_DIRECTORY = os.path.join(os.path.dirname(__file__), "../Characters")

def load_user_stats(user_id: int):
    """Load user stats from a JSON file in the Characters directory."""
    files = os.listdir(CHARACTERS_DIRECTORY)
    matching_file = next(
        (f for f in files if f.startswith(f"{user_id}_") and f.endswith(".json")),
        None
    )
    if not matching_file:
        return None
    stats_file = os.path.join(CHARACTERS_DIRECTORY, matching_file)
    with open(stats_file, "r") as file:
        return json.load(file)

def build_dice_query(dice_count: int):
    """Build a query string for ParsedRollQuery based on the number of dice."""
    return f"{dice_count}d6"

def get_move_field(move: dict, field: str, alt_field: str = None):
    """
    Retrieve a value from the move dict, trying both the provided key and an alternate version.
    If alt_field is not provided, defaults to the lowercase version of field.
    """
    if alt_field is None:
        alt_field = field.lower()
    return move.get(field) or move.get(alt_field)

class MoveCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cache movecard names at startup
        self.movecard_cache: List[str] = []
        self.movecard_cache_lower: List[str] = []
        self.load_movecard_cache()
    
    def load_movecard_cache(self):
        """Load all movecard names into memory for fast autocomplete"""
        self.movecard_cache, self.movecard_cache_lower = load_or_build_cache(
            "movecards.json",
            MOVECARD_DIRECTORY,
            "[Movecard] movecards"
        )

    async def move_name_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Fast autocomplete using cached movecard names"""
        if not current:
            return [app_commands.Choice(name=name, value=name) for name in self.movecard_cache[:25]]
        
        current_lower = current.lower()
        matches = []
        
        for name, name_lower in zip(self.movecard_cache, self.movecard_cache_lower):
            if current_lower in name_lower:
                matches.append(app_commands.Choice(name=name, value=name))
                if len(matches) >= 25:
                    break
        
        return matches

    @app_commands.command(
        name="move", 
        description="Display details of a Pokémon move."
    )
    @app_commands.autocomplete(move=move_name_autocomplete)
    async def move(self, interaction: discord.Interaction, move: str):
        move = load_move(move)
        if move is None:
            await interaction.response.send_message(
                f"Move '{move}' not found.", ephemeral=True
            )
            return

        user_stats = load_user_stats(interaction.user.id)

        # Retrieve move fields using the helper to support both key formats.
        move_name_field = get_move_field(move, "Name")
        type_field = get_move_field(move, "Type")
        category_field = get_move_field(move, "Category")
        description_field = get_move_field(move, "Description")
        target_field = get_move_field(move, "Target")
        effect_field = get_move_field(move, "Effect")
        damage_field = get_move_field(move, "Damage1", "damage")
        power_field = get_move_field(move, "Power", "power")
        accuracy_field = get_move_field(move, "Accuracy1", "accuracy")

        # Get emojis for the move's type and category
        type_icon = get_type_emoji(type_field)
        category_icon = get_category_emoji(category_field)

        # Build the move description text
        move_description = f"""
### {move_name_field}
*{description_field}*
**Type**: {type_icon} {type_field} — **{category_icon} {category_field}**
**Target**: {target_field}
"""
        if damage_field:
            move_description += f"**Damage Dice**: {damage_field} + {power_field}\n"
        move_description += f"""**Accuracy Dice**: {accuracy_field} + Rank
**Effect**: {effect_field}
"""
        await interaction.response.send_message(move_description)

async def setup(bot):
    await bot.add_cog(MoveCommand(bot))
