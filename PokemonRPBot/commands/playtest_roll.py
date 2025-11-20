import discord
from discord import app_commands
from discord.ext import commands
from helpers import ParsedRollQuery
import random

def count_successes_from_result(result_text):
    import re
    match = re.search(r"\*\*(\d+)\*\* Success", result_text)
    return int(match.group(1)) if match else 0

def format_accuracy_result(acc_result, raw_successes, accuracy_mod):
    if accuracy_mod != 0:
        base_line = acc_result.split("\n")[0]
        dice_line = acc_result.split("\n")[1] if "\n" in acc_result else ""
        mod_line = f" **{accuracy_mod:+d}** Accuracy "
        final_successes = max(0, raw_successes + accuracy_mod)
        final_line = f"= **{final_successes}** Successes."
        extra = "\n".join(acc_result.split("\n")[2:]) if "\n" in acc_result else ""
        return f"{base_line}\n{dice_line}{mod_line}{final_line}" + (f"\n{extra}" if extra else "")
    else:
        return acc_result

def crit_roll_d100(crit_chance_percent):
    roll = random.randint(1, 100)
    is_crit = roll <= crit_chance_percent
    return roll, is_crit

def build_crit_line_for_initial(crit_roll_number, was_crit, crit_chance, final_damage=None):
    line = f"**Crit Roll:** 1d100 → {crit_roll_number} (crits on {crit_chance} or lower)"
    if was_crit:
        line += "\n**CRIT!**"
        if final_damage is not None:
            line += f"\nUse ```/crit damage:{final_damage}``` and fill out the other parameters to determine the damage."
    return line

def build_crit_line_for_reroll(final_successes):
    return f"Use ```/crit damage:{final_successes}``` and fill out the other parameters to determine the damage."

async def crit_ability_autocomplete(interaction: discord.Interaction, current: str):
    options = ["No", "Yes"]
    return [
        app_commands.Choice(name=option, value=option)
        for option in options if current.lower() in option.lower()
    ]

async def crit_modifier_autocomplete(interaction: discord.Interaction, current: str):
    options = [str(i) for i in range(0, 11)]
    return [
        app_commands.Choice(name=opt, value=int(opt))
        for opt in options if current in opt
    ]

class Roll2View(discord.ui.View):
    def __init__(
        self,
        acc_query_str,
        dmg_query_str,
        interaction_user,
        acc_successes,
        original_miss,
        accuracy_mod,
        crit_roll_number,
        was_crit,
        crit_chance,
        final_damage
    ):
        super().__init__(timeout=None)
        self.acc_query_str = acc_query_str
        self.dmg_query_str = dmg_query_str
        self.interaction_user = interaction_user
        self.rerolled = False
        self.acc_successes = acc_successes
        self.original_miss = original_miss
        self.accuracy_mod = accuracy_mod
        self.crit_roll_number = crit_roll_number
        self.was_crit = was_crit
        self.crit_chance = crit_chance
        self.final_damage = final_damage
        if not dmg_query_str or dmg_query_str.strip() == "":
            self.children[1].disabled = True
        if acc_successes == 0:
            self.children[1].disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.interaction_user:
            await interaction.response.send_message(
                "Only the original roller can reroll!",
                ephemeral=True
            )
            return False
        if self.rerolled:
            await interaction.response.send_message(
                "You can only reroll once.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Reroll Accuracy", style=discord.ButtonStyle.primary, custom_id="reroll_accuracy")
    async def reroll_accuracy(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.rerolled = True
        acc_query = ParsedRollQuery.from_query(self.acc_query_str)
        acc_result = acc_query.execute()
        raw_successes = count_successes_from_result(acc_result)
        final_successes = max(0, raw_successes + self.accuracy_mod)

        for child in self.children:
            child.disabled = True
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass

        if final_successes == 0:
            content = f"{format_accuracy_result(acc_result, raw_successes, self.accuracy_mod)}\n\n**Miss!**"
            await interaction.response.send_message(content=content, ephemeral=False)
        else:
            if self.original_miss:
                dmg_result = ParsedRollQuery.from_query(self.dmg_query_str).execute() if self.dmg_query_str else None
                content = (
                    f"**Accuracy Roll:**\n{format_accuracy_result(acc_result, raw_successes, self.accuracy_mod)}\n\n"
                    f"**Hit!**\n\n"
                )
                if dmg_result:
                    content += f"**Damage Roll:**\n{dmg_result}\n\n"
                    if self.was_crit:
                        from re import search
                        match = search(r"\*\*(\d+)\*\* Success", dmg_result)
                        final_successes = match.group(1) if match else "?"
                        if final_successes != "?":
                            content += build_crit_line_for_reroll(final_successes)
                await interaction.response.send_message(content=content.strip(), ephemeral=False)
            else:
                content = (
                    f"**Accuracy Roll:**\n{format_accuracy_result(acc_result, raw_successes, self.accuracy_mod)}\n\n"
                    f"**Hit!**\n\n"
                )
                await interaction.response.send_message(content=content, ephemeral=False)

    @discord.ui.button(label="Reroll Damage", style=discord.ButtonStyle.danger, custom_id="reroll_damage")
    async def reroll_damage(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.rerolled = True
        dmg_result = ParsedRollQuery.from_query(self.dmg_query_str).execute()
        for child in self.children:
            child.disabled = True
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass
        content = f"**Damage Roll:**\n{dmg_result}"
        await interaction.response.send_message(content=content, ephemeral=False)

class PlaytestRoll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="playtest_roll",
        description="Roll accuracy, damage, and crit (playtest rules)."
    )
    @app_commands.describe(
        accuracy="Dice roll for accuracy, e.g. '2d6+1'",
        damage="Dice roll for damage, e.g. '3d8' (use 0 for status moves)",
        accuracy_mod="Accuracy modifier (e.g. -1 or 2).",
        crit_modifier="Crit modifier (default 2)",
        crit_ability="Does the mon have a crit-enhancing ability?"
    )
    @app_commands.autocomplete(
        crit_ability=crit_ability_autocomplete,
        crit_modifier=crit_modifier_autocomplete
    )
    async def playtest_roll(
        self,
        interaction: discord.Interaction,
        accuracy: str,
        damage: str,
        accuracy_mod: int = 0,
        crit_modifier: int = 2,
        crit_ability: str = "No"
    ):
        # Roll accuracy
        acc_query = ParsedRollQuery.from_query(accuracy)
        acc_result = acc_query.execute()
        raw_successes = count_successes_from_result(acc_result)
        final_successes = max(0, raw_successes + accuracy_mod)
        
        acc_query_str = acc_query.as_button_callback_query_string()
        damage_clean = damage.replace(" ", "").lower()
        no_damage = (
            damage_clean in ("0", "0d", "0d6", "0d8", "")
            or damage_clean.startswith("0d")
        )

        dmg_result = None
        final_damage = 0

        # Playtest Crit Calculation
        effective_crit_modifier = crit_modifier
        base_crit_chance = 30 if crit_ability.lower() == "yes" else 15
        excess_successes = max(0, final_successes - 1)
        crit_chance = base_crit_chance + (excess_successes * effective_crit_modifier)
        crit_chance = min(100, crit_chance)  # Cap at 100%

        # Single d100 crit roll
        crit_roll_number, was_crit = crit_roll_d100(crit_chance)

        if final_successes == 0:
            content = f"{format_accuracy_result(acc_result, raw_successes, accuracy_mod)}\n\n**Miss!**"
            original_miss = True
        else:
            if not no_damage:
                dmg_query = ParsedRollQuery.from_query(damage)
                dmg_result = dmg_query.execute()
                dmg_successes = count_successes_from_result(dmg_result)
                final_damage = dmg_successes

                content = (
                    f"**Accuracy Roll:**\n{format_accuracy_result(acc_result, raw_successes, accuracy_mod)}\n\n"
                    f"**Hit!**\n\n"
                    f"**Damage Roll:**\n{dmg_result}\n\n"
                    f"**Final Damage:**\n{final_damage}"
                )
            else:
                content = (
                    f"**Accuracy Roll:**\n{format_accuracy_result(acc_result, raw_successes, accuracy_mod)}\n\n"
                    f"**Hit!**"
                )
            original_miss = False

        # Always show crit info
        content += (
            f"\n\n{build_crit_line_for_initial(crit_roll_number, was_crit, crit_chance, final_damage if was_crit else None)}"
            f"\n**Crit Chance:** {crit_chance}% (Base {base_crit_chance}% + {excess_successes} × {effective_crit_modifier})"
        )

        view = Roll2View(
            acc_query_str,
            damage if not no_damage else "",
            interaction.user,
            final_successes,
            original_miss,
            accuracy_mod,
            crit_roll_number,
            was_crit,
            crit_chance,
            final_damage
        )
        await interaction.response.send_message(content=content.strip(), view=view)

async def setup(bot):
    await bot.add_cog(PlaytestRoll(bot))
