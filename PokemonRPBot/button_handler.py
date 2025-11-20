# button_handler.py
import discord
from helpers import ParsedRollQuery  # Import ParsedRollQuery for rolling logic

class RollView(discord.ui.View):
    def __init__(self, query_string: str):
        super().__init__(timeout=180)  # Timeout for button inactivity
        self.query_string = query_string  # Store the query string to reuse in the callback

    @discord.ui.button(label="Roll again!", style=discord.ButtonStyle.primary)
    async def roll_again_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Parse the query string and execute the roll
        parsed_query = ParsedRollQuery.from_query(self.query_string)
        result_text = parsed_query.execute()

        # Send a new message with the roll result without the button (ephemeral=False for visibility)
        await interaction.response.send_message(content=result_text, ephemeral=False)

# Function to provide an instance of RollView, which can be imported in other files
def get_roll_view(query_string: str) -> RollView:
    return RollView(query_string)
