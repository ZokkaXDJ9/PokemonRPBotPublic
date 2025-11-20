import discord_token
import discord
from discord.ext import commands
import config
import sys
import os
import folder_manager  # Import the folder manager
import error_logger  # Import the error logger

# Add the root directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up intents, including message content intent
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent
intents.reactions = True         # Enable reaction intent
intents.guilds = True            # Enable guilds intent
intents.members = True  # This enables the members intent

# Initialize bot with the updated intents
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_command_error(ctx, error):
    """Handle errors from text commands"""
    await error_logger.on_command_error(bot, ctx, error)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Handle errors from slash commands"""
    await error_logger.on_app_command_error(bot, interaction, error)

async def load_commands():
    for extension in config.COMMANDS:
        try:
            await bot.load_extension(extension)
            print(f"Loaded extension: {extension}")
        except Exception as e:
            print(f"Failed to load extension {extension}: {e}")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    
    # Set up folders for all guilds
    try:
        await folder_manager.setup_folders(bot)
        print("Folders set up for all guilds.")
    except Exception as e:
        print(f"Error setting up folders: {e}")
    
    # Load commands
    await load_commands()
    
    # Sync commands with Discord
    try:
        await bot.tree.sync()
        print("Commands loaded and synced with Discord.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# Register the on_guild_join event from folder_manager
try:
    bot.event(folder_manager.on_guild_join)
    print("Registered on_guild_join event.")
except Exception as e:
    print(f"Error registering on_guild_join event: {e}")

# Add reaction-based message deletion functionality
@bot.event
async def on_reaction_add(reaction, user):
    # Check if the message is sent by the bot and the reaction is the "X" emoji
    if reaction.message.author == bot.user and str(reaction.emoji) == "❌":
        # Ensure the user reacting is not a bot
        if not user.bot:
            await reaction.message.delete()

# Test command to send a deletable message
@bot.command()
async def send(ctx):
    message = await ctx.send("React with ❌ to delete this message!")
    await message.add_reaction("❌")

# Run the bot with the token from discord_token module
try:
    bot.run(discord_token.TOKEN)
except Exception as e:
    print(f"Failed to run the bot: {e}")
