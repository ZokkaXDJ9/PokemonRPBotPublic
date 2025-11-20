import discord
from discord import app_commands
from discord.ext import commands
import random
from typing import List

class LootBox(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Define multiple lock tables with optional categories
        self.lock_boxes = {
            "Berry": {
                "Common Berries": {"probability": 350, "items": [
                    {"item": "2x Aspear Berry", "probability": 25},
                    {"item": "2x Cheri Berry", "probability": 25},
                    {"item": "2x Pecha Berry", "probability": 25},
                    {"item": "2x Rawst Berry", "probability": 25},
                    {"item": "2x Cheri Berry", "probability": 25},
                    {"item": "2x Chesto Berry", "probability": 25},
                    {"item": "2x Coba Berry", "probability": 25},
                    {"item": "2x Colbur Berry", "probability": 25},
                    {"item": "2x Drash Berry", "probability": 25},
                    {"item": "2x Pecha Berry", "probability": 25},
                    {"item": "2x Persim Berry", "probability": 25},
                    {"item": "2x Rawst Berry", "probability": 25},
                    {"item": "2x Starf Berry", "probability": 25},
                ]},
                "Uncommon Berries": {"probability": 350, "items": [
                    {"item": "Bitmel Berry", "probability": 50},
                    {"item": "Charti Berry", "probability": 50},
                    {"item": "Petaya Berry", "probability": 50},
                    {"item": "Chilan Berry", "probability": 50},
                    {"item": "Roseli Berry", "probability": 50},
                    {"item": "Babiri Berry", "probability": 50},
                    {"item": "Chipe Berry", "probability": 50},
                    {"item": "Chople Berry", "probability": 50},
                    {"item": "Haban Berry", "probability": 50},
                    {"item": "Kasib Berry", "probability": 50},
                    {"item": "Kebia Berry", "probability": 50},
                    {"item": "Leichi Berry", "probability": 50},
                    {"item": "Magost Berry", "probability": 50},
                    {"item": "Nomel Berry", "probability": 50},
                    {"item": "Occa Berry", "probability": 50},
                    {"item": "Passho Berry", "probability": 50},
                    {"item": "Payapa Berry", "probability": 50},
                    {"item": "Pumkin Berry", "probability": 50},
                    {"item": "Rindo Berry", "probability": 50},
                    {"item": "Salac Berry", "probability": 50},
                    {"item": "Shuca Berry", "probability": 50},
                    {"item": "Sitrus Berry", "probability": 50},
                    {"item": "Tanga Berry", "probability": 50},
                    {"item": "Wacan Berry", "probability": 50},
                    {"item": "Yache Berry", "probability": 50},
                    {"item": "Jaboca Berry", "probability": 50},
                    {"item": "Rowap Berry", "probability": 50},
                ]},
                "Rare Berries": {"probability": 200, "items": [
                    {"item": "Lum Berry", "probability": 50},
                    {"item": "Apicot Berry", "probability": 50},
                    {"item": "Ganlon Berry", "probability": 50},
                    {"item": "Lansat Berry", "probability": 50},
                    {"item": "Meyt Berry", "probability": 50},
                ]},
                "Very Rare Berries": {"probability": 100, "items": [
                    {"item": "Enigma Berry", "probability": 50},
                    {"item": "Leppa Berry", "probability": 50},
                ]},
                "???": {"probability": 1, "items": [
                    {"item": "???-Berry", "probability": 1},
                ]}
            },

            "TM": [
                {"item": "Play Rough",          "probability": 100},
                {"item": "Moonblast",           "probability": 100},
                {"item": "Metal Claw",          "probability": 100},
                {"item": "Flash Cannon",        "probability": 100},
                {"item": "Metal Sound",         "probability": 100},
                {"item": "Assurance",           "probability": 100},
                {"item": "Dark Pulse",          "probability": 100},
                {"item": "Nasty Plot",          "probability": 100},
                {"item": "Shadow Claw",         "probability": 100},
                {"item": "Shadow Ball",         "probability": 100},
                {"item": "Curse",               "probability": 100},            
                {"item": "Dragon Claw",         "probability": 100},
                {"item": "Dragon Pulse",        "probability": 100},
                {"item": "Dragon Dance",        "probability": 100},
                {"item": "Bug Bite",            "probability": 100},
                {"item": "Signal Beam",         "probability": 100},
                {"item": "Ice Fang",            "probability": 100},
                {"item": "Aurora Beam",         "probability": 100},
                {"item": "Rock Tomb",           "probability": 100},
                {"item": "Power Gem",           "probability": 100},
                {"item": "Stealth Rock",        "probability": 100},
                {"item": "Zen Headbutt",        "probability": 100},
                {"item": "Psychic",             "probability": 100},
                {"item": "Agility",             "probability": 100},
                {"item": "Light Screen",        "probability": 100},
                {"item": "Reflect",             "probability": 100},
                {"item": "Calm Mind",           "probability": 100},
                {"item": "Drill Run",           "probability": 100},
                {"item": "Earth Power",         "probability": 100},
                {"item": "Spikes",              "probability": 100},
                {"item": "Thunder Fang",        "probability": 100},
                {"item": "Thunderbolt",         "probability": 100},
                {"item": "Thunder Wave",        "probability": 100},
                {"item": "Poison Jab",          "probability": 100},
                {"item": "Venoshock",           "probability": 100},
                {"item": "Toxic",               "probability": 100},
                {"item": "Seed Bomb",           "probability": 100},
                {"item": "Energy Ball",         "probability": 100},
                {"item": "Synthesis",           "probability": 100},
                {"item": "Aerial Ace",          "probability": 100},
                {"item": "Air Slash",           "probability": 100},
                {"item": "Tailwind",            "probability": 100},
                {"item": "Liquidation",         "probability": 100},
                {"item": "Scald",               "probability": 100},
                {"item": "Rock Smash",          "probability": 100},
                {"item": "Aura Sphere",         "probability": 100},
                {"item": "Bulk Up",             "probability": 100},
                {"item": "Detect",              "probability": 100},
                {"item": "Fire Fang",           "probability": 100},
                {"item": "Flamethrower",        "probability": 100},
                {"item": "Will-O-Wisp",         "probability": 100},
                {"item": "Body Slam",           "probability": 100},
                {"item": "Crush Claw",          "probability": 100},
                {"item": "Slash",               "probability": 100},
                {"item": "Round",               "probability": 100},
                {"item": "Double Team",         "probability": 100},
                {"item": "Focus Energy",        "probability": 100},
                {"item": "Helping Hand",        "probability": 100},
                {"item": "Metronome",           "probability": 100},
                {"item": "Protect",             "probability": 100},
                {"item": "Swords Dance",        "probability": 100},
                {"item": "Hidden Power",        "probability": 100},
                {"item": "Song of Storms",      "probability": 100},
                {"item": "Infinity Fracture",   "probability": 100},
                {"item": "Witching Hour",       "probability": 100},
                {"item": "Aura Burst",          "probability": 100},
                {"item": "Springtide",          "probability": 100},
                {"item": "Ground Zero",         "probability": 100},
                {"item": "Tempest",             "probability": 100},
                {"item": "Eclipse",             "probability": 100},
                {"item": "Pheromones",          "probability": 100},
                {"item": "Pole Shift",          "probability": 100},
                {"item": "Cloudy Day",          "probability": 100},
                {"item": "Starry Sky",          "probability": 100},
                {"item": "Incantation",         "probability": 100},
                {"item": "Weather Ball",        "probability": 100},
            ],

            "Seed": [
                {"item": "Blast Seed",      "probability": 100},
                {"item": "Encourage Seed",  "probability": 66},
                {"item": "Heal Seed",       "probability": 50},
                {"item": "Reviver Seed",    "probability": 33},
                {"item": "Sleep Seed",      "probability": 100},
                {"item": "Stun Seed",       "probability": 100},
            ],

            "Money": [ # This is assuming that Boxes will cost 100 to open
                {"item": "200",    "probability": 100},
                {"item": "300",    "probability": 75},
                {"item": "500",    "probability": 50},
                {"item": "1000",   "probability": 20},
                {"item": "1500",   "probability": 10},
                {"item": "2000",   "probability": 5},
                {"item": "5000",   "probability": 1},
            ],

            "Orb": {
                "Common": {"probability": 35, "items": [
                    {"item": "Hail Orb", "probability": 25},
                    {"item": "Rainy Orb", "probability":  25},
                    {"item": "Sandy Orb", "probability":  25},
                    {"item": "Sunny Orb", "probability":  25},
                    {"item": "Slow Orb", "probability":  25},
                ]},
                "Uncommon": {"probability": 35, "items": [
                    {"item": "Health Orb", "probability":  25},
                    {"item": "Memory Orb", "probability":  25},
                    {"item": "Petrify Orb", "probability":  25},
                    {"item": "Slumber Orb", "probability":  25},
                    {"item": "Trapbust Orb", "probability":  25},
                    {"item": "Trapper Orb", "probability":  25},
                    {"item": "Weather Orb", "probability":  25},
                    {"item": "Observer Orb", "probability":  25},
                ]},
                "Rare": {"probability": 25, "items": [
                    {"item": "All-Charge Orb", "probability":  50},
                    {"item": "All-Power Orb", "probability":  50},
                    {"item": "Snatch Orb", "probability":  50},
                    {"item": "Align Orb", "probability":  50},
                    {"item": "All-Hit Orb", "probability":  50},
                    {"item": "All-Mach Orb", "probability":  50},
                    {"item": "Lob Orb", "probability":  50},
                    {"item": "Totter Orb", "probability":  50},
                    {"item": "Weather Lock Orb", "probability":  50},
                    {"item": "All-Dodge Orb", "probability":  50},
                    {"item": "Evasion Orb", "probability":  50},
                    {"item": "Nullify Orb", "probability":  50},
                ]},
                "Very Rare": {"probability": 5, "items": [
                    {"item": "Storage Orb", "probability": 25},
                    {"item": "Reviver Orb", "probability": 25},
                ]},
            },

            "Common Held Item": [
                {"item": "Air Balloon",     "probability": 100},
                {"item": "Destiny Knot",    "probability": 100},
                {"item": "Electric Seed",   "probability": 100},
                {"item": "Grassy Seed",     "probability": 100},
                {"item": "Misty Seed",      "probability": 100},
                {"item": "Psychic Seed",    "probability": 100},
                {"item": "Focus Band",      "probability": 100},
                {"item": "Grip Claw",       "probability": 100},
                {"item": "Iron Ball",       "probability": 100},
                {"item": "Iron Braces",     "probability": 100},
                {"item": "Punching Glove",  "probability": 100},
                {"item": "Quick Claw",      "probability": 100},
                {"item": "Ring Target",     "probability": 100},
                {"item": "Room Service",    "probability": 100},
                {"item": "Throat Spray",    "probability": 100},
                {"item": "Blunder Policy",  "probability": 100},
                {"item": "Blue Scarf",      "probability": 100},
                {"item": "Green Scarf",     "probability": 100},
                {"item": "Pink Scarf",      "probability": 100},
                {"item": "Red Scarf",       "probability": 100},
                {"item": "Yellow Scarf",    "probability": 100},
                {"item": "Shed Shell",      "probability": 100},
                {"item": "Black Belt",      "probability": 100},
                {"item": "Black Glasses",   "probability": 100},
                {"item": "Charcoal",        "probability": 100},
                {"item": "Dragon Fang",     "probability": 100},
                {"item": "Fairy Feather",   "probability": 100},
                {"item": "Hard Stone",      "probability": 100},
                {"item": "Magnet",          "probability": 100},
                {"item": "Metal Coat",      "probability": 100},
                {"item": "Miracle Seed",    "probability": 100},
                {"item": "Mystic Water",    "probability": 100},
                {"item": "Never-Melt Ice",  "probability": 100},
                {"item": "Poison Barb",     "probability": 100},
                {"item": "Sharp Beak",      "probability": 100},
                {"item": "Silk Scarf",      "probability": 100},
                {"item": "Silver Powder",   "probability": 100},
                {"item": "Soft Sand",       "probability": 100},
                {"item": "Spell Tag",       "probability": 100},
                {"item": "Twisted Spoon",   "probability": 100},
            ],

            "Rare": {
                "TM": {"probability": 25, "items": [
                    {"item": "3000 TM", "probability": 45},
                    {"item": "4000 TM", "probability": 25},
                    {"item": "5000 TM", "probability": 15},
                    {"item": "6000 TM", "probability": 10},
                    {"item": "Any TM",  "probability": 5},
                ]},
                "Rare": {"probability": 67, "items": [
                    {"item": "Fire Plate", "probability": 100},
                    {"item": "Normal Plate", "probability": 100},
                    {"item": "Grass Plate", "probability": 100},
                    {"item": "Ice Plate", "probability": 100},
                    {"item": "Fairy Plate", "probability": 100},
                    {"item": "Dragon Plate", "probability": 100},
                    {"item": "Ground Plate", "probability": 100},
                    {"item": "Rock Plate", "probability": 100},
                    {"item": "Water Plate", "probability": 100},
                    {"item": "Fighting Plate", "probability": 100},
                    {"item": "Steel Plate", "probability": 100},
                    {"item": "Poison Plate", "probability": 100},
                    {"item": "Psychic Plate", "probability": 100},
                    {"item": "Flying Plate", "probability": 100},
                    {"item": "Dark Plate", "probability": 100},
                    {"item": "Ghost Plate", "probability": 100},
                    {"item": "Electric Plate", "probability": 100},
                    {"item": "Bug Plate", "probability": 100},
                    {"item": "Expert Belt", "probability": 100},
                    {"item": "King's Rock", "probability": 100},
                    {"item": "Razor Fang", "probability": 100},
                    {"item": "Leftovers", "probability": 100},
                    {"item": "Black Sludge", "probability": 100},
                    {"item": "Life Orb", "probability": 100},
                    {"item": "Razor Claw", "probability": 100},
                    {"item": "Shadow Crystal", "probability": 100},
                    {"item": "Utility Umbrella", "probability": 100},
                    {"item": "Zoom Lens", "probability": 100},
                    {"item": "Binding Band", "probability": 100},
                    {"item": "Metronome", "probability": 100},
                    {"item": "Safety Goggles", "probability": 100},
                    {"item": "Big Root", "probability": 100},
                    {"item": "Eviolite", "probability": 100},
                    {"item": "Assault Vest", "probability": 100},
                    {"item": "White Tea", "probability": 100},
                    {"item": "Mirror Tea", "probability": 100},
                ]},
                "Very Rare": {"probability": 8, "items": [
                    {"item": "Ability Patch", "probability": 25},
                    {"item": "Clear Amulet", "probability": 25},
                    {"item": "Covert Cloak", "probability": 25},
                    {"item": "Scope Lens", "probability": 25},
                    {"item": "Shell Bell", "probability": 25},
                    {"item": "Loaded Dice", "probability": 25},
                ]},
            },

#             "Shop Voucher": [
#                 {"item": "20% in Alexa's Library",                              "probability": 100},
#                 {"item": "20% in Vapid's Mystical Studyroom",                   "probability": 100},
#                 {"item": "1 free Local Map in Dusks Cartography",               "probability": 100},
#                 {"item": "1x not having to pay the bidding fee to Dragapult",   "probability": 100},
#                 {"item": "10% off your next entire basket in Kecleon Shops",    "probability": 100},
#                 {"item": "20% in the Armory",                                   "probability": 100},
#                 {"item": "25% off your next potion in Aura Alchemy",            "probability": 100},
#                 {"item": "20% off in the Music Shop",                           "probability": 100},
#                 {"item": "10% in the Kitten Carpenter's Workshop",              "probability": 100},
#             ],

            "Move Card": [
                {"item": "Raging Storm",   "probability": 8},
                {"item": "Focused Winds",   "probability": 8},
                {"item": "Fairy Blessing",   "probability": 8},
                {"item": "Piercing Force",   "probability": 8},
                {"item": "Meteor Shower",   "probability": 5},
                {"item": "Laser Cutter",   "probability": 5},
                {"item": "Reckless Malice",   "probability": 5},
                {"item": "Flash Freeze",   "probability": 5},
                {"item": "Aura Assault",   "probability": 5},
                {"item": "Mystery Sting",   "probability": 14},
                {"item": "Adaptive Blade",   "probability": 11},
                {"item": "Adaptive Blast",   "probability": 11},
                {"item": "Unleash Aura",   "probability": 11},
                {"item": "Weather Syphon",   "probability": 9},
                {"item": "Luck Blessing",   "probability": 9},
            ],

#            "RP Item": [
#                {"item": "",   "probability": 100},
#                {"item": "",   "probability": 100},
#                {"item": "",   "probability": 100},
#                {"item": "",   "probability": 100},
#                {"item": "",   "probability": 100},
#                {"item": "",   "probability": 100},
#                {"item": "",   "probability": 100},
#                {"item": "",   "probability": 100},
#                {"item": "",   "probability": 100},
#                {"item": "",   "probability": 100},
#            ],
#            
#            "Thing": [
#                {"item": "",   "probability": 100},
#                {"item": "",   "probability": 100},
#                {"item": "",   "probability": 100},
#                {"item": "",   "probability": 100},
#                {"item": "",   "probability": 100},
#                {"item": "",   "probability": 100},
#                {"item": "",   "probability": 100},
#                {"item": "",   "probability": 100},
#                {"item": "",   "probability": 100},
#                {"item": "",   "probability": 100},
#            ],
        }
        
        # Pre-compute cached box names and lowercase versions for fast autocomplete
        self.box_names_cache = sorted(list(self.lock_boxes.keys()))
        self.box_names_cache_lower = [name.lower() for name in self.box_names_cache]
    
    def roll_category(self, box_type):
        """Rolls a category based on its probability."""
        if isinstance(self.lock_boxes[box_type], dict):
            categories = self.lock_boxes[box_type]
            total_prob = sum(cat["probability"] for cat in categories.values())
            roll = random.uniform(0, total_prob)
            
            cumulative_prob = 0
            for category, data in categories.items():
                cumulative_prob += data["probability"]
                if roll <= cumulative_prob:
                    return category, data["items"]
        return None, self.lock_boxes[box_type]
    
    def roll_item(self, items):
        """Rolls an item within a selected category or from a flat list."""
        total_prob = sum(item["probability"] for item in items)
        roll = random.uniform(0, total_prob)
        
        cumulative_prob = 0
        for item in items:
            cumulative_prob += item["probability"]
            if roll <= cumulative_prob:
                return item["item"]
    
    async def lockbox_autocomplete(self, interaction: discord.Interaction, current: str):
        """Fast autocomplete using cached lockbox names"""
        if not current:
            return [app_commands.Choice(name=name, value=name) for name in self.box_names_cache[:25]]
        
        current_lower = current.lower()
        matches = []
        
        for name, name_lower in zip(self.box_names_cache, self.box_names_cache_lower):
            if current_lower in name_lower:
                matches.append(app_commands.Choice(name=name, value=name))
                if len(matches) >= 25:
                    break
        
        return matches
    
    @app_commands.command(name="open_box")
    @app_commands.autocomplete(box_type=lockbox_autocomplete)
    async def lockbox(self, interaction: discord.Interaction, box_type: str):
        """Roll a lockbox of a specified type, optionally rolling a category first."""
        try:
            if box_type not in self.lock_boxes:
                raise ValueError(f"Invalid lockbox type: {box_type}.")
            
            category, items = self.roll_category(box_type)
            item_won = self.roll_item(items)
            
            if category:
                await interaction.response.send_message(
                    f"You opened a {box_type} box and received: **{item_won}**!"
                )
            else:
                await interaction.response.send_message(
                    f"You opened a {box_type} box and received: **{item_won}**!"
                )
        except ValueError as e:
            await interaction.response.send_message(f"❌ {interaction.user.mention}, {str(e)}", ephemeral=True)

# Setup function to add the cog
async def setup(bot):
    await bot.add_cog(LootBox(bot))
