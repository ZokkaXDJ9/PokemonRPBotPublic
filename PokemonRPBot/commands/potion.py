import discord
from discord import app_commands
from discord.ext import commands
import os
import json
from typing import List
from cache_helper import load_or_build_cache

def normalize_keys(obj):
    """Recursively convert all dictionary keys to lowercase."""
    if isinstance(obj, dict):
        return {k.lower(): normalize_keys(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [normalize_keys(i) for i in obj]
    return obj

def load_potion(potion_name: str):
    """
    Load a potion JSON file from the potions directory,
    normalize all keys to lowercase,
    and return the data as a dictionary.
    """
    POTION_DIRECTORY = os.path.join(os.path.dirname(__file__), "../Data/potions")
    file_path = os.path.join(POTION_DIRECTORY, f"{potion_name}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return normalize_keys(data)
    except FileNotFoundError:
        return None

class PotionCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cache potion names at startup
        self.potion_cache: List[str] = []
        self.potion_cache_lower: List[str] = []
        self.load_potion_cache()
    
    def load_potion_cache(self):
        """Load all potion names into memory for fast autocomplete"""
        POTION_DIRECTORY = os.path.join(os.path.dirname(__file__), "../Data/potions")
        self.potion_cache, self.potion_cache_lower = load_or_build_cache(
            "potions.json",
            POTION_DIRECTORY,
            "[Potion] potions"
        )

    async def autocomplete_potion(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Fast autocomplete using cached potion names"""
        if not current:
            return [app_commands.Choice(name=name, value=name) for name in self.potion_cache[:25]]
        
        current_lower = current.lower()
        matches = []
        
        for name, name_lower in zip(self.potion_cache, self.potion_cache_lower):
            if current_lower in name_lower:
                matches.append(app_commands.Choice(name=name, value=name))
                if len(matches) >= 25:
                    break
        
        return matches

    @app_commands.command(name="potion", description="Display details of a potion")
    @app_commands.autocomplete(name=autocomplete_potion)
    async def potion(self, interaction: discord.Interaction, name: str):
        # Load the potion data (with normalized keys)
        potion = load_potion(name)
        if potion is None:
            await interaction.response.send_message(
                content=f"Unable to find a potion named **{name}**, sorry!",
                ephemeral=True,
            )
            return

        # Define fields and their formatting
        fields = {
            "name": ("### {}", "Unnamed Potion"),
            "description": ("*{}*", "No description provided"),
            "effect": ("{}", ""),
            "recipes": ("**Recipes:**\n{}", ""),
        }

        response_lines = []
        for key, (fmt, default) in fields.items():
            value = potion.get(key, default)
            if key == "recipes" and isinstance(value, list):
                value = "\n".join(f"> {line}" for line in value)
                # Insert an empty line before recipes if effect is present
                if response_lines:
                    response_lines.append("")
            if key == "effect":
                value = value.strip()
                if not value:
                    continue  # Skip empty effect
            response_lines.append(fmt.format(value))

        response = "\n".join(response_lines)

        await interaction.response.send_message(response)

async def setup(bot: commands.Bot):
    await bot.add_cog(PotionCommand(bot))