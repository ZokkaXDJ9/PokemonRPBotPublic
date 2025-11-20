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

def load_item(item_name: str):
    """
    Load an item JSON file from the items directory,
    normalize all keys to lowercase,
    and return the data as a dictionary.
    """
    ITEM_DIRECTORY = os.path.join(os.path.dirname(__file__), "../Data/items")
    file_path = os.path.join(ITEM_DIRECTORY, f"{item_name}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return normalize_keys(data)
    except FileNotFoundError:
        return None

class ItemCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cache item names at startup
        self.item_cache: List[str] = []
        self.item_cache_lower: List[str] = []
        self.load_item_cache()
    
    def load_item_cache(self):
        """Load all item names into memory for fast autocomplete"""
        items_dir = os.path.join(os.path.dirname(__file__), "..", "Data", "items")
        self.item_cache, self.item_cache_lower = load_or_build_cache(
            "items.json",
            items_dir,
            "items"
        )

    async def autocomplete_item(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Fast autocomplete using cached item names"""
        if not current:
            return [app_commands.Choice(name=name, value=name) for name in self.item_cache[:25]]
        
        current_lower = current.lower()
        matches = []
        
        for name, name_lower in zip(self.item_cache, self.item_cache_lower):
            if current_lower in name_lower:
                matches.append(app_commands.Choice(name=name, value=name))
                if len(matches) >= 25:
                    break
        
        return matches

    @app_commands.command(name="item", description="Display details of an item")
    @app_commands.autocomplete(name=autocomplete_item)
    async def item(self, interaction: discord.Interaction, name: str):
        # Load the item data (with normalized keys)
        item = load_item(name)
        if item is None:
            await interaction.response.send_message(
                content=f"Unable to find an item named **{name}**, sorry!",
                ephemeral=True,
            )
            return

        # Define fields and their formatting
        fields = {
            "name": ("### {}", "Unnamed Item"),
            "effect": ("{}", ""),
            "description": ("{}", "No description provided"),
            "category": ("**Category:** {}", "unknown"),
            "rarity": ("**Rarity:** {}", "unknown"),
        }

        response_lines = []
        for key, (fmt, default) in fields.items():
            value = item.get(key, default)
            if key == "effect":
                value = value.strip()
                if not value:
                    continue  # Skip empty effect
            response_lines.append(fmt.format(value))

        response = "\n".join(response_lines)

        await interaction.response.send_message(response)

async def setup(bot: commands.Bot):
    await bot.add_cog(ItemCommand(bot))
