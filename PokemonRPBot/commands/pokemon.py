import math
import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import re
from typing import List

from emojis import get_type_emoji
from cache_helper import load_or_build_cache

# ------------------------------
# Evolution data & helpers
# ------------------------------
EVO_FILE = os.path.join(os.path.dirname(__file__), "..", "Data", "pokemon_evolutions.json")
try:
    with open(EVO_FILE, "r", encoding="utf-8") as f:
        EVOLUTION_DATA = json.load(f)
except Exception:
    EVOLUTION_DATA = {}

def find_evolution_key(normalized: str, evo_data: dict) -> str:
    target = normalized.replace("-", "")
    for key in evo_data:
        if normalize_name(key).replace("-", "") == target:
            return key
    return None

def load_related_data(name: str) -> dict:
    filename = find_movelist_filename(normalize_name(name))
    if not filename:
        return {}
    with open(filename, "r", encoding="utf-8") as f:
        return normalize_keys(json.load(f))

def combine_moves(main_data: dict, related_names: list) -> dict:
    """
    Combine the main Pokémon's moves with those of pre-evolutions:
      - For TM/Egg/Tutor and other non-rank categories, union and mark extras with '*'
      - For badge ranks, merge in progression order and mark extras
    """
    combined = {}
    moves_all = main_data.get("moves", {})
    ranks = ["bronze", "silver", "gold", "platinum", "diamond"]

    # 1) Non-rank categories: tm, egg, tutor, etc.
    non_rank_cats = [cat for cat in moves_all if cat not in ranks]
    for cat in non_rank_cats:
        main_moves = set(moves_all.get(cat, []))
        union = set(main_moves)
        for rel in related_names:
            union |= set(load_related_data(rel).get("moves", {}).get(cat, []))
        merged = sorted(union, key=lambda m: m.lower())
        # mark moves that come only from related forms
        combined[cat] = [m if m in main_moves else f"{m}*" for m in merged]

    # 2) Ranked categories: preserve progression order, avoid duplicates
    seen = set()
    for rank in ranks:
        main_moves = set(moves_all.get(rank, []))
        union = set(main_moves)
        for rel in related_names:
            union |= set(load_related_data(rel).get("moves", {}).get(rank, []))
        new_moves = union - seen
        merged = sorted(new_moves, key=lambda m: m.lower())
        combined[rank] = [m if m in main_moves else f"{m}*" for m in merged]
        seen |= union

    return combined

# ------------------------------
# Helper functions & constants
# ------------------------------

def normalize_name(name: str) -> str:
    normalized = name.lower()
    normalized = re.sub(r'[^a-z0-9]', '-', normalized)
    normalized = re.sub(r'-+', '-', normalized)
    return normalized.strip('-')

def normalize_keys(obj):
    if isinstance(obj, dict):
        return {k.lower(): normalize_keys(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [normalize_keys(item) for item in obj]
    else:
        return obj

def load_defensive_chart():
    file_path = os.path.join(os.path.dirname(__file__), "..", "Data", "typechart.json")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

DEFENSIVE_CHART = load_defensive_chart()

def normalize_type(t: str) -> str:
    t_lower = t.lower()
    for key in DEFENSIVE_CHART:
        if key.lower() == t_lower:
            return key
    return t

def sorted_moves_list(moves):
    return sorted(moves, key=lambda x: x.lower())

def get_effectiveness_category(multiplier: float) -> str:
    if multiplier == 0:
        return "Immune (No Damage)"
    shift = round(math.log(multiplier, 2))
    if shift == 0:
        return "Neutral (0)"
    elif shift == 1:
        return "Effective (+1)"
    elif shift == 2:
        return "Super Effective (+2)"
    elif shift == -1:
        return "Ineffective (-1)"
    elif shift == -2:
        return "Super Ineffective (-2)"
    elif shift > 2:
        return f"Ultra Effective (+{shift})"
    else:
        return f"Ultra Ineffective ({shift})"

def sort_key(category: str) -> float:
    if category.startswith("Immune"):
        return -999
    m = re.search(r'\(([-+]\d+)\)', category)
    return int(m.group(1)) if m else 0

def find_movelist_filename(normalized: str, folder: str = os.path.join("Data", "pokemon")) -> str:
    exact_path = os.path.join(folder, f"{normalized}.json")
    if os.path.exists(exact_path):
        return exact_path
    # Prefer an exact normalized-name match of the filename (keeps separators intact)
    for filename in os.listdir(folder):
        if not filename.endswith(".json"):
            continue
        base = filename[:-5]
        base_norm = normalize_name(base)
        if base_norm == normalized:
            return os.path.join(folder, filename)

    # Fallback: looser matching by removing separators (handles e.g. hyphen/space differences)
    target = normalized.replace("-", "")
    for filename in os.listdir(folder):
        if not filename.endswith(".json"):
            continue
        base = filename[:-5]
        norm = normalize_name(base).replace("-", "")
        if norm == target or norm in target or target in norm:
            return os.path.join(folder, filename)
    return None

def format_stat_bar(stat: str) -> str:
    try:
        filled, total = map(int, stat.split('/'))
        return "⬤" * filled + "⭘" * (total - filled)
    except:
        return stat

def format_moves(moves_list: list) -> str:
    return "  |  ".join(moves_list) if moves_list else "None"

def load_ability(ability_name: str, folder: str = None) -> dict:
    if folder is None:
        folder = os.path.join(os.path.dirname(__file__), "..", "Data", "abilities")
    file_path = os.path.join(folder, f"{ability_name}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return normalize_keys(json.load(f))
        except Exception:
            pass
    return None

# ------------------------------
# Persistent view classes
# ------------------------------

class PersistentPokemonAbilitiesButton(discord.ui.Button):
    def __init__(self, normalized: str):
        super().__init__(label="Abilities", style=discord.ButtonStyle.primary,
                         custom_id=f"pokemon:abilities:{normalized}")

    async def callback(self, interaction: discord.Interaction):
        self.disabled = True
        await interaction.response.edit_message(view=self.view)

        _, _, norm = self.custom_id.split(":")
        fn = find_movelist_filename(norm, "Data/pokemon")
        if not fn:
            return await interaction.followup.send("Could not find Pokémon data.")

        with open(fn, "r", encoding="utf-8") as f:
            data = normalize_keys(json.load(f))

        msg = f"## {data.get('name','Unknown')} Abilities\n"
        for a in data.get("abilities", {}).get("normal", []):
            ad = load_ability(a)
            if ad:
                msg += f"\n### {a}\n{ad.get('effect','')}\n*{ad.get('description','')}*\n"
            else:
                msg += f"\n### {a}\nNo data found.\n"
        for a in data.get("abilities", {}).get("hidden", []):
            ad = load_ability(a)
            if ad:
                msg += f"\n### {a} (Hidden)\n{ad.get('effect','')}\n*{ad.get('description','')}*\n"
            else:
                msg += f"\n### {a} (Hidden)\nNo data found.\n"

        await interaction.followup.send(msg)

class PersistentPokemonTypeEffectivenessButton(discord.ui.Button):
    def __init__(self, normalized: str):
        super().__init__(label="Type Effectiveness", style=discord.ButtonStyle.primary,
                         custom_id=f"pokemon:te:{normalized}")

    async def callback(self, interaction: discord.Interaction):
        self.disabled = True
        await interaction.response.edit_message(view=self.view)

        _, _, norm = self.custom_id.split(":")
        fn = find_movelist_filename(norm, "Data/pokemon")
        if not fn:
            return await interaction.followup.send("Could not find Pokémon data.")

        with open(fn, "r", encoding="utf-8") as f:
            data = normalize_keys(json.load(f))

        defender_types = [normalize_type(t) for t in data.get("types", [])]
        results = {}
        for atk in DEFENSIVE_CHART:
            m = 1.0
            for dt in defender_types:
                m *= DEFENSIVE_CHART[dt][atk]
            if m == 1:
                continue
            cat = get_effectiveness_category(m)
            if cat != "Neutral (0)":
                results.setdefault(cat, []).append(atk)

        msg = f"## Type Chart for {data.get('name','Unknown')}\n"
        for cat in sorted(results, key=sort_key, reverse=True):
            line = "  |  ".join(f"{get_type_emoji(t)} {t}" for t in results[cat])
            msg += f"\n### {cat}\n{line}"

        await interaction.followup.send(msg)

class PersistentPokemonMovesButton(discord.ui.Button):
    def __init__(self, normalized: str):
        super().__init__(label="Moves", style=discord.ButtonStyle.primary,
                         custom_id=f"pokemon:moves:{normalized}")

    async def callback(self, interaction: discord.Interaction):
        self.disabled = True
        await interaction.response.edit_message(view=self.view)

        _, _, norm = self.custom_id.split(":")
        fn = find_movelist_filename(norm, "Data/pokemon")
        if not fn:
            return await interaction.followup.send("Could not find Pokémon data.")

        with open(fn, "r", encoding="utf-8") as f:
            data = normalize_keys(json.load(f))

        # --- evolution-based move merging ---
        evo_key = find_evolution_key(norm, EVOLUTION_DATA)
        if evo_key:
            data["moves"] = combine_moves(data, EVOLUTION_DATA[evo_key])

        header = f"### {data.get('name','Unknown')} [#{data.get('number','?')}]"
        mv = data.get("moves", {})
        sections = []
        for icon, rank in [
            ("<:badgebronze:1272532685197152349>", "bronze"),
            ("<:badgesilver:1272533590697185391>", "silver"),
            ("<:badgegold:1272532681992962068>", "gold"),
            ("<:badgeplatinum:1272533593750507570>", "platinum"),
        ]:
            moves_text = format_moves(sorted_moves_list(mv.get(rank, [])))
            if moves_text != "None":
                sections.append(f"{icon} **{rank.title()}**\n{moves_text}")

        msg = header
        if sections:
            msg += "\n\n" + "\n\n".join(sections)

        view = PersistentLearnMovesView(norm)
        await interaction.followup.send(msg, view=view)

class PersistentLearnMovesView(discord.ui.View):
    def __init__(self, normalized: str):
        super().__init__(timeout=None)
        self.normalized = normalized
        btn = discord.ui.Button(
            label="Show all learnable Moves",
            style=discord.ButtonStyle.primary,
            custom_id=f"pokemon:learnmoves:{normalized}"
        )
        btn.callback = self.learn_moves_callback
        self.add_item(btn)

    async def learn_moves_callback(self, interaction: discord.Interaction):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)

        _, _, norm = interaction.data.get("custom_id", "").split(":")
        fn = find_movelist_filename(norm, "Data/pokemon")
        if not fn:
            return await interaction.followup.send("Could not find Pokémon data.")

        with open(fn, "r", encoding="utf-8") as f:
            data = normalize_keys(json.load(f))

        evo_key = find_evolution_key(norm, EVOLUTION_DATA)
        if evo_key:
            data["moves"] = combine_moves(data, EVOLUTION_DATA[evo_key])

        header = f"### {data.get('name','Unknown')} [#{data.get('number','?')}]"
        mv = data.get("moves", {})
        sections = [
            (":cd: **TM Moves**", "tm"),
            (":egg: **Egg Moves**", "egg"),
            (":teacher: **Tutor Moves**", "tutor"),
        ]

        messages = []
        for title, key in sections:
            moves = sorted_moves_list(mv.get(key, []))
            if not moves:
                continue
            content = format_moves(moves)
            full_section = f"{title}\n{content}"
            if len(full_section) <= 2000:
                messages.append(full_section)
            else:
                # Split the moves into chunks
                chunk_size = 50  # adjust as needed
                for i in range(0, len(moves), chunk_size):
                    chunk = moves[i:i+chunk_size]
                    chunk_content = format_moves(chunk)
                    part_num = i // chunk_size + 1
                    messages.append(f"{title} (Part {part_num})\n{chunk_content}")

        for m in messages:
            if len(m) > 2000:
                # If still too long, truncate
                m = m[:1997] + "..."
            await interaction.followup.send(m)

class PersistentPokemonView(discord.ui.View):
    def __init__(self, normalized: str):
        super().__init__(timeout=None)
        self.add_item(PersistentPokemonAbilitiesButton(normalized))
        self.add_item(PersistentPokemonTypeEffectivenessButton(normalized))
        self.add_item(PersistentPokemonMovesButton(normalized))

# ------------------------------
# The main Pokémon cog
# ------------------------------

class PokemonCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Cache Pokémon names at startup
        self.pokemon_cache: List[str] = []
        self.pokemon_cache_lower: List[str] = []
        self.load_pokemon_cache()
    
    def load_pokemon_cache(self):
        """Load all Pokémon names into memory for fast autocomplete"""
        pokemon_dir = os.path.join("Data", "pokemon")
        self.pokemon_cache, self.pokemon_cache_lower = load_or_build_cache(
            "pokemon.json",
            pokemon_dir,
            "[Pokemon] Pokémon species"
        )

    @app_commands.command(name="pokemon", description="Show details for a Pokémon")
    async def pokemon(self, interaction: discord.Interaction, pokemon: str):
        norm = normalize_name(pokemon)
        folder = os.path.join("Data", "pokemon")
        if not os.path.exists(folder):
            return await interaction.response.send_message(
                "Pokémon data folder not found.", ephemeral=True
            )
        fn = find_movelist_filename(norm, folder)
        if not fn:
            return await interaction.response.send_message(
                f"Could not find data for Pokémon **{pokemon}**.", ephemeral=True
            )

        with open(fn, "r", encoding="utf-8") as f:
            data = normalize_keys(json.load(f))

        out = f"### {data.get('name','Unknown')} [#{data.get('number','?')}]"
        if all(k in data for k in ("height_m","height_ft","weight_kg","weight_lb")):
            out += (
                f"\n{data['height_m']}m / {data['height_ft']}ft   |   "
                f"{data['weight_kg']}kg / {data['weight_lb']}lbs"
            )
        else:
            out += "\n"

        type_str = " / ".join(f"{get_type_emoji(t)} {t}" for t in data.get("types", []))
        out += f"\n**Type**: {type_str}"
        out += f"\n**Base HP**: {data.get('base_hp','?')}"
        for stat in ["strength","dexterity","vitality","special","insight"]:
            val = data.get(stat,"")
            bar = format_stat_bar(val)
            out += f"\n**{stat.title()}**: {bar} `{val}`"

        abn = data.get("abilities",{}).get("normal",[])
        abh = data.get("abilities",{}).get("hidden",[])
        ab_str = " / ".join(abn)
        if abh:
            ab_str += " (" + " / ".join(abh) + ")"
        out += f"\n**Ability**: {ab_str}"

        view = PersistentPokemonView(norm)
        await interaction.response.send_message(out, view=view)
        self.bot.add_view(view)

    @pokemon.autocomplete("pokemon")
    async def pokemon_autocomplete(self, interaction: discord.Interaction, current: str):
        """Fast autocomplete using cached Pokémon names"""
        if not current:
            return [app_commands.Choice(name=name, value=name) for name in self.pokemon_cache[:25]]
        
        current_lower = current.lower()
        matches = []
        
        for name, name_lower in zip(self.pokemon_cache, self.pokemon_cache_lower):
            if current_lower in name_lower:
                matches.append(app_commands.Choice(name=name, value=name))
                if len(matches) >= 25:
                    break
        
        return matches

async def setup(bot: commands.Bot):
    await bot.add_cog(PokemonCog(bot))
