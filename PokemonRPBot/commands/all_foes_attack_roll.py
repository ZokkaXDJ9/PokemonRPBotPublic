import random
import discord
from discord.ext import commands
from discord import app_commands
from helpers import ParsedRollQuery, DEFAULT_CRIT_DIE_COUNT

# --- Commentary Lists (add more if you like) ---
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
OUT_OF_DAMAGE_DICE_COMMENTARY = [
    "Ran out of steam halfway through the smackdown!",
    "And just like that... the move gave up.",
    "Somehow forgot to pack enough pain for everyone.",
    "The move fizzled out like a budget fireworks show.",
    "Someone, somewhere, breathes a sigh of relief.",
    "Out of dice, out of damage, out of luck!",
    "The attack stopped politely after hitting a few folks.",
    "Guess they didn’t pay for the full AoE package.",
    "Ran out of damage halfway through the dramatic pose.",
    "They brought fists to seven targets. There were ten.",
    "Oops! All energy, no follow-through.",
    "The rest just stood there awkwardly — untouched!",
    "Some targets got lucky. Others got lazy coding.",
    "The attack got tired and went home.",
    "They were like 'nah, that's enough damage for today.'",
    "Too much ambition, not enough dice.",
    "Some targets were spared... by pure arithmetic!",
    "Only hit as many targets as they could count to.",
    "Momentum? Gone. Damage? Also gone.",
    "It started strong and ended... confused.",
    "The final targets were spared by technicality!",
    "The leftovers just looked around like, 'Was that it?'",
    "Damage budget blown halfway through!",
    "Got halfway through the rampage, then ran out of rage.",
    "And just like that, the violence stopped.",
    "Looks like someone needs to roll a bit harder next time.",
    "That’s what happens when you don’t pace yourself.",
    "The attack tripped on its own enthusiasm.",
    "Too many targets, not enough juice!",
    "RNG giveth, damage dice taketh away.",
    "Damage dice ran out like batteries in a remote.",
    "That move was 70% murder, 30% shrug.",
    "The back half of the battlefield just blinked in confusion.",
    "Ambition: 10 targets. Reality: 7 dice.",
    "Some were hit. Others just got popcorn.",
    "And the rest of the enemies? Not even winded.",
    "Ran out of oomph halfway through the boomph.",
    "Everyone else just flinched for no reason.",
    "It was a group attack! ...In theory.",
    "This is what happens when you overbook destruction.",
    "Guess the second wave of damage missed their flight.",
    "The move came, it saw, it kinda forgot the rest.",
    "Some got clobbered. Others just observed.",
    "They didn’t get hit — just slightly startled.",
    "A move so powerful... it gave up halfway.",
    "And the rest were spared by sheer technicality.",
    "Out of dice, out of spite.",
    "Turns out the AoE was more of a SoE — *Some* of Effect.",
    "Damage didn’t run out — it just got picky.",
    "What started as an area attack ended as a selective slap.",
    "Collateral damage was canceled due to low resources.",
    "The last few targets just got a light breeze.",
]
ALL_HIT_COMMENTARY = [
    "Let’s find out who gets hit first — completely fair, totally random!",
    "Spinning the wheel of unfortunate priorities...",
    "Which poor soul goes first? Only fate knows!",
    "Time to shuffle the order of doom!",
    "No favorites here — the attack order is up to chance!",
    "Deciding who eats the first hit... randomly!",
    "Let’s randomize the pain delivery route!",
    "Who gets clobbered first? Let’s ask the dice.",
    "Distributing damage in random order — equal opportunity chaos!",
    "Rolling to see who gets unlucky first...",
    "It’s not personal — just randomized!",
    "We’ll let fate choose the lucky first victim!",
    "The attack queue is getting shuffled!",
    "It’s like a lottery... but with more bruising.",
    "Let’s spin the pain wheel and see where it lands first!",
    "No bias here — just good old chaos ordering.",
    "Pulling names from the hat of suffering...",
    "Deciding the order of regret!",
    "Shuffling the hit list...",
    "Time to deal damage... randomly and democratically!",
    "The RNG will now choose who gets whacked first!",
    "Prioritizing targets? Nah, we let fate do that.",
    "Rearranging targets like a deck of doom!",
    "Starting a fair and balanced beatdown... in random order!",
    "Which target gets the honor of being first? Let’s find out!",
    "Rolling for hit order — place your bets!",
    "Target order: determined by pure chaos!",
    "Nobody’s safe — but someone’s going first!",
    "Launching attack... with shuffled priorities!",
    "Time to deal damage, randomized for flavor!",
    "Target priority? Never heard of it!",
    "Lining up the targets... badly and randomly.",
    "It’s time for the damage lottery!",
    "Someone’s gotta go first. Let’s make it random!",
    "Eeny, meeny, miny — chaos.",
    "Randomizing the victim queue!",
    "Serving up damage — order chosen by dice gods.",
    "The hit parade begins… in random order!",
    "It’s a mystery who goes down first!",
    "Hope someone packed insurance — order’s out of our hands!",
    "Let’s pick the unlucky lead-off target!",
    "Damage roulette begins now!",
    "Which target gets the spotlight first? Let’s ask chance.",
    "The attack’s coming... just not sure who gets it first!",
    "We let the dice pick who gets regret first!",
    "Organizing pain... with maximum disorder.",
    "Time to roll for first target!",
    "It’s chaos o’clock — let’s decide the strike order!",
    "There is no plan. Only target shuffling.",
    "Let the drama of random targeting begin!",
    "No tactics. Just vibes.",
    "Reordering targets by the power of shrug!",
    "Rolling initiative, but for suffering!",
    "Someone has to go first. RNG will decide their fate.",
    "Time to put these targets in random firing order!",
    "Step right up — who wants to be unlucky today?",
    "Damage is coming — we just don’t know where it starts.",
    "No strategy here. Just pure chaos sequencing!",
    "The hit list is now being randomized...",
    "Choosing a victim sequence... the chaotic way!",
    "Don’t take it personally. The dice just hate you.",
    "We’re going to let fate figure out the first casualty.",
    "Fate is loading the damage queue...",
    "It’s time to let luck be the tactician!",
    "Spinning the order wheel of misfortune!",
    "Let’s roll for regret sequencing!",
    "Hope you weren’t expecting fairness in order!",
    "Determining strike order with scientific randomness!",
    "Let’s get the randomness rolling — literally!",
    "Who gets hit first? Not even I know!",
    "Hold tight — we’re shuffling the target deck!",
    "This will be completely impartial chaos. Promise!",
    "Prioritizing targets? That’s so last turn.",
    "The damage train is leaving — who’s the first stop?",
    "No one’s safe, but someone’s first. Let’s find out!",
    "We asked a coin, a die, and a squirrel. Consensus reached!",
    "The strike order is now chaos-certified!",
    "Rolling dice to see who regrets their life choices first...",
    "The RNG wheel spins! Screaming optional!",
    "And now... a completely irresponsible order of destruction!",
    "We’ll be attacking in absolutely no logical order!",
    "No strategy here — just vibes and mild chaos.",
    "And the first sacrifice shall be... decided randomly!",
    "Time to find out who annoyed the universe the most.",
    "Step right up for your randomized whacking!",
    "Someone’s about to get hit first — and it might be personal!",
    "It’s like a raffle, but the prize is pain!",
    "We asked the dice who should suffer first. The dice were cruel.",
    "Starting the attack sequence... in comedy mode!",
    "Hope someone brought a helmet — this is pure improv!",
    "Attack order? Never heard of her.",
    "Let’s put targets in random order — for dramatic tension!",
    "Picking a victim at random, like a badly managed game show!",
    "Who gets hit first? Spin the Wheel of Misfortune™!",
    "Just a moment — the chaos monkeys are deciding...",
    "Prioritizing by who looked at us funny.",
    "Tossing names into a blender and seeing who gets puree'd first!",
    "Initiating random violence... now!",
    "Throwing darts at the target list again!",
    "Hold on, consulting a crystal ball and some dice.",
    "Who goes first? It’s whoever the dice hate today!",
    "Performing randomized target acquisition. Science!",
    "Shuffling targets like a very angry DJ.",
    "You get a hit! You get a hit! But who gets it first?",
    "Initiating completely fair and mildly cursed hit order!",
    "Organizing pain distribution alphabetically! Just kidding — RANDOM!",
    "And now… a surprise attack order, courtesy of our gremlin intern!",
    "Unleashing chaos. Gently. One target at a time.",
    "Let’s see who RNG woke up cranky about!",
    "Starting the attack with a random act of hostility.",
    "Time to disappoint someone specifically... by chance!",
    "Deciding attack order by pulling names out of a suspicious hat.",
    "Sorting targets based on who tripped last turn.",
    "Spin the wheel! Win a concussion!",
    "Starting the pain parade with a random guest of honor!",
    "It’s time to play: Who Gets Hit First?",
    "The first lucky victim is being selected now!",
    "RNG, shuffle these souls like a bad playlist!",
    "And the chaos gods said... this one dies first!",
    "Commencing randomized smacking sequence!",
    "Assigning first place in the hurt line!",
    "The order of destruction is... drumroll of doom...",
    "Our target queue is being generated by trained raccoons.",
    "Drawing straws for first blood!",
    "Distributing damage via a lottery no one wanted to enter.",
    "Let’s pick someone to regret existing — completely at random!",
    "Target order determined by throwing darts blindfolded.",
    "Hold onto your hit points, we’re choosing randomly!",
    "Selecting the first target with a blindfold and a grudge!",
    "Let fate decide who goes down slightly faster!",
    "Who’s up first in the suffering queue? Let’s find out!",
    "Somebody’s about to be first on the punch list!",
    "Our sorting hat is just a dice in a trench coat.",
    "Brace yourself — chaos is making decisions now.",
    "Attack order courtesy of 'Spinny the RNG Goblin'!",
    "Choosing targets with maximum confusion — on purpose!",
    "Who gets hit first? We let the hamster in charge of RNG decide!",
    "It’s random, it’s chaotic, it’s deeply concerning!",
    "Let’s roll some dice and ruin someone’s day — efficiently!",
    "Selecting the unlucky first target… doom pending.",
    "First target? Whichever one flinched first!",
    "Attack sequence determined by imaginary astrology!",
    "Your order of suffering is now being randomized.",
    "Placing bets on who gets walloped first!",
    "We asked RNG to be gentle. RNG declined.",
    "Opening the buffet of pain — who’s first in line?",
    "Queueing up targets in a totally nonsensical order!",
    "Today’s pain is brought to you by random.org!",
    "And the RNG says: you!",
    "We let fate handle the hard choices. Bad idea, really.",
    "Initiating the tactical dartboard method!",
    "Let’s deal damage the lazy, chaotic way!",
    "It's attack time — let’s go full random feral mode!",
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
    return "(CRIT" in successes_line or "CRIT" in successes_line

def append_crit_stat_if_changed(message_lines, crit_6_count):
    if crit_6_count != DEFAULT_CRIT_DIE_COUNT:
        message_lines.append(f"-# **[Changed: Crit on {crit_6_count}x 6's]**")

class AllFoesAttackRollCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @app_commands.command(
        name="all_foes_attack_roll",
        description="Attack all foes in your chosen order, reducing damage dice by 1 for each successive foe."
    )
    @app_commands.describe(
        accuracy_dice="How many accuracy dice should be rolled?",
        damage_dice="How many damage dice for the first target?",
        targets="A comma separated list of enemy names. Target Randomization is off by default.",
        crit_6_count="How many 6's required to crit?",
        status_effect_dice="How many status effect dice should be rolled?",
        status_effect_dice_2="How many status effect dice should be rolled for a second status effect?",
        accuracy_reduction="Add an accuracy reduction. Defaults to 0.",
        randomize_order="Set to true to turn on random target selection. Off by default.",
    )
    async def all_foes_attack_roll(
        self,
        interaction: discord.Interaction,
        accuracy_dice: app_commands.Range[int, 1, 40],
        damage_dice: app_commands.Range[int, 1, 80],
        targets: str,
        crit_6_count: app_commands.Range[int, 0, 5] = None,
        status_effect_dice: app_commands.Range[int, 0, 5] = None,
        status_effect_dice_2: app_commands.Range[int, 0, 5] = None,
        accuracy_reduction: app_commands.Range[int, 0, 10] = 0,
        randomize_order: bool = False,
    ):
        await interaction.response.defer(thinking=True)
        # Collect roll parameters into a dict used by composer and reroll view
        roll_params = {
            'accuracy_dice': accuracy_dice,
            'damage_dice': damage_dice,
            'crit_6_count': crit_6_count if crit_6_count is not None else DEFAULT_CRIT_DIE_COUNT,
            'status_effect_dice': status_effect_dice,
            'status_effect_dice_2': status_effect_dice_2,
            'accuracy_reduction': accuracy_reduction,
            'targets': [t.strip() for t in targets.split(',') if t.strip()],
            'randomize_order': randomize_order,
        }

        # Compose message and view
        message_lines, view = self._compose_all_foes_message_and_view(roll_params)

        # Send the composed message lines (chunk if necessary). Attach view to the first block.
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
        return
    

    def _compose_all_foes_message_and_view(self, roll_params, previous_results=None, reroll_type=None, reroll_view=False):
        # Extract params
        accuracy_dice = roll_params['accuracy_dice']
        damage_dice = roll_params['damage_dice']
        crit_6_count = roll_params['crit_6_count']
        status_effect_dice = roll_params.get('status_effect_dice')
        status_effect_dice_2 = roll_params.get('status_effect_dice_2')
        accuracy_reduction = roll_params.get('accuracy_reduction', 0)
        required_accuracy = 1 + (accuracy_reduction or 0)
        targets = list(roll_params.get('targets') or [])
        randomize_order = bool(roll_params.get('randomize_order'))

        # Reroll view branches
        if reroll_view and reroll_type == 'accuracy':
            message_lines = ["### Reroll — Accuracy"]
            accuracy_query = ParsedRollQuery(accuracy_dice, crit_6_count=crit_6_count)
            accuracy_roll_result = accuracy_query.execute()
            dice_line, successes_line = split_dice_and_successes(accuracy_roll_result)
            success_count = get_success_count(successes_line)
            message_lines.append(f"**Reroll Accuracy**: {dice_line} – {successes_line} ({required_accuracy} needed)")
            if success_count < required_accuracy:
                append_random_mockery(message_lines, COMPLETE_MISS_COMMENTARY)
            prev_acc_success = None
            if previous_results and 'accuracy' in previous_results:
                prev_acc_success = get_success_count(split_dice_and_successes(previous_results.get('accuracy',''))[1])
            # Only roll damage if original was miss and reroll is a hit
            if prev_acc_success is not None and prev_acc_success < required_accuracy and success_count >= required_accuracy and damage_dice > 0:
                damage_query = ParsedRollQuery(damage_dice)
                damage_roll_result = damage_query.execute()
                d_dice_line, d_successes_line = split_dice_and_successes(damage_roll_result)
                message_lines.append(f"**Damage roll**: {d_dice_line} – {d_successes_line}")
                damage_success = get_success_count(d_successes_line)
                if damage_success == 0:
                    append_random_mockery(message_lines, OUT_OF_DAMAGE_DICE_COMMENTARY)
                elif damage_success == damage_dice:
                    append_random_mockery(message_lines, ALL_HIT_COMMENTARY)
            return message_lines, None
        # Per-target damage reroll: reroll_type can be ('damage', index)
        if reroll_view and isinstance(reroll_type, tuple) and reroll_type[0] == 'damage':
            idx = reroll_type[1]
            # Validate index
            if not targets or idx is None or idx < 0 or idx >= len(targets):
                return ["No such target to reroll damage for."], None
            # Damage dice for target i is damage_dice - i (cannot go below 0)
            dice_for_target = max(damage_dice - idx, 0)
            message_lines = [f"### Reroll — Damage ({targets[idx]})"]
            if dice_for_target <= 0:
                message_lines.append(f"**Reroll Damage**: 0d6 — 0 Successes")
                append_random_mockery(message_lines, OUT_OF_DAMAGE_DICE_COMMENTARY)
                return message_lines, None
            damage_query = ParsedRollQuery(dice_for_target)
            damage_roll_result = damage_query.execute()
            d_dice_line, d_successes_line = split_dice_and_successes(damage_roll_result)
            message_lines.append(f"**Reroll Damage** for **{targets[idx]}**: {d_dice_line} – {d_successes_line}")
            damage_success = get_success_count(d_successes_line)
            if damage_success == 0:
                append_random_mockery(message_lines, OUT_OF_DAMAGE_DICE_COMMENTARY)
            elif damage_success == dice_for_target:
                append_random_mockery(message_lines, ALL_HIT_COMMENTARY)
            return message_lines, None

        # Per-target status1 reroll: reroll_type can be ('status1', index)
        if reroll_view and isinstance(reroll_type, tuple) and reroll_type[0] == 'status1':
            idx = reroll_type[1]
            if not targets or idx is None or idx < 0 or idx >= len(targets):
                return ["No such target to reroll status for."], None
            dice_for_status = status_effect_dice
            message_lines = [f"### Reroll — Status Effect ({targets[idx]})"]
            if not dice_for_status or dice_for_status <= 0:
                message_lines.append(f"**Reroll Status Effect**: 0d6 — 0 Successes")
                return message_lines, None
            status_query = ParsedRollQuery(dice_for_status)
            status_roll_result = status_query.execute()
            s_dice_line, s_successes_line = split_dice_and_successes(status_roll_result)
            message_lines.append(f"**Reroll Status Effect** for **{targets[idx]}**: {s_dice_line} – {s_successes_line}")
            return message_lines, None

        # Per-target status2 reroll: reroll_type can be ('status2', index)
        if reroll_view and isinstance(reroll_type, tuple) and reroll_type[0] == 'status2':
            idx = reroll_type[1]
            if not targets or idx is None or idx < 0 or idx >= len(targets):
                return ["No such target to reroll status #2 for."], None
            dice_for_status = status_effect_dice_2
            message_lines = [f"### Reroll — Status Effect #2 ({targets[idx]})"]
            if not dice_for_status or dice_for_status <= 0:
                message_lines.append(f"**Reroll Status Effect #2**: 0d6 — 0 Successes")
                return message_lines, None
            status_query = ParsedRollQuery(dice_for_status)
            status_roll_result = status_query.execute()
            s_dice_line, s_successes_line = split_dice_and_successes(status_roll_result)
            message_lines.append(f"**Reroll Status Effect #2** for **{targets[idx]}**: {s_dice_line} – {s_successes_line}")
            return message_lines, None

        elif reroll_view and reroll_type == 'damage':
            damage_query = ParsedRollQuery(damage_dice)
            damage_roll_result = damage_query.execute()
            d_dice_line, d_successes_line = split_dice_and_successes(damage_roll_result)
            message_lines = ["### Reroll — Damage", f"**Reroll Damage**: {d_dice_line} – {d_successes_line}"]
            damage_success = get_success_count(d_successes_line)
            if damage_success == 0:
                append_random_mockery(message_lines, OUT_OF_DAMAGE_DICE_COMMENTARY)
            elif damage_success == damage_dice:
                append_random_mockery(message_lines, ALL_HIT_COMMENTARY)
            return message_lines, None
        elif reroll_view and reroll_type == 'status1':
            if status_effect_dice:
                status_query = ParsedRollQuery(status_effect_dice)
                status_roll_result = status_query.execute()
                dice_line, successes_line = split_dice_and_successes(status_roll_result)
                message_lines = ["### Reroll — Status Effect", f"**Reroll Status Effect**: {dice_line} – {successes_line}"]
                return message_lines, None
        elif reroll_view and reroll_type == 'status2':
            if status_effect_dice_2:
                status_query = ParsedRollQuery(status_effect_dice_2)
                status_roll_result = status_query.execute()
                dice_line, successes_line = split_dice_and_successes(status_roll_result)
                message_lines = ["### Reroll — Status Effect #2", f"**Reroll Status Effect #2**: {dice_line} – {successes_line}"]
                return message_lines, None

        # Normal full composition
        message_lines = []
        if not targets:
            message_lines.append("You must specify at least one target (comma separated).")
            return message_lines, None

        params_line = f"-# Parameters: Accuracy dice: {accuracy_dice} | Required Accuracy: {required_accuracy} | Starting Damage dice: {damage_dice}"
        if randomize_order:
            random.shuffle(targets)
            params_line += " | Targets randomized!"
        message_lines.extend(["### All Foes Attack Roll", params_line])
        append_crit_stat_if_changed(message_lines, crit_6_count)
        message_lines.append(f"-# **Target focus order:** {', '.join(targets)}")
        message_lines.append("")

        if required_accuracy > accuracy_dice:
            message_lines.append("### That'd be an instant-miss! Did you typo your accuracy dice?")
            return message_lines, None

        # Accuracy roll
        accuracy_query = ParsedRollQuery(accuracy_dice, crit_6_count=crit_6_count)
        accuracy_roll_result = accuracy_query.execute()
        acc_dice_line, acc_successes_line = split_dice_and_successes(accuracy_roll_result)
        acc_success_count = get_success_count(acc_successes_line)
        if acc_successes_line:
            message_lines.append(f"**Accuracy roll**: {acc_dice_line} – {acc_successes_line} ({required_accuracy} needed)")
        else:
            message_lines.append(f"**Accuracy roll**: {acc_dice_line} ({required_accuracy} needed)")

        if randomize_order:
            append_random_mockery(message_lines, ALL_HIT_COMMENTARY)

        if required_accuracy > acc_success_count:
            append_random_mockery(message_lines, COMPLETE_MISS_COMMENTARY)
            return message_lines, None

        if is_crit(acc_successes_line):
            message_lines.append(f"**{targets[0]} got a critical hit!**")

        message_lines.append("")

        # Damage loop for each target
        remaining_damage_dice = damage_dice
        for i, target in enumerate(targets):
            if remaining_damage_dice <= 0:
                message_lines.append("**Out of damage dice!**")
                append_random_mockery(message_lines, OUT_OF_DAMAGE_DICE_COMMENTARY)
                break

            message_lines.append(f"**Targeting {target}!**")
            dmg_query = ParsedRollQuery(remaining_damage_dice)
            dmg_roll_result = dmg_query.execute()
            dmg_dice_line, dmg_successes_line = split_dice_and_successes(dmg_roll_result)
            damage_success = get_success_count(dmg_successes_line)
            if dmg_successes_line:
                message_lines.append(f"> **Damage roll**: {dmg_dice_line} – {dmg_successes_line}")
            else:
                message_lines.append(f"> **Damage roll**: {dmg_dice_line}")

            if status_effect_dice and status_effect_dice > 0:
                status_query = ParsedRollQuery(status_effect_dice)
                status_roll_result = status_query.execute()
                s_dice_line, s_successes_line = split_dice_and_successes(status_roll_result)
                if s_successes_line:
                    message_lines.append(f"> **Status Effect roll**: {s_dice_line} – {s_successes_line}")
                else:
                    message_lines.append(f"> **Status Effect roll**: {s_dice_line}")
            if status_effect_dice_2 and status_effect_dice_2 > 0:
                status_query2 = ParsedRollQuery(status_effect_dice_2)
                status_roll_result2 = status_query2.execute()
                s2_dice_line, s2_successes_line = split_dice_and_successes(status_roll_result2)
                if s2_successes_line:
                    message_lines.append(f"> **Status Effect #2 roll**: {s2_dice_line} – {s2_successes_line}")
                else:
                    message_lines.append(f"> **Status Effect #2 roll**: {s2_dice_line}")

            remaining_damage_dice -= 1

        view = AllFoesRerollView(roll_params, show_accuracy=True, show_damage=damage_dice > 0, show_status1=status_effect_dice, show_status2=status_effect_dice_2)
        return message_lines, view


class AllFoesRerollView(discord.ui.View):
    def __init__(self, roll_params, show_accuracy=True, show_damage=False, show_status1=None, show_status2=None):
        # Increased timeout to match other command
        super().__init__(timeout=300)
        self.roll_params = roll_params
        if show_accuracy:
            self.add_item(AllFoesRerollButton('accuracy', label='Reroll Accuracy', style=discord.ButtonStyle.primary))
        if show_damage:
            # Add a damage reroll button for each target so users can reroll a specific target's damage
            targets = list(roll_params.get('targets') or [])
            if targets:
                for i, t in enumerate(targets):
                    # Shorten label if too long
                    label = f"Reroll Damage — {t}"
                    if len(label) > 80:
                        label = f"Reroll Damage — target {i+1}"
                    self.add_item(AllFoesRerollButton('damage', label=label, style=discord.ButtonStyle.danger, target_index=i))
            else:
                # fallback: single generic damage button
                self.add_item(AllFoesRerollButton('damage', label='Reroll Damage', style=discord.ButtonStyle.danger))
        if show_status1:
            # Add a status1 reroll button per-target when possible
            targets = list(roll_params.get('targets') or [])
            if targets:
                for i, t in enumerate(targets):
                    label = f"Reroll Status — {t}"
                    if len(label) > 80:
                        label = f"Reroll Status — target {i+1}"
                    self.add_item(AllFoesRerollButton('status1', label=label, style=discord.ButtonStyle.success, target_index=i))
            else:
                self.add_item(AllFoesRerollButton('status1', label='Reroll Status Effect', style=discord.ButtonStyle.success))
        if show_status2:
            # Add a status2 reroll button per-target when possible
            targets = list(roll_params.get('targets') or [])
            if targets:
                for i, t in enumerate(targets):
                    label = f"Reroll Status #2 — {t}"
                    if len(label) > 80:
                        label = f"Reroll Status #2 — target {i+1}"
                    self.add_item(AllFoesRerollButton('status2', label=label, style=discord.ButtonStyle.success, target_index=i))
            else:
                self.add_item(AllFoesRerollButton('status2', label='Reroll Status Effect #2', style=discord.ButtonStyle.success))


class AllFoesRerollButton(discord.ui.Button):
    def __init__(self, reroll_type, label, style, target_index=None):
        super().__init__(label=label, style=style)
        self.reroll_type = reroll_type
        self.target_index = target_index

    async def callback(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog('AllFoesAttackRollCog')
        params = dict(self.view.roll_params)
        previous_message = interaction.message.content or ''
        previous_results = {}
        import re
        # Enhanced parsing: track which target we're on so damage rolls per-target can be captured
        current_target_idx = None
        target_pointer = 0
        for raw_line in previous_message.split('\n'):
            line = raw_line.strip()
            if not line:
                continue
            # Detect target header lines like "**Targeting X!**"
            m_target = re.match(r"^\*\*Targeting\s+.+?!\*\*", line)
            if m_target:
                # advance pointer — we assume target order in message matches params['targets'] order
                current_target_idx = target_pointer
                target_pointer += 1
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
                # If we are inside a Targeting block, store as per-target damage
                key = 'damage'
                if current_target_idx is not None:
                    key = f'damage_{current_target_idx}'
                if '–' in content:
                    left, right = content.split('–', 1)
                    previous_results[key] = f"{left.strip()}\n{right.strip()}"
                else:
                    previous_results[key] = content
                continue

            m = re.match(r"^\*\*(?:Reroll\s+)?Status Effect\s+#2\s*roll\*\*:\s*(.+)$", line)
            if m:
                content = m.group(1).strip()
                # store per-target if within a Targeting block
                key = 'status2'
                if current_target_idx is not None:
                    key = f'status2_{current_target_idx}'
                if '–' in content:
                    left, right = content.split('–', 1)
                    previous_results[key] = f"{left.strip()}\n{right.strip()}"
                else:
                    previous_results[key] = content
                continue

            m = re.match(r"^\*\*(?:Reroll\s+)?Status Effect(?:\s+roll)?\*\*:\s*(.+)$", line)
            if m:
                content = m.group(1).strip()
                key = 'status1'
                if current_target_idx is not None:
                    key = f'status1_{current_target_idx}'
                if '–' in content:
                    left, right = content.split('–', 1)
                    previous_results[key] = f"{left.strip()}\n{right.strip()}"
                else:
                    previous_results[key] = content
                continue

        # If this button corresponds to a specific target, send that index along with reroll_type
        reroll_type_to_send = self.reroll_type
        if getattr(self, 'target_index', None) is not None:
            reroll_type_to_send = (self.reroll_type, self.target_index)

        message_lines, _ = cog._compose_all_foes_message_and_view(
            params,
            previous_results=previous_results,
            reroll_type=reroll_type_to_send,
            reroll_view=True
        )
        await interaction.response.send_message('\n'.join(message_lines), ephemeral=False)

    # Duplicate app command inside the button class removed — command is defined once on the Cog above.

async def setup(bot):
    await bot.add_cog(AllFoesAttackRollCog(bot))
