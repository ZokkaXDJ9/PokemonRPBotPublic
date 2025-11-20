import random
import math
import discord
from discord.ext import commands
from discord import app_commands

from helpers import ParsedRollQuery, DEFAULT_CRIT_DIE_COUNT

COMPLETE_MISS_COMMENTARY = [
    "Congratulations! You've just created a minor natural disaster — for fun!",
    "All that for nothing.",
    "That looked expensive... and pointless.",
    "A dramatic display of failure.",
    "Big move. Zero impact.",
    "They went all-in and got absolutely nothing.",
    "So much noise, so little result.",
    "It hit no one, but it sure looked cool!",
    "They just emptied the clip into the void.",
    "The only thing affected was the vibe.",
    "An impressive effort to scare the air molecules.",
    "That was basically a special effects test.",
    "They announced their presence. And nothing else.",
    "The opponents remain entirely unbothered.",
    "A bold move to miss everyone.",
    "An overcommitment to the art of missing.",
    "The arena's ears are ringing. That’s about it.",
    "They must’ve been aiming for future enemies.",
    "Who needs accuracy when you have spectacle?",
    "That was a cinematic failure.",
    "I think they just wanted attention.",
    "A big swing at absolutely no one.",
    "They activated a light show — not an attack.",
    "Did they mean to hit anyone, or...?",
    "A very convincing threat. Not much else.",
    "Spectacular. Useless. Memorable.",
    "The enemies dodged. Or maybe just stood still.",
    "Their intimidation stat is high. Their accuracy? Not so much.",
    "A full-power group miss!",
    "You could feel the effort. Just not the results.",
    "They really committed to disappointing everyone equally.",
    "A great way to clear the air... and nothing else.",
    "Not a single soul was touched.",
    "They missed so hard it looped back to impressive.",
    "That was like shouting in a crowd — dramatic, but ineffective.",
    "An inspired attempt to hit everything... except the targets.",
    "It echoed across the field... but that's all.",
    "Somewhere, a coach is rethinking their life choices.",
    "A masterclass in wasted potential.",
    "If the goal was to create suspense, mission accomplished.",
    "A full-area threat with none of the consequences.",
    "That move was heard around the world — and dodged by all of it.",
    "The power was real. The accuracy was theoretical.",
    "It felt important. It wasn’t.",
    "They just gave a TED Talk in the middle of a battle.",
    "A wide miss for wide audiences.",
    "Their opponents didn't even flinch.",
    "All that buildup... for that?",
    "They attacked the concept of enemies, not the actual ones.",
    "It’s hard to miss that much. Truly.",
    "The effort was massive. The failure was larger.",
    "Impressive in size. Legendary in futility.",
]

def append_random_mockery(message_lines, commentary_list):
    message_lines.append(f"*{random.choice(commentary_list)}*")

def split_dice_and_successes(roll_result_string):
    parts = roll_result_string.strip().split("\n", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    else:
        return parts[0], ""

def get_success_count(successes_line):
    import re
    m = re.search(r"\*\*(\d+)\*\*", successes_line)
    return int(m.group(1)) if m else 0

def is_crit(successes_line):
    # Detects "**(CRIT)**" (or similar) in the line
    return "(CRIT" in successes_line or "CRIT" in successes_line

def append_status_effect_roll(status_effect_dice, prefix, roll_number_string, message_lines):
    if status_effect_dice is None or status_effect_dice == 0:
        return
    query = ParsedRollQuery(status_effect_dice)
    status_roll_result = query.execute()
    dice_line, successes_line = split_dice_and_successes(status_roll_result)
    if successes_line:
        message_lines.append(f"{prefix}**Status Effect {roll_number_string}roll**: {dice_line} – {successes_line}")
    else:
        message_lines.append(f"{prefix}**Status Effect {roll_number_string}roll**: {dice_line}")

def append_crit_stat_if_changed(message_lines, crit_6_count):
    if crit_6_count != DEFAULT_CRIT_DIE_COUNT:
        message_lines.append(f"-# **[Changed: Crit on {crit_6_count}x 6's]**")

class AreaAttackRollCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _compose_area_attack_message_and_view(self, roll_params, previous_results=None, reroll_type=None, reroll_view=False):
        # Extract params
        accuracy_dice = roll_params['accuracy_dice']
        damage_dice = roll_params['damage_dice']
        crit_6_count = roll_params['crit_6_count']
        status_effect_dice = roll_params.get('status_effect_dice')
        status_effect_dice_2 = roll_params.get('status_effect_dice_2')
        accuracy_reduction = roll_params.get('accuracy_reduction', 0)
        required_accuracy = 1 + (accuracy_reduction or 0)
        main_target = roll_params.get('main_target')

        # Reroll branches
        if reroll_view and reroll_type == 'accuracy':
            message_lines = ["### Reroll — Accuracy"]
            accuracy_query = ParsedRollQuery(accuracy_dice, crit_6_count=crit_6_count)
            accuracy_roll_result = accuracy_query.execute()
            dice_line, successes_line = split_dice_and_successes(accuracy_roll_result)
            success_count = get_success_count(successes_line)
            message_lines.append(f"**Reroll Accuracy**: {dice_line} – {successes_line} ({required_accuracy} needed)")
            if success_count < required_accuracy:
                append_random_mockery(message_lines, COMPLETE_MISS_COMMENTARY)
            # Check previous accuracy to determine if we should also roll damage
            prev_acc_success = None
            if previous_results and 'accuracy' in previous_results:
                prev_acc_success = get_success_count(split_dice_and_successes(previous_results.get('accuracy',''))[1])
            if prev_acc_success is not None and prev_acc_success < required_accuracy and success_count >= required_accuracy and damage_dice > 0:
                damage_query = ParsedRollQuery(damage_dice)
                damage_roll_result = damage_query.execute()
                d_dice_line, d_successes_line = split_dice_and_successes(damage_roll_result)
                message_lines.append(f"**Damage roll**: {d_dice_line} – {d_successes_line}")
                damage_success = get_success_count(d_successes_line)
                if damage_success == 0:
                    append_random_mockery(message_lines, COMPLETE_MISS_COMMENTARY)
                else:
                    message_lines.append("")
                    message_lines.append(f"**Enemies hit for {damage_success} damage each.**")
                    half_damage = math.ceil(damage_success / 2)
                    message_lines.append(f"**Allies hit for {half_damage} damage each (half, rounded up).**")
            return message_lines, None

        if reroll_view and reroll_type == 'damage':
            damage_query = ParsedRollQuery(damage_dice)
            damage_roll_result = damage_query.execute()
            d_dice_line, d_successes_line = split_dice_and_successes(damage_roll_result)
            message_lines = ["### Reroll — Damage", f"**Reroll Damage**: {d_dice_line} – {d_successes_line}"]
            damage_success = get_success_count(d_successes_line)
            if damage_success == 0:
                append_random_mockery(message_lines, COMPLETE_MISS_COMMENTARY)
            else:
                message_lines.append("")
                message_lines.append(f"**Enemies hit for {damage_success} damage each.**")
                half_damage = math.ceil(damage_success / 2)
                message_lines.append(f"**Allies hit for {half_damage} damage each (half, rounded up).**")
            return message_lines, None

        if reroll_view and reroll_type == 'status1':
            if status_effect_dice:
                status_query = ParsedRollQuery(status_effect_dice)
                status_roll_result = status_query.execute()
                dice_line, successes_line = split_dice_and_successes(status_roll_result)
                message_lines = ["### Reroll — Status Effect", f"**Reroll Status Effect**: {dice_line} – {successes_line}"]
                return message_lines, None

        if reroll_view and reroll_type == 'status2':
            if status_effect_dice_2:
                status_query = ParsedRollQuery(status_effect_dice_2)
                status_roll_result = status_query.execute()
                dice_line, successes_line = split_dice_and_successes(status_roll_result)
                message_lines = ["### Reroll — Status Effect #2", f"**Reroll Status Effect #2**: {dice_line} – {successes_line}"]
                return message_lines, None

        # Normal full composition
        message_lines = [
            f"### Area Attack Roll",
            f"-# Parameters: Accuracy dice: {accuracy_dice} | Required Accuracy: {required_accuracy} | Damage dice: {damage_dice}"
        ]
        append_crit_stat_if_changed(message_lines, crit_6_count)
        message_lines.append(f"-# **Main target:** {main_target}")
        message_lines.append("")

        if required_accuracy > accuracy_dice:
            message_lines.append("### That'd be an instant-miss! Did you typo your accuracy dice?")
            return message_lines, None

        # Accuracy
        accuracy_query = ParsedRollQuery(accuracy_dice, crit_6_count=crit_6_count)
        accuracy_roll_result = accuracy_query.execute()
        acc_dice_line, acc_successes_line = split_dice_and_successes(accuracy_roll_result)
        acc_success_count = get_success_count(acc_successes_line)
        if acc_successes_line:
            message_lines.append(f"**Accuracy roll**: {acc_dice_line} – {acc_successes_line} ({required_accuracy} needed)")
        else:
            message_lines.append(f"**Accuracy roll**: {acc_dice_line} ({required_accuracy} needed)")

        if required_accuracy > acc_success_count:
            append_random_mockery(message_lines, COMPLETE_MISS_COMMENTARY)
            return message_lines, None

        if is_crit(acc_successes_line):
            message_lines.append(f"**{main_target} got a critical hit!**")

        message_lines.append("")

        # Damage
        damage_query = ParsedRollQuery(damage_dice)
        damage_roll_result = damage_query.execute()
        dmg_dice_line, dmg_successes_line = split_dice_and_successes(damage_roll_result)
        damage_success = get_success_count(dmg_successes_line)
        message_lines.append(f"**Damage roll**: {dmg_dice_line} – {dmg_successes_line}")

        message_lines.append("")
        message_lines.append(f"**Enemies hit for {damage_success} damage each.**")
        half_damage = math.ceil(damage_success / 2)
        message_lines.append(f"**Allies hit for {half_damage} damage each (half, rounded up).**")

        # Status effects
        if status_effect_dice and status_effect_dice > 0:
            append_status_effect_roll(status_effect_dice, "", "", message_lines)
        if status_effect_dice_2 and status_effect_dice_2 > 0:
            append_status_effect_roll(status_effect_dice_2, "", "#2 ", message_lines)

        view = AreaRerollView(roll_params, show_accuracy=True, show_damage=damage_dice > 0, show_status1=status_effect_dice, show_status2=status_effect_dice_2)
        return message_lines, view

    @app_commands.command(
        name="area_attack_roll",
        description="Area moves: pick a main target for full damage; other enemies and allies take group damage."
    )
    @app_commands.describe(
        accuracy_dice="How many accuracy dice should be rolled?",
        damage_dice="How many damage dice should be rolled?",
        main_target="The name of your main (primary) target for full damage.",
        crit_6_count="How many 6's are required to crit.",
        status_effect_dice="How many status effect dice should be rolled?",
        status_effect_dice_2="How many status effect dice should be rolled for a second status effect?",
        accuracy_reduction="Add an accuracy reduction. Defaults to 0.",
    )
    async def area_attack_roll(
        self,
        interaction: discord.Interaction,
        accuracy_dice: app_commands.Range[int, 1, 40],
        damage_dice: app_commands.Range[int, 0, 80],
        main_target: str,
        crit_6_count: app_commands.Range[int, 0, 5] = None,
        status_effect_dice: app_commands.Range[int, 0, 5] = None,
        status_effect_dice_2: app_commands.Range[int, 0, 5] = None,
        accuracy_reduction: app_commands.Range[int, 0, 10] = 0,
    ):
        await interaction.response.defer(thinking=True)
        # Build roll params and use composer to get message lines + view
        roll_params = {
            'accuracy_dice': accuracy_dice,
            'damage_dice': damage_dice,
            'crit_6_count': crit_6_count if crit_6_count is not None else DEFAULT_CRIT_DIE_COUNT,
            'status_effect_dice': status_effect_dice,
            'status_effect_dice_2': status_effect_dice_2,
            'accuracy_reduction': accuracy_reduction,
            'main_target': main_target,
        }

        message_lines, view = self._compose_area_attack_message_and_view(roll_params)

        # Send the composed message lines (attach view to the first chunk)
        msg_block = ""
        sent_first = False
        for line in message_lines:
            if len(msg_block) + len(line) + 1 > 1800:
                if not sent_first:
                    if view is not None:
                        await interaction.followup.send(msg_block, view=view)
                    else:
                        await interaction.followup.send(msg_block)
                    sent_first = True
                else:
                    await interaction.followup.send(msg_block)
                msg_block = ""
            msg_block += line + "\n"
        if msg_block:
            if not sent_first:
                if view is not None:
                    await interaction.followup.send(msg_block, view=view)
                else:
                    await interaction.followup.send(msg_block)
            else:
                await interaction.followup.send(msg_block)

async def setup(bot):
    await bot.add_cog(AreaAttackRollCog(bot))


class AreaRerollView(discord.ui.View):
    def __init__(self, roll_params, show_accuracy=True, show_damage=False, show_status1=None, show_status2=None):
        super().__init__(timeout=300)
        self.roll_params = roll_params
        if show_accuracy:
            self.add_item(AreaRerollButton('accuracy', label='Reroll Accuracy', style=discord.ButtonStyle.primary))
        if show_damage:
            self.add_item(AreaRerollButton('damage', label='Reroll Damage', style=discord.ButtonStyle.danger))
        if show_status1:
            self.add_item(AreaRerollButton('status1', label='Reroll Status Effect', style=discord.ButtonStyle.success))
        if show_status2:
            self.add_item(AreaRerollButton('status2', label='Reroll Status Effect #2', style=discord.ButtonStyle.success))


class AreaRerollButton(discord.ui.Button):
    def __init__(self, reroll_type, label, style):
        super().__init__(label=label, style=style)
        self.reroll_type = reroll_type

    async def callback(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog('AreaAttackRollCog')
        params = dict(self.view.roll_params)
        previous_message = interaction.message.content or ''
        previous_results = {}
        import re
        for raw_line in previous_message.split('\n'):
            line = raw_line.strip()
            if not line:
                continue
            m = re.match(r"^\*\*(?:Reroll\s+)?Accuracy(?:\s+roll)?\*\*:\s*(.+)$", line)
            if m:
                content = m.group(1).strip()
                if '–' in content:
                    left, right = content.split('–', 1)
                    previous_results['accuracy'] = f"{left.strip()}\n{right.strip()}"
                else:
                    previous_results['accuracy'] = content
                continue
            m = re.match(r"^\*\*(?:Reroll\s+)?Damage(?:\s+roll)?\*\*:\s*(.+)$", line)
            if m:
                content = m.group(1).strip()
                if '–' in content:
                    left, right = content.split('–', 1)
                    previous_results['damage'] = f"{left.strip()}\n{right.strip()}"
                else:
                    previous_results['damage'] = content
                continue
            m = re.match(r"^\*\*(?:Reroll\s+)?Status Effect\s+#2\s*roll\*\*:\s*(.+)$", line)
            if m:
                content = m.group(1).strip()
                if '–' in content:
                    left, right = content.split('–', 1)
                    previous_results['status2'] = f"{left.strip()}\n{right.strip()}"
                else:
                    previous_results['status2'] = content
                continue
            m = re.match(r"^\*\*(?:Reroll\s+)?Status Effect(?:\s+roll)?\*\*:\s*(.+)$", line)
            if m:
                content = m.group(1).strip()
                if '–' in content:
                    left, right = content.split('–', 1)
                    previous_results['status1'] = f"{left.strip()}\n{right.strip()}"
                else:
                    previous_results['status1'] = content
                continue

        message_lines, _ = cog._compose_area_attack_message_and_view(
            params,
            previous_results=previous_results,
            reroll_type=self.reroll_type,
            reroll_view=True
        )
        await interaction.response.send_message('\n'.join(message_lines), ephemeral=False)
