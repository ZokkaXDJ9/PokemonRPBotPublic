from __future__ import annotations
import re
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple

import discord
from discord.ext import commands

# --------------------------------------------------------------------------------
# OFFSET STORAGE FUNCTIONS (reuse these from your other module)
# --------------------------------------------------------------------------------
OFFSET_FILE = "user_offsets.json"

def load_offsets() -> Dict[str, List[int]]:
    if not os.path.exists(OFFSET_FILE):
        return {}
    try:
        with open(OFFSET_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, IOError):
        return {}

async def get_user_offset(user_id: int) -> Optional[Tuple[int, int]]:
    offsets = load_offsets()
    data = offsets.get(str(user_id))
    if data and len(data) == 2:
        return (data[0], data[1])
    return None

# --------------------------------------------------------------------------------
# HELPER FUNCTION: Build "local now" from stored offset
# --------------------------------------------------------------------------------
def build_now_with_offset(hours: int, minutes: int) -> datetime:
    utc_now = datetime.utcnow()
    return utc_now + timedelta(hours=hours, minutes=minutes)

# --------------------------------------------------------------------------------
# TIMESTAMP TRACKER COG
# --------------------------------------------------------------------------------
class TimestampTracker(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore messages from bots.
        if message.author.bot:
            return

        # Look for a pattern like "ts:18:00" anywhere in the message.
        pattern = r"\bts:(\d{1,2}):(\d{2})\b"
        match = re.search(pattern, message.content)
        if not match:
            return

        hour_str, minute_str = match.groups()
        try:
            hour = int(hour_str)
            minute = int(minute_str)
        except ValueError:
            return

        # Validate the extracted time values.
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            return

        # Get the user's stored offset (if not set, assume UTC).
        user_offset = await get_user_offset(message.author.id)
        if user_offset is None:
            offset_hours, offset_minutes = 0, 0
        else:
            offset_hours, offset_minutes = user_offset

        # Determine today's date in the user's local time.
        local_now = build_now_with_offset(offset_hours, offset_minutes)
        # Build a datetime object for today with the given hour:minute.
        try:
            local_dt = datetime(local_now.year, local_now.month, local_now.day, hour, minute, 0)
        except ValueError:
            return

        # Create a Unix timestamp directly from the chosen local time.
        # (This timestamp will be treated as if it's UTC.)
        unix_ts = int(local_dt.timestamp())

        # Prepare a response message containing the Discord timestamp.
        response = (
            f"You mean <t:{unix_ts}:t>?"
        )

        await message.channel.send(response)
        # Ensure commands still work if this message also invoked one.
        await self.bot.process_commands(message)

async def setup(bot: commands.Bot):
    await bot.add_cog(TimestampTracker(bot))
