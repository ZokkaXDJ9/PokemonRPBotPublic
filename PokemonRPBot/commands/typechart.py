import discord
from discord import app_commands
from discord.ext import commands
import json
import math
import os
import re

# Import only the functions needed from your custom emojis file.
from emojis import get_type_emoji

def load_defensive_chart():
    r"""
    Load the defensive type interaction chart from a JSON file.
    The JSON file is located at:
    PokemonRPBot/PokemonRPBot/Data/typechart.json
    """
    file_path = os.path.join(os.path.dirname(__file__), "..", "Data", "typechart.json")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Load the defensive chart once when the cog is loaded.
DEFENSIVE_CHART = load_defensive_chart()

def normalize_type(t: str) -> str:
    """
    Normalize the input type string to match one of the keys in DEFENSIVE_CHART.
    This function compares the lowercase of the input to the lowercase of each key
    and returns the properly cased key if found. Otherwise, it returns the input.
    """
    t_normalized = t.lower()
    for key in DEFENSIVE_CHART.keys():
        if key.lower() == t_normalized:
            return key
    return t

def get_effectiveness_category(multiplier: float) -> str:
    """
    Convert the combined multiplier into a text category using base-2 logarithms:
      - log₂(4) = 2    → "Super Effective (+2)"
      - log₂(2) = 1    → "Effective (+1)"
      - log₂(0.5) = -1 → "Ineffective (-1)"
      - log₂(0.25) = -2→ "Super Ineffective (-2)"
      - 0 multiplier  → "Immune (No Damage)"
    """
    if multiplier == 0:
        return "Immune (No Damage)"
    shift = round(math.log(multiplier, 2))
    if shift == 0:
        return "Neutral (0)"
    elif shift == 1:
        return "Effective (+1)"
    elif shift == 2:
        return "Super Effective (+2)"
    elif shift == -1:
        return "Ineffective (-1)"
    elif shift == -2:
        return "Super Ineffective (-2)"
    elif shift > 2:
        return f"Ultra Effective (+{shift})"
    elif shift < -2:
        return f"Ultra Ineffective ({shift})"
    return f"Multiplier {multiplier}"

def sort_key(category: str) -> float:
    """
    Extract a numeric key from the category string by searching for the numeric value
    within parentheses (e.g., '(+2)'). "Immune (No Damage)" is forced to a low value.
    """
    if category == "Immune (No Damage)":
        return -999
    m = re.search(r'\(([-+]\d+)\)', category)
    if m:
        return int(m.group(1))
    return 0

class TypeInteractionsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="typechart",
        description="Show defensive type interactions for a given type combination."
    )
    @app_commands.describe(
        type1="Primary type",
        type2="Secondary type (optional)",
        type3="Tertiary type (optional)",
        type4="Quaternary type (optional)"
    )
    async def typechart(
        self,
        interaction: discord.Interaction,
        type1: str,
        type2: str = None,
        type3: str = None,
        type4: str = None
    ):
        # Defer the response while processing.
        await interaction.response.defer()

        # Normalize and build the list of defending types.
        defender_types = [normalize_type(type1)]
        for t in (type2, type3, type4):
            if t is not None:
                defender_types.append(normalize_type(t))

        # Calculate overall effectiveness for each attacking type.
        results = {}
        for attack_type in DEFENSIVE_CHART.keys():
            multiplier = 1.0
            for def_type in defender_types:
                multiplier *= DEFENSIVE_CHART[def_type][attack_type]
            if multiplier == 1:
                continue
            category = get_effectiveness_category(multiplier)
            if category == "Neutral (0)":
                continue
            results.setdefault(category, []).append(attack_type)

        # Sort the categories using the numeric value in parentheses (descending)
        sorted_categories = sorted(results.keys(), key=sort_key, reverse=True)

        # Build the defender string with type emojis and names.
        defender_str = " / ".join(f"{get_type_emoji(t)} {t}" for t in defender_types)

        # Build a plain text message using an f-string for the header.
        message_lines = [f"## Type Chart for {defender_str}"]
        for category in sorted_categories:
            types_list = results[category]
            # Build a string of types with their corresponding emoji.
            types_str = "  |  ".join(f"{get_type_emoji(t)} {t}" for t in types_list)
            message_lines.append(f"### {category}")
            message_lines.append(types_str)

        message = "\n".join(message_lines)
        await interaction.followup.send(message)

    # Autocomplete functions for the type parameters.
    @typechart.autocomplete("type1")
    async def type1_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=t, value=t)
            for t in sorted(DEFENSIVE_CHART.keys())
            if current.lower() in t.lower()
        ][:25]

    @typechart.autocomplete("type2")
    async def type2_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=t, value=t)
            for t in sorted(DEFENSIVE_CHART.keys())
            if current.lower() in t.lower()
        ][:25]

    @typechart.autocomplete("type3")
    async def type3_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=t, value=t)
            for t in sorted(DEFENSIVE_CHART.keys())
            if current.lower() in t.lower()
        ][:25]

    @typechart.autocomplete("type4")
    async def type4_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=t, value=t)
            for t in sorted(DEFENSIVE_CHART.keys())
            if current.lower() in t.lower()
        ][:25]

async def setup(bot: commands.Bot):
    await bot.add_cog(TypeInteractionsCog(bot))
