import discord
from discord import app_commands
from discord.ext import commands
import os
import json
import random

class Moody(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_folder = "Data"

        # Ensure the folder exists
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)

    def simulate_moody(self, stats):
        """Simulate Moody's effect on a Pokémon's stats."""
        stat_names = list(stats.keys())
        
        # Select a stat to boost
        boost_stat = random.choice(stat_names)

        # Ensure a different stat for the second boost
        boost_other_stat = random.choice([stat for stat in stat_names if stat != boost_stat])

        # Ensure a different stat for the reduction
        lower_stat = random.choice([stat for stat in stat_names if stat not in {boost_stat, boost_other_stat}])

        # Apply the boosts and reduction
        stats[boost_stat] += 1
        stats[boost_other_stat] += 1
        stats[lower_stat] -= 1

        # Ensure stats remain within logical bounds
        stats[boost_stat] = min(stats[boost_stat], 3)  # Max stage is 3
        stats[boost_other_stat] = min(stats[boost_other_stat], 3)  # Max stage is 3
        stats[lower_stat] = max(stats[lower_stat], -3)  # Min stage is -3

        return boost_stat, boost_other_stat, lower_stat

    async def autocomplete_pokemon_name(self, interaction: discord.Interaction, current: str):
        """Autocomplete Pokémon names based on the user's saved Pokémon."""
        user_id = str(interaction.user.id)
        file_path = os.path.join(self.data_folder, f"{user_id}_stats.json")

        # Check if the file exists
        if not os.path.exists(file_path):
            return []

        # Load Pokémon names
        with open(file_path, "r") as file:
            data = json.load(file)

        # Filter Pokémon names based on user input
        return [
            app_commands.Choice(name=name, value=name)
            for name in data.keys()
            if current.lower() in name.lower()
        ]

    @app_commands.command(name="moody", description="Simulate Moody for your Pokémon or reset its stats.")
    @app_commands.autocomplete(pokemon_name=autocomplete_pokemon_name)
    async def moody(self, interaction: discord.Interaction, pokemon_name: str, reset: bool = False):
        user_id = str(interaction.user.id)
        file_path = os.path.join(self.data_folder, f"{user_id}_stats.json")

        # If the file doesn't exist, create it with a sample Pokémon's stats
        if not os.path.exists(file_path):
            stats = {"Strength": 0, "Dexterity": 0, "Special": 0, "Defense": 0, "Special Defense": 0}
            data = {pokemon_name: stats}

            with open(file_path, "w") as file:
                json.dump(data, file, indent=4)

        # Load Pokémon stats
        with open(file_path, "r") as file:
            data = json.load(file)

        # Get stats for the specified Pokémon
        if pokemon_name not in data:
            await interaction.response.send_message(
                f"{pokemon_name} is not set up yet. Use the command again to create it.",
                ephemeral=True
            )
            return

        stats = data[pokemon_name]

        if reset:
            # Reset stats to zero
            data[pokemon_name] = {"Strength": 0, "Dexterity": 0, "Special": 0, "Defense": 0, "Special Defense": 0}
            with open(file_path, "w") as file:
                json.dump(data, file, indent=4)

            non_zero_stats = {}  # Initialize as empty since stats are reset
            await interaction.response.send_message(
                f"{pokemon_name}'s stats have been reset to zero.",
                ephemeral=True
            )
            return

        # Apply Moody effect
        boost_stat, boost_other_stat, lower_stat = self.simulate_moody(stats)

        # Save the updated stats
        data[pokemon_name] = stats
        with open(file_path, "w") as file:
            json.dump(data, file, indent=4)

        # Filter stats to only show non-zero values
        non_zero_stats = {key: value for key, value in stats.items() if value != 0}

        # Format stats to display vertically
        non_zero_stats_str = "\n".join(f"{key}: {value}" for key, value in non_zero_stats.items())

        # Confirm the changes
        await interaction.response.send_message(
            f"{pokemon_name}'s Moody activated! {boost_stat} and {boost_other_stat} rose by 1 stage each, and {lower_stat} fell by 1 stage.\n\n"
            f"Updated stats:\n{non_zero_stats_str}"
        )

async def setup(bot):
    await bot.add_cog(Moody(bot))
