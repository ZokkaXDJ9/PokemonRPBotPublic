import discord
from discord import app_commands
from discord.ext import commands
import os
import json
from typing import List
from helpers import load_rule  # Function to load rule data
from cache_helper import load_or_build_cache

RULES_DIRECTORY = os.path.join(os.path.dirname(__file__), "../Data/rules")
MAX_DISCORD_MESSAGE_LENGTH = 2000

def chunk_message_preserve_formatting(text: str, limit: int = 2000) -> list[str]:
    """
    Splits 'text' into chunks of at most 'limit' characters each,
    preserving all original spacing/newlines and attempting
    not to break words. If a single word is longer than 'limit',
    it will necessarily be broken mid-word.
    """
    chunks = []
    i = 0
    n = len(text)

    while i < n:
        # If the remaining text is short enough, just append it
        if n - i <= limit:
            chunks.append(text[i:])
            break

        end_index = i + limit

        candidate_break = end_index
        if not text[end_index - 1].isspace() and end_index < n and not text[end_index].isspace():
            whitespace_pos = -1
            for sep in (" ", "\n", "\r", "\t"):
                pos = text.rfind(sep, i, end_index)
                if pos > whitespace_pos:
                    whitespace_pos = pos

            # If we found whitespace in the chunk, break there
            if whitespace_pos != -1 and whitespace_pos >= i:
                candidate_break = whitespace_pos
        if candidate_break == i:
            candidate_break = end_index

        chunk = text[i:candidate_break]
        chunks.append(chunk)

        i = candidate_break

        while i < n and text[i].isspace():
            i += 1

    return chunks

class RulesCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cache rule names at startup
        self.rule_cache: List[str] = []
        self.rule_cache_lower: List[str] = []
        self.load_rule_cache()
    
    def load_rule_cache(self):
        """Load all rule names into memory for fast autocomplete"""
        rules_dir = os.path.join(os.path.dirname(__file__), "..", "Data", "rules")
        self.rule_cache, self.rule_cache_lower = load_or_build_cache(
            "rules.json",
            rules_dir,
            "rules"
        )

    # Autocomplete function to suggest rule names
    async def autocomplete_rule(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Fast autocomplete using cached rule names"""
        if not current:
            return [app_commands.Choice(name=name, value=name) for name in self.rule_cache[:25]]
        
        current_lower = current.lower()
        matches = []
        
        for name, name_lower in zip(self.rule_cache, self.rule_cache_lower):
            if current_lower in name_lower:
                matches.append(app_commands.Choice(name=name, value=name))
                if len(matches) >= 25:
                    break
        
        return matches

    @app_commands.command(name="rule", description="Display details of a game rule")
    @app_commands.autocomplete(name=autocomplete_rule)
    async def rules(self, interaction: discord.Interaction, name: str):
        # Load the rule data from JSON file
        rule = load_rule(name)
        if rule is None:
            await interaction.response.send_message(
                content=f"Unable to find a rule named **{name}**, sorry! If that wasn't a typo, maybe it isn't implemented yet?",
                ephemeral=True
            )
            return

        # Construct a plain text message with Discord Markdown formatting
        response = f"""
### {rule['name']}
*{rule['flavor']}*
{rule['text']}
"""
        if rule.get("example"):
            response += f"**Example**: {rule['example']}\n"

        # Split the response in a way that preserves all formatting
        chunks = chunk_message_preserve_formatting(response, MAX_DISCORD_MESSAGE_LENGTH)

        # Send the first chunk with interaction.response
        await interaction.response.send_message(chunks[0])

        # Send remaining chunks via followup
        for chunk in chunks[1:]:
            await interaction.followup.send(chunk)

async def setup(bot):
    await bot.add_cog(RulesCommand(bot))
