import discord
from discord import app_commands
from discord.ext import commands
import os
import json
from typing import List
from helpers import load_weather  # Function to load weather data
from cache_helper import load_or_build_cache

# Directory where weather files are stored
WEATHER_DIRECTORY = os.path.join(os.path.dirname(__file__), "../Data/weather")

class WeatherCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cache weather names at startup
        self.weather_cache: List[str] = []
        self.weather_cache_lower: List[str] = []
        self.load_weather_cache()
    
    def load_weather_cache(self):
        """Load all weather names into memory for fast autocomplete"""
        weather_dir = os.path.join(os.path.dirname(__file__), "..", "Data", "weather")
        self.weather_cache, self.weather_cache_lower = load_or_build_cache(
            "weather.json",
            weather_dir,
            "weather effects"
        )

    # Autocomplete function to suggest weather names
    async def autocomplete_weather(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Fast autocomplete using cached weather names"""
        if not current:
            return [app_commands.Choice(name=name, value=name) for name in self.weather_cache[:25]]
        
        current_lower = current.lower()
        matches = []
        
        for name, name_lower in zip(self.weather_cache, self.weather_cache_lower):
            if current_lower in name_lower:
                matches.append(app_commands.Choice(name=name, value=name))
                if len(matches) >= 25:
                    break
        
        return matches

    @app_commands.command(name="weather", description="Display details of a weather effect")
    @app_commands.autocomplete(name=autocomplete_weather)
    async def weather(self, interaction: discord.Interaction, name: str):
        # Load the weather data from JSON file
        weather = load_weather(name)  # Use a helper function to load weather data
        if weather is None:
            await interaction.response.send_message(
                content=f"Unable to find a weather effect named **{name}**, sorry! If that wasn't a typo, maybe it isn't implemented yet?",
                ephemeral=True
            )
            return

        # Construct a plain text message with Discord Markdown formatting
        response = f"""
### {weather['name']} Weather
*{weather['description']}*
{weather['effect']}
"""

        # Send the message as plain text, formatted with Markdown
        await interaction.response.send_message(response)

async def setup(bot):
    await bot.add_cog(WeatherCommand(bot))
