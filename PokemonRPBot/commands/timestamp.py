from __future__ import annotations  # Postpone evaluation of annotations

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple

import discord
from discord import app_commands
from discord.ext import commands

# --------------------------------------------------------------------------------
# JSON FILE-BASED OFFSET STORAGE
# --------------------------------------------------------------------------------
OFFSET_FILE = "user_offsets.json"

def load_offsets() -> Dict[str, List[int]]:
    """
    Load a JSON dict from user_offsets.json, format: { "user_id": [hours, minutes], ... }.
    """
    if not os.path.exists(OFFSET_FILE):
        return {}
    try:
        with open(OFFSET_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, IOError):
        return {}

def save_offsets(offsets: Dict[str, List[int]]):
    """
    Save the offsets dict to user_offsets.json.
    """
    with open(OFFSET_FILE, "w", encoding="utf-8") as f:
        json.dump(offsets, f)

def is_central_european_summer_time(dt: datetime) -> bool:
    year = dt.year
    march = datetime(year, 3, 31)
    last_sunday_march = march - timedelta(days=march.weekday() + 1)
    october = datetime(year, 10, 31)
    last_sunday_october = october - timedelta(days=october.weekday() + 1)
    return last_sunday_march < dt < last_sunday_october

async def get_user_offset(user_id: int) -> Optional[Tuple[int, int]]:
    """
    Return (hours, minutes) if found for the user, else None.
    """
    offsets = load_offsets()
    data = offsets.get(str(user_id))
    if data and len(data) == 2:
        return (data[0], data[1])
    return None

async def set_user_offset(user_id: int, hours: int, minutes: int):
    """
    Save the user's offset as [hours, minutes] in user_offsets.json.
    """
    offsets = load_offsets()
    offsets[str(user_id)] = [hours, minutes]
    save_offsets(offsets)

def get_corrected_offset_simple(hours: int, minutes: int) -> Tuple[int, int]:
    """
    EINFACHE LÖSUNG OHNE JSON-ÄNDERUNG:
    
    PROBLEM: Alle Offsets wurden in SOMMERZEIT gesetzt, aber jetzt ist WINTERZEIT!
    
    Europa: UTC+2 (Sommer) → UTC+1 (Winter) = -1 Stunde
    USA West: UTC-7 (Sommer PDT) → UTC-8 (Winter PST) = -1 Stunde
    USA Ost: UTC-4 (Sommer EDT) → UTC-5 (Winter EST) = -1 Stunde
    
    Lösung: Wenn JETZT Winterzeit ist → ALLE Offsets -1 Stunde!
    """
    utc_now = datetime.utcnow()
    
    # Prüfe ob JETZT Winterzeit in Europa ist (gilt global als Referenz)
    approx_european = utc_now + timedelta(hours=1)  # UTC+1 als Basis
    is_now_dst = is_central_european_summer_time(approx_european)
    
    if not is_now_dst:  # JETZT ist Winterzeit
        # ALLE Offsets wurden in Sommerzeit gesetzt → -1 Stunde
        # Europa: UTC+2 → UTC+1
        # USA West: UTC-7 → UTC-8  
        # USA Ost: UTC-4 → UTC-5
        return hours - 1, minutes
    
    return hours, minutes

# --------------------------------------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------------------------------------
def build_now_with_offset(hours: int, minutes: int) -> datetime:
    """Return 'local now' by adding (hours, minutes) to UTC now."""
    utc_now = datetime.utcnow()
    return utc_now + timedelta(hours=hours, minutes=minutes)

def format_local_time(hours: int, minutes: int) -> str:
    """Return current local time (MM-DD HH:MM) using the given offset."""
    local_now = build_now_with_offset(hours, minutes)
    return local_now.strftime("%m-%d %H:%M")

def build_select_menu_option(hours: int, minutes: int) -> discord.SelectOption:
    """
    Creates a select-menu option labeled with date/time in both 24h and 12h format.
    The option's value is "hours_minutes".
    """
    local_now = build_now_with_offset(hours, minutes)
    label_24h = local_now.strftime("%H:%M")
    label_12h = local_now.strftime("%I:%M%p")
    label_date = local_now.strftime("%m-%d")
    label = f"{label_date}  |  {label_24h} or {label_12h}"
    value = f"{hours}_{minutes}"
    return discord.SelectOption(label=label, value=value)

# Negative offsets (UTC–X)
NEGATIVE_OFFSETS = [
    (-12, 0), (-11, 0), (-10, 0), (-9, -30), (-9, 0), (-8, 0),
    (-7, 0), (-6, 0), (-5, 0), (-4, 0), (-3, -30), (-3, 0),
    (-2, 0), (-1, 0), (0, 0),
]

# Positive offsets (UTC+X)
POSITIVE_OFFSETS = [
    (0, 0), (1, 0), (2, 0), (3, 0), (3, 30), (4, 0), (4, 30),
    (5, 0), (5, 30), (5, 45), (6, 0), (6, 30), (7, 0),
    (8, 0), (8, 45), (9, 0), (9, 30), (10, 0), (10, 30),
    (11, 0), (12, 0), (12, 45), (13, 0), (14, 0),
]

# --------------------------------------------------------------------------------
# SELECT MENUS
# --------------------------------------------------------------------------------
class UTCMinusSelect(discord.ui.Select):
    """Dropdown of negative offsets (UTC–X)."""
    def __init__(self):
        options = [build_select_menu_option(h, m) for (h, m) in NEGATIVE_OFFSETS]
        super().__init__(
            placeholder="Select your local time (UTC-X)",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="timestamp-offset_UTC-X"
        )

    async def callback(self, interaction):
        raw = self.values[0]
        hours_str, minutes_str = raw.split("_", 1)
        hours, minutes = int(hours_str), int(minutes_str)
        await set_user_offset(interaction.user.id, hours, minutes)
        await interaction.response.send_message(
            f"Offset set to UTC{hours:+d}:{minutes:02d}.", ephemeral=True
        )

class UTCPlusSelect(discord.ui.Select):
    """Dropdown of positive offsets (UTC+X)."""
    def __init__(self):
        options = [build_select_menu_option(h, m) for (h, m) in POSITIVE_OFFSETS]
        super().__init__(
            placeholder="Select your local time (UTC+X)",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="timestamp-offset_UTC+X"
        )

    async def callback(self, interaction):
        raw = self.values[0]
        hours_str, minutes_str = raw.split("_", 1)
        hours, minutes = int(hours_str), int(minutes_str)
        await set_user_offset(interaction.user.id, hours, minutes)
        await interaction.response.send_message(
            f"Offset set to UTC{hours:+d}:{minutes:02d}.", ephemeral=True
        )

class TimeOffsetView(discord.ui.View):
    """A view containing both select menus."""
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(UTCMinusSelect())
        self.add_item(UTCPlusSelect())

# --------------------------------------------------------------------------------
# COG
# --------------------------------------------------------------------------------
class TimestampCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setting_time_offset", description="Select your local timezone.")
    async def setting_time_offset(self, interaction):
        """
        Opens a dialogue with dropdowns for selecting your local timezone.
        Stores the chosen offset in user_offsets.json.
        """
        user_offset = await get_user_offset(interaction.user.id)
        if user_offset is not None:
            hours, minutes = user_offset
            # Korrigiere für DST wenn nötig
            corrected_hours, corrected_minutes = get_corrected_offset_simple(hours, minutes)
            local_now_str = format_local_time(corrected_hours, corrected_minutes)
            content = (
                f"Your current setting is UTC{hours:+d}:{minutes:02d}, which implies local time is **{local_now_str}** now.\n\n"
                "If that's wrong, pick your correct local time below."
            )
        else:
            content = (
                "You haven't set an offset yet. It's assumed UTC+0.\n\n"
                "Pick your local time below to change it."
            )
        view = TimeOffsetView()
        await interaction.response.send_message(content=content, view=view, ephemeral=True)

# The issue is in the timestamp function. Here's the fixed version:

    @app_commands.command(name="timestamp", description="Create a timestamp that shows your chosen local time as a Discord timestamp.")
    @app_commands.describe(
        minute="Which minute? (0-59). Defaults to your local 'now'.",
        hour="Which hour (0-23)? Defaults to your local 'now'.",
        day="Which day (1-31)? Defaults to your local 'now'.",
        month="Which month (1-12)? Defaults to your local 'now'.",
        year="Which year? Defaults to your local 'now'."
    )
    async def timestamp(
        self,
        interaction,
        minute: Optional[int] = None,
        hour: Optional[int] = None,
        day: Optional[int] = None,
        month: Optional[int] = None,
        year: Optional[int] = None
    ):
        """
        Creates a Discord timestamp for the specified local time.
        This timestamp will display correctly for all users in their respective timezones.
        """
        await interaction.response.defer(thinking=True)
        user_offset = await get_user_offset(interaction.user.id)
        if user_offset is None:
            utc_now = datetime.utcnow()
            default_year = utc_now.year
            default_month = utc_now.month
            default_day = utc_now.day
            default_hour = utc_now.hour
            default_minute = utc_now.minute
            hint = (
                "You haven't set your time offset yet! Using UTC for now.\n"
                f"Right now, **UTC** is {utc_now.strftime('%Y-%m-%d %H:%M')}.\n"
                "Use `/setting_time_offset` to fix this."
            )
            await interaction.followup.send(hint)
            offset_hours, offset_minutes = 0, 0
        else:
            offset_hours, offset_minutes = user_offset
            # Automatische DST-Korrektur - keine JSON-Änderung!
            corrected_hours, corrected_minutes = get_corrected_offset_simple(offset_hours, offset_minutes)
            local_now = build_now_with_offset(corrected_hours, corrected_minutes)
            default_year = local_now.year
            default_month = local_now.month
            default_day = local_now.day
            default_hour = local_now.hour
            default_minute = local_now.minute
            # Verwende den korrigierten Offset für die Berechnung
            offset_hours, offset_minutes = corrected_hours, corrected_minutes

        final_year = year if year is not None else default_year
        final_month = month if month is not None else default_month
        final_day = day if day is not None else default_day
        final_hour = hour if hour is not None else default_hour
        final_minute = minute if minute is not None else default_minute

        try:
            # COMPLETELY SIMPLIFIED SOLUTION: Work directly with UTC

            # Step 1: Create the user's local datetime
            local_dt = datetime(final_year, final_month, final_day, final_hour, final_minute, 0)
            # Step 2: Convert this to UTC by subtracting the user's offset
            utc_dt = local_dt - timedelta(hours=offset_hours, minutes=offset_minutes)

            # Step 3: Convert UTC datetime to Unix timestamp
            # We'll use a method that doesn't depend on system timezone
            unix_ts = int((utc_dt - datetime(1970, 1, 1)).total_seconds())

            # For debugging
            utc_display = utc_dt.strftime('%Y-%m-%d %H:%M')
            local_display = local_dt.strftime('%Y-%m-%d %H:%M')

            # Add detailed debug info
            debug_info = (
                f"Debug:\n"
                f"- User's local time: {local_display}\n"
                f"- Corresponding UTC time: {utc_display}\n"
                f"- User offset: UTC{offset_hours:+d}:{offset_minutes:02d}\n"
                f"- Final Unix timestamp: {unix_ts}\n"
            )

        except ValueError as e:
            await interaction.followup.send(f"Invalid date/time: {e}")
            return

        formatted_local_time = local_dt.strftime("%Y-%m-%d %H:%M")

        result_str = (
            f"<t:{unix_ts}:f> (<t:{unix_ts}:R>)\n"
            f"```<t:{unix_ts}:f> (<t:{unix_ts}:R>)```"
        )
        await interaction.followup.send(result_str)
    
# Standard async setup function for discord.py cogs.
async def setup(bot: commands.Bot):
    await bot.add_cog(TimestampCommands(bot))