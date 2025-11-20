import discord
from discord.ext import commands
from discord import app_commands

class About(commands.Cog):
    @app_commands.command(name="about", description="Displays information about the bot.")
    async def about_slash(self, interaction: discord.Interaction):
        message = (
            "## About the Bot\n"
            "Author: Bahamut (bahamutdx)\n"
            "GitHub: https://github.com/ZokkaXDJ9/PokemonRPBotPublic\n"
            "Special Thanks:\n"
            "- Lilo for creating the original Bot this all started from (and for making the source code available to use under the MIT License)\n"
            "- Our amazing community for their support and contributions!\n"
            "- Verthal for her massive contribution to the system!\n"
            "- Lennoth for being an invaluable friend and supporter!\n"
            "- The entire Bot Manager team for their hard work and dedication including:\n"
            "  • Verthal\n"
            "  • Tearan\n"
            "  • Mega Ray\n"
            "  • Buckets/Compass\n"
            "- You, for using the bot and being part of this journey!\n"
            "Join The Development Discord server for support: \n"
        )
        await interaction.response.send_message(message)
    """Cog for bot information and credits."""

    def __init__(self, bot):
        self.bot = bot


async def setup(bot):
    cog = About(bot)
    await bot.add_cog(cog)
