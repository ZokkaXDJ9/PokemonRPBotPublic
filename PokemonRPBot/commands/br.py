import discord
from discord import app_commands
from discord.ext import commands

class BR(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="br", description="Sends a line break for formatting purposes.")
    async def br(self, interaction: discord.Interaction):
        await interaction.response.send_message("``` ```")

async def setup(bot):
    await bot.add_cog(BR(bot))