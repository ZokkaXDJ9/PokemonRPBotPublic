import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import re
from datetime import datetime, timedelta

REMINDERS_FILE = "reminders.json"

# Functions to load and save reminders
def load_reminders():
    try:
        with open(REMINDERS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

def save_reminders(reminders):
    with open(REMINDERS_FILE, "w") as f:
        json.dump(reminders, f)

# Function to parse time strings
def parse_time_string(time_str):
    """
    Parses a time string and converts it to seconds.
    Supports formats like:
      - '10min', '10 min', '10 minutes'
      - '2h', '2 h', '2 hours'
      - '1h 30min', '1 hour 15 minutes'
    Ensures no negative or zero values are allowed.
    """
    total_seconds = 0
    time_str = time_str.lower()

    # Strictly validate the format (only digits + valid units allowed)
    if not re.match(r"^(\d+\s*(hours|hour|h|minutes|minute|min|m)\s*)+$", time_str):
        return None

    # Regex to match time components (e.g., '1h', '30min')
    matches = re.findall(r"(\d+)\s*(hours|hour|h|minutes|minute|min|m)", time_str)
    if not matches:
        return None  # Invalid format

    for value, unit in matches:
        value = int(value)
        if value <= 0:  # Reject zero or negative values
            return None
        if unit.startswith("h"):  # hours
            total_seconds += value * 3600
        elif unit.startswith("m"):  # minutes
            total_seconds += value * 60

    return total_seconds if total_seconds > 0 else None

# Reminder command class
class ReminderCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reminders = load_reminders()
        self.check_reminders.start()

    @app_commands.command(name="remind", description="Set a reminder to notify you after a specific time.")
    @app_commands.describe(
        time="The duration until the reminder, e.g., '10 minutes', '2h', or '1h 30m'. No negatives or zero.",
        message="The message for the reminder. If not provided, a default message will be used."
    )
    async def remind(self, interaction: discord.Interaction, time: str, *, message: str = None):
        """
        Slash command to set a reminder.
        Time format examples: '10 min', '2h', '1h 30min', '10 minutes', '2 hours'.
        Ensures no negative or zero times are allowed.
        """
        try:
            # Parse the time
            delay = parse_time_string(time)
            if delay is None:  # Check for invalid or zero/negative values
                await interaction.response.send_message(
                    "Invalid time format or negative value. Use something like '10 minutes', '2h', '1h 30min', etc.",
                    ephemeral=True
                )
                return

            # Default message if none is provided
            if not message:
                message = "This is your reminder!"

            # Calculate the reminder time
            remind_time = datetime.utcnow() + timedelta(seconds=delay)

            # Save the reminder
            reminder_id = str(interaction.id)
            self.reminders[reminder_id] = {
                "user_id": interaction.user.id,
                "channel_id": interaction.channel_id,
                "remind_time": remind_time.isoformat(),
                "message": message,
                "bot_message_id": None
            }
            save_reminders(self.reminders)

            # Respond to the user and save bot message ID
            await interaction.response.send_message(f"Got it! I'll remind you in {time}.")
            bot_message = await interaction.original_response()
            self.reminders[reminder_id]["bot_message_id"] = bot_message.id
            save_reminders(self.reminders)

        except ValueError:
            await interaction.response.send_message(
                "Invalid time format or negative value. Use something like '10 minutes', '2h', '1h 30min', etc.",
                ephemeral=True
            )

    @tasks.loop(seconds=30)
    async def check_reminders(self):
        """
        Periodically checks reminders and sends notifications when due.
        """
        now = datetime.utcnow()
        reminders_to_delete = []

        for reminder_id, reminder in self.reminders.items():
            remind_time = datetime.fromisoformat(reminder["remind_time"])
            if now >= remind_time:
                # Time to remind the user
                channel = self.bot.get_channel(reminder["channel_id"])
                if channel:
                    try:
                        user = await self.bot.fetch_user(reminder["user_id"])
                        if user:
                            bot_message_id = reminder.get("bot_message_id")
                            if bot_message_id:
                                bot_message = await channel.fetch_message(bot_message_id)
                                await bot_message.reply(
                                    content=f"⏰ Reminder for {user.mention}: {reminder['message']}"
                                )
                    except discord.NotFound:
                        pass
                reminders_to_delete.append(reminder_id)

        # Clean up reminders
        for reminder_id in reminders_to_delete:
            del self.reminders[reminder_id]
        if reminders_to_delete:
            save_reminders(self.reminders)

    @check_reminders.before_loop
    async def before_check_reminders(self):
        """
        Waits until the bot is ready before starting the reminder loop.
        """
        await self.bot.wait_until_ready()

# Setup function to load the cog
async def setup(bot):
    await bot.add_cog(ReminderCommand(bot))
