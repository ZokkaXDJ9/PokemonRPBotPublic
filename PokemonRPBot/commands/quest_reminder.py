import re
import json
import os
from time import time
from typing import Optional, List, Dict

import discord
from discord import app_commands
from discord.ext import commands, tasks

REMINDERS_FILE = "quest_reminders.json"

class ReminderCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminders: List[Dict] = []
        self._load_reminders()
        self.check_reminders.start()

    def _load_reminders(self):
        if os.path.exists(REMINDERS_FILE):
            try:
                with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.reminders = data
            except Exception:
                self.reminders = []
        else:
            self.reminders = []

    def _save_reminders(self):
        os.makedirs(os.path.dirname(REMINDERS_FILE) or ".", exist_ok=True)
        with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.reminders, f, ensure_ascii=False, indent=2)

    @tasks.loop(seconds=30.0)
    async def check_reminders(self):
        now_ts = int(time())
        to_fire = [r for r in self.reminders if r["remind_ts"] <= now_ts]
        for rem in to_fire:
            chan = self.bot.get_channel(rem["channel_id"])
            if chan:
                await chan.send(f"{rem['mentions']} {rem['reminder_name']} reminder!")
            self.reminders.remove(rem)
        if to_fire:
            self._save_reminders()

    @check_reminders.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="quest_reminder",
        description="Remind players about your quest."
    )
    @app_commands.describe(
        timestamp="Discord timestamp (e.g. <t:1747090500:f>) or raw Unix seconds",
        reminder1="First reminder (required)",
        user1="User to ping",
        reminder2="Second reminder (optional)",
        reminder3="Third reminder (optional)",
        user2="Second user to ping (optional)",
        user3="Third user to ping (optional)",
        user4="Fourth user to ping (optional)",
        user5="Fifth user to ping (optional)"
    )
    @app_commands.choices(
        reminder1=[
            app_commands.Choice(name="24 hours", value=86400),
            app_commands.Choice(name="12 hours", value=43200),
            app_commands.Choice(name="6 hours", value=21600),
            app_commands.Choice(name="1 hour", value=3600),
        ],
        reminder2=[
            app_commands.Choice(name="24 hours", value=86400),
            app_commands.Choice(name="12 hours", value=43200),
            app_commands.Choice(name="6 hours", value=21600),
            app_commands.Choice(name="1 hour", value=3600),
        ],
        reminder3=[
            app_commands.Choice(name="24 hours", value=86400),
            app_commands.Choice(name="12 hours", value=43200),
            app_commands.Choice(name="6 hours", value=21600),
            app_commands.Choice(name="1 hour", value=3600),
        ],
    )
    async def reminder(
        self,
        interaction: discord.Interaction,
        timestamp: str,
        reminder1: app_commands.Choice[int],
        user1: discord.User,
        reminder2: Optional[app_commands.Choice[int]] = None,
        reminder3: Optional[app_commands.Choice[int]] = None,
        user2: Optional[discord.User] = None,
        user3: Optional[discord.User] = None,
        user4: Optional[discord.User] = None,
        user5: Optional[discord.User] = None,
    ):
        await interaction.response.defer(thinking=True)

        # 1) Parse the Unix seconds
        m = re.search(r"(\d{9,})", timestamp)
        if not m:
            return await interaction.followup.send(
                "Could not parse a valid timestamp.", ephemeral=True
            )
        event_ts = int(m.group(1))

        # 2) Collect and dedupe reminders
        choices = [reminder1]
        if reminder2 and reminder2.value != reminder1.value:
            choices.append(reminder2)
        if reminder3 and reminder3.value not in {c.value for c in choices}:
            choices.append(reminder3)

        # 3) Build mention string
        users = [u for u in (user1, user2, user3, user4, user5) if u]
        mention_str = " ".join(u.mention for u in users)
        if not mention_str:
            return await interaction.followup.send(
                "Please mention at least one user.", ephemeral=True
            )

        # 4) Schedule each
        now_ts = int(time())
        ping_info = []
        for c in choices:
            rem_ts = event_ts - c.value
            if rem_ts <= now_ts:
                continue
            self.reminders.append({
                "remind_ts": rem_ts,
                "channel_id": interaction.channel_id,
                "mentions": mention_str,
                "reminder_name": c.name
            })
            ping_info.append((c.name, rem_ts))

        if ping_info:
            self._save_reminders()
        else:
            return await interaction.followup.send(
                "All chosen reminders are in the past; nothing scheduled.", ephemeral=True
            )

        # 5) Confirm
        lines = [f"• Quest: <t:{event_ts}:f>"]
        for name, ts in ping_info:
            lines.append(f"• {name} ping: <t:{ts}:f>")
        await interaction.followup.send(
            "Scheduled reminders:\n" + "\n".join(lines),
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(ReminderCog(bot))
