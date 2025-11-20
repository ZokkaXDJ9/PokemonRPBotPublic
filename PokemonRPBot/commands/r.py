# r.py
import discord
from discord import app_commands
from discord.ext import commands
from helpers import ParsedRollQuery
from button_handler import get_roll_view  # Import RollView handler

class RollCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="r", description="Roll dice using a '1d6+4' style query.")
    async def roll(self, interaction: discord.Interaction, query: str):
        parsed_query = ParsedRollQuery.from_query(query)
        result_text = parsed_query.execute()
        query_string = parsed_query.as_button_callback_query_string()
        
        # Send the initial roll message with the "Roll again!" button
        await interaction.response.send_message(
            content=result_text,
            view=get_roll_view(query_string)  # Use the view with the button for rerolling
        )

async def setup(bot):
    await bot.add_cog(RollCommand(bot))
