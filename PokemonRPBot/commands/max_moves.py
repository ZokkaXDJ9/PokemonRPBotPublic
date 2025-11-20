import discord
from discord import app_commands
from discord.ext import commands
import os
import json
from typing import List
from helpers import load_move, ParsedRollQuery
from emojis import get_type_emoji, get_category_emoji
from cache_helper import load_or_build_cache

# Directories for move files and character files
BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
MAX_MOVES_DIRECTORY = os.path.join(BASE_DIR, "Data", "max_moves")
MOVES_DIRECTORY = os.path.join(BASE_DIR, "Data", "moves")
CHARACTERS_DIRECTORY = os.path.join(BASE_DIR, "Characters")

def load_user_stats(user_id: int):
    """Load user stats from a JSON file in the Characters directory."""
    files = os.listdir(CHARACTERS_DIRECTORY)
    matching_file = next(
        (f for f in files if f.startswith(f"{user_id}_") and f.endswith(".json")),
        None
    )
    if not matching_file:
        return None
    stats_file = os.path.join(CHARACTERS_DIRECTORY, matching_file)
    with open(stats_file, "r") as file:
        return json.load(file)

def build_dice_query(dice_count: int):
    """Build a query string for ParsedRollQuery based on the number of dice."""
    return f"{dice_count}d6"

def get_move_field(move: dict, field: str, alt_field: str = None):
    """Case-insensitive lookup for a field in a move dict.

    This function searches the move dictionary's keys in a forgiving way so
    it works with keys like "Name", "name", "damage1", "Damage1", etc.

    Search order:
    1. Exact case-insensitive match for `field` or `alt_field`.
    2. Keys containing the field/alt_field as a substring (handles numeric suffixes).
    3. Fallback to trying a few common variant names (preserves previous behavior).

    If the found value is a list, the first element is returned (callers expect a string).
    """
    if not move or not field:
        return None

    want = field.lower()
    alt = alt_field.lower() if alt_field else None

    # 1) Exact (case-insensitive) or alt exact
    for k, v in move.items():
        if k.lower() == want or (alt and k.lower() == alt):
            if isinstance(v, list) and v:
                return v[0]
            return v

    # 2) Substring match (e.g. 'damage1' should match 'damage')
    for k, v in move.items():
        kl = k.lower()
        if want in kl or (alt and alt in kl):
            if isinstance(v, list) and v:
                return v[0]
            return v

    # 3) Fallback: try a few common literal variants to keep backward compatibility
    candidates = [field, field.lower(), field.capitalize(), alt_field or ""]
    for k in candidates:
        if not k:
            continue
        val = move.get(k)
        if val is not None:
            if isinstance(val, list) and val:
                return val[0]
            return val

    return None

# New helper: find a max move that matches a given type
def load_max_move_for_type(type_name: str):
    """Scan MAX_MOVES_DIRECTORY for a max move that matches type_name.

    The max-move JSON files in this project use lowercase keys such as
    "type", "name", "description", "damage", "accuracy", "effect",
    and "category". This function looks up the "type" field (or variants)
    and performs a case-insensitive match. As a final fallback it also
    checks whether the filename contains the type name.
    """
    if not type_name:
        return None
    wanted = type_name.lower()
    for fname in os.listdir(MAX_MOVES_DIRECTORY):
        if not fname.lower().endswith(".json"):
            continue
        # Exclude explicit Max Guard files from type-based selection by filename
        if "max guard" in fname.lower():
            continue
        path = os.path.join(MAX_MOVES_DIRECTORY, fname)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            continue

        candidates = data if isinstance(data, list) else [data]

        for mv in candidates:
            mv_type = get_move_field(mv, "type")
            if not mv_type:
                continue
            # (Do not exclude by category; Max Guard files should be excluded by filename only.)
            # mv_type may be like "Electric" or a list - normalize to string
            if isinstance(mv_type, str):
                if wanted == mv_type.lower() or wanted in mv_type.lower():
                    return mv
            elif isinstance(mv_type, list):
                if any(wanted == t.lower() or wanted in t.lower() for t in mv_type if isinstance(t, str)):
                    return mv

        # fallback: filename contains the type name
        if wanted in fname.lower():
            if isinstance(data, dict):
                return data
            elif isinstance(data, list) and data:
                return data[0]
    return None


def load_max_guard():
    """Load the special 'Max Guard' max-move file directly.

    Return the JSON dict for Max Guard if present, else None.
    """
    fname = os.path.join(MAX_MOVES_DIRECTORY, "Max Guard.json")
    if not os.path.exists(fname):
        # try case-insensitive search
        for f in os.listdir(MAX_MOVES_DIRECTORY):
            if f.lower().startswith("max guard") and f.lower().endswith(".json"):
                fname = os.path.join(MAX_MOVES_DIRECTORY, f)
                break
    try:
        with open(fname, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None

class MaxMoveCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cache move names at startup
        self.move_cache: List[str] = []
        self.move_cache_lower: List[str] = []
        self.load_move_cache()
    
    def load_move_cache(self):
        """Load all move names into memory for fast autocomplete"""
        self.move_cache, self.move_cache_lower = load_or_build_cache(
            "moves.json",
            MOVES_DIRECTORY,
            "[Max Move] moves"
        )

    async def move_name_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Fast autocomplete using cached move names"""
        if not current:
            return [app_commands.Choice(name=name, value=name) for name in self.move_cache[:25]]
        
        current_lower = current.lower()
        matches = []
        
        for name, name_lower in zip(self.move_cache, self.move_cache_lower):
            if current_lower in name_lower:
                matches.append(app_commands.Choice(name=name, value=name))
                if len(matches) >= 25:
                    break
        
        return matches

    @app_commands.command(
        name="max_move", 
        description="Display details of a Pokémon's corresponding Max Move (by type)."
    )
    @app_commands.autocomplete(move=move_name_autocomplete)
    async def max_move(self, interaction: discord.Interaction, move: str):
        move_obj = load_move(move)
        if move_obj is None:
            await interaction.response.send_message(
                f"Move '{move}' not found.", ephemeral=True
            )
            return

        user_stats = load_user_stats(interaction.user.id)

        # Retrieve move fields using the helper to support both key formats.
        move_name_field = get_move_field(move_obj, "Name")
        type_field = get_move_field(move_obj, "Type")
        category_field = get_move_field(move_obj, "Category")
        description_field = get_move_field(move_obj, "Description")
        target_field = get_move_field(move_obj, "Target")
        effect_field = get_move_field(move_obj, "Effect")
        damage_field = get_move_field(move_obj, "Damage1", "damage")
        power_field = get_move_field(move_obj, "Power", "power")
        accuracy_field = get_move_field(move_obj, "Accuracy1", "accuracy")
        type_icon = get_type_emoji(type_field)
        category_icon = get_category_emoji(category_field)
    
        # We will display only the Max Move. Start with an empty description
        # and populate it when we find the matching Max Move.
        move_description = ""

        # Find the Max Move for this move's type
        max_move = None
        # type_field may be a list or string; prefer the first element when list
        search_type = None
        if isinstance(type_field, list) and type_field:
            search_type = type_field[0]
        elif isinstance(type_field, str):
            search_type = type_field

        if search_type:
            max_move = load_max_move_for_type(search_type)

        # Special case: if the original move is Support, we must use Max Guard exclusively
        if isinstance(category_field, str) and category_field.lower() == "support":
            mg = load_max_guard()
            if mg:
                max_move = mg

        if max_move:
            # Use the actual JSON keys present in the max_moves files (lowercase),
            # but keep get_move_field as a fallback to handle variants.
            max_name = max_move.get("name") or get_move_field(max_move, "Name")
            max_desc = max_move.get("description") or get_move_field(max_move, "Description")
            max_type = max_move.get("type") or get_move_field(max_move, "Type")
            max_cat = max_move.get("category") or get_move_field(max_move, "Category")
            # Max move files use 'damage' instead of 'power'
            # Max move files use 'damage' and 'accuracy'
            max_damage = max_move.get("damage") or get_move_field(max_move, "Damage", "damage")
            max_accuracy = max_move.get("accuracy") or get_move_field(max_move, "Accuracy", "accuracy")
            # Compute max-move power as original move's power + 2 when possible, unless
            # this is a Support -> Max Guard special case where we use Max Guard fields only.
            def _parse_int(v):
                try:
                    return int(v)
                except Exception:
                    return None

            is_support_to_max_guard = isinstance(category_field, str) and category_field.lower() == "support"
            if not is_support_to_max_guard:
                orig_power_val = _parse_int(power_field)
                if orig_power_val is not None:
                    max_power = orig_power_val + 2
                else:
                    # try explicit max move power
                    mm_pow = max_move.get("power") or get_move_field(max_move, "Power", "power")
                    mm_pow_val = _parse_int(mm_pow)
                    if mm_pow_val is not None:
                        max_power = mm_pow_val + 2
                    else:
                        # final fallback: use power_field literally (could be string)
                        max_power = power_field
            else:
                # Use Max Guard's own power/damage/accuracy exclusively
                max_power = max_move.get("power") or get_move_field(max_move, "Power", "power")
            max_effect = max_move.get("effect") or get_move_field(max_move, "Effect")
            max_target = max_move.get("target") or get_move_field(max_move, "Target")
            # If the original move is a Support move, we will load Max Guard and
            # the fields (including category) will come from that Max Guard JSON.

            max_type_icon = get_type_emoji(max_type)
            max_cat_icon = get_category_emoji(max_cat)

            # Present Max Move dice/info similarly to regular moves; use fallbacks
            md = max_damage if max_damage not in (None, "", []) else "—"
            if is_support_to_max_guard:
                # In the Max Guard special case, take accuracy exclusively from Max Guard
                ma = max_accuracy if max_accuracy not in (None, "", []) else "—"
            else:
                # Prefer original move accuracy for Max Moves when available
                ma = accuracy_field if accuracy_field not in (None, "", []) else (
                    max_accuracy if max_accuracy not in (None, "", []) else "—"
                )

            # Build Max Move output and include the original move name below the
            # Max Move title.
            # Avoid extra spaces when an icon is missing (icon functions may return empty string).
            formatted_type = f"{max_type_icon} {max_type}" if max_type_icon else f"{max_type}"
            formatted_cat = f"{max_cat_icon} {max_cat}" if max_cat_icon else f"{max_cat}"
            move_description = (
                f"### {max_name}\n"
                f"-# Original Move: {move_name_field}\n"
                f"*{max_desc}*\n"
                f"**Type**: {formatted_type} — **{formatted_cat}**\n"
            )
            move_description += f"**Target**: {max_target}\n"
            # Damage Dice should be shown as Damage + Power (omit for Max Guard special case)
            if not is_support_to_max_guard:
                move_description += f"**Damage Dice**: {md} + {max_power}\n"
            move_description += f"**Accuracy Dice**: {ma} + Rank\n"
            if max_effect:
                move_description += f"**Effect**: {max_effect}\n"
        else:
            move_description += f"\n*No matching Max Move found for type: {search_type}.*\n"

        await interaction.response.send_message(move_description)

async def setup(bot):
    await bot.add_cog(MaxMoveCommand(bot))
