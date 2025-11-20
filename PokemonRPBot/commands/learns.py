import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import re
from typing import List
from cache_helper import load_or_build_cache

def normalize_name(name: str) -> str:
    """
    Converts a Pokémon name to a normalized form:
      - Lowercase
      - Replaces non-alphanumeric characters with hyphens
      - Merges multiple hyphens and strips leading/trailing hyphens.
    Example: "Sirfetch'd" -> "sirfetch-d"
    """
    normalized = name.lower()
    normalized = re.sub(r'[^a-z0-9]', '-', normalized)
    normalized = re.sub(r'-+', '-', normalized)
    normalized = normalized.strip('-')
    return normalized

def find_movelist_filename(normalized: str, folder: str = os.path.join("data", "pokemon")) -> str:
    """
    Given a normalized Pokémon name, returns the full filename of the movelist JSON file.
    First, it checks for an exact match. If not found, it scans the folder and compares
    candidate filenames with hyphens removed.
    Returns None if no match is found.
    """
    # Try exact match.
    exact_path = os.path.join(folder, f"{normalized}.json")
    if os.path.exists(exact_path):
        return exact_path

    target_nohyphen = normalized.replace("-", "")
    for filename in os.listdir(folder):
        if filename.endswith(".json"):
            candidate = filename[:-5]  # remove .json
            candidate_norm = normalize_name(candidate)
            candidate_nohyphen = candidate_norm.replace("-", "")
            if candidate_nohyphen == target_nohyphen:
                return os.path.join(folder, filename)
            # Extra fuzzy check: one is a substring of the other.
            if candidate_nohyphen in target_nohyphen or target_nohyphen in candidate_nohyphen:
                return os.path.join(folder, filename)
    return None

def find_evolution_key(normalized: str, evo_data: dict) -> str:
    """
    Given a normalized Pokémon name and evolution data dictionary,
    returns the key from evo_data that matches the normalized name, ignoring hyphens.
    """
    target = normalized.replace("-", "")
    for key in evo_data:
        if normalize_name(key).replace("-", "") == target:
            return key
    return None

def sorted_moves_list(moves):
    # Helper to always alphabetize move lists (case-insensitive)
    return sorted(moves, key=lambda x: x.lower())

def format_moves(moves_list: list) -> str:
    return "  |  ".join(moves_list) if moves_list else "None"

class LearnMovesView(discord.ui.View):
    def __init__(self, pokemon_data: dict, author: discord.User):
        super().__init__(timeout=180)
        self.pokemon_data = pokemon_data
        self.author = author

    @discord.ui.button(label="Show all learnable Moves", style=discord.ButtonStyle.primary)
    async def show_all_moves(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("You did not invoke this command.", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        header = f"### {self.pokemon_data.get('name', 'Unknown')} [#{self.pokemon_data.get('number', '?')}]"
        moves = self.pokemon_data.get("moves", {})

        # Ensure all lists are sorted before formatting
        tm_moves = format_moves(sorted_moves_list(moves.get("tm", [])))
        egg_moves = format_moves(sorted_moves_list(moves.get("egg", [])))
        tutor_moves = format_moves(sorted_moves_list(moves.get("tutor", [])))

        sections = [
            (":cd: **TM Moves**", tm_moves),
            (":egg: **Egg Moves**", egg_moves),
            (":teacher: **Tutor Moves**", tutor_moves)
        ]

        messages = []
        current_message = header
        for title, content in sections:
            section_text = f"{title}\n{content}"
            if len(current_message) + 2 + len(section_text) > 2000:
                messages.append(current_message)
                current_message = header + "\n\n" + section_text
            else:
                current_message += "\n\n" + section_text
        messages.append(current_message)

        for msg in messages:
            await interaction.followup.send(msg, ephemeral=False)

class MovesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Cache Pokémon names at startup
        self.pokemon_cache: List[str] = []
        self.pokemon_cache_lower: List[str] = []
        self.load_pokemon_cache()
        # Load evolution data from data/pokemon_evolutions.json
        evolution_file = os.path.join("data", "pokemon_evolutions.json")
        if os.path.exists(evolution_file):
            try:
                with open(evolution_file, "r", encoding="utf-8") as f:
                    self.evolution_data = json.load(f)
            except Exception as e:
                print(f"Error loading evolution data: {e}")
                self.evolution_data = {}
        else:
            self.evolution_data = {}
    
    def load_pokemon_cache(self):
        """Load all Pokémon names into memory for fast autocomplete"""
        pokemon_dir = os.path.join("data", "pokemon")
        self.pokemon_cache, self.pokemon_cache_lower = load_or_build_cache(
            "pokemon.json",
            pokemon_dir,
            "[Learns] Pokémon species"
        )

    def load_related_data(self, rel: str) -> dict:
        """
        Attempts to load the movelist JSON for a related Pokémon using the fallback lookup.
        """
        rel_norm = normalize_name(rel)
        filename = find_movelist_filename(rel_norm)
        print(f"Looking for related file for '{rel}' using normalized value '{rel_norm}'.")
        if not filename:
            print(f"File not found for '{rel}'.")
            return None
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"Loaded data for '{rel}' from {filename}.")
                return data
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return None

    def combine_moves(self, main_data: dict, related_names: list) -> dict:
        """
        Combines moves from the main Pokémon with those from related Pokémon.
        
        For non-rank categories (like 'tm', 'tutor', 'egg'), it does a simple union with marking.
        For rank categories ('bronze', 'silver', 'gold', 'platinum', 'diamond'),
        it processes them in order so that moves learned earlier are preserved and duplicates
        in later ranks are removed. If a move in a rank comes only from a related form (and not
        from the main Pokémon's own moves for that rank), it is marked with an asterisk.
        """
        combined = {}
        # Process non-rank categories
        non_rank = set(main_data.get("moves", {}).keys()) - {"bronze", "silver", "gold", "platinum", "diamond"}
        for cat in non_rank:
            main_moves = set(main_data.get("moves", {}).get(cat, []))
            union_moves = set(main_moves)
            for rel in related_names:
                rel_data = self.load_related_data(rel)
                if rel_data:
                    union_moves.update(rel_data.get("moves", {}).get(cat, []))
            sorted_moves = sorted(union_moves, key=lambda x: x.lower())
            marked_moves = [f"{move}*" if move not in main_moves else move for move in sorted_moves]
            combined[cat] = marked_moves

        # Process rank categories in order.
        ranks = ["bronze", "silver", "gold", "platinum", "diamond"]
        previous_moves = set()
        for rank in ranks:
            main_moves = set(main_data.get("moves", {}).get(rank, []))
            related_moves = set()
            for rel in related_names:
                rel_data = self.load_related_data(rel)
                if rel_data:
                    related_moves.update(rel_data.get("moves", {}).get(rank, []))
            union_moves = main_moves.union(related_moves)
            # Remove moves already learned in earlier ranks.
            new_moves = union_moves - previous_moves
            sorted_moves = sorted(new_moves, key=lambda x: x.lower())
            # Mark a move with an asterisk if it is not present in the main moves for this rank.
            marked_moves = [move if move in main_moves else f"{move}*" for move in sorted_moves]
            combined[rank] = marked_moves
            previous_moves.update(union_moves)
        return combined

    @app_commands.command(name="learns", description="Show move list info for a Pokémon")
    async def learns(self, interaction: discord.Interaction, pokemon: str):
        norm_pokemon = normalize_name(pokemon)
        filename = find_movelist_filename(norm_pokemon)
        if not filename:
            await interaction.response.send_message(f"Could not find data for Pokémon **{pokemon}**.", ephemeral=True)
            return

        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            await interaction.response.send_message("Error loading the Pokémon data.", ephemeral=True)
            print(f"Error loading {filename}: {e}")
            return

        # Look for evolution data using fuzzy matching on keys.
        evo_key = find_evolution_key(norm_pokemon, self.evolution_data)
        if evo_key:
            related_pokemon = self.evolution_data[evo_key]
            print(f"Combining moves for {pokemon} with related Pokémon: {related_pokemon}")
            data["moves"] = self.combine_moves(data, related_pokemon)
        else:
            print(f"No evolution data found for {pokemon}.")

        header = f"### {data.get('name', 'Unknown')} [#{data.get('number', '?')}]"
        moves = data.get("moves", {})

        # Sort all displayed move lists
        bronze_moves = format_moves(sorted_moves_list(moves.get("bronze", [])))
        silver_moves = format_moves(sorted_moves_list(moves.get("silver", [])))
        gold_moves = format_moves(sorted_moves_list(moves.get("gold", [])))
        platinum_moves = format_moves(sorted_moves_list(moves.get("platinum", [])))

        rank_sections = []
        rank_data = [
            ("<:badgebronze:1272532685197152349> **Bronze**", bronze_moves),
            ("<:badgesilver:1272533590697185391> **Silver**", silver_moves),
            ("<:badgegold:1272532681992962068> **Gold**", gold_moves),
            ("<:badgeplatinum:1272533593750507570> **Platinum**", platinum_moves)
        ]
        for rank_title, moves_text in rank_data:
            if moves_text != "None":
                rank_sections.append(f"{rank_title}\n{moves_text}")

        initial_text = header
        if rank_sections:
            initial_text += "\n\n" + "\n\n".join(rank_sections)

        view = LearnMovesView(pokemon_data=data, author=interaction.user)
        await interaction.response.send_message(initial_text, view=view)

    @learns.autocomplete("pokemon")
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
    await bot.add_cog(MovesCog(bot))
