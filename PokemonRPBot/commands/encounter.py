import random
import discord
from discord import app_commands
from discord.app_commands import Choice
from discord import ui
import os
import json
import math
from typing import List

from .pokemon import normalize_name, find_movelist_filename
from emojis import get_type_emoji, get_badge_emoji
from helpers import normalize_keys, load_move, load_ability
from ranks import get_rank
from cache_helper import load_or_build_cache

rank_values = {"bronze": 1, "silver": 2, "gold": 3, "platinum": 4, "diamond": 5, "master": 5}

# Cache Pokémon names at module load for fast autocomplete
_pokemon_cache: List[str] = []
_pokemon_cache_lower: List[str] = []

def _load_pokemon_cache():
    """Load all Pokémon names into memory for fast autocomplete"""
    global _pokemon_cache, _pokemon_cache_lower
    pokemon_dir = os.path.join("Data", "pokemon")
    _pokemon_cache, _pokemon_cache_lower = load_or_build_cache(
        "pokemon.json",
        pokemon_dir,
        "[Encounter] Pokémon species"
    )

# Load cache at module import
_load_pokemon_cache()


async def pkmn_encounter(ctx, number, level, pokelist, boss, guild, format_type="standard", include_extra=False, evil=False):
    smart_stats = boss
    output = ''
    for pokemon_name in pokelist:
        norm = normalize_name(pokemon_name)
        movelist_file = find_movelist_filename(norm, "Data/pokemon")
        if not movelist_file:
            output += f"No data for {pokemon_name}\n"
            continue
        with open(movelist_file, "r", encoding="utf-8") as f:
            data = normalize_keys(json.load(f))
        rank = get_rank(level).lower()
        ranks_order = ["bronze", "silver", "gold", "platinum", "diamond", "master"]
        current_index = ranks_order.index(rank) if rank in ranks_order else 0
        moves_list = []
        # Helper: pick up to `needed` moves from candidates by key, but randomize among the top group
        def pick_from_top(candidates, key_func, needed):
            if not candidates or needed <= 0:
                return []
            scored = []
            for m in candidates:
                try:
                    s = key_func(m)
                except Exception:
                    s = -999999
                scored.append((m, s))
            scored.sort(key=lambda x: x[1], reverse=True)
            if needed >= len(scored):
                return [m for m, _ in scored]
            # define a larger eligible set: max(needed*4, half of list)
            max_candidates = max(needed * 4, len(scored) // 2)
            threshold_index = min(len(scored) - 1, max_candidates - 1)
            threshold_score = scored[threshold_index][1]
            eligible = [m for m, s in scored if s >= threshold_score]
            if len(eligible) <= needed:
                return [m for m, _ in scored[:needed]]
            return random.sample(eligible, needed)
        # Reusable STAB key used in several places
        def compute_stab_key(m):
            move_data = load_move(m)
            if not move_data:
                return (-1, -1, -1, -1)
            move_data = normalize_keys(move_data)
            try:
                power = int(move_data.get('power', 0))
            except (TypeError, ValueError):
                power = 0
                damage_str = move_data.get('damage', '')
                if isinstance(damage_str, str) and '+' in damage_str:
                    parts = damage_str.split('+')
                    if parts[1].strip().isdigit():
                        power = int(parts[1].strip())
            target = move_data.get('target', '')
            target_score = 2 if 'All Foes' in target or 'Area' in target else 1
            effect = move_data.get('effect', '').lower()
            successive_score = 3 if any(kw in effect for kw in ['successive', 'double', 'triple']) else 0
            try:
                crit_score = int(move_data.get('crit', '0'))
            except ValueError:
                crit_score = 0
            if power <= 2 and successive_score == 0 and crit_score == 0:
                return (-1, -1, -1, -1)
            return (power, target_score, successive_score, crit_score)
        # Safe helper to get a move's category even if the move file is missing
        def move_category(move_name):
            mv = load_move(move_name)
            if not mv:
                return ''
            mv = normalize_keys(mv)
            return mv.get('category', '')
        for i in range(current_index + 1):
            moves_list.extend(data.get("moves", {}).get(ranks_order[i], []))

        # Analyze move pool to detect offense-heavy sets. If many high-power
        # Special attacks exist, prefer Special/Dexterity over pumping
        # Vitality/Insight in smart mode.
        offense_score = 0.0
        special_count = 0
        attack_count = 0
        # Determine whether Dexterity should be treated as an attacking stat
        # Parse dexterity max from the movelist data without relying on max_vals_temp
        dex_str = data.get('dexterity', '0/10')
        try:
            dex_max = int(dex_str.split('/')[1]) if '/' in dex_str else 0
        except Exception:
            dex_max = 0
        dex_is_offense_cap = dex_max > 6
        for m in moves_list:
            mv = load_move(m)
            if not mv:
                continue
            mv = normalize_keys(mv)
            cat = mv.get('category', '')
            if cat in ['Physical', 'Special']:
                attack_count += 1
                try:
                    p = int(mv.get('power', 0))
                except Exception:
                    p = 0
                if cat == 'Special':
                    special_count += 1
                    offense_score += p * 1.25
                else:
                    offense_score += p
        # Compute simple heuristic: high offense_score per attack implies
        # build should prioritize offense. Use thresholds empirically.
        offense_ratio = (offense_score / attack_count) if attack_count > 0 else 0
        # Require either a high dex cap or presence of several special moves
        offense_heavy = (attack_count >= 3 and offense_ratio >= 4 and (dex_is_offense_cap or special_count >= 2))
        # If include_extra is requested, interleave TM/Tutor/Egg moves into the candidate pool
        if include_extra:
            extras = []
            moves_section = data.get("moves", {})
            for key in ['tm', 'tutor', 'egg']:
                extras.extend(moves_section.get(key, []))
            # Interleave extras with the rank-based moves to increase their selection chance
            interleaved = []
            i = 0
            j = 0
            # Work off copies to avoid mutating while iterating
            base = moves_list[:]
            ext = [m for m in extras if m not in base]
            while i < len(base) or j < len(ext):
                if i < len(base):
                    if base[i] not in interleaved:
                        interleaved.append(base[i])
                    i += 1
                if j < len(ext):
                    if ext[j] not in interleaved:
                        interleaved.append(ext[j])
                    j += 1
            moves_list = interleaved
        
            # Helper: pick up to `needed` moves from candidates by key, but randomize among the top group
            def pick_from_top(candidates, key_func, needed):
                if not candidates or needed <= 0:
                    return []
                scored = []
                for m in candidates:
                    try:
                        s = key_func(m)
                    except Exception:
                        s = -999999
                    scored.append((m, s))
                scored.sort(key=lambda x: x[1], reverse=True)
                if needed >= len(scored):
                    return [m for m, _ in scored]
                # define a threshold: allow randomness among roughly top 2*needed candidates
                threshold_index = min(len(scored) - 1, max(needed, needed * 2) - 1)
                threshold_score = scored[threshold_index][1]
                eligible = [m for m, s in scored if s >= threshold_score]
                if len(eligible) <= needed:
                    # Return top `needed` by score
                    return [m for m, _ in scored[:needed]]
                # Otherwise pick randomly from eligible
                return random.sample(eligible, needed)
        abilities = data.get("abilities", {}).get("normal", [])
        selected_ability = random.choice(abilities) if abilities else "None"
        # Stat boosting for moves and display
        points = 3 + level
        stats_list = ["strength", "dexterity", "vitality", "special", "insight"]
        social_list = ["tough", "cool", "beauty", "cute", "clever"]
        # Initialize max_vals for smart distribution
        max_vals_temp = {}
        base_vals_temp = {}
        for stat in stats_list:
            val = data.get(stat, "0/10")
            parts = val.split('/') if '/' in val else ['0', '10']
            base_vals_temp[stat] = int(parts[0])
            max_vals_temp[stat] = int(parts[1])
        # For vitality and insight, cap at the highest odd value <= max
        for stat in ['vitality', 'insight']:
            if max_vals_temp[stat] % 2 == 0:
                max_vals_temp[stat] -= 1
        boosts = [0] * 5
        # Fallback/shared state and helpers so non-smart (standard) mode
        # can operate without relying on smart-mode-local functions.
        current_boosts = boosts[:]
        limit_count = 0
        purchase_idx = 0
        last_purchase_at = {s: -100 for s in stats_list}
        purchase_history = []

        def can_buy_limit_for(stat_name):
            # In standard mode, allow purchases freely; smart-mode will
            # redefine this helper to impose spacing rules.
            if not smart_stats:
                return True
            last = last_purchase_at.get(stat_name, -100)
            if purchase_idx - last < 2:
                return False
            return True

        def record_limit_purchase(stat_name):
            nonlocal purchase_idx
            last_purchase_at[stat_name] = purchase_idx
            purchase_idx += 1

        def buy_single(stat_name, idx):
            """Fallback single-point purchase for standard mode."""
            nonlocal points, limit_count, current_boosts
            cost = limit_count + 2
            if points >= cost and can_buy_limit_for(stat_name):
                current_boosts[idx] += 1
                points -= cost
                limit_count += 1
                record_limit_purchase(stat_name)
                purchase_history.append(('single', stat_name, cost))
                return True
            return False

        def buy_double(stat_name, idx):
            # Two-point purchases are only allowed in smart mode; in
            # standard mode we don't perform +2 batch limit-break buys.
            return False
        if boss:  # smart_stats
            # First, when base is even, increase by +1 only when there are
            # enough points to perform a subsequent +2 batch increase.
            # This prevents producing final value 2; rule: require points >= 3
            # (1 to make odd + 2 to spend the first batch).
            for stat in ['vitality', 'insight']:
                idx = stats_list.index(stat)
                if base_vals_temp[stat] % 2 == 0:
                    if points >= 3:
                        boosts[idx] = 1
                        points -= 1
            current_boosts = boosts[:]  # copy
            # track global limit-break points purchased across all stats
            limit_count = 0
            # track the last stat that received a limit-break to avoid consecutive purchases
            last_limit_stat = None
            # Purchase sequencing: require at least one other stat purchase before
            # a stat can receive another limit-break when in smart mode. We use
            # a purchase index to track ordering of purchases per-stat.
            purchase_idx = 0
            last_purchase_at = {s: -100 for s in stats_list}

            # Record of purchases for auditing and safety
            purchase_history = []

            def buy_single(stat_name, idx):
                """Attempt a single-point limit-break purchase for stat_name.
                Returns True on success and updates points, limit_count, current_boosts
                and purchase history. Otherwise returns False.
                """
                nonlocal points, limit_count, current_boosts
                # New model: first single-point limit-break costs 2, then 3, 4, ...
                cost = limit_count + 2
                if points >= cost and can_buy_limit_for(stat_name):
                    current_boosts[idx] += 1
                    points -= cost
                    limit_count += 1
                    record_limit_purchase(stat_name)
                    purchase_history.append(('single', stat_name, cost))
                    return True
                return False

            def buy_double(stat_name, idx):
                """Attempt a two-point (Vitality/Insight) limit-break purchase.
                Returns True on success and updates points, limit_count, current_boosts
                and purchase history. Otherwise returns False.
                """
                nonlocal points, limit_count, current_boosts
                # New model: two sequential singles cost (L+2) + (L+3) = 2*L + 5
                cost = 2 * limit_count + 5
                if points >= cost and can_buy_limit_for(stat_name):
                    current_boosts[idx] += 2
                    points -= cost
                    limit_count += 2
                    record_limit_purchase(stat_name)
                    purchase_history.append(('double', stat_name, cost))
                    return True
                return False

            def can_buy_limit_for(stat_name):
                # allow in non-smart mode
                if not smart_stats:
                    return True
                last = last_purchase_at.get(stat_name, -100)
                # require at least one other purchase in between (distance >= 2)
                if purchase_idx - last < 2:
                    return False
                return True

            def record_limit_purchase(stat_name):
                nonlocal purchase_idx
                last_purchase_at[stat_name] = purchase_idx
                purchase_idx += 1
            # In smart mode, determine which offensive stat to favour for limit-breaks
            # Prefer dexterity as highest offense when its cap qualifies
            if dex_is_offense_cap:
                highest_offense = 'dexterity'
            else:
                highest_offense = 'special' if base_vals_temp.get('special', 0) >= base_vals_temp.get('strength', 0) else 'strength'
            # If the movelist is offense-heavy (many high-power special moves),
            # prefer offensive allocation and reduce defensive bias multiplier.
            defensive_bias_mult = 5.0
            if offense_heavy:
                defensive_bias_mult = 1.5
                # Favor special and dexterity when offense-heavy; if Dex cap qualifies,
                # keep dexterity as top offensive stat.
                if not dex_is_offense_cap:
                    highest_offense = 'special'
            # Decide which of Strength/Special should be considered when
            # allocating offensive points. If their max caps are unequal,
            # only the higher-cap stat should be actively advanced; when
            # equal, both are allowed.
            s_max = max_vals_temp.get('special', 0)
            st_max = max_vals_temp.get('strength', 0)
            allow_both_offense = (s_max == st_max)
            preferred_offense = 'special' if s_max > st_max else 'strength'
            # Build an explicit offense ranking (first, second, third) including dexterity
            offense_candidates = []
            # include dexterity if its cap qualifies (we treated dex as offense when dex_is_offense_cap)
            if dex_is_offense_cap:
                offense_candidates.append('dexterity')
            # include special/strength ordered by their base max preference
            if preferred_offense not in offense_candidates:
                offense_candidates.append(preferred_offense)
            other_off = 'special' if preferred_offense == 'strength' else 'strength'
            if other_off not in offense_candidates:
                offense_candidates.append(other_off)
            # ensure unique and length 3
            offense_ranking = []
            for s in offense_candidates:
                if s not in offense_ranking:
                    offense_ranking.append(s)
            while len(offense_ranking) < 3:
                for s in ['strength','special','dexterity']:
                    if s not in offense_ranking:
                        offense_ranking.append(s)
                        if len(offense_ranking) >= 3:
                            break
            top_offense, second_offense, third_offense = offense_ranking[0], offense_ranking[1], offense_ranking[2]
            # Helper: attempt to touch (plain-increment) preferred offensive stat
            # using only plain increments (no limit-breaks). Returns True if
            # preferred stat is touched after the call.
            def try_touch_preferred():
                nonlocal current_boosts, points
                p = preferred_offense
                p_idx = stats_list.index(p)
                p_base = base_vals_temp[p]
                p_cur = base_vals_temp[p] + current_boosts[p_idx]
                if p_cur > p_base:
                    return True
                # Attempt a plain increment (respecting Vitality/Insight rules)
                if p in ['vitality', 'insight']:
                    if p_cur % 2 == 0 and points >= 1:
                        current_boosts[p_idx] += 1
                        points -= 1
                        return True
                    if p_cur % 2 == 1 and points >= 2:
                        current_boosts[p_idx] += 2
                        points -= 2
                        return True
                    return False
                else:
                    if p_cur < max_vals_temp[p] and points >= 1:
                        current_boosts[p_idx] += 1
                        points -= 1
                        # mark preferred as touched
                        return True
                    return False
            # track whether preferred offensive stat has received a plain increment
            preferred_touched = False
            # Probabilistic allocation: sample stats each iteration using computed weights with a small insight bias
            # Helper: determine if there exists another stat (not vit/ins) with a
            # max >= threshold and which can accept points (either below max or
            # afford a single-point limit-break). Used to avoid limit-breaking
            # Vitality/Insight when other similar-or-higher-max stats can be filled.
            def can_spend_elsewhere(points_available, threshold_max):
                for j, s in enumerate(stats_list):
                    if s in ['vitality', 'insight']:
                        continue
                    cur = base_vals_temp[s] + current_boosts[j]
                    if cur < max_vals_temp[s]:
                        return True
                    # if other stat has a compatible max and we can afford a single-point break
                    if max_vals_temp[s] >= threshold_max and points_available >= (limit_count + 2):
                        return True
                return False

            # Safety: break if a full pass makes no progress to avoid infinite loops
            no_progress_counter = 0
            last_points = points
            while points > 0:
                weights = []
                # Determine if vitality/insight are already maxed (considering odd caps)
                vit_idx = stats_list.index('vitality')
                ins_idx = stats_list.index('insight')
                vit_cur = base_vals_temp['vitality'] + current_boosts[vit_idx]
                ins_cur = base_vals_temp['insight'] + current_boosts[ins_idx]
                vit_need = vit_cur < max_vals_temp['vitality']
                ins_need = ins_cur < max_vals_temp['insight']
                for i, stat in enumerate(stats_list):
                    # Enforce the user's policy: if strength and special have
                    # unequal caps, never allocate to the lower-cap stat.
                    if stat in ('strength', 'special') and not allow_both_offense and stat != preferred_offense:
                        weights.append(0.0)
                        continue
                    current_val = base_vals_temp[stat] + current_boosts[i]
                    if current_val >= max_vals_temp[stat]:
                        # at or above max: consider limit-break purchase if affordable
                        if stat in ['vitality', 'insight']:
                            # for vitality/insight we spend in +2 batches and require current to be odd
                            if current_val % 2 == 1:
                                # cost to add two points beyond max: (2+L) + (2+(L+1)) = 5 + 2*L
                                cost_for_two = 5 + 2 * limit_count
                                if points >= cost_for_two:
                                    # if either vitality or insight still need points,
                                    # deprioritize buying further limit-breaks on them
                                    if smart_stats and (vit_need or ins_need):
                                        w = 0.0
                                    else:
                                        # avoid limit-breaking vit/ins when other
                                        # stats with similar/higher max can be filled
                                        if smart_stats and can_spend_elsewhere(points, max_vals_temp[stat]):
                                            w = 0.0
                                        else:
                                            w = float(max_vals_temp[stat] ** 3) * 0.5
                                else:
                                    w = 0.0
                            else:
                                w = 0.0
                        else:
                            # single-point limit break cost
                            cost1 = limit_count + 2
                            if points >= cost1:
                                # Don't offer limit-break weight for non-preferred offensive
                                # stats until the preferred offensive stat has been touched.
                                if smart_stats and not allow_both_offense and not preferred_touched and stat != preferred_offense:
                                    w = 0.0
                                else:
                                    # In smart mode, set explicit priorities:
                                    if smart_stats:
                                        base_score = float(max_vals_temp[stat] ** 3)
                                        if stat == top_offense:
                                            w = base_score * 3.0
                                        elif stat == second_offense:
                                            w = base_score * 1.8
                                        elif stat == 'insight':
                                            # insight slightly preferred over vitality
                                            w = base_score * 1.2
                                        elif stat == 'vitality':
                                            w = base_score * 0.6
                                        elif stat == third_offense:
                                            # de-prioritize third offensive stat heavily
                                            w = base_score * 0.05
                                        else:
                                            w = base_score * 0.1
                                    else:
                                        w = float(max_vals_temp[stat] ** 3) * 0.5
                            else:
                                w = 0.0
                    else:
                        # Encourage filling Vitality/Insight first in smart mode
                        if smart_stats and stat in ['vitality', 'insight'] and (vit_need or ins_need):
                            # boost weight so the sampling prefers defensive fills
                            w = float(max_vals_temp[stat] ** 3) * defensive_bias_mult
                        else:
                            w = float(max_vals_temp[stat] ** 3)
                        # small bias toward Insight, with reduced multiplier
                        if stat == 'insight':
                            w *= 1.02
                        # add small jitter so choices aren't identical across runs
                        w *= (1.0 + random.uniform(-0.04, 0.04))
                    if stat in ['vitality', 'insight']:
                        current_val = base_vals_temp[stat] + current_boosts[i]
                        # require 2 points to increase vitality/insight when below max
                        if current_val < max_vals_temp[stat] and not (points >= 2 and current_val % 2 == 1):
                            w = 0.0
                    weights.append(w)
                if all(w == 0 for w in weights):
                    break
                # detect no-progress: if weights nonzero but points didn't change
                if points == last_points:
                    no_progress_counter += 1
                else:
                    no_progress_counter = 0
                last_points = points
                # if we've had several consecutive passes with no point change,
                # break to avoid infinite loops
                if no_progress_counter >= (len(stats_list) + 3):
                    break
                # Normalize weights to probabilities
                total_w = sum(weights)
                if total_w <= 0:
                    break
                probs = [w / total_w for w in weights]
                chosen_idx = random.choices(range(len(stats_list)), weights=probs, k=1)[0]
                chosen = stats_list[chosen_idx]
                if chosen in ['vitality', 'insight']:
                    current_val = base_vals_temp[chosen] + current_boosts[chosen_idx]
                    # If below max, use normal +2 batch cost
                    if current_val < max_vals_temp[chosen]:
                        if points >= 2 and current_val % 2 == 1:
                            # Avoid increasing to an even max when that would waste points
                            if (current_val + 2) == max_vals_temp[chosen] and max_vals_temp[chosen] % 2 == 0:
                                continue
                            current_boosts[chosen_idx] += 2
                            points -= 2
                        else:
                            continue
                    else:
                        # At/above max: consider limit-break two-point purchase
                        if current_val % 2 == 1:
                            cost_for_two = 2 * limit_count + 5
                            if points >= cost_for_two:
                                # Avoid buying vit/ins limit-break if other similar-or-higher
                                # max stats can still be filled first
                                if smart_stats and can_spend_elsewhere(points, max_vals_temp[chosen]):
                                    continue
                                # avoid consecutive limit-breaks into same stat
                                if not can_buy_limit_for(chosen):
                                    continue
                                if not buy_double(chosen, chosen_idx):
                                    continue
                            else:
                                continue
                        else:
                            continue
                else:
                    current_val = base_vals_temp[chosen] + current_boosts[chosen_idx]
                    if current_val < max_vals_temp[chosen]:
                        current_boosts[chosen_idx] += 1
                        points -= 1
                        # if we touched the preferred offensive stat with a plain increment, mark it
                        if chosen == preferred_offense:
                            preferred_touched = True
                    else:
                        # single-point limit-break purchase
                        cost1 = limit_count + 2
                        if points >= cost1:
                            # avoid consecutive limit-breaks into same stat
                            if not can_buy_limit_for(chosen):
                                continue
                            if not buy_single(chosen, chosen_idx):
                                continue
                        else:
                            continue
            boosts = current_boosts
            # If smart mode and there are leftover points, try to spend them on
            # the highest offensive stat (strength or special) by purchasing
            # limit-breaks when affordable. This ensures smart builds actually
            # get extra power when points remain.
            if smart_stats and points > 0:
                # Try an ordered spend: prefer highest offensive stat, then the
                # other offensive stat, then dexterity, then vitality/insight.
                # Ensure the list is unique and preserves priority order so we
                # don't accidentally process the same stat twice (which could
                # result in duplicate limit-break purchases on that stat).
                # Build ordered list respecting the preferred-offense rule: only
                # include the preferred offensive stat unless both caps equal.
                offense_other = 'special' if highest_offense == 'strength' else 'strength'
                if allow_both_offense:
                    ordered = [highest_offense, offense_other, 'dexterity', 'vitality', 'insight']
                else:
                    # prefer the precomputed preferred_offense; ensure highest_offense
                    # is used first if it matches the preferred choice
                    first = highest_offense if highest_offense in (preferred_offense, 'dexterity') else preferred_offense
                    ordered = [first, 'dexterity', 'vitality', 'insight']
                # make unique while preserving order
                seen = set()
                unique_ordered = []
                for s in ordered:
                    if s not in seen:
                        seen.add(s)
                        unique_ordered.append(s)
                ordered = unique_ordered
                # First pass: try to fill each stat to its normal max using
                # standard increments (1 point or +2 batches for Vit/Ins).
                for stat_name in ordered:
                    idx = stats_list.index(stat_name)
                    # Fill to max using the cheaper "plain" increments first.
                    while points > 0:
                        cur_val = base_vals_temp[stat_name] + current_boosts[idx]
                        if stat_name in ['vitality', 'insight']:
                            # vitality/insight use +2 batches; if even we can add
                            # a single point to make it odd first.
                            if cur_val < max_vals_temp[stat_name]:
                                if cur_val % 2 == 0 and points >= 1:
                                    current_boosts[idx] += 1
                                    points -= 1
                                    continue
                                if cur_val % 2 == 1 and points >= 2:
                                    current_boosts[idx] += 2
                                    points -= 2
                                    continue
                                break
                            else:
                                break
                        else:
                            if cur_val < max_vals_temp[stat_name]:
                                current_boosts[idx] += 1
                                points -= 1
                                continue
                            else:
                                break

                # Before attempting limit-break purchases, optionally touch offensive
                # stats. Policy: between Strength and Special, only the stat with the
                # higher max should be actively advanced unless their max caps are
                # equal — in which case both may be touched. This prevents wasting
                # plain increments on the lower offensive stat when the other is
                # strictly better.
                if smart_stats:
                    # Determine special/strength max parity
                    s_max = max_vals_temp.get('special', 0)
                    st_max = max_vals_temp.get('strength', 0)
                    allow_both_offense = (s_max == st_max)
                    # Decide preferred offensive stat between strength and special
                    preferred_offense = 'special' if s_max > st_max else 'strength'
                    # If highest_offense is dexterity, still prefer the higher of
                    # strength/special for touching decisions, but don't force the
                    # non-preferred one.
                    if allow_both_offense:
                        # when equal, touch both offensive stats (preserve highest_offense order)
                        if highest_offense in ('strength', 'special'):
                            offense_targets = [highest_offense, 'special' if highest_offense == 'strength' else 'strength']
                        else:
                            # dexterity was selected as highest_offense; prefer special first
                            offense_targets = ['special', 'strength']
                    else:
                        # only touch the preferred offensive stat
                        offense_targets = [preferred_offense]
                    # perform minimal touch on chosen targets
                    for partner in offense_targets:
                        p_idx = stats_list.index(partner)
                        p_cur = base_vals_temp[partner] + current_boosts[p_idx]
                        # If partner is untouched, try to give it one plain point
                        if p_cur == base_vals_temp[partner] and points > 0:
                            if partner in ['vitality', 'insight']:
                                # try to make odd first, then a +2 batch if possible
                                if p_cur % 2 == 0 and points >= 1:
                                    current_boosts[p_idx] += 1
                                    points -= 1
                                if p_cur % 2 == 1 and points >= 2:
                                    current_boosts[p_idx] += 2
                                    points -= 2
                            else:
                                # give one plain point if available
                                current_boosts[p_idx] += 1
                                points -= 1

                # Second pass: after filling, attempt limit-break purchases in order.
                # Instead of buying repeatedly from a single stat, iterate in passes
                # where each pass allows at most one limit-break purchase per stat.
                if points > 0:
                    made_any = True
                    while points > 0 and made_any:
                        made_any = False
                        for stat_name in ordered:
                            if points <= 0:
                                break
                            idx = stats_list.index(stat_name)
                            cur_val = base_vals_temp[stat_name] + current_boosts[idx]
                            # Vitality/Insight: two-point purchases (only when odd)
                            if stat_name in ['vitality', 'insight']:
                                cost_two = 2 * limit_count + 5
                                if cur_val % 2 == 1 and points >= cost_two:
                                    # Avoid buying vit/ins limit-break if other stats can still
                                    # be filled normally (preserve non-limit spending first)
                                    if smart_stats and can_spend_elsewhere(points, max_vals_temp[stat_name]):
                                        continue
                                    if not buy_double(stat_name, idx):
                                        continue
                                    made_any = True
                            else:
                                # single-point limit-break cost
                                cost1 = limit_count + 2
                                # Do not buy a limit-break on one offensive stat if its
                                # offensive partner has not been incremented yet.
                                if smart_stats and stat_name in (highest_offense, ('special' if highest_offense == 'strength' else 'strength')):
                                    offense_other = 'special' if highest_offense == 'strength' else 'strength'
                                    partner_idx = stats_list.index(offense_other if stat_name == highest_offense else highest_offense)
                                    partner_cur = base_vals_temp[stats_list[partner_idx]] + current_boosts[partner_idx]
                                    # if partner hasn't been incremented above base, skip limit-breaks here
                                    if partner_cur == base_vals_temp[stats_list[partner_idx]]:
                                        continue
                                # If preferred offense hasn't been touched, try to touch it
                                if smart_stats and preferred_offense and stat_name != preferred_offense:
                                    pref_idx = stats_list.index(preferred_offense)
                                    pref_cur = base_vals_temp[preferred_offense] + current_boosts[pref_idx]
                                    if pref_cur == base_vals_temp[preferred_offense]:
                                        if not try_touch_preferred():
                                            # couldn't touch preferred; skip limit-break on others
                                            continue
                                if points >= cost1:
                                    if not buy_single(stat_name, idx):
                                        continue
                                    made_any = True
                boosts = current_boosts
            # If still have points, try to purchase additional limit-breaks
            # across the ordered list before doing any tiny remainder distribution.
            # Ensure `attempts` is always defined for later loops.
            attempts = 0
            if smart_stats and points > 0:
                # Interleaved passes: try at most one limit-break per stat per pass
                made_any = True
                while points > 0 and made_any:
                    made_any = False
                    for stat_name in ordered:
                        if points <= 0:
                            break
                        idx = stats_list.index(stat_name)
                        cur_val = base_vals_temp[stat_name] + current_boosts[idx]
                        if stat_name in ['vitality', 'insight']:
                            cost_two = 2 * limit_count + 5
                            if cur_val % 2 == 1 and points >= cost_two:
                                # Avoid buying vit/ins limit-break if other stats can still
                                # be filled normally
                                if smart_stats and can_spend_elsewhere(points, max_vals_temp[stat_name]):
                                    continue
                                # avoid consecutive limit-breaks into the same stat
                                if not can_buy_limit_for(stat_name):
                                    continue
                                if not buy_double(stat_name, idx):
                                    continue
                                made_any = True
                        else:
                            cost1 = limit_count + 2
                            # same guard: avoid breaking one offensive stat while
                            # its partner is untouched
                            if smart_stats and stat_name in (highest_offense, ('special' if highest_offense == 'strength' else 'strength')):
                                offense_other = 'special' if highest_offense == 'strength' else 'strength'
                                partner_idx = stats_list.index(offense_other if stat_name == highest_offense else highest_offense)
                                partner_cur = base_vals_temp[stats_list[partner_idx]] + current_boosts[partner_idx]
                                if partner_cur == base_vals_temp[stats_list[partner_idx]]:
                                    continue
                            # If preferred offense hasn't been touched, try to touch it
                            if smart_stats and preferred_offense and stat_name != preferred_offense:
                                pref_idx = stats_list.index(preferred_offense)
                                pref_cur = base_vals_temp[preferred_offense] + current_boosts[pref_idx]
                                if pref_cur == base_vals_temp[preferred_offense]:
                                    if not try_touch_preferred():
                                        continue
                            if points >= cost1:
                                # avoid consecutive limit-breaks into the same stat
                                if not can_buy_limit_for(stat_name):
                                    continue
                                if not buy_single(stat_name, idx):
                                    continue
                                made_any = True
                # If points still remain, distribute them round-robin over the ordered list
                if points > 0:
                    # Distribute remaining points across the ordered list but
                    # respect limit-break costs. Iterate passes until no spend
                    # occurs in a full pass.
                    made_spend = True
                    while points > 0 and made_spend:
                        made_spend = False
                        for stat_name in ordered:
                            if points <= 0:
                                break
                            idx = stats_list.index(stat_name)
                            cur_val = base_vals_temp[stat_name] + current_boosts[idx]
                            if stat_name in ['vitality', 'insight']:
                                # below max: need +2 batches (or +1 to make odd)
                                if cur_val < max_vals_temp[stat_name]:
                                    # if even, try to add single point to make odd
                                    if cur_val % 2 == 0 and points >= 1:
                                        current_boosts[idx] += 1
                                        points -= 1
                                        made_spend = True
                                    # if odd and have 2 points, add batch
                                    elif cur_val % 2 == 1 and points >= 2:
                                        current_boosts[idx] += 2
                                        points -= 2
                                        made_spend = True
                                else:
                                    # at/above max: attempt limit-break two-point purchase
                                    # Use centralized helper to ensure global sequential costing
                                    if cur_val % 2 == 1:
                                        if not can_buy_limit_for(stat_name):
                                            pass
                                        else:
                                            if buy_double(stat_name, idx):
                                                made_spend = True
                            else:
                                if cur_val < max_vals_temp[stat_name]:
                                    current_boosts[idx] += 1
                                    points -= 1
                                    made_spend = True
                                else:
                                    # at/above max: attempt single-point limit-break via helper
                                    if not can_buy_limit_for(stat_name):
                                        pass
                                    else:
                                        if buy_single(stat_name, idx):
                                            made_spend = True
                    boosts = current_boosts
            else:
                # Normal mode: distribute points randomly, and allow random limit-break purchases
                current_boosts = boosts[:]
                limit_count = 0
                # Non-smart mode behaviour:
                # 1) Randomly fill plain increments until no plain increments remain.
                # 2) Then exhaustively purchase single-point limit-breaks while
                #    affordable, choosing a random eligible maxed stat each time.
                # This ensures all affordable breaks are bought and applied randomly.
                # Step 1: fill plain increments randomly
                attempts = 0
                while points > 0:
                    plain_candidates = [i for i, s in enumerate(stats_list) if (base_vals_temp[s] + current_boosts[i]) < max_vals_temp[s]]
                    if not plain_candidates:
                        break
                    idx = random.choice(plain_candidates)
                    current_boosts[idx] += 1
                    points -= 1
                    attempts += 1
                    # safety bail-out
                    if attempts > 1000:
                        break
                # Step 2: exhaustively buy single-point limit-breaks while affordable.
                made_buy = True
                while points >= (limit_count + 2) and made_buy:
                    made_buy = False
                    eligible = [i for i, s in enumerate(stats_list)
                                if (base_vals_temp[s] + current_boosts[i]) >= max_vals_temp[s]
                                and can_buy_limit_for(stats_list[i])]
                    if not eligible:
                        break
                    idx = random.choice(eligible)
                    if buy_single(stats_list[idx], idx):
                        made_buy = True
                        # loop will continue while more breaks are affordable
                # If any plain increments remain (rare), they'll be handled by the
                # subsequent forced-spend/fallback code below.
            boosts = current_boosts
        # Final safety: if any points remain due to affordability logic, forcibly
        # spend them so no leftover points remain. Honor 2-point batches for
        # vitality/insight where possible; otherwise distribute to other stats.
        if points > 0:
            current_boosts = boosts[:]
            i = 0
            # Final safety: break if no progress after a full rotation
            i = 0
            last_points = points
            no_progress_counter = 0
            while points > 0:
                stat = stats_list[i % len(stats_list)]
                idx = stats_list.index(stat)
                cur_val = base_vals_temp[stat] + current_boosts[idx]
                # If below max, spend plain increments as before
                if cur_val < max_vals_temp[stat]:
                    if stat in ['vitality', 'insight']:
                        if cur_val % 2 == 0 and points >= 1:
                            current_boosts[idx] += 1
                            points -= 1
                        elif cur_val % 2 == 1 and points >= 2:
                            current_boosts[idx] += 2
                            points -= 2
                        else:
                            # not enough points to complete batch; try next stat
                            pass
                    else:
                        current_boosts[idx] += 1
                        points -= 1
                else:
                    # stat at/above max: attempt purchases via helpers so cost is global
                    if stat in ['vitality', 'insight']:
                        # attempt purchases:
                        if cur_val % 2 == 1:
                            # odd-valued vit/ins can accept a +2 batch in smart mode
                            if smart_stats:
                                if buy_double(stat, idx):
                                    pass
                                else:
                                    pass
                            else:
                                # non-smart: treat like normal stat, try a single-point purchase
                                cost1 = limit_count + 2
                                if points >= cost1 and can_buy_limit_for(stat):
                                    if buy_single(stat, idx):
                                        pass
                        else:
                            # even-valued vit/ins at/above max: in non-smart mode allow single-point purchase
                            if not smart_stats:
                                cost1 = limit_count + 2
                                if points >= cost1 and can_buy_limit_for(stat):
                                    if buy_single(stat, idx):
                                        pass
                            else:
                                # smart mode: even-valued vit/ins can't take +2 cleanly
                                pass
                    else:
                        # attempt single-point limit-break
                        if buy_single(stat, idx):
                            pass
                        else:
                            # couldn't buy; try next stat
                            pass
                i += 1
                # If we completed a full rotation over stats without reducing points, increment counter
                if i % len(stats_list) == 0:
                    if points == last_points:
                        no_progress_counter += 1
                    else:
                        no_progress_counter = 0
                    last_points = points
                    if no_progress_counter >= 3:
                        break
            boosts = current_boosts
        rank_name = get_rank(level)
        social_points = 4 + (rank_values.get(rank_name.lower(), 1) - 1) * 2
        social_boosts = [0] * 5
        for _ in range(social_points):
            social_boosts[random.randint(0, 4)] += 1
        insight_boost = 0
        base_vals = {}
        new_vals = {}
        max_vals = {}
        stat_lines = []
        for i, stat in enumerate(stats_list):
            val = data.get(stat, "0/10")
            base = int(val.split('/')[0]) if '/' in val else 0
            max_val = int(val.split('/')[1]) if '/' in val else 10
            # Allow new_val to exceed max_val when limit-breaks were purchased
            new_val = base + boosts[i]
            base_vals[stat] = base
            new_vals[stat] = new_val
            max_vals[stat] = max_val
            if stat == "insight":
                insight_boost = new_val
            bar = "⬤" * new_val + "⭘" * (max_val - new_val)
            stat_lines.append(f"\n**{stat.title()}**: {bar} `{new_val}/{max_val}`")
        for i, stat in enumerate(social_list):
            val = data.get(stat, "1/5")
            base = int(val.split('/')[0]) if '/' in val else 1
            max_val = int(val.split('/')[1]) if '/' in val else 5
            new_val = min(base + social_boosts[i], max_val)
            base_vals[stat] = base
            new_vals[stat] = new_val
            max_vals[stat] = max_val
            bar = "⬤" * new_val + "⭘" * (max_val - new_val)
            stat_lines.append(f"\n**{stat.title()}**: {bar} `{new_val}/{max_val}`")
        # Slight probabilistic post-process: if Insight <= Vitality, with small probability
        # transfer 2 points from Vitality to Insight (if feasible). This yields a slightly
        # higher-than-50% chance for Insight to be greater while keeping randomness.
        try:
            cur_vit = new_vals.get('vitality', 0)
            cur_ins = new_vals.get('insight', 0)
            # probability target slightly above 50% (reduced to be conservative)
            # Tie-break Bernoulli approach: when Insight <= Vitality, attempt a single
            # probabilistic adjustment with a target probability slightly above 50%.
            # This flips a single coin (p_target) and if it succeeds, transfers 2 points
            # from Vitality to Insight when possible. This is easier to control than
            # repeated small p_bias adjustments.
            p_target = 0.12
            # only attempt adjustment when values are equal to avoid pushing
            # low Vitality cases down too often
            if cur_ins == cur_vit and random.random() < p_target:
                # attempt to move 2 points from vitality to insight if within bounds
                can_take_from_vit = (cur_vit - 2) >= base_vals.get('vitality', 0)
                can_add_to_ins = (cur_ins + 2) <= max_vals.get('insight', 10)
                if can_take_from_vit and can_add_to_ins:
                    new_vals['vitality'] = cur_vit - 2
                    new_vals['insight'] = cur_ins + 2
                elif can_add_to_ins:
                    new_vals['insight'] = cur_ins + 2
                elif can_take_from_vit:
                    new_vals['vitality'] = cur_vit - 2
        except Exception:
            pass
        selected_moves = random.sample(moves_list, min(new_vals.get('insight', 0) + 2, len(moves_list))) if moves_list else []
        original_moves_list = moves_list[:]  # keep original pool for fallbacks
        if boss and evil:  # evil mode
            # Filter out excluded moves
            filtered_moves = []
            for m in moves_list:
                if m in ['Explosion', 'Self Destruct']:
                    continue
                move_data = load_move(m)
                if move_data:
                    move_data = normalize_keys(move_data)
                    effect = move_data.get('effect', '').lower()
                    if 'charge' in effect or 'recharge' in effect:
                        continue
                filtered_moves.append(m)
            # Filter out low power moves without keywords
            def is_good_move(m):
                move_data = load_move(m)
                if not move_data:
                    return False
                move_data = normalize_keys(move_data)
                category = move_data.get('category', '')
                if category not in ['Physical', 'Special']:
                    return True  # support ok
                # Prefer numeric 'power' field when available
                try:
                    power = int(move_data.get('power', 0))
                except (TypeError, ValueError):
                    power = 0
                    # Fallback: parse damage string for a "+ N" suffix (eg. 'Rank + 3')
                    damage_str = move_data.get('damage', '')
                    if isinstance(damage_str, str) and '+' in damage_str:
                        parts = damage_str.split('+')
                        if parts[1].strip().isdigit():
                            power = int(parts[1].strip())
                # allow multi-hit or high-crit moves to bypass the low-power cutoff
                effect = move_data.get('effect', '').lower()
                multi_hit = any(kw in effect for kw in ['successive', 'double', 'triple', 'multi-hit', 'hits'])
                try:
                    crit_val = int(move_data.get('crit', '0'))
                except Exception:
                    crit_val = 0
                if power <= 2 and not multi_hit and crit_val == 0:
                    return False
                return True
            filtered_moves = [m for m in filtered_moves if is_good_move(m)]
            moves_list = filtered_moves
            selected_moves = []
            spdef = new_vals.get('insight', 0)
            # Prioritize powerful support and aggressive attacking moves.
            evil_support = ['Swords Dance', 'Agility', 'Nasty Plot', 'Iron Defense', 'Amnesia', 'Cosmic Power']
            available_evil_support = [m for m in evil_support if m in moves_list]
            # Number of support moves equals Special Defense (spdef)
            num_support = min(spdef, len(available_evil_support))
            selected_moves.extend(available_evil_support[:num_support])

            # Aggressive attack selection: prefer All Foes / Area moves with high power,
            # slightly favour multi-hit (successive) moves and STAB.
            def move_power_and_score(m):
                mv = load_move(m)
                if not mv:
                    return (-1, -1, -1)
                mv = normalize_keys(mv)
                category = mv.get('category', '')
                if category not in ['Physical', 'Special']:
                    return (-1, -1, -1)
                # get numeric power preference
                try:
                    p = int(mv.get('power', 0))
                except (TypeError, ValueError):
                    p = 0
                    damage_str = mv.get('damage', '')
                    if isinstance(damage_str, str) and '+' in damage_str:
                        parts = damage_str.split('+')
                        if parts[1].strip().isdigit():
                            p = int(parts[1].strip())
                # effect-based bonuses
                effect = mv.get('effect', '').lower()
                multi_hit = any(kw in effect for kw in ['successive', 'double', 'triple', 'multi-hit', 'hits'])
                successive_bonus = 150 if multi_hit else 0
                # detect explicit recoil flag or textual mention
                recoil_flag = bool(mv.get('recoil', False)) or ('recoil' in effect)
                # target preference: All Foes/Area gets a boost (we favor multi-target damage)
                target = mv.get('target', '')
                target_bonus = 50 if ('All Foes' in target or 'Area' in target) else 0
                # STAB preference
                stab_bonus = 20 if mv.get('type', '') in data.get('types', []) else 0
                try:
                    crit_bonus = int(mv.get('crit', '0')) * 10
                except Exception:
                    crit_bonus = 0
                # If the move causes recoil/self-damage, avoid it unless it meets
                # a reasonable exception (STAB, very high power, multi-hit, or high crit).
                if recoil_flag:
                    allowed_recoil = False
                    if stab_bonus > 0:
                        allowed_recoil = True
                    if p >= 5:
                        allowed_recoil = True
                    if multi_hit:
                        allowed_recoil = True
                    if crit_bonus >= 10:
                        allowed_recoil = True
                    if not allowed_recoil:
                        # exclude this move from evil candidates
                        return (-1, p, successive_bonus)
                    # otherwise allow but slightly penalize recoil moves so non-recoil
                    # options are preferred when equivalent
                    recoil_penalty = -40
                else:
                    recoil_penalty = 0

                # large negative for extremely low-power single hit moves
                if p <= 2 and not multi_hit and crit_bonus == 0:
                    return (-1, -1, -1)
                score = p + successive_bonus + target_bonus + stab_bonus + crit_bonus
                score += recoil_penalty
                # Also return power for tie-breaking
                return (score, p, successive_bonus)

            # Build candidates excluding already chosen supports
            candidate_attacks = [m for m in moves_list if m not in selected_moves]
            scored = [(m, ) + move_power_and_score(m) for m in candidate_attacks]
            # Filter out invalid entries
            scored = [s for s in scored if s[1] >= 0]
            # Sort by score then power then multi-hit bonus
            scored.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)
            # Choose up to spdef attacks (number of attacking moves equals Special Defense)
            num_attack = spdef
            top_attacks = [m for m, *_ in scored][:num_attack]
            selected_moves.extend(top_attacks)
            # Fill remaining slots up to Insight+2 with any high-power moves if needed
            selected_moves = list(dict.fromkeys(selected_moves))
            remaining_slots = (insight_boost + 2) - len(selected_moves)
            if remaining_slots > 0:
                remaining = [m for m in moves_list if m not in selected_moves]
                # sort remaining by fallback power
                remaining.sort(key=lambda m: (move_power_and_score(m)[0], move_power_and_score(m)[1]), reverse=True)
                selected_moves.extend(remaining[:remaining_slots])
        if boss:  # smart_stats
            selected_moves = []
            spdef = new_vals.get('insight', 0)
            highest_stat = 'special' if new_vals['special'] >= new_vals['strength'] else 'strength'
            # Categorize moves
            attacking_moves = []
            support_moves = []
            stab_moves = []
            for m in moves_list:
                move_data = load_move(m)
                if move_data:
                    move_data = normalize_keys(move_data)
                    category = move_data.get('category', '')
                    if category == 'Support':
                        support_moves.append(m)
                    elif category in ['Physical', 'Special']:
                        attacking_moves.append(m)
                        move_type = move_data.get('type', '')
                        if move_type in data.get('types', []):
                            stab_moves.append(m)
            # Enforce absolute exclusion: if one offensive stat is preferred,
            # drop attacking moves that use the non-preferred offensive stat.
            if highest_stat == 'special':
                # keep only Special moves
                attacking_moves = [m for m in attacking_moves if normalize_keys(load_move(m)).get('category','') == 'Special']
                stab_moves = [m for m in stab_moves if normalize_keys(load_move(m)).get('category','') == 'Special']
            elif highest_stat == 'strength':
                # keep only Physical moves
                attacking_moves = [m for m in attacking_moves if normalize_keys(load_move(m)).get('category','') == 'Physical']
                stab_moves = [m for m in stab_moves if normalize_keys(load_move(m)).get('category','') == 'Physical']
            # Use Special Defense (ceil(insight/2)) to determine counts for both
            spdef_count = math.ceil(new_vals.get('insight', 0) / 2)
            num_attacking = spdef_count
            num_stab = min(num_attacking, len(stab_moves))
            # choose STAB moves from top candidates
            # Determine which offensive stat is preferred (based on final new_vals)
            highest_stat = 'special' if new_vals['special'] >= new_vals['strength'] else 'strength'
            non_preferred_stat = 'strength' if highest_stat == 'special' else 'special'

            def stab_key_wrapper(m):
                # Compute base tuple
                tup = compute_stab_key(m)
                if tup[0] < 0:
                    return tup
                # Heavily penalize moves that use the non-preferred offensive stat
                mv = load_move(m)
                if mv:
                    mv = normalize_keys(mv)
                    cat = mv.get('category', '')
                    if (cat == 'Physical' and non_preferred_stat == 'strength') or (cat == 'Special' and non_preferred_stat == 'special'):
                        # return a very low tuple to push this move to the bottom
                        return (-99999, -99999, -99999, -99999)
                return tup
            chosen_stab = pick_from_top([m for m in stab_moves if m not in selected_moves], stab_key_wrapper, num_stab)
            selected_moves.extend(chosen_stab)
            remaining_attacking = num_attacking - len(chosen_stab)
            candidate = [m for m in attacking_moves if m not in selected_moves]
            def candidate_key(m):
                move_data = load_move(m)
                if not move_data:
                    return -1
                move_data = normalize_keys(move_data)
                category = move_data.get('category', '')
                if category in ['Physical', 'Special']:
                    try:
                        damage_str = move_data.get('damage', '0')
                        if '+' in damage_str:
                            parts = damage_str.split('+')
                            power = int(parts[1].strip()) if parts[1].strip().isdigit() else 0
                        else:
                            power = int(damage_str)
                    except ValueError:
                        power = 0
                    effect = move_data.get('effect', '').lower()
                    successive_bonus = 100 if any(kw in effect for kw in ['successive', 'double', 'triple']) else 0
                    try:
                        crit_bonus = int(move_data.get('crit', '0')) * 10
                    except ValueError:
                        crit_bonus = 0
                    # If this move uses the non-preferred offensive stat, heavily penalize it
                    if (category == 'Physical' and non_preferred_stat == 'strength') or (category == 'Special' and non_preferred_stat == 'special'):
                        return -999999
                    return power + successive_bonus + crit_bonus
                return -1
            # choose remaining attacking moves from top candidates
            chosen_attack = pick_from_top(candidate, candidate_key, remaining_attacking)
            selected_moves.extend(chosen_attack)
            # If we couldn't find enough attacking moves in the filtered pool
            # and we have an original pool (pre-evil filters), try to pull
            # attacking moves from there to meet the minimum requirement.
            if len([m for m in selected_moves if load_move(m) and move_category(m) in ['Physical','Special']]) < num_attacking and original_moves_list is not None:
                needed = num_attacking - len([m for m in selected_moves if load_move(m) and move_category(m) in ['Physical','Special']])
                fallback_candidates = []
                for m in original_moves_list:
                    if m in selected_moves:
                        continue
                    mv = load_move(m)
                    if not mv:
                        continue
                    mv = normalize_keys(mv)
                    if mv.get('category','') in ['Physical','Special']:
                        # respect preferred offensive stat when selecting fallbacks
                        if highest_stat == 'special' and mv.get('category','') != 'Special':
                            continue
                        if highest_stat == 'strength' and mv.get('category','') != 'Physical':
                            continue
                        fallback_candidates.append(m)
                # rank fallback candidates by same candidate_key
                fallback_candidates.sort(key=candidate_key, reverse=True)
                to_take = fallback_candidates[:needed]
                selected_moves.extend(to_take)
            # Choose support moves equal to Special Defense
            num_support = min(spdef_count, len(support_moves))
            def support_key(m):
                move_data = load_move(m)
                if not move_data:
                    return False
                move_data = normalize_keys(move_data)
                acc = move_data.get('accuracy', '').lower()
                return 'insight' in acc
            # choose support moves with some randomness among top candidates
            support_candidates = [m for m in support_moves if m not in selected_moves]
            chosen_support = pick_from_top(support_candidates, lambda m: 1 if support_key(m) else 0, num_support)
            selected_moves.extend(chosen_support)
            selected_moves = list(dict.fromkeys(selected_moves))
            remaining_slots = (insight_boost + 2) - len(selected_moves)
            if remaining_slots > 0:
                candidate = [m for m in moves_list if m not in selected_moves]
                # Filter out non-preferred offensive moves from remaining fill
                if highest_stat == 'special':
                    candidate = [m for m in candidate if move_category(m) != 'Physical']
                elif highest_stat == 'strength':
                    candidate = [m for m in candidate if move_category(m) != 'Special']
                random.shuffle(candidate)
                selected_moves.extend(candidate[:remaining_slots])


        if format_type == "standard":
            rank = get_rank(level).capitalize()
            rank_emoji = get_badge_emoji(rank.lower())
            type_str = " / ".join(get_type_emoji(t) for t in data.get("types", []))
            hp_calc = (data.get('base_hp', 0) + new_vals.get('vitality', 0)) * 2
            out = f"## {rank_emoji} {data.get('name','Unknown')}\n**Level {level}**\n### Stats {type_str}\n```\nHP: {hp_calc}\nWillpower: {new_vals.get('insight', 0) + 2}\n\n"
            for stat in stats_list:
                val = new_vals.get(stat, 0)
                maxv = max_vals.get(stat, 10)
                if val > maxv:
                    bar = "⬤" * maxv + "⧳" * (val - maxv)
                else:
                    bar = "⬤" * val + "⭘" * (maxv - val)
                name = stat.title()
                pad = ' ' * (9 - len(name))
                out += f"{name}:{pad} {val:2} |{bar}\n"
            out += f"\nDefense: {math.ceil(new_vals.get('vitality', 0) / 2)}\nSpecial Defense: {math.ceil(new_vals.get('insight', 0) / 2)}\nActive Move Limit: {new_vals.get('insight', 0) + 2}\n\n"
            for stat in social_list:
                val = new_vals.get(stat, 0)
                maxv = max_vals.get(stat, 5)
                if val > maxv:
                    bar = "⬤" * maxv + "⧳" * (val - maxv)
                else:
                    bar = "⬤" * val + "⭘" * (maxv - val)
                name = stat.title()
                pad = ' ' * (6 - len(name))
                out += f"{name}:{pad} {val:2} |{bar}\n"
            out += f"```\n### Ability\n- {selected_ability}\n### Moves\n"
            for move in selected_moves:
                out += f"- {move}\n"
            out += "\n"
        elif format_type == "detailed":
            gender = random.choice(["(M)", "(F)"])
            rank = get_rank(level).capitalize()
            out = f"{data.get('name','Unknown')} {gender} | **Lv.{level} ({rank})**\n"
            out += f"**Types**: {' / '.join(f'{get_type_emoji(t)} {t}' for t in data.get('types', []))}\n"
            hp_calc = (data.get('base_hp', 0) + new_vals.get('vitality', 0)) * 2
            def_calc = math.ceil(new_vals.get('vitality', 0) / 2)
            spdef_calc = math.ceil(new_vals.get('insight', 0) / 2)
            out += f"```\nHP: {hp_calc}  |  Def: {def_calc}  |  SpDef: {spdef_calc}\n"
            out += f"STR:  {new_vals.get('strength', 0)} / {max_vals.get('strength', 10)}      Tough:  {new_vals.get('tough', 0)} / {max_vals.get('tough', 5)}\n"
            out += f"DEX:  {new_vals.get('dexterity', 0)} / {max_vals.get('dexterity', 10)}      Cool:   {new_vals.get('cool', 0)} / {max_vals.get('cool', 5)}\n"
            out += f"VIT:  {new_vals.get('vitality', 0)} / {max_vals.get('vitality', 10)}      Beauty: {new_vals.get('beauty', 0)} / {max_vals.get('beauty', 5)}\n"
            out += f"SPE:  {new_vals.get('special', 0)} / {max_vals.get('special', 10)}      Cute:   {new_vals.get('cute', 0)} / {max_vals.get('cute', 5)}\n"
            out += f"INS:  {new_vals.get('insight', 0)} / {max_vals.get('insight', 10)}      Clever: {new_vals.get('clever', 0)} / {max_vals.get('clever', 5)}\n"
            out += "```\n"
            out += f"**Ability**: {selected_ability}\n"
            ability_data = load_ability(selected_ability)
            if ability_data and 'effect' in ability_data:
                out += f"*{ability_data['effect']}*\n"
            rank_name = get_rank(level).lower()
            rank_val = rank_values.get(rank_name, 1)
            out += "## Moves\n"
            # Purchase audit is internal-only. Toggle DEBUG_ENCOUNTER_AUDIT to True
            # during development to see the audit. Default is False so players
            # won't see internal purchase history in the detailed output.
            DEBUG_ENCOUNTER_AUDIT = False
            if DEBUG_ENCOUNTER_AUDIT:
                try:
                    initial_points_total = 3 + level
                    total_limit_spent = 0
                    for ptype, sname, cost in purchase_history:
                        total_limit_spent += int(cost)
                    out += f"\n## Purchase Audit\nInitial Points: {initial_points_total}\nTotal spent on limit-breaks: {total_limit_spent}\nRemaining points (should be >=0): {points}\nPurchase History: {purchase_history}\n"
                except Exception:
                    pass
            for move_name in selected_moves:
                move_data = load_move(move_name)
                if move_data:
                    move_data = normalize_keys(move_data)
                    move_type = move_data.get('type', 'Normal')
                    category = move_data.get('category', 'Physical')
                    target = move_data.get('target', 'Foe')
                    # Parse power and damage descriptor. Moves in the data may
                    # use keys like `damage`, `damage1`, `damage2` and likewise
                    # `power` or `power1`/`power2`. Prefer explicit damage keys
                    # when present. Also accept a `damage` string like
                    # 'Special + 6' and prefer the +N suffix when present.
                    damage_field = None
                    for k in ('damage', 'damage1', 'damage2'):
                        if k in move_data and move_data.get(k):
                            damage_field = move_data.get(k)
                            break

                    # collect power from obvious fields
                    power = 0
                    # try primary power field first
                    if 'power' in move_data and move_data.get('power') is not None:
                        try:
                            power = int(move_data.get('power'))
                        except Exception:
                            power = 0
                    # fallback to power1/power2
                    if power == 0:
                        for pk in ('power1', 'power2'):
                            if pk in move_data and move_data.get(pk) is not None:
                                try:
                                    power = int(move_data.get(pk))
                                except Exception:
                                    power = 0
                                break

                    # Now parse damage descriptor and optional "+N" suffix
                    if isinstance(damage_field, str) and '+' in damage_field:
                        parts = damage_field.split('+')
                        left = parts[0].strip().lower()
                        right = parts[1].strip()
                        try:
                            # +N in the damage string overrides the numeric power
                            power = int(right)
                        except Exception:
                            # leave previously-determined `power` as-is
                            pass
                        damage_stat = left
                    else:
                        # If damage_field is present and is a plain stat name, use it
                        if isinstance(damage_field, str):
                            damage_stat = damage_field.lower()
                        else:
                            # final fallback to an explicit `damage` key or 'strength'
                            damage_stat = move_data.get('damage', 'Strength')
                            if isinstance(damage_stat, str):
                                damage_stat = damage_stat.lower()
                            else:
                                damage_stat = 'strength'
                    # Prefer accuracy, accuracy1, accuracy2 keys (some moves use
                    # Accuracy1/Accuracy2 in the JSON). Normalize to lowercase.
                    accuracy_field = None
                    for ak in ('accuracy', 'accuracy1', 'accuracy2'):
                        if ak in move_data and move_data.get(ak):
                            accuracy_field = move_data.get(ak)
                            break
                    if accuracy_field is None:
                        accuracy_field = 'Dexterity'
                    # Normalize to lowercase if string
                    accuracy_stat = accuracy_field.lower() if isinstance(accuracy_field, str) else str(accuracy_field)
                    effect = move_data.get('effect', '')
                    # Calculate numbers
                    # Keep original descriptor for display decisions
                    damage_descriptor = damage_stat
                    if "/" in damage_stat:
                        dmg_parts = damage_stat.split("/")
                        dmg1 = new_vals.get(dmg_parts[0].lower(), 0) + power
                        dmg2 = new_vals.get(dmg_parts[1].lower(), 0) + power
                        dmg_num = f"{dmg1}/{dmg2}"
                    elif damage_stat == 'rank':
                        dmg_num = rank_val + power
                    else:
                        dmg_num = new_vals.get(damage_stat, 0) + power

                    # Always display numeric damage (user requested numeric
                    # calculation). If dmg_num is a slash form keep it; else
                    # convert to integer string.
                    if isinstance(dmg_num, str):
                        display_dmg = dmg_num
                    else:
                        try:
                            display_dmg = str(int(dmg_num))
                        except Exception:
                            display_dmg = str(dmg_num)
                    # Calculate numeric accuracy. Accept 'rank' as a valid
                    # descriptor meaning add the numeric rank value.
                    if isinstance(accuracy_stat, str) and "/" in accuracy_stat:
                        acc_parts = [p.strip().lower() for p in accuracy_stat.split("/")]
                        acc1 = new_vals.get(acc_parts[0], 0) + rank_val
                        acc2 = new_vals.get(acc_parts[1], 0) + rank_val
                        acc_num = f"{acc1}/{acc2}"
                    else:
                        if isinstance(accuracy_stat, str) and accuracy_stat == 'rank':
                            acc_num = rank_val
                        else:
                            # stat name or numeric fallback
                            try:
                                acc_num = new_vals.get(accuracy_stat, 0) + rank_val
                            except Exception:
                                try:
                                    acc_num = int(accuracy_stat) + rank_val
                                except Exception:
                                    acc_num = rank_val
                    stab = move_type in data.get('types', [])
                    dmg_str = f"{display_dmg} + STAB" if stab else display_dmg
                    out += f"**{move_name}** – {get_type_emoji(move_type)} {move_type} | {category} | {target}\n"
                    out += f"ACC: **{acc_num}**"
                    if category in ["Physical", "Special"]:
                        out += f" | DMG: **{dmg_str}**"
                    out += f"\n"
                    if effect:
                        out += f"{effect}\n"
                    out += "\n"
        output += out + "\n\n"
    return output

class ToggleMovesButton(ui.Button):
    def __init__(self, top_text, moves_text, showing=False):
        label = "Hide Moves" if showing else "Show Moves"
        custom_id = "hide_moves" if showing else "show_moves"
        super().__init__(label=label, style=discord.ButtonStyle.primary, custom_id=custom_id)
        self.top_text = top_text
        self.moves_text = moves_text
        self.showing = showing
        # Track any extra messages (followups/channel sends) created when
        # showing large move sections so we can delete them when hiding.
        self.extra_message_ids = []

    async def callback(self, interaction):
        # Determine the new content and state
        showing_now = (self.custom_id == "show_moves")
        if showing_now:
            new_content = self.top_text + self.moves_text
            new_showing = True
        else:
            new_content = self.top_text
            new_showing = False

        # Create a fresh button instance for the new state and preserve any
        # extra message IDs so the toggle can delete them later.
        new_button = ToggleMovesButton(self.top_text, self.moves_text, new_showing)
        new_button.extra_message_ids = list(getattr(self, 'extra_message_ids', []) or [])
        new_view = ui.View()
        new_view.add_item(new_button)

        try:
            if len(new_content) > 2000:
                # Edit original to top_text (can't include full moves in the
                # original when length exceeds 2000). Send moves as a followup
                # and track the followup/channel message id for later deletion.
                await interaction.response.edit_message(content=self.top_text, view=new_view)
                if showing_now:
                    try:
                        msg = await interaction.followup.send(self.moves_text)
                        new_button.extra_message_ids.append(getattr(msg, 'id', None))
                    except Exception:
                        if interaction.channel:
                            try:
                                msg = await interaction.channel.send(self.moves_text)
                                new_button.extra_message_ids.append(getattr(msg, 'id', None))
                            except Exception:
                                pass
            else:
                await interaction.response.edit_message(content=new_content, view=new_view)
        except Exception:
            # If the original interaction is no longer valid, try followup,
            # then finally send via channel. Track any IDs created.
            try:
                if len(new_content) > 2000:
                    await interaction.followup.send(self.top_text)
                    if showing_now:
                        msg = await interaction.followup.send(self.moves_text)
                        new_button.extra_message_ids.append(getattr(msg, 'id', None))
                else:
                    await interaction.followup.send(new_content)
            except Exception:
                if interaction.channel:
                    sent = await interaction.channel.send(new_content if len(new_content) <= 2000 else new_content[:2000])
                    if showing_now and len(new_content) > 2000:
                        new_button.extra_message_ids.append(getattr(sent, 'id', None))

        # If we're hiding, attempt to delete any extra messages that were
        # created when we previously showed the moves.
        if not showing_now:
            for mid in list(getattr(self, 'extra_message_ids', []) or []):
                try:
                    if getattr(interaction, 'followup', None):
                        await interaction.followup.delete_message(mid)
                except Exception:
                    try:
                        if interaction.channel and mid:
                            msg = await interaction.channel.fetch_message(mid)
                            if msg:
                                await msg.delete()
                    except Exception:
                        pass

async def send_big_msg(ctx, arg, wrap_in_code_block, view):
    if wrap_in_code_block:
        arg = f"```{arg}```"
    if "## Moves" in arg and "### Moves" not in arg:
        parts = arg.split("## Moves", 1)
        if len(parts) == 2:
            top = parts[0] + "\n"
            moves_section = "## Moves" + parts[1]
            button_view = ui.View()
            button_view.add_item(ToggleMovesButton(top, moves_section, showing=False))
            # Try to send via the interaction response, fall back to followup
            try:
                await ctx.response.send_message(top, view=button_view)
            except Exception:
                try:
                    await ctx.followup.send(top)
                except Exception:
                    # Final fallback: channel send
                    if getattr(ctx, 'channel', None):
                        await ctx.channel.send(top)
            return
    # Normal handling
    if len(arg) <= 2000:
        try:
            if view:
                await ctx.response.send_message(arg, view=view)
            else:
                await ctx.response.send_message(arg)
        except Exception:
            try:
                if view:
                    await ctx.followup.send(arg)
                else:
                    await ctx.followup.send(arg)
            except Exception:
                if getattr(ctx, 'channel', None):
                    await ctx.channel.send(arg)
    else:
        # Send first chunk using response/fallbacks
        first_chunk = arg[:2000]
        remaining = arg[2000:]
        try:
            if view:
                await ctx.response.send_message(first_chunk, view=view)
            else:
                await ctx.response.send_message(first_chunk)
        except Exception:
            try:
                await ctx.followup.send(first_chunk)
            except Exception:
                if getattr(ctx, 'channel', None):
                    await ctx.channel.send(first_chunk)
        # Send remaining chunks via followup/channel
        while remaining:
            chunk = remaining[:2000]
            try:
                await ctx.followup.send(chunk)
            except Exception:
                if getattr(ctx, 'channel', None):
                    await ctx.channel.send(chunk)
            remaining = remaining[2000:]

SLASH_COMMANDS = []
async def pokemon_autocomplete(interaction, current: str):
    """Fast autocomplete using cached Pokémon names"""
    if not current:
        return [app_commands.Choice(name=name, value=name) for name in _pokemon_cache[:25]]
    
    current_lower = current.lower()
    matches = []
    
    for name, name_lower in zip(_pokemon_cache, _pokemon_cache_lower):
        if current_lower in name_lower:
            matches.append(app_commands.Choice(name=name, value=name))
            if len(matches) >= 25:
                break
    
    return matches

@app_commands.command(
    name = 'encounter',
    description = 'Generate a random encounter with up to 6 Pokémon!'
)
@app_commands.describe(
    pokemon = "Which pokemon? (leave blank for random)",
    level = "What level? (Default: 1)",
    include_extra = "Include TM, Egg, or Tutor moves? (Default: No)",
    format_type = "How to format the encounter info",
    smart_stats = "Use the improved stat distribution? (Default: False)",
    evil_mode = "Use evil mode for move selection? (Default: False)",
    number = "How many? (up to 6)"
)
@app_commands.choices(
    include_extra = [
        Choice(name = 'Yes', value = 1),
        Choice(name = 'No', value = 0),
    ],
    format_type = [
        Choice(name = 'Standard', value = 'standard'),
        Choice(name = 'Detailed', value = 'detailed'),
    ],
    smart_stats = [
        Choice(name = 'Yes', value = 1),
        Choice(name = 'No', value = 0),
    ],
    evil_mode = [
        Choice(name = 'Yes', value = 1),
        Choice(name = 'No', value = 0),
    ]
)
@app_commands.autocomplete(pokemon = pokemon_autocomplete)
async def encounter_slash(
    inter: discord.Interaction,
    pokemon: str = '',
    level: app_commands.Range[int, 1, 999999] = 1,
    include_extra: int = 0,
    format_type: str = 'standard',
    smart_stats: int = 0,
    evil_mode: int = 0,
    number: app_commands.Range[int, 1, 6] = 1
):
    smart_stats = bool(smart_stats)
    evil_mode = bool(evil_mode)
    wrap_in_code_block = False
    rank = get_rank(level)

    # If no pokemon specified, pick random ones for the given level
    if pokemon == '':
        # Get list of all pokemon names from Data/pokemon that have moves for the selected rank
        folder = "Data/pokemon"
        if os.path.exists(folder):
            all_pokemon = []
            rank_lower = rank.lower()
            ranks_order = ["bronze", "silver", "gold", "platinum", "diamond", "master"]
            current_index = ranks_order.index(rank_lower) if rank_lower in ranks_order else 0
            for filename in os.listdir(folder):
                if filename.endswith(".json"):
                    name = filename[:-5]
                    filepath = os.path.join(folder, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = normalize_keys(json.load(f))
                            moves = data.get("moves", {})
                            has_moves = any(moves.get(r, []) for r in ranks_order[:current_index + 1])
                            if has_moves:
                                all_pokemon.append(name)
                    except Exception:
                        pass
            pokelist = random.sample(all_pokemon, number) if all_pokemon else []
        else:
            pokelist = []
    else:
        pokelist = pokemon.split(', ')

    # Error handling for empty pokelist
    if not pokelist:
        if pokemon == '':
            await inter.response.send_message(f'No Pokémon available for level {level}.', ephemeral=True)
        else:
            await inter.response.send_message('No valid Pokémon found for the specified names.', ephemeral=True)
        return

    # Generate encounter(s)
    msg = ''
    for idx, pokemon_name in enumerate(pokelist):
        try:
            msg += await pkmn_encounter(
                ctx=inter,
                number=1,
                level=level,
                pokelist=[pokemon_name],
                boss=smart_stats,
                guild=0,
                format_type=format_type,
                include_extra=include_extra,
                evil=evil_mode
            )
        except Exception as e:
            msg += f'Error generating encounter for {pokemon_name}: {e}\n'
    await send_big_msg(ctx=inter, arg=msg, wrap_in_code_block=wrap_in_code_block, view=None)
async def setup(bot):
    bot.tree.add_command(encounter_slash)