import os
import discord

# Define the root directory for guild-specific folders
ROOT_FOLDER = "Guilds"

def ensure_guild_folder(guild):
    """Ensures a folder exists for the given guild."""
    guild_folder = os.path.join(ROOT_FOLDER, str(guild.id))
    os.makedirs(guild_folder, exist_ok=True)  # Create guild folder if it doesn't exist
    print(f"Ensured folder for guild: {guild.name} (ID: {guild.id})")

async def setup_folders(bot):
    """Sets up folders for all guilds the bot is currently in at startup."""
    # Ensure the root folder exists
    os.makedirs(ROOT_FOLDER, exist_ok=True)
    
    # Create a folder for each guild the bot is in
    for guild in bot.guilds:
        ensure_guild_folder(guild)
    print("All guild folders have been set up.")

# Event handler for joining a new guild
async def on_guild_join(guild):
    """Creates a folder when the bot joins a new guild."""
    ensure_guild_folder(guild)
    print(f"Joined new guild: {guild.name} (ID: {guild.id}) - Folder created.")
