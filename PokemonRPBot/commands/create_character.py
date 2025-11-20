import discord
from discord import app_commands
from discord.ext import commands
import os
import json
from typing import Literal, List
from data_loader import load_pokemon_data
from emojis import get_type_emoji
from ranks import get_rank  # Import the ranks
from cache_helper import load_or_build_cache

# Resolve the absolute path to the current script's directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Use absolute paths for Pokémon data directories
POKEMON_NEW_DIRECTORY = os.path.join(BASE_DIR, "../Data/pokemon_new")
POKEMON_OLD_DIRECTORY = os.path.join(BASE_DIR, "../Data/pokemon_old")

# Character storage directory
CHARACTERS_DIR = os.path.join(BASE_DIR, "../characters/")

if not os.path.exists(CHARACTERS_DIR):
    os.makedirs(CHARACTERS_DIR)


# Helper function to load Pokémon data with priority to new format
def load_pokemon_data_with_priority(pokemon_species):
    """Load Pokémon data, prioritizing the new format over the old."""
    # Attempt to load from new format
    new_file_path = os.path.join(POKEMON_NEW_DIRECTORY, f"{pokemon_species.lower()}.json")
    if os.path.exists(new_file_path):
        with open(new_file_path, "r") as f:
            data = json.load(f)
            data['format'] = 'new'
        return data

    # Attempt to load from old format
    old_file_path = os.path.join(POKEMON_OLD_DIRECTORY, f"{pokemon_species.lower()}.json")
    if os.path.exists(old_file_path):
        with open(old_file_path, "r") as f:
            data = json.load(f)
            data['format'] = 'old'
        return data

    # If not found in either, return None
    return None


# Helper function to load character data
def load_character_data(user_id: int, guild_id: int, character_name: str):
    character_file = os.path.join(CHARACTERS_DIR, f"{user_id}_{guild_id}_{character_name.lower()}.json")
    if os.path.exists(character_file):
        with open(character_file, 'r') as file:
            return json.load(file)
    else:
        return None


class PermanentSheetView(discord.ui.View):
    """Persistent view for the character sheet."""
    def __init__(self, user_id: int, guild_id: int, character_name: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.guild_id = guild_id
        self.character_name = character_name

        # Load character data
        character_data = load_character_data(user_id, guild_id, character_name)
        if character_data is None:
            return  # No character data found

        # Get unallocated points
        unallocated_battle_points = character_data.get('unallocated_battle_points', 0)
        unallocated_social_points = character_data.get('unallocated_social_points', 0)

        # Update button labels and disable if no points
        if unallocated_battle_points > 0:
            self.distribute_battle_stats.label = f"Distribute Battle Stats ({unallocated_battle_points})"
            self.distribute_battle_stats.disabled = False
            self.distribute_battle_stats.style = discord.ButtonStyle.blurple
        else:
            # Make the button less visible when there are no points
            self.distribute_battle_stats.label = "\u200b"  # Zero-width space
            self.distribute_battle_stats.disabled = True
            self.distribute_battle_stats.style = discord.ButtonStyle.secondary

        if unallocated_social_points > 0:
            self.distribute_social_stats.label = f"Distribute Social Stats ({unallocated_social_points})"
            self.distribute_social_stats.disabled = False
            self.distribute_social_stats.style = discord.ButtonStyle.blurple
        else:
            # Make the button less visible when there are no points
            self.distribute_social_stats.label = "\u200b"
            self.distribute_social_stats.disabled = True
            self.distribute_social_stats.style = discord.ButtonStyle.secondary

    @discord.ui.button(label='Distribute Battle Stats', style=discord.ButtonStyle.blurple, row=0, custom_id='persistent_distribute_battle_stats')
    async def distribute_battle_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_stat_distribution(interaction, category='battle')

    @discord.ui.button(label='Distribute Social Stats', style=discord.ButtonStyle.blurple, row=1, custom_id='persistent_distribute_social_stats')
    async def distribute_social_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_stat_distribution(interaction, category='social')

    async def handle_stat_distribution(self, interaction: discord.Interaction, category: str):
        # Check if the user interacting is the character owner
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You don't have permission to edit this character.", ephemeral=True)
            return

        character_data = load_character_data(self.user_id, self.guild_id, self.character_name)
        if character_data is None:
            await interaction.response.send_message("Character data not found.", ephemeral=True)
            return

        filepath = os.path.join(CHARACTERS_DIR, f"{self.user_id}_{self.guild_id}_{self.character_name.lower()}.json")
        view = StatDistributionView(character_data, filepath, interaction.message, category)
        content = view.get_message_content()
        await interaction.response.send_message(
            content=content,
            view=view,
            ephemeral=True
        )


class StatDistributionView(discord.ui.View):
    """Interactive view for stat distribution."""
    def __init__(self, character_data, filepath, main_message, category):
        super().__init__(timeout=None)
        self.character_data = character_data
        self.filepath = filepath
        self.main_message = main_message  # Reference to the main message for updating
        self.category = category  # 'battle' or 'social'
        self.unallocated_points = character_data.get(f'unallocated_{category}_points', 0)
        self.limit_break_level = character_data.get('limit_breaks', {}).get(category, 0)

        # Fixed stats at the start of the allocation session
        self.fixed_stats = character_data["stats"].copy()
        # Allocated stats during this session
        self.allocated_stats = character_data["stats"].copy()

        self.create_buttons()

    def get_message_content(self):
        """Generate the message content showing the stats and remaining points."""
        stats = self.allocated_stats
        max_stats = self.character_data["max_stats"]

        # Helper function to format stat lines
        def format_stat_line(stat_name, display_name):
            current = stats[stat_name]
            max_value = max_stats[stat_name]
            dots = '⬤' * min(current, max_value)
            if current > max_value:
                # Use ⧳ for limit break
                dots += '⧳' * (current - max_value)
            empty_dots = '⭘' * max(0, max_value - current)
            return f"{display_name:<6}{current:<2} |{dots}{empty_dots}"

        # Define abbreviations for battle stats
        battle_abbr = {
            "strength": "STR",
            "dexterity": "DEX",
            "vitality": "VIT",
            "special": "SPE",
            "insight": "INS"
        }

        # Select the appropriate stat display based on category
        if self.category == 'battle':
            stats_display = "\n".join(
                format_stat_line(stat_name, battle_abbr.get(stat_name, stat_name.title()))
                for stat_name in ["strength", "dexterity", "vitality", "special", "insight"]
                if stat_name in stats
            )
        else:
            # Social Stats: Ensure all labels have the same length by padding with zero-width spaces
            stats_list = ["tough", "cool", "beauty", "cute", "clever"]
            max_length = max(len(stat.title()) for stat in stats_list)  # 6 for "Beauty" and "Clever"

            def pad_label(stat):
                label = stat.title()
                padding_needed = max_length - len(label)
                return label + '\u200b' * padding_needed  # Pad with zero-width spaces

            stats_display = "\n".join(
                format_stat_line(stat_name, pad_label(stat_name))
                for stat_name in stats_list
                if stat_name in stats
            )

        content = (
            f"{self.character_data['name']}\n"
            f"```{stats_display}```\n"
            f"{self.unallocated_points} Remaining {self.category.title()} Points.\n"
            f"(You don't have to apply them all at once!)\n"
        )
        return content

    async def update_message(self, interaction: discord.Interaction):
        """Update the ephemeral message with the current stats and remaining points."""
        content = self.get_message_content()
        await interaction.response.edit_message(content=content, view=self)

    async def update_main_sheet(self):
        """Update the main character sheet message."""
        stats = self.character_data["stats"]
        max_stats = self.character_data["max_stats"]

        # Recalculate current experience towards next level
        current_exp = self.character_data["experience"] % self.character_data["experience_to_next_level"]

        # Build the updated character sheet content
        updated_response = create_character_sheet_content(self.character_data)

        # Check if there are still unallocated points
        has_battle_points = self.character_data.get('unallocated_battle_points', 0) > 0
        has_social_points = self.character_data.get('unallocated_social_points', 0) > 0

        if has_battle_points or has_social_points:
            new_view = PermanentSheetView(self.character_data['user_id'], self.character_data['guild_id'], self.character_data['name'])
            await self.main_message.edit(content=updated_response, view=new_view)
        else:
            # Remove the view if no points are left
            await self.main_message.edit(content=updated_response, view=None)

    def create_buttons(self):
        """Create increment and decrement buttons for each stat in the category."""
        if self.category == 'battle':
            stats_list = ["strength", "dexterity", "vitality", "special", "insight"]
            # Define abbreviations
            battle_abbr = {
                "strength": "STR",
                "dexterity": "DEX",
                "vitality": "VIT",
                "special": "SPE",
                "insight": "INS"
            }
            # Row 0: + STR | + DEX | + VIT | + SPE | + INS
            for stat in stats_list:
                abbr = battle_abbr.get(stat, stat.title())
                button = StatIncrementButton(stat_name=stat, stat_view=self, row=0, label=f"+ {abbr}")
                self.add_item(button)
            # Row 1: - STR | - DEX | - VIT | - SPE | - INS
            for stat in stats_list:
                abbr = battle_abbr.get(stat, stat.title())
                button = StatDecrementButton(stat_name=stat, stat_view=self, row=1, label=f"- {abbr}")
                self.add_item(button)
        else:
            # Social Stats: Ensure all labels have the same length by padding with zero-width spaces
            stats_list = ["tough", "cool", "beauty", "cute", "clever"]
            max_length = max(len(stat.title()) for stat in stats_list)  # 6 for "Beauty" and "Clever"

            def pad_label(stat):
                label = stat.title()
                padding_needed = max_length - len(label)
                return label + '\u200b' * padding_needed  # Pad with zero-width spaces

            # Row 0: + Tough | + Cool | + Beauty | + Cute | + Clever
            for stat in stats_list:
                padded_label = f"+ {pad_label(stat)}"
                button = StatIncrementButton(stat_name=stat, stat_view=self, row=0, label=padded_label)
                self.add_item(button)
            # Row 1: - Tough | - Cool | - Beauty | - Cute | - Clever
            for stat in stats_list:
                padded_label = f"- {pad_label(stat)}"
                button = StatDecrementButton(stat_name=stat, stat_view=self, row=1, label=padded_label)
                self.add_item(button)

        # Row 2: Accept | Cancel
        self.add_item(AcceptStatButton(stat_view=self, row=2))
        self.add_item(CancelStatButton(stat_view=self, row=2))


class StatIncrementButton(discord.ui.Button):
    def __init__(self, stat_name: str, stat_view: StatDistributionView, row: int, label: str):
        super().__init__(label=label, style=discord.ButtonStyle.green, row=row, custom_id=f'stat_{stat_name}_increment')
        self.stat_name = stat_name
        self.stat_view = stat_view

    async def callback(self, interaction: discord.Interaction):
        view = self.stat_view

        current_value = view.allocated_stats[self.stat_name]
        max_stat = view.character_data["max_stats"][self.stat_name]
        limit_break_level = view.limit_break_level

        cost = 1  # Base cost
        if current_value >= max_stat:
            # Cost is base cost + total limit break level + 1
            cost += limit_break_level + 1

        if view.unallocated_points < cost:
            await interaction.response.send_message(
                content=f"You don't have enough points to increase **{self.stat_name.title()}**. You need {cost} points.",
                ephemeral=True
            )
            return

        # Increment the stat and decrease the unallocated stat points
        view.allocated_stats[self.stat_name] += 1
        view.unallocated_points -= cost

        # If limit breaking, increment the limit break level for the category
        if current_value >= max_stat:
            view.limit_break_level += 1  # Increase limit break level

        await view.update_message(interaction)


class StatDecrementButton(discord.ui.Button):
    def __init__(self, stat_name: str, stat_view: StatDistributionView, row: int, label: str):
        super().__init__(label=label, style=discord.ButtonStyle.red, row=row, custom_id=f'stat_{stat_name}_decrement')
        self.stat_name = stat_name
        self.stat_view = stat_view

    async def callback(self, interaction: discord.Interaction):
        view = self.stat_view

        current_value = view.allocated_stats[self.stat_name]
        fixed_value = view.fixed_stats[self.stat_name]
        limit_break_level = view.limit_break_level

        if current_value <= fixed_value:
            await interaction.response.send_message(
                content=f"You cannot decrease **{self.stat_name.title()}** below its fixed value of {fixed_value}.",
                ephemeral=True
            )
            return

        max_stat = view.character_data["max_stats"][self.stat_name]

        # Determine if we are reducing a limit break
        if current_value > max_stat:
            # Decrement limit break level
            view.limit_break_level -= 1

        # Calculate the cost refund
        cost_refund = 1  # Base cost refund
        if current_value > max_stat:
            cost_refund += limit_break_level + 1

        # Decrease the stat and increase the unallocated stat points
        view.allocated_stats[self.stat_name] -= 1
        view.unallocated_points += cost_refund

        await view.update_message(interaction)


class AcceptStatButton(discord.ui.Button):
    def __init__(self, stat_view: StatDistributionView, row: int):
        super().__init__(label="Accept", style=discord.ButtonStyle.success, row=row, custom_id='stat_accept')
        self.stat_view = stat_view

    async def callback(self, interaction: discord.Interaction):
        view = self.stat_view
        character_data = view.character_data

        # Update the character's stats with the allocated stats
        character_data["stats"] = view.allocated_stats.copy()

        # Update unallocated points and limit breaks
        character_data['limit_breaks'][view.category] = view.limit_break_level
        character_data[f'unallocated_{view.category}_points'] = view.unallocated_points

        # Save changes to the JSON file
        with open(view.filepath, "w") as file:
            json.dump(character_data, file, indent=4)

        # Update the main message to reflect the finalized state
        await view.update_main_sheet()

        # Confirm to the user that everything is finalized
        await interaction.response.edit_message(
            content=f"Stat allocation for **{character_data['name']}** has been finalized and saved!",
            view=None  # Disable the view
        )


class CancelStatButton(discord.ui.Button):
    def __init__(self, stat_view: StatDistributionView, row: int):
        super().__init__(label="Cancel", style=discord.ButtonStyle.danger, row=row, custom_id='stat_cancel')
        self.stat_view = stat_view

    async def callback(self, interaction: discord.Interaction):
        view = self.stat_view

        # Confirm cancellation
        await interaction.response.edit_message(
            content=f"Stat allocation for **{view.character_data['name']}** has been canceled. No changes were made.",
            view=None  # Disable the view
        )


def create_character_sheet_content(character_data):
    stats = character_data["stats"]
    max_stats = character_data["max_stats"]

    # Calculate current experience towards next level for display
    current_exp = character_data["experience"] % character_data["experience_to_next_level"]

    # Helper function to format stat lines
    def format_stat_line(stat_name, display_name):
        current = stats[stat_name]
        max_value = max_stats[stat_name]
        dots = '⬤' * min(current, max_value)
        if current > max_value:
            # Use ⧳ for limit break
            dots += '⧳' * (current - max_value)
        empty_dots = '⭘' * max(0, max_value - current)
        return f"{display_name:<6}{current:<2} |{dots}{empty_dots}"

    # Define abbreviations for battle stats
    battle_abbr = {
        "strength": "STR",
        "dexterity": "DEX",
        "vitality": "VIT",
        "special": "SPE",
        "insight": "INS"
    }

    # Battle stats display
    battle_stats_display = "\n".join(
        format_stat_line(stat_name, battle_abbr.get(stat_name, stat_name.title()))
        for stat_name in ["strength", "dexterity", "vitality", "special", "insight"]
        if stat_name in stats
    )

    # Social stats display
    social_stats_display = "\n".join(
        format_stat_line(stat_name, stat_name.title())
        for stat_name in ["tough", "cool", "beauty", "cute", "clever"]
        if stat_name in stats
    )

    response = (
        f"## {character_data['name']}\n"
        f"**Level {character_data['level']}** ({current_exp} / {character_data['experience_to_next_level']})\n"
        f"Rank: {get_rank(character_data['level'])}\n"
        f"{character_data['money']} Coins\n"
        f"### Stats {' '.join([get_type_emoji(t) for t in character_data['types']])}\n"
        f"```HP: {stats['hp']}\n"
        f"Willpower: {stats['willpower']}\n\n"
        f"{battle_stats_display}\n\n"
        f"Defense: {stats['defense']}\n"
        f"Special Defense: {stats['special_defense']}\n"
        f"Active Move Limit: {stats['active_move_limit']}\n\n"
        f"{social_stats_display}```\n"
        f"### Abilities\n"
        + "\n".join(f"- {ability}" for ability in character_data['abilities']) + "\n"
        f"### Statistics\n"
        f"Backpack Slots: {character_data['statistics']['backpack_slots']}\n"
        f"Completed Quests: {character_data['statistics']['completed_quests']}\n"
        f"Total Sparring Sessions: {character_data['statistics']['sparring_sessions']}"
    )
    return response


class CreateCharacterCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cache Pokémon names at startup
        self.pokemon_cache: List[str] = []
        self.pokemon_cache_lower: List[str] = []
        self.load_pokemon_cache()
    
    def load_pokemon_cache(self):
        """Load all Pokémon names from both old and new directories into memory for fast autocomplete"""
        # Combine names from both directories
        all_names = []
        
        if os.path.exists(POKEMON_NEW_DIRECTORY):
            new_names = [f[:-5] for f in os.listdir(POKEMON_NEW_DIRECTORY) if f.endswith(".json")]
            all_names.extend(new_names)
        
        if os.path.exists(POKEMON_OLD_DIRECTORY):
            old_names = [f[:-5] for f in os.listdir(POKEMON_OLD_DIRECTORY) if f.endswith(".json")]
            # Add old names that aren't already in new directory
            all_names.extend([name for name in old_names if name not in all_names])
        
        # Sort and create lowercase cache
        self.pokemon_cache = sorted(all_names)
        self.pokemon_cache_lower = [name.lower() for name in self.pokemon_cache]
        print(f"[Create Character] Loaded {len(self.pokemon_cache)} Pokémon species")

    async def autocomplete_pokemon(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Fast autocomplete using cached Pokémon names from both new and old directories"""
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

    async def autocomplete_gender(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete gender options."""
        genders = ["Male", "Female", "Genderless"]
        return [
            app_commands.Choice(name=gender, value=gender)
            for gender in genders
            if current.lower() in gender.lower()
        ]

    @app_commands.command(
        name="create_character",
        description="Create a new character with custom parameters."
    )
    @app_commands.autocomplete(
        pokemon_species=autocomplete_pokemon, gender=autocomplete_gender
    )
    async def create_character(
        self,
        interaction: discord.Interaction,
        player: discord.Member,
        name: str,
        pokemon_species: str,
        gender: str,
        is_shiny: bool = False,
        exp: int = 0,
        money: int = 500
    ):
        """Create a character for a specified player."""
        user_id = player.id
        guild_id = interaction.guild.id

        character_file = os.path.join(CHARACTERS_DIR, f"{user_id}_{guild_id}_{name.lower()}.json")

        if os.path.exists(character_file):
            await interaction.response.send_message(content=f"A character named **{name}** already exists for {player.mention} in this server.", ephemeral=True)
            return

        data = load_pokemon_data_with_priority(pokemon_species)
        if data is None:
            await interaction.response.send_message(content=f"Unable to find Pokémon data for **{pokemon_species}**, sorry!", ephemeral=True)
            return

        level = exp // 100 + 1

        # Calculate experience towards next level
        experience_to_next_level = 100
        current_exp = exp % experience_to_next_level

        # Extract stats based on data format
        if data.get('format') == 'new':
            # New format
            base_hp = data.get("base_hp", 10)  # Default to 10 if not specified
            # Extract starting stats and max stats
            starting_stats = {}
            max_stats = {}
            for stat_name in ["strength", "dexterity", "vitality", "special", "insight"]:
                if stat_name in data:
                    stat_value = data.get(stat_name, "1/1")
                    try:
                        start, max_value = map(int, stat_value.split('/'))
                    except ValueError:
                        start, max_value = 1, 1  # Default values if parsing fails
                    starting_stats[stat_name] = start
                    max_stats[stat_name] = max_value
            # Types
            types = data.get("types", ["Normal"])
            # Abilities
            abilities = []
            for rarity in ['bronze', 'silver', 'gold', 'platinum', 'diamond']:
                abilities.extend(data.get('abilities', {}).get(rarity, []))
            # Take first two abilities
            abilities = abilities[:2] if abilities else ["Unknown"]
        else:
            # Old format
            base_hp = data.get("BaseHP", 10)
            starting_stats = {}
            max_stats = {}
            for stat_name in ["Strength", "Dexterity", "Vitality", "Special", "Insight"]:
                if stat_name in data:
                    stat_value = data.get(stat_name, 1)
                    max_value = data.get(f"Max{stat_name}", 5)
                    stat_key = stat_name.lower()
                    starting_stats[stat_key] = stat_value
                    max_stats[stat_key] = max_value
            # Types
            types = [t for t in [data.get("Type1", ""), data.get("Type2", "")] if t]
            # Abilities
            abilities = [a for a in [data.get("Ability1"), data.get("Ability2")] if a]

        # Initialize battle stats with starting values
        stats = {
            "hp": base_hp,
            "willpower": 3,
            "defense": 1,
            "special_defense": 1,
            "active_move_limit": 3
        }
        stats.update({stat: starting_stats.get(stat, 1) for stat in starting_stats})

        # Initialize social stats with base 1 and max 5
        social_stats = ["tough", "cool", "beauty", "cute", "clever"]
        for stat in social_stats:
            stats[stat] = 1  # Base value
            max_stats[stat] = 5  # Max value

        # Initialize unallocated stat points
        unallocated_battle_points = 4 + (level - 1)  # Gain 1 battle point per level

        # Determine rank based on level
        rank = get_rank(level)

        # Initialize unallocated social points
        # Characters start with 4 social stat points at Bronze rank
        # Gain 2 additional social points each time they reach a new rank
        rank_levels = [1, 2, 4, 8, 16, 20]  # Levels at which rank changes
        social_points = 0
        for rank_level in rank_levels:
            if level >= rank_level:
                social_points += 2  # Gain 2 social points per new rank
        unallocated_social_points = social_points

        # Adjust initial social points to 4 at Bronze rank
        if level == 1:
            unallocated_social_points = 4

        character_data = {
            "id": user_id,
            "user_id": user_id,
            "guild_id": guild_id,
            "name": name,
            "level": level,
            "experience": exp,  # Store total experience here
            "experience_to_next_level": experience_to_next_level,
            "money": money,
            "types": types,
            "gender": gender,
            "is_shiny": is_shiny,
            "stats": stats,
            "max_stats": max_stats,
            "starting_stats": starting_stats,
            "abilities": abilities,
            "statistics": {
                "backpack_slots": 6,
                "completed_quests": 0,
                "sparring_sessions": 0
            },
            "unallocated_battle_points": unallocated_battle_points,
            "unallocated_social_points": unallocated_social_points,
            "limit_breaks": {"battle": 0, "social": 0}
        }

        with open(character_file, "w") as file:
            json.dump(character_data, file, indent=4)

        # Prepare the character sheet content
        response = create_character_sheet_content(character_data)

        main_message = await interaction.channel.send(response)
        view = PermanentSheetView(user_id, guild_id, name)
        await main_message.edit(view=view)

        # Confirm creation to the user
        await interaction.response.send_message(f"Character **{name}** has been created for {player.mention}!", ephemeral=True)


async def setup(bot):
    """Load the cog."""
    await bot.add_cog(CreateCharacterCommand(bot))

    # Register persistent views for all existing characters
    for filename in os.listdir(CHARACTERS_DIR):
        if filename.endswith('.json'):
            user_id_str, guild_id_str, character_name = filename[:-5].split('_', 2)
            user_id = int(user_id_str)
            guild_id = int(guild_id_str)
            character_data = load_character_data(user_id, guild_id, character_name)
            if character_data is not None:
                view = PermanentSheetView(user_id, guild_id, character_name)
                bot.add_view(view)
