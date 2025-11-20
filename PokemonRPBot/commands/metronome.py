import discord
from discord import app_commands
from discord.ext import commands
import os, random, logging, json, traceback
from helpers import load_move        # keep using your existing loader
from emojis  import get_type_emoji, get_category_emoji

MOVES_DIRECTORY = os.path.join(os.path.dirname(__file__), "../Data/moves")

def g(obj, *keys, default="—"):
    """Return the first key that exists in *obj* (case-insensitive)."""
    for k in keys:
        if k in obj:               # exact match
            return obj[k]
        k_low = k.lower()
        for kk in obj:             # fallback: case-folded match
            if kk.lower() == k_low:
                return obj[kk]
    return default

class MetronomeCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="metronome",
        description="Use the most randomest of moves!"
    )
    async def metronome(self, inter: discord.Interaction):
        # 1) Never make Discord wait: acknowledge instantly
        await inter.response.defer(thinking=True)

        try:
            files = [f for f in os.listdir(MOVES_DIRECTORY) if f.endswith(".json")]
            if not files:
                await inter.followup.send("No moves found.", ephemeral=True)
                return

            move_name = random.choice(files)[:-5]
            move      = load_move(move_name) or {}

            # ---- pull fields, old-or-new spelling ----
            name     = g(move, "Name",      "name",      default=move_name)
            desc     = g(move, "Description","description","")
            mtype    = g(move, "Type",      "type")
            cat      = g(move, "Category",  "category")
            target   = g(move, "Target",    "target")
            dmg      = g(move, "Damage1",   "damage",     default="")
            power    = g(move, "Power",     "power",      default="")
            acc      = g(move, "Accuracy1", "accuracy")
            effect   = g(move, "Effect",    "effect")

            t_icon = get_type_emoji(mtype)
            c_icon = get_category_emoji(cat)

            # ---- build the message ----
            lines = [
                f"### {name}",
                f"*{desc}*",
                f"**Type**: {t_icon} {mtype} — **{c_icon} {cat}**",
                f"**Target**: {target}",
            ]
            if dmg:
                lines.append(f"**Damage Dice**: {dmg} + {power}")
            lines.extend([
                f"**Accuracy Dice**: {acc} + Rank",
                f"**Effect**: {effect}",
            ])

            await inter.followup.send("\n".join(lines))

        except Exception as e:
            logging.error("metronome failed: %s\n%s", e, traceback.format_exc())
            await inter.followup.send(
                "⚠️ Something went wrong picking that move. Try again!",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(MetronomeCommand(bot))
