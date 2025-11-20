import discord
from discord import app_commands
from discord.ext import commands
import os
import json
from typing import List
from cache_helper import load_or_build_content_cache

ITEMS_DIR = os.path.join(os.path.dirname(__file__), '../Data/items')

def get_all_items():
    items = []
    for fname in os.listdir(ITEMS_DIR):
        if fname.endswith('.json'):
            with open(os.path.join(ITEMS_DIR, fname), encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    items.append(data)
                except Exception:
                    continue
    return items

def get_all_categories():
    items = get_all_items()
    cats = set()
    for item in items:
        cat = item.get('category') or item.get('Category')
        if cat:
            cats.add(cat)
    return sorted(cats)

def get_all_rarities():
    items = get_all_items()
    rars = set()
    for item in items:
        rar = item.get('rarity') or item.get('Rarity')
        if rar:
            rars.add(rar)
    return sorted(rars)

class FilterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cache categories and rarities at startup using centralized cache helper
        self.categories_cache, self.categories_cache_lower = load_or_build_content_cache(
            "item_categories.json",
            ITEMS_DIR,
            get_all_categories,
            "item categories"
        )
        self.rarities_cache, self.rarities_cache_lower = load_or_build_content_cache(
            "item_rarities.json",
            ITEMS_DIR,
            get_all_rarities,
            "item rarities"
        )

    async def category_autocomplete(self, interaction: discord.Interaction, current: str):
        """Fast autocomplete using cached categories"""
        if not current:
            return [app_commands.Choice(name=name, value=name) for name in self.categories_cache[:25]]
        
        current_lower = current.lower()
        matches = []
        
        for name, name_lower in zip(self.categories_cache, self.categories_cache_lower):
            if current_lower in name_lower:
                matches.append(app_commands.Choice(name=name, value=name))
                if len(matches) >= 25:
                    break
        
        return matches

    async def rarity_autocomplete(self, interaction: discord.Interaction, current: str):
        """Fast autocomplete using cached rarities"""
        if not current:
            return [app_commands.Choice(name=name, value=name) for name in self.rarities_cache[:25]]
        
        current_lower = current.lower()
        matches = []
        
        for name, name_lower in zip(self.rarities_cache, self.rarities_cache_lower):
            if current_lower in name_lower:
                matches.append(app_commands.Choice(name=name, value=name))
                if len(matches) >= 25:
                    break
        
        return matches


    @app_commands.command(name='filter_items', description='Filter your items by category, rarity, or both.')
    @app_commands.describe(category='Item category', rarity='Item rarity')
    @app_commands.autocomplete(category=category_autocomplete, rarity=rarity_autocomplete)
    async def filter_items(self, interaction: discord.Interaction, category: str = None, rarity: str = None):
        items = get_all_items()
        if category:
            items = [i for i in items if (i.get('category') or i.get('Category')) == category]
        if rarity:
            items = [i for i in items if (i.get('rarity') or i.get('Rarity')) == rarity]
        if not items:
            await interaction.response.send_message('No items found for the given filter.', ephemeral=True)
            return
        lines = [f"**{i.get('name', i.get('Name', 'Unknown'))}** - {i.get('category', i.get('Category', ''))} - {i.get('rarity', i.get('Rarity', ''))}" for i in items]
        messages = []
        current_msg = ''
        for line in lines:
            if len(current_msg) + len(line) + 1 > 2000:
                messages.append(current_msg)
                current_msg = line
            else:
                if current_msg:
                    current_msg += '\n' + line
                else:
                    current_msg = line
        if current_msg:
            messages.append(current_msg)
        for idx, msg in enumerate(messages):
            await interaction.response.send_message(msg, ephemeral=True) if idx == 0 else await interaction.followup.send(msg, ephemeral=True)

async def setup(bot):
    await bot.add_cog(FilterCog(bot))
