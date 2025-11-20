import discord
from discord import app_commands
from discord.ext import commands
import os
from typing import List
from helpers import load_status  # Function to load status data
from cache_helper import load_or_build_cache

# Directory where status files are stored
STATUS_DIRECTORY = os.path.join(os.path.dirname(__file__), "../Data/status")

class StatusCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cache status names at startup
        self.status_cache: List[str] = []
        self.status_cache_lower: List[str] = []
        self.load_status_cache()
    
    def load_status_cache(self):
        """Load all status names into memory for fast autocomplete"""
        self.status_cache, self.status_cache_lower = load_or_build_cache(
            "status.json",
            STATUS_DIRECTORY,
            "[Status] status effects"
        )

    # Autocomplete function to suggest status names
    async def autocomplete_status(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Fast autocomplete using cached status names"""
        if not current:
            return [app_commands.Choice(name=name, value=name) for name in self.status_cache[:25]]
        
        current_lower = current.lower()
        matches = []
        
        for name, name_lower in zip(self.status_cache, self.status_cache_lower):
            if current_lower in name_lower:
                matches.append(app_commands.Choice(name=name, value=name))
                if len(matches) >= 25:
                    break
        
        return matches

    @app_commands.command(name="status", description="Display details of a status effect")
    @app_commands.autocomplete(name=autocomplete_status)
    async def status(self, interaction: discord.Interaction, name: str):
        # Load the status data from JSON file
        status = load_status(name)  # Use a helper function to load status data
        if status is None:
            await interaction.response.send_message(
                content=f"Unable to find a status named **{name}**, sorry! If that wasn't a typo, maybe it isn't implemented yet?",
                ephemeral=True
            )
            return

        # Construct a plain text message with Discord Markdown formatting
        response = f"""
### {status['name']}
*{status['description']}*
- {status['resist']}
- {status['effect']}
- {status['duration']}
"""

        # Send the message as plain text, formatted with Markdown
        await interaction.response.send_message(response)

async def setup(bot):
    await bot.add_cog(StatusCommand(bot))
