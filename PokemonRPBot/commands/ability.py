import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from typing import List
from helpers import load_ability
from cache_helper import load_or_build_cache

class AbilityCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Cache ability names at startup
        self.ability_cache: List[str] = []
        self.load_ability_cache()
    
    def load_ability_cache(self):
        """Load all ability names into memory for fast autocomplete"""
        abilities_dir = os.path.join(os.path.dirname(__file__), "..", "Data", "abilities")
        self.ability_cache, self.ability_cache_lower = load_or_build_cache(
            "abilities.json",
            abilities_dir,
            "abilities"
        )
    
    async def ability_name_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Fast autocomplete using cached ability names"""
        if not current:
            # Return first 25 if no input
            return [app_commands.Choice(name=name, value=name) for name in self.ability_cache[:25]]
        
        current_lower = current.lower()
        matches = []
        
        # Use zip with pre-computed lowercase list for faster comparison
        for name, name_lower in zip(self.ability_cache, self.ability_cache_lower):
            if current_lower in name_lower:
                matches.append(app_commands.Choice(name=name, value=name))
                if len(matches) >= 25:  # Stop as soon as we have 25
                    break
        
        return matches

    @app_commands.command(name="ability", description="Display details of a Pokémon ability.")
    @app_commands.autocomplete(ability_name=ability_name_autocomplete)
    async def ability(self, interaction: discord.Interaction, ability_name: str):
        # Load the ability data from JSON file or data source
        ability = load_ability(ability_name)  # Use a helper function to load ability data
        if ability is None:
            await interaction.response.send_message(
                content=f"Unable to find an ability named **{ability_name}**, sorry! If that wasn't a typo, maybe it isn't implemented yet?",
                ephemeral=True
            )
            return

        # Construct a plain text message with Discord Markdown formatting
        response = f"""
### {ability['name']}
{ability['effect']}
*{ability['description']}*
"""

        # Send the message as plain text, formatted with Markdown
        await interaction.response.send_message(response)

async def setup(bot):
    await bot.add_cog(AbilityCommand(bot))
