from __future__ import annotations

import asyncio
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import discord
from discord.ext import commands
from discord import app_commands


class GMTime(commands.Cog):
    """Cog providing GM time-tracking and currency-management slash commands."""

    # ───────────────────────── class-level constants ──────────────────────────
    EXP_PER_HOUR:    int = 4
    POKE_PER_HOUR:   int = 225
    CREDITS_PER_HOUR = 100

    DATA_DIR  = Path("Data")
    DATA_FILE = DATA_DIR / "gm_time.json"

    # ────────────────────────────── init / setup ──────────────────────────────
    def __init__(self, bot: commands.Bot):
        self.bot  = bot
        self.lock = asyncio.Lock()
        self.data: Dict[str, Dict[str, Any]] = {}
        self._ensure_data_file()
        self._load_data()

    # ───────────────────────────── helper view ────────────────────────────────
    class _ConfirmHoursView(discord.ui.View):
        """Two-button confirmation view for >12-hour entries, locked to author."""

        def __init__(
            self,
            cog: "GMTime",
            origin: discord.Interaction,
            hours: float,
            *,
            timeout: float | None = 60,
        ):
            super().__init__(timeout=timeout)
            self.cog        = cog
            self.origin     = origin         # original interaction
            self.hours      = hours
            self.author_id  = origin.user.id
            self.message: Optional[discord.Message] = None  # set after send

        # ----------- internal helpers -----------
        async def _not_author(self, interaction: discord.Interaction):
            """Reply (ephemeral) if someone else tries to press the buttons."""
            await interaction.response.send_message(
                "Sorry, only the GM who ran the command can use these buttons.",
                ephemeral=True,
            )

        # ----------- buttons -----------
        @discord.ui.button(label="Send it!", style=discord.ButtonStyle.green)
        async def _confirm(
            self,
            interaction: discord.Interaction,
            button: discord.ui.Button,
        ):
            if interaction.user.id != self.author_id:
                await self._not_author(interaction)
                return

            # compute & persist
            exp_gain     = math.ceil(self.hours * self.cog.EXP_PER_HOUR)
            poke_gain    = math.ceil(self.hours * self.cog.POKE_PER_HOUR)
            credits_gain = math.ceil(self.hours * self.cog.CREDITS_PER_HOUR)

            profile = self.cog._get_or_create_profile(self.author_id)
            profile["time"]    += self.hours
            profile["exp"]     += exp_gain
            profile["poke"]    += poke_gain
            profile["credits"] += credits_gain
            await self.cog._save_data()

            # acknowledge
            await interaction.response.defer()  # instant ack

            await self.message.edit(
                content=(
                    f"Stored **{self.hours:.2f}** h for "
                    f"{self.origin.user.display_name}.\n"
                    f"You gained **{exp_gain} Exp**, **{poke_gain} Poke** and "
                    f"**{credits_gain} Credits**."
                ),
                view=None,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            self.stop()

        @discord.ui.button(label="Ooops...", style=discord.ButtonStyle.red)
        async def _cancel(
            self,
            interaction: discord.Interaction,
            button: discord.ui.Button,
        ):
            if interaction.user.id != self.author_id:
                await self._not_author(interaction)
                return

            await interaction.response.defer()
            await self.message.edit(
                content="Entry cancelled – nothing was stored.",
                view=None,
            )
            self.stop()

    # ───────────────────────────── utilities ──────────────────────────────────
    @staticmethod
    def _parse_time_input(input_str: str) -> float:
        """Convert flexible time input to hours as float."""
        input_str = input_str.lower().strip().replace(",", ".")
        if re.fullmatch(r"\d+(?:\.\d+)?", input_str):
            return float(input_str)

        m = re.fullmatch(
            r"(?:(?P<hours>\d+(?:\.\d+)?)\s*h(?:ours?)?)?\s*"
            r"(?:(?P<minutes>\d+(?:\.\d+)?)\s*m(?:in(?:utes?)?)?)?$",
            input_str,
        )
        if not m:
            raise ValueError("Time format not recognised. Use a number or “xh ymin”.")

        hours   = float(m.group("hours") or 0)
        minutes = float(m.group("minutes") or 0)
        return hours + minutes / 60

    def _ensure_data_file(self) -> None:
        self.DATA_DIR.mkdir(exist_ok=True)
        if not self.DATA_FILE.exists():
            self.DATA_FILE.write_text("{}", encoding="utf-8")

    def _load_data(self) -> None:
        try:
            with self.DATA_FILE.open("r", encoding="utf-8") as fp:
                self.data = json.load(fp)
        except (IOError, json.JSONDecodeError):
            self.data = {}

    async def _save_data(self) -> None:
        async with self.lock:
            with self.DATA_FILE.open("w", encoding="utf-8") as fp:
                json.dump(self.data, fp, ensure_ascii=False, indent=4)

    def _get_or_create_profile(self, user_id: int) -> Dict[str, Any]:
        uid = str(user_id)
        if uid not in self.data:
            self.data[uid] = {"time": 0.0, "exp": 0, "poke": 0, "credits": 0}
        return self.data[uid]

    # ───────────────────────────── slash commands ─────────────────────────────
    @app_commands.guild_only()
    @app_commands.command(
        name="store_gm_time",
        description="Add GM hours and receive rewards.",
    )
    @app_commands.describe(
        time_input="Number of hours (e.g. 2.5) or “xh ymin” (e.g. 1h 30min)",
    )
    async def store_gm_time(self, interaction: discord.Interaction, time_input: str):
        # 1. parse
        try:
            hours = self._parse_time_input(time_input)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        if hours <= 0:
            await interaction.response.send_message("Hours must be greater than zero.", ephemeral=True)
            return

        # 2. confirm unusually large entries
        if hours > 12:
            view = GMTime._ConfirmHoursView(self, interaction, hours)
            await interaction.response.send_message(
                (
                    "Did you mean to put in **that many hours**?\n"
                    "This system is time-based now – no need to calculate anymore!"
                ),
                view=view,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            view.message = await interaction.original_response()
            # view handles everything else
            return

        # 3. compute rewards & persist (≤12 h path – no confirmation)
        exp_gain     = math.ceil(hours * self.EXP_PER_HOUR)
        poke_gain    = math.ceil(hours * self.POKE_PER_HOUR)
        credits_gain = math.ceil(hours * self.CREDITS_PER_HOUR)

        profile = self._get_or_create_profile(interaction.user.id)
        profile["time"]    += hours
        profile["exp"]     += exp_gain
        profile["poke"]    += poke_gain
        profile["credits"] += credits_gain
        await self._save_data()

        # 4. final acknowledgement
        await interaction.response.send_message(
            (
                f"Stored **{hours:.2f}** h for {interaction.user.display_name}.\n"
                f"You gained **{exp_gain} Exp**, **{poke_gain} Poke** and "
                f"**{credits_gain} Credits**."
            ),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    # ----------------------------- /gm_stats helpers --------------------------
    async def user_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete any guild member by display name (up to 25)."""
        guild = interaction.guild
        if not guild:
            return []

        current_lower = current.lower()
        choices: List[app_commands.Choice[str]] = []
        for member in guild.members:
            name = member.display_name
            if current_lower in name.lower():
                choices.append(app_commands.Choice(name=name, value=str(member.id)))
            if len(choices) >= 25:
                break
        return choices
    
    @app_commands.guild_only()
    @app_commands.command(name="gm_stats", description="Show a GM's statistics.")
    @app_commands.describe(member="Select a GM (optional, defaults to you)")
    @app_commands.autocomplete(member=user_autocomplete)
    async def gm_stats(self, interaction: discord.Interaction, member: Optional[str] = None):
        target_id = int(member) if member else interaction.user.id
        profile = self._get_or_create_profile(target_id)

        # Use display name only – no ping
        if interaction.guild:
            member_obj = interaction.guild.get_member(target_id)
            display_name = member_obj.display_name if member_obj else f"User ID {target_id}"
        else:
            display_name = f"User ID {target_id}"

        message = (
            f"## GM statistics for {display_name}\n"
            f"GM Time: **{profile['time']:.2f}** hours\n"
            f"GM Exp: **{profile['exp']}** (Please use /player_info to display the correct amount!)\n"
            f"GM Poke: **{profile['poke']}**\n"
            f"GM Credits: **{profile['credits']}**"
        )

        await interaction.response.send_message(message)

    # ------------------------------ spend commands ---------------------------
    @app_commands.guild_only()
    @app_commands.command(name="spend_gm_credits", description="Spend GM Credits from your wallet.")
    @app_commands.describe(amount="Amount of credits to spend")
    async def spend_gm_credits(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            await interaction.response.send_message("Amount must be positive.", ephemeral=True)
            return

        profile = self._get_or_create_profile(interaction.user.id)
        if profile["credits"] < amount:
            await interaction.response.send_message("You do not have enough GM Credits.", ephemeral=True)
            return

        profile["credits"] -= amount
        await self._save_data()
        await interaction.response.send_message(
            f"Spent **{amount}** GM Credits. You have **{profile['credits']}** left."
        )
    
    @app_commands.guild_only()
    @app_commands.command(name="spend_gm_poke", description="Spend GM Poke from your wallet.")
    @app_commands.describe(amount="Amount of Poke to spend")
    async def spend_gm_poke(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            await interaction.response.send_message("Amount must be positive.", ephemeral=True)
            return

        profile = self._get_or_create_profile(interaction.user.id)
        if profile["poke"] < amount:
            await interaction.response.send_message("You do not have enough GM Poke.", ephemeral=True)
            return

        profile["poke"] -= amount
        await self._save_data()
        await interaction.response.send_message(
            f"Spent **{amount}** GM Poke. You have **{profile['poke']}** left."
        )

    # ───────────────────────────── cog lifecycle ──────────────────────────────
    @commands.Cog.listener()
    async def on_ready(self):
        try:
            synced = await self.bot.tree.sync()
            print(f"[GMTime] Synced {len(synced)} commands.")
        except Exception as e:
            print(f"[GMTime] Failed to sync commands: {e!r}")


async def setup(bot: commands.Bot):
    """Standard entry point for `discord.ext.commands` extension loading."""
    await bot.add_cog(GMTime(bot))
