import discord
from discord import app_commands
from discord.ext import commands
import os
import json
from typing import List
from helpers import load_move
from emojis import get_type_emoji, get_category_emoji
from .max_moves import get_move_field, load_max_guard
from cache_helper import load_or_build_cache

# Directories
BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
G_MAX_MOVES_DIRECTORY = os.path.join(BASE_DIR, "Data", "g_max_moves")
MOVES_DIRECTORY = os.path.join(BASE_DIR, "Data", "moves")


def load_g_max_move_for_type(type_name: str):
    if not type_name:
        return None
    wanted = type_name.lower()
    for fname in os.listdir(G_MAX_MOVES_DIRECTORY):
        if not fname.lower().endswith('.json'):
            continue
        path = os.path.join(G_MAX_MOVES_DIRECTORY, fname)
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
        except Exception:
            continue

        candidates = data if isinstance(data, list) else [data]
        for mv in candidates:
            mv_type = get_move_field(mv, 'type')
            if not mv_type:
                continue
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


class GMaxCommand(commands.Cog):
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
            "[G-Max] moves"
        )

    async def _gmax_move_autocomplete(self, interaction: discord.Interaction, current: str):
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

    @app_commands.command(name='gmax_move', description='Display G-Max move for a move (by type).')
    @app_commands.autocomplete(move=_gmax_move_autocomplete)
    async def gmax(self, interaction: discord.Interaction, move: str):
        move_obj = load_move(move)
        if move_obj is None:
            await interaction.response.send_message(f"Move '{move}' not found.", ephemeral=True)
            return

        # fields
        move_name_field = get_move_field(move_obj, 'Name')
        type_field = get_move_field(move_obj, 'Type')
        category_field = get_move_field(move_obj, 'Category')
        damage_field = get_move_field(move_obj, 'Damage1', 'damage')
        power_field = get_move_field(move_obj, 'Power', 'power')
        accuracy_field = get_move_field(move_obj, 'Accuracy1', 'accuracy')

        # find g-max
        search_type = None
        if isinstance(type_field, list) and type_field:
            search_type = type_field[0]
        elif isinstance(type_field, str):
            search_type = type_field

        gmax_move = None
        if search_type:
            gmax_move = load_g_max_move_for_type(search_type)

        # Special case: if original is Support, use Max Guard exclusively
        if isinstance(category_field, str) and category_field.lower() == 'support':
            mg = load_max_guard()
            if mg:
                gmax_move = mg

        if not gmax_move:
            await interaction.response.send_message(f"No matching G-Max Move found for type: {search_type}")
            return

        # gather gmax fields (prefer lowercase JSON keys)
        g_name = gmax_move.get('name') or get_move_field(gmax_move, 'Name')
        g_desc = gmax_move.get('description') or get_move_field(gmax_move, 'Description')
        g_type = gmax_move.get('type') or get_move_field(gmax_move, 'Type')
        g_cat = gmax_move.get('category') or get_move_field(gmax_move, 'Category')
        g_damage = gmax_move.get('damage') or get_move_field(gmax_move, 'Damage', 'damage')
        g_accuracy = gmax_move.get('accuracy') or get_move_field(gmax_move, 'Accuracy', 'accuracy')
        g_effect = gmax_move.get('effect') or get_move_field(gmax_move, 'Effect')
        g_target = gmax_move.get('target') or get_move_field(gmax_move, 'Target')

        # compute gmax power as original power + 2 when possible
        def _parse_int(v):
            try:
                return int(v)
            except Exception:
                return None

        orig_power_val = _parse_int(power_field)
        if orig_power_val is not None:
            g_power = orig_power_val + 2
        else:
            mm_pow = gmax_move.get('power') or get_move_field(gmax_move, 'Power', 'power')
            mm_pow_val = _parse_int(mm_pow)
            if mm_pow_val is not None:
                g_power = mm_pow_val + 2
            else:
                g_power = mm_pow or power_field

        # prefer original move accuracy when available
        ma = accuracy_field if accuracy_field not in (None, '', []) else (g_accuracy if g_accuracy not in (None, '', []) else '—')

        g_type_icon = get_type_emoji(g_type)
        g_cat_icon = get_category_emoji(g_cat)
        formatted_type = f"{g_type_icon} {g_type}" if g_type_icon else f"{g_type}"
        formatted_cat = f"{g_cat_icon} {g_cat}" if g_cat_icon else f"{g_cat}"

        md = g_damage if g_damage not in (None, '', []) else '—'

        out = (
            f"### {g_name}\n"
            f"-# Original Move: {move_name_field}\n"
            f"*{g_desc}*\n"
            f"**Type**: {formatted_type} — **{formatted_cat}**\n"
            f"**Target**: {g_target}\n"
        )
        # omit Damage Dice if this is the Max Guard special case
        is_support_to_max_guard = isinstance(category_field, str) and category_field.lower() == 'support'
        if not is_support_to_max_guard:
            out += f"**Damage Dice**: {md} + {g_power}\n"
        out += f"**Accuracy Dice**: {ma} + Rank\n"
        if g_effect:
            out += f"**Effect**: {g_effect}\n"

        await interaction.response.send_message(out)


async def setup(bot):
    await bot.add_cog(GMaxCommand(bot))
