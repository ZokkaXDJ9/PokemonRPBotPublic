import random
import json
import os
from database import Database

CHARACTERS_DIR = "Characters"
CRIT = 6
FAIL_THRESHOLD = 3
DEFAULT_CRIT_DIE_COUNT = 3  # Change this if your game's default is something else

def normalize_keys(obj):
    """Recursively convert all dictionary keys to lowercase."""
    if isinstance(obj, dict):
        return {k.lower(): normalize_keys(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [normalize_keys(i) for i in obj]
    return obj

class ParsedRollQuery:
    def __init__(self, amount: int = 1, sides: int = 6, flat_addition: int = 0, crit_6_count: int = DEFAULT_CRIT_DIE_COUNT):
        self.amount = max(1, min(amount, 100))  # Clamp between 1 and 100
        self.sides = max(2, min(sides, 100))    # Clamp between 2 and 100
        self.flat_addition = flat_addition
        self.crit_6_count = crit_6_count

    @classmethod
    def from_query(cls, query: str, crit_6_count: int = DEFAULT_CRIT_DIE_COUNT):
        """Parse a query like '1d6+5'."""
        flat_addition = 0
        if '+' in query:
            query, add_value = query.split('+', 1)
            flat_addition = int(add_value)

        if 'd' in query:
            amount_str, sides_str = query.split('d', 1)
            amount = int(amount_str) if amount_str else 1
            sides = int(sides_str) if sides_str else 6
        else:
            amount = int(query)
            sides = 6

        return cls(amount, sides, flat_addition, crit_6_count=crit_6_count)

    def as_button_callback_query_string(self) -> str:
        """Returns a query string that can be reused for the button callback."""
        return f"{self.amount}d{self.sides}+{self.flat_addition}" if self.flat_addition > 0 else f"{self.amount}d{self.sides}"

    def execute(self) -> str:
        # Determine if we should display successes based on pure `d6` rolls
        is_pure_d6 = self.sides == 6 and self.flat_addition == 0
        display_successes = is_pure_d6

        results = []
        total = self.flat_addition
        six_count = 0
        successes = 0

        for _ in range(self.amount):
            value = random.randint(1, self.sides)
            total += value
            results.append(value)
            if display_successes and value > FAIL_THRESHOLD:
                successes += 1
                if value == CRIT:
                    six_count += 1

        # Format results to apply bold for 4, 5, and bold + underscore for 6
        result_list = ", ".join(
            f"**__{x}__**" if x == CRIT else f"**{x}**" if x > FAIL_THRESHOLD else str(x)
            for x in results
        )

        # Display basic roll result
        text = f"{self.amount}d{self.sides}"
        if self.flat_addition > 0:
            text += f"+{self.flat_addition} — {result_list} + {self.flat_addition} = {total}"
        else:
            text += f" — {result_list}"

        # Append success and critical information only if display_successes is True
        if display_successes:
            success_string = "Success!" if successes == 1 else "Successes!"
            crit_string = " **(CRIT!)**" if (self.crit_6_count > 0 and six_count >= self.crit_6_count) else ""
            text += f"\n**{successes}** {success_string}{crit_string}"

        return text

# Load a specific legendary move from a JSON file
def load_legend_move(move_name):
    """Load a move from a JSON file based on the move name."""
    file_path = os.path.join(os.path.dirname(__file__), "Data", "legend_moves", f"{move_name}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None  # Return None if the file does not exist

# Load a specific move from a JSON file
def load_move(move_name):
    """Load a move from a JSON file based on the move name."""
    file_path = os.path.join(os.path.dirname(__file__), "Data", "moves", f"{move_name}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None  # Return None if the file does not exist

# Retrieve a move by name (if loading multiple moves at once)
def get_move(move_name):
    moves = load_move()  # This function might need to load multiple moves at once, not just one.
    for move in moves:
        if move["Name"].lower() == move_name.lower():  # Case-insensitive search
            return move
    return None

def load_ability(ability_name):
    """Load an ability from a JSON file based on the ability name."""
    file_path = os.path.join(os.path.dirname(__file__), "Data", "abilities", f"{ability_name}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return normalize_keys(json.load(f))  # Normalize the keys!
    except FileNotFoundError:
        return None

def load_rule(rule_name):
    """Load a rule from a JSON file based on the rule name."""
    file_path = os.path.join(os.path.dirname(__file__), "Data", "rules", f"{rule_name}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None  # Return None if the file does not exist

def load_status(status_name):
    """Load a status from a JSON file based on the status name."""
    file_path = os.path.join(os.path.dirname(__file__), "Data", "status", f"{status_name}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None  # Return None if the file does not exist

def load_weather(weather_name):
    """Load a weather effect from a JSON file based on the weather name."""
    file_path = os.path.join(os.path.dirname(__file__), "Data", "weather", f"{weather_name}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:  # Ensure UTF-8 encoding for special characters
            return json.load(f)
    except FileNotFoundError:
        return None  # Return None if the file does not exist

def load_item(item_name):
    """Load an item from a JSON file based on the item name."""
    file_path = os.path.join(os.path.dirname(__file__), "Data", "items", f"{item_name}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None  # Return None if the file does not exist

def load_potion(potion_name):
    """Load a potion from a JSON file based on the potion name."""
    file_path = os.path.join(os.path.dirname(__file__), "Data", "potions", f"{potion_name}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None  # Return None if the file does not exist

def load_z_move(zmove_name):
    """Load a Z‑Move from a JSON file based on the z‑move name."""
    file_path = os.path.join(os.path.dirname(__file__), "Data", "z_moves", f"{zmove_name}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None  # Return None if the file does not exist
