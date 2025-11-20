import random
import discord
from discord.ext import commands
from discord import app_commands

from helpers import ParsedRollQuery

DEFAULT_CRIT_DIE_COUNT = 3

ALL_HIT_COMMENTARY = [
    "Boom! Right on the money!",
    "That hit like a truck full of determination!",
    "No mercy, no misses — just pure power!",
    "Everything connected — and then some!",
    "An absolute textbook strike!",
    "That one echoed through the arena!",
    "A flawless execution!",
    "That’s gotta sting!",
    "Did you see the form on that hit?",
    "Maximum efficiency, maximum pain!",
    "All power, all precision!",
    "A beautiful example of doing everything right!",
    "That hit was art. Violent art.",
    "A picture-perfect strike!",
    "Critical technique, zero hesitation!",
    "Direct hit! Devastation confirmed!",
    "No wasted motion — just results.",
    "That one’s going in the highlight reel!",
    "An absolute home run!",
    "Full marks for pain delivery!",
    "Bang! Everything hit like a dream.",
    "They brought the pain. And then brought more.",
    "One clean strike — total devastation!",
    "Damage dice? More like damage destiny.",
    "That opponent felt all of it.",
    "When they land it, they really land it.",
    "If that’s not power, I don’t know what is.",
    "They hit with the force of storytelling momentum!",
    "No hesitation, no forgiveness.",
    "Who gave them permission to hit that hard?",
    "It was as if the universe wanted that hit to land.",
    "Their opponent is questioning life choices.",
    "Absolutely obliterated!",
    "That was just... disrespectfully effective.",
    "A demolition in one strike!",
    "Ten out of ten — from every angle.",
    "Ruthless. Precise. Beautiful.",
    "A jaw-dropper of a hit!",
    "You could hear that from the next region.",
    "An attack worthy of a championship belt.",
    "That one broke the sound barrier.",
    "Delivered with love... and incredible force.",
    "Total commitment. Total damage.",
    "They didn't just hit — they made a statement.",
    "They made the battlefield their canvas.",
    "That was the move they practiced all week.",
    "Their opponent’s soul left the building.",
    "One hit. All heart.",
    "Perfect timing, perfect strike.",
    "They hit the sweet spot so hard it cracked.",
    "Someone’s going to feel that tomorrow — and next week.",
]
ZERO_DAMAGE_COMMENTARY = [
    "That hit looked way cooler than it felt.",
    "Made contact, did nothing.",
    "It's like a handshake. With dramatic flair.",
    "A friendly reminder, not a threat.",
    "It technically hit, yes.",
    "That was a very polite attack.",
    "Their opponent barely blinked.",
    "All sizzle, no steak.",
    "Damage output: theatrical, but ineffective.",
    "Hit confirmed. Impact denied.",
    "That did more to the air than the target.",
    "That was more of a statement than an attack.",
    "They grazed their opponent’s confidence, maybe.",
    "It was like a warning shot. But worse.",
    "They touched victory... and immediately let go.",
    "They dealt zero damage and zero dignity.",
    "That hit will echo forever... in embarrassment.",
    "Their opponent is confused but unharmed.",
    "No damage, but so much effort!",
    "Could’ve been something. Wasn’t.",
    "That was an emotional tap, not a real one.",
    "I think their opponent just shrugged it off.",
    "Well, they made their point. Sort of.",
    "Like being hit with a rolled-up napkin.",
    "Even the referee winced... from awkwardness.",
    "That hit was legally classified as 'gentle'.",
    "Perfect aim. Pathetic damage.",
    "Technically correct — the worst kind of correct.",
    "They hit them like a wet leaf.",
    "A dramatic flourish with no follow-through.",
    "They tried to hurt them. The universe said no.",
    "One strike. Zero impact.",
    "All that effort for a friendly tap.",
    "That did more to their own confidence.",
    "Even the target looked surprised to be untouched.",
    "Like punching a memory foam mattress.",
    "That was basically a high five.",
    "They hit with the intensity of a lullaby.",
    "The air moved more than the target did.",
    "Just a soft little nudge of failure.",
    "That hit landed... emotionally.",
    "A glancing blow on the opponent's patience.",
    "Like blowing a raspberry in combat.",
    "Definitely not worth the energy cost.",
    "Even the damage dice are embarrassed.",
    "At least they practiced the motion.",
    "If disappointment were a stat, it's maxed out.",
    "A good swing. A better letdown.",
    "The target barely noticed the breeze.",
    "Maybe next time try hurting them?",
    "That hit was the nicest thing they’ve ever done in battle.",
]
COMPLETE_MISS_COMMENTARY = [
    "Oof — not even close!",
    "They just attacked the idea of the target.",
    "A masterclass in missing.",
    "The only thing they hit was their pride.",
    "That was... aspirational.",
    "Air got obliterated. The opponent? Not so much.",
    "Someone’s going to pretend that was intentional.",
    "That target was in a different timezone.",
    "Their opponent didn’t even blink.",
    "Even gravity dodged that one.",
    "That was a warning shot. Hopefully.",
    "They attacked the memory of the opponent.",
    "An aggressive display of spatial misunderstanding.",
    "A truly strategic use of failure.",
    "New Olympic event: synchronized whiffing!",
    "If you don’t hit, you can’t miss... oh wait.",
    "They aimed with their soul. Unfortunately.",
    "The ghost of that move might haunt someone someday.",
    "Nowhere near. But very confidently so.",
    "A flawless display of bad luck.",
    "The floor took a lot of damage. The target? Not so much.",
    "That was like yelling into the void — but with effort.",
    "Worthy of mockery!",
    "It was an attack. It just wasn’t a good one.",
    "They've mastered the art of missing with style.",
    "A swing, a spin, a total fail!",
    "Was that a feint? No? Just a miss? Okay.",
    "They had one job.",
    "Even their shadow is shaking its head.",
    "I've seen better aim from a fellow Magikarp!",
    "That was less an attack, more a motion.",
    "Wind resistance: 1. Accuracy: 0.",
    "They missed and emotionally damaged the audience.",
    "That strike is now in orbit.",
    "Someone just facepalmed.",
    "An elegant miss, if nothing else.",
    "The attack landed in an alternate dimension.",
    "They used Foresight... but forgot to hit.",
    "That wasn’t a move — that was wishful thinking.",
    "They missed so hard it created a gust.",
    "Nobody knows what they were aiming at.",
    "Their Pokémon looked proud... but why?",
    "The opponent politely applauded the attempt.",
    "If you miss with flair, does it count?",
    "The miss was so clean it deserves a replay.",
    "They wrote a love letter to failure.",
    "That attack had commitment, just no accuracy.",
    "They boldly struck nothing at all.",
    "It looked cool. Shame about the result.",
    "It missed, but the drama was top tier.",
]

def append_random_mockery(message: list, commentary: list):
    mockery = random.choice(commentary)
    message.append(f"*{mockery}*")

def append_status_effect_roll(status_effect_dice, prefix, roll_number_string, message: list):
    if status_effect_dice is None or status_effect_dice == 0:
        return
    query = ParsedRollQuery(status_effect_dice)
    status_roll_result = query.execute()
    dice_line, successes_line = split_dice_and_successes(status_roll_result)
    if successes_line:
        message.append(
            f"{prefix}**Status Effect {roll_number_string}roll**: {dice_line} – {successes_line}"
        )
    else:
        message.append(
            f"{prefix}**Status Effect {roll_number_string}roll**: {dice_line}"
        )

def append_crit_stat_if_changed(message: list, crit_6_count):
    if crit_6_count != DEFAULT_CRIT_DIE_COUNT:
        message.append(f"-# **[Changed: Crit on {crit_6_count}x 6's]**")

def split_dice_and_successes(roll_result_string):
    # Split classic helpers.py result into (dice_line, successes_line)
    parts = roll_result_string.strip().split("\n", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    else:
        return parts[0], ""

def get_success_count(successes_line):
    import re
    m = re.search(r"\*\*(\d+)\*\*", successes_line)
    return int(m.group(1)) if m else 0

class AttackRollCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="attack_roll",
        description="Quickly get the results for attack actions."
    )
    @app_commands.describe(
        accuracy_dice="How many accuracy dice should be rolled?",
        damage_dice="How many damage dice should be rolled?",
        crit_6_count="How many 6's are required to crit.",
        status_effect_dice="How many status effect dice should be rolled?",
        status_effect_dice_2="How many status effect dice should be rolled for a second status effect?",
        accuracy_reduction="Add an accuracy reduction (defaults to 0).",
    )
    async def attack_roll(
        self,
        interaction: discord.Interaction,
        accuracy_dice: app_commands.Range[int, 1, 40],
        damage_dice: app_commands.Range[int, 0, 40],
        crit_6_count: app_commands.Range[int, 0, 5] = None,
        status_effect_dice: app_commands.Range[int, 0, 5] = None,
        status_effect_dice_2: app_commands.Range[int, 0, 5] = None,
        accuracy_reduction: app_commands.Range[int, 0, 10] = 0,
    ):
        await interaction.response.defer(thinking=True)

        required_accuracy = 1 + (accuracy_reduction or 0)
        crit_6_count = crit_6_count if crit_6_count is not None else DEFAULT_CRIT_DIE_COUNT

        # Store all roll parameters for rerolling
        roll_params = {
            "accuracy_dice": accuracy_dice,
            "damage_dice": damage_dice,
            "crit_6_count": crit_6_count,
            "status_effect_dice": status_effect_dice,
            "status_effect_dice_2": status_effect_dice_2,
            "accuracy_reduction": accuracy_reduction,
        }

        # Compose the message and buttons
        message_lines, view = self._compose_attack_roll_message_and_view(roll_params)
        await interaction.followup.send('\n'.join(message_lines), view=view)


    def _compose_attack_roll_message_and_view(self, roll_params, previous_results=None, reroll_type=None, reroll_view=False):
        accuracy_dice = roll_params["accuracy_dice"]
        damage_dice = roll_params["damage_dice"]
        crit_6_count = roll_params["crit_6_count"]
        status_effect_dice = roll_params["status_effect_dice"]
        status_effect_dice_2 = roll_params["status_effect_dice_2"]
        accuracy_reduction = roll_params["accuracy_reduction"]
        required_accuracy = 1 + (accuracy_reduction or 0)

        if reroll_view and reroll_type == "accuracy":
            message_lines = ["### Reroll — Accuracy"]
            accuracy_query = ParsedRollQuery(accuracy_dice, crit_6_count=crit_6_count)
            accuracy_roll_result = accuracy_query.execute()
            dice_line, successes_line = split_dice_and_successes(accuracy_roll_result)
            success_count = get_success_count(successes_line)
            message_lines.append(f"**Reroll Accuracy**: {dice_line} – {successes_line} ({required_accuracy} needed)")
            # Append accuracy commentary based on the new result
            if success_count < required_accuracy:
                append_random_mockery(message_lines, COMPLETE_MISS_COMMENTARY)
            prev_acc_success = None
            if previous_results is not None and "accuracy" in previous_results:
                prev_acc_success = get_success_count(split_dice_and_successes(previous_results.get("accuracy", ""))[1])
            # Only roll damage if original was miss (prev_acc_success < required_accuracy) and reroll is a hit (success_count >= required_accuracy)
            if prev_acc_success is not None and prev_acc_success < required_accuracy and success_count >= required_accuracy and damage_dice > 0:
                damage_query = ParsedRollQuery(damage_dice)
                damage_roll_result = damage_query.execute()
                dmg_dice_line, dmg_successes_line = split_dice_and_successes(damage_roll_result)
                message_lines.append(f"**Damage roll**: {dmg_dice_line} – {dmg_successes_line}")
                damage_success = get_success_count(dmg_successes_line)
                if damage_success == 0:
                    append_random_mockery(message_lines, ZERO_DAMAGE_COMMENTARY)
                elif damage_success == damage_dice:
                    append_random_mockery(message_lines, ALL_HIT_COMMENTARY)
            return message_lines, None
        elif reroll_view and reroll_type == "damage":
            damage_query = ParsedRollQuery(damage_dice)
            damage_roll_result = damage_query.execute()
            dmg_dice_line, dmg_successes_line = split_dice_and_successes(damage_roll_result)
            message_lines = [f"### Reroll — Damage", f"**Reroll Damage**: {dmg_dice_line} – {dmg_successes_line}"]
            damage_success = get_success_count(dmg_successes_line)
            if damage_success == 0:
                append_random_mockery(message_lines, ZERO_DAMAGE_COMMENTARY)
            elif damage_success == damage_dice:
                append_random_mockery(message_lines, ALL_HIT_COMMENTARY)
            return message_lines, None
        elif reroll_view and reroll_type == "status1":
            if status_effect_dice:
                status_query = ParsedRollQuery(status_effect_dice)
                status_roll_result = status_query.execute()
                dice_line, successes_line = split_dice_and_successes(status_roll_result)
                message_lines = [f"### Reroll — Status Effect", f"**Reroll Status Effect**: {dice_line} – {successes_line}"]
                return message_lines, None
        elif reroll_view and reroll_type == "status2":
            if status_effect_dice_2:
                status_query = ParsedRollQuery(status_effect_dice_2)
                status_roll_result = status_query.execute()
                dice_line, successes_line = split_dice_and_successes(status_roll_result)
                message_lines = [f"### Reroll — Status Effect #2", f"**Reroll Status Effect #2**: {dice_line} – {successes_line}"]
                return message_lines, None
        elif reroll_view and reroll_type == "status1":
            if status_effect_dice:
                status_query = ParsedRollQuery(status_effect_dice)
                status_roll_result = status_query.execute()
                dice_line, successes_line = split_dice_and_successes(status_roll_result)
                message_lines = [f"### Reroll", f"**Reroll Status Effect**: {dice_line} – {successes_line}"]
        elif reroll_view and reroll_type == "status2":
            if status_effect_dice_2:
                status_query = ParsedRollQuery(status_effect_dice_2)
                status_roll_result = status_query.execute()
                dice_line, successes_line = split_dice_and_successes(status_roll_result)
                message_lines = [f"### Reroll", f"**Reroll Status Effect #2**: {dice_line} – {successes_line}"]
        else:
            message_lines = []
            # ...existing code for normal roll...
            # --- Accuracy roll ---
            if previous_results and reroll_type != "accuracy":
                accuracy_roll_result = previous_results.get("accuracy")
            else:
                accuracy_query = ParsedRollQuery(accuracy_dice, crit_6_count=crit_6_count)
                accuracy_roll_result = accuracy_query.execute()
            dice_line, successes_line = split_dice_and_successes(accuracy_roll_result)
            success_count = get_success_count(successes_line)
            if required_accuracy > accuracy_dice:
                message_lines.append("### That'd be an instant-miss! Did you typo your accuracy dice?")
                return message_lines, None
            if successes_line:
                message_lines.append(f"**Accuracy roll**: {dice_line} – {successes_line} ({required_accuracy} needed)")
            else:
                message_lines.append(f"**Accuracy roll**: {dice_line} ({required_accuracy} needed)")
            if required_accuracy > success_count:
                append_random_mockery(message_lines, COMPLETE_MISS_COMMENTARY)
                view = AttackRollRerollView(roll_params, show_accuracy=True)
                return message_lines, view

        # --- Damage roll ---
        if damage_dice > 0:
            if previous_results and reroll_type != "damage":
                damage_roll_result = previous_results.get("damage")
            else:
                damage_query = ParsedRollQuery(damage_dice)
                damage_roll_result = damage_query.execute()
            dmg_dice_line, dmg_successes_line = split_dice_and_successes(damage_roll_result)
            damage_success = get_success_count(dmg_successes_line)
            maybe_crit = " (+CRIT)" if "(CRIT!)" in successes_line else ""
            if dmg_successes_line:
                message_lines.append(f"**Damage roll**: {dmg_dice_line} – {dmg_successes_line}{maybe_crit}")
            else:
                message_lines.append(f"**Damage roll**: {dmg_dice_line}{maybe_crit}")
            if damage_success == 0:
                append_random_mockery(message_lines, ZERO_DAMAGE_COMMENTARY)
            elif damage_dice > 0 and damage_success == damage_dice:
                append_random_mockery(message_lines, ALL_HIT_COMMENTARY)
        if previous_results and reroll_type != "status1":
            status1_result = previous_results.get("status1")
        else:
            status1_result = None
        if previous_results and reroll_type != "status2":
            status2_result = previous_results.get("status2")
        else:
            status2_result = None

        if status_effect_dice:
            if status1_result:
                dice_line, successes_line = split_dice_and_successes(status1_result)
                if successes_line:
                    message_lines.append(f"**Status Effect roll**: {dice_line} – {successes_line}")
                else:
                    message_lines.append(f"**Status Effect roll**: {dice_line}")
            else:
                append_status_effect_roll(status_effect_dice, "", "", message_lines)
        if status_effect_dice_2:
            if status2_result:
                dice_line, successes_line = split_dice_and_successes(status2_result)
                if successes_line:
                    message_lines.append(f"**Status Effect #2 roll**: {dice_line} – {successes_line}")
                else:
                    message_lines.append(f"**Status Effect #2 roll**: {dice_line}")
            else:
                append_status_effect_roll(status_effect_dice_2, "", "#2 ", message_lines)

        view = AttackRollRerollView(roll_params, show_accuracy=True, show_damage=damage_dice > 0, show_status1=status_effect_dice, show_status2=status_effect_dice_2)
        return message_lines, view


class AttackRollRerollView(discord.ui.View):
    def __init__(self, roll_params, show_accuracy=True, show_damage=False, show_status1=None, show_status2=None):
        # Increase timeout to 5 minutes to allow more time for rerolls
        super().__init__(timeout=300)
        self.roll_params = roll_params
        if show_accuracy:
            self.add_item(AttackRollRerollButton("accuracy", label="Reroll Accuracy", style=discord.ButtonStyle.primary))
        if show_damage:
            self.add_item(AttackRollRerollButton("damage", label="Reroll Damage", style=discord.ButtonStyle.danger))
        if show_status1:
            self.add_item(AttackRollRerollButton("status1", label="Reroll Status Effect", style=discord.ButtonStyle.success))
        if show_status2:
            self.add_item(AttackRollRerollButton("status2", label="Reroll Status Effect #2", style=discord.ButtonStyle.success))

class AttackRollRerollButton(discord.ui.Button):
    def __init__(self, reroll_type, label, style):
        super().__init__(label=label, style=style)
        self.reroll_type = reroll_type

    async def callback(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("AttackRollCog")
        params = dict(self.view.roll_params)
        previous_message = interaction.message.content or ""
        previous_results = {}
        import re

        # Parse visible lines and reconstruct a multiline raw-roll style string
        # that matches what ParsedRollQuery.execute() returns (dice_line\nsuccesses_line)
        for raw_line in previous_message.split('\n'):
            line = raw_line.strip()
            if not line:
                continue
            # Accuracy (matches both "**Accuracy roll**:" and "**Reroll Accuracy**:")
            m = re.match(r"^\*\*(?:Reroll\s+)?Accuracy(?:\s+roll)?\*\*:\s*(.+)$", line)
            if m:
                content = m.group(1).strip()
                if '–' in content:
                    left, right = content.split('–', 1)
                    previous_results["accuracy"] = f"{left.strip()}\n{right.strip()}"
                else:
                    previous_results["accuracy"] = content
                continue
            # Damage (matches both "**Damage roll**:" and "**Reroll Damage**:")
            m = re.match(r"^\*\*(?:Reroll\s+)?Damage(?:\s+roll)?\*\*:\s*(.+)$", line)
            if m:
                content = m.group(1).strip()
                if '–' in content:
                    left, right = content.split('–', 1)
                    previous_results["damage"] = f"{left.strip()}\n{right.strip()}"
                else:
                    previous_results["damage"] = content
                continue
            # Status Effect #2
            m = re.match(r"^\*\*(?:Reroll\s+)?Status Effect\s+#2\s*roll\*\*:\s*(.+)$", line)
            if m:
                content = m.group(1).strip()
                if '–' in content:
                    left, right = content.split('–', 1)
                    previous_results["status2"] = f"{left.strip()}\n{right.strip()}"
                else:
                    previous_results["status2"] = content
                continue
            # Status Effect (first)
            m = re.match(r"^\*\*(?:Reroll\s+)?Status Effect(?:\s+roll)?\*\*:\s*(.+)$", line)
            if m:
                content = m.group(1).strip()
                if '–' in content:
                    left, right = content.split('–', 1)
                    previous_results["status1"] = f"{left.strip()}\n{right.strip()}"
                else:
                    previous_results["status1"] = content
                continue
        message_lines, _ = cog._compose_attack_roll_message_and_view(
            params,
            previous_results=previous_results,
            reroll_type=self.reroll_type,
            reroll_view=True
        )
        await interaction.response.send_message('\n'.join(message_lines), ephemeral=False)

async def setup(bot):
    await bot.add_cog(AttackRollCog(bot))
