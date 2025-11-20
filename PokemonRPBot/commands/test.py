import discord
from discord import app_commands
from discord.ext import commands


class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="test", description="Test command for debugging various features")
    @app_commands.describe(
        test_type="What to test",
        message="Optional message for certain tests"
    )
    @app_commands.choices(test_type=[
        app_commands.Choice(name="Error Logging - ZeroDivisionError", value="error_zero"),
        app_commands.Choice(name="Error Logging - KeyError", value="error_key"),
        app_commands.Choice(name="Error Logging - Custom Exception", value="error_custom"),
        app_commands.Choice(name="Ping - Check bot response time", value="ping"),
        app_commands.Choice(name="Echo - Send back your message", value="echo"),
    ])
    async def test(
        self,
        interaction: discord.Interaction,
        test_type: app_commands.Choice[str],
        message: str = None
    ):
        """Test command for debugging various bot features"""
        
        if test_type.value == "error_zero":
            # Test error logging with ZeroDivisionError
            await interaction.response.send_message("Testing error logging... (ZeroDivisionError)", ephemeral=True)
            result = 1 / 0  # This will raise ZeroDivisionError
            
        elif test_type.value == "error_key":
            # Test error logging with KeyError
            await interaction.response.send_message("Testing error logging... (KeyError)", ephemeral=True)
            test_dict = {"a": 1}
            value = test_dict["nonexistent_key"]  # This will raise KeyError
            
        elif test_type.value == "error_custom":
            # Test error logging with custom exception
            await interaction.response.send_message("Testing error logging... (Custom Exception)", ephemeral=True)
            raise Exception("This is a custom test exception with some context!")
            
        elif test_type.value == "ping":
            # Simple ping test
            latency = round(self.bot.latency * 1000)
            await interaction.response.send_message(
                f"🏓 Pong! Latency: {latency}ms",
                ephemeral=True
            )
            
        elif test_type.value == "echo":
            # Echo back the message
            if message:
                await interaction.response.send_message(
                    f"Echo: {message}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "Please provide a message to echo!",
                    ephemeral=True
                )


async def setup(bot):
    await bot.add_cog(Test(bot))
