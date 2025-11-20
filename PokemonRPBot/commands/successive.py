import discord
from discord import app_commands
from discord.ext import commands
from helpers import ParsedRollQuery
import re
import logging

# Configure logging
logger = logging.getLogger('discord.successive')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='successive_debug.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

class SuccessiveRollView(discord.ui.View):
    def __init__(self, bot, query, required_successes, total_successes, total_rolls, accuracy=0, has_rerolled=False):
        super().__init__(timeout=None)
        self.bot = bot
        self.query = query
        self.required_successes = required_successes
        self.total_successes = total_successes
        self.total_rolls = total_rolls
        self.accuracy = accuracy
        self.has_rerolled = has_rerolled

    @discord.ui.button(label="Reroll Last Failed Roll", style=discord.ButtonStyle.primary)
    async def reroll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.has_rerolled:
            await interaction.response.send_message(
                "You have already rerolled the last failed roll.",
                ephemeral=True
            )
            return
        self.has_rerolled = True

        # Perform the reroll
        parsed_query = ParsedRollQuery.from_query(self.query)
        roll_result_text = parsed_query.execute()

        # Log the reroll result for debugging
        logger.debug(f"Reroll Roll Result Text: {roll_result_text}")

        # Extract rolls from the reroll result
        match = re.search(r'[—–-]\s*([^\n\r]*)', roll_result_text)
        if match:
            rolls_text = match.group(1)
            rolls_text_clean = re.sub(r'[^0-9,]', '', rolls_text)
            rolls = [int(num.strip()) for num in rolls_text_clean.split(',') if num.strip().isdigit()]
        else:
            rolls = []

        # Log extracted rolls
        logger.debug(f"Extracted Rolls: {rolls}")

        successes = sum(1 for die in rolls if die >= 4)
        crits = sum(1 for die in rolls if die == 6)
        adjusted_successes = successes + self.accuracy

        # Format the roll results with critical marking
        formatted_rolls = []
        for die in rolls:
            if die == 6:
                formatted_rolls.append("**__6__**")
            elif die >= 4:
                formatted_rolls.append(f"**{die}**")
            else:
                formatted_rolls.append(f"{die}")
        roll_text = ", ".join(formatted_rolls)

        # Check for "CRIT!" condition
        crit_text = " **(CRIT!)**" if crits >= 3 else ""

        # Prepare the reroll output
        reroll_output = f"**Reroll of Last Failed Roll:**\n"
        reroll_output += f"{self.query} — {roll_text}\n"
        reroll_output += f"**Successes:** {adjusted_successes} / **Required:** {self.required_successes}{crit_text}\n\n"

        if adjusted_successes >= self.required_successes:
            reroll_output += "✅ **Success after reroll!**\n\n"
            self.total_successes += 1
            self.required_successes += 2
            roll_number = 1
            while True:
                parsed_query = ParsedRollQuery.from_query(self.query)
                roll_result_text = parsed_query.execute()

                logger.debug(f"Continuing Roll {roll_number} Result Text: {roll_result_text}")

                match = re.search(r'[—–-]\s*([^\n\r]*)', roll_result_text)
                if match:
                    rolls_text = match.group(1)
                    rolls_text_clean = re.sub(r'[^0-9,]', '', rolls_text)
                    rolls = [int(num.strip()) for num in rolls_text_clean.split(',') if num.strip().isdigit()]
                else:
                    rolls = []

                logger.debug(f"Extracted Rolls for Roll {roll_number}: {rolls}")

                successes = sum(1 for die in rolls if die >= 4)
                crits = sum(1 for die in rolls if die == 6)
                adjusted_successes = successes + self.accuracy

                formatted_rolls = []
                for die in rolls:
                    if die == 6:
                        formatted_rolls.append("**__6__**")
                    elif die >= 4:
                        formatted_rolls.append(f"**{die}**")
                    else:
                        formatted_rolls.append(f"{die}")
                roll_text = ", ".join(formatted_rolls)
                crit_text = " **(CRIT!)**" if crits >= 3 else ""

                reroll_output += f"**Roll:** {self.query} — {roll_text}\n"
                reroll_output += f"**Successes:** {adjusted_successes} / **Required:** {self.required_successes}{crit_text}\n\n"

                if adjusted_successes >= self.required_successes:
                    reroll_output += "✅ **Success!**\n\n"
                    self.total_successes += 1
                    self.required_successes += 2
                else:
                    reroll_output += "❌ **Failed!**\n\n"
                    break
                roll_number += 1
        else:
            reroll_output += "❌ **Failed after reroll!**\n\n"

        # Count total successful rolls
        reroll_output += f"**Total Successful Rolls:** {self.total_successes}\n"

        # Send the reroll result directly as a response to the button interaction
        await interaction.response.send_message(content=reroll_output)

class SuccessiveCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="successive", description="Perform successive rolls with increasing difficulty.")
    @app_commands.describe(
        query='The dice roll query',
        accuracy='The accuracy modifier (can be positive or negative)'
    )
    async def successive(self, interaction: discord.Interaction, query: str, accuracy: int = 0):
        required_successes = 1
        total_successes = 0
        output = ""
        roll_number = 1

        while True:
            parsed_query = ParsedRollQuery.from_query(query)
            roll_result_text = parsed_query.execute()

            logger.debug(f"Roll {roll_number} Result Text: {roll_result_text}")

            match = re.search(r'[—–-]\s*([^\n\r]*)', roll_result_text)
            if match:
                rolls_text = match.group(1)
                rolls_text_clean = re.sub(r'[^0-9,]', '', rolls_text)
                rolls = [int(num.strip()) for num in rolls_text_clean.split(',') if num.strip().isdigit()]
            else:
                rolls = []

            logger.debug(f"Extracted Rolls for Roll {roll_number}: {rolls}")

            successes = sum(1 for die in rolls if die >= 4)
            crits = sum(1 for die in rolls if die == 6)
            adjusted_successes = successes + accuracy

            formatted_rolls = []
            for die in rolls:
                if die == 6:
                    formatted_rolls.append("**__6__**")
                elif die >= 4:
                    formatted_rolls.append(f"**{die}**")
                else:
                    formatted_rolls.append(f"{die}")
            roll_text = ", ".join(formatted_rolls)
            crit_text = " **(CRIT!)**" if crits >= 3 else ""

            output += f"**Roll {roll_number}:** {query} — {roll_text}\n"
            output += f"**Successes:** {adjusted_successes} / **Required:** {required_successes}{crit_text}\n\n"

            if adjusted_successes >= required_successes:
                total_successes += 1
                output += "✅ **Success!**\n\n"
                required_successes += 2
            else:
                output += "❌ **Failed!**\n\n"
                break

            roll_number += 1

        output += f"**Total Successful Rolls:** {total_successes}\n"

        if "❌ **Failed!**" in output:
            view = SuccessiveRollView(
                bot=self.bot,
                query=query,
                required_successes=required_successes,
                total_successes=total_successes,
                total_rolls=[],
                accuracy=accuracy
            )
            await interaction.response.send_message(content=output, view=view)
        else:
            await interaction.response.send_message(content=output)

async def setup(bot):
    await bot.add_cog(SuccessiveCommand(bot))
