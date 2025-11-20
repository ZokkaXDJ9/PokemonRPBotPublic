# roll.py
import discord
from discord import app_commands
from discord.ext import commands
from helpers import ParsedRollQuery
from button_handler import get_roll_view  # Import RollView handler

class RollManualCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="roll", description="Roll dice with manual inputs for dice, sides, and flat addition.")
    async def roll_manual(
        self,
        interaction: discord.Interaction,
        dice: int = 1,
        sides: int = 6,
        flat_addition: int = 0,
    ):
        parsed_query = ParsedRollQuery(dice, sides, flat_addition)
        result_text = parsed_query.execute()
        query_string = parsed_query.as_button_callback_query_string()
        
        await interaction.response.send_message(
            content=result_text,
            view=get_roll_view(query_string)  # Use the view with the button for rerolling
        )

# Setup function to register the Cog
async def setup(bot):
    await bot.add_cog(RollManualCommand(bot))
