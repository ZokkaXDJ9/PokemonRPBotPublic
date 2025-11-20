# Define emojis for types
type_emojis = {
    "Normal":   "<:typenormal:1272535965893791824>",
    "Fighting": "<:typefighting:1272535949569429586>",
    "Flying":   "<:typeflying:1272536305380753440>",
    "Poison":   "<:typepoison:1272536309147238440>",
    "Ground":   "<:typeground:1272535961682579496>",
    "Rock":     "<:typerock:1272535973481283596>",
    "Bug":      "<:typebug:1272535941420027924>",
    "Ghost":    "<:typeghost:1272535956733300879>",
    "Steel":    "<:typesteel:1272536310984212491>",
    "Fire":     "<:typefire:1272535951129968780>",
    "Water":    "<:typewater:1272535976794652673>",
    "Grass":    "<:typegrass:1272535959677960222>",
    "Electric": "<:typeelectric:1272535946788606123>",
    "Psychic":  "<:typepsychic:1272535970897592330>",
    "Ice":      "<:typeice:1272536307276709898>",
    "Dragon":   "<:typedragon:1272535944804962335>",
    "Dark":     "<:typedark:1272535943060000800>",
    "Fairy":    "<:typefairy:1272535948357537894>",
    "Shadow":   "<:typeshadow:1304155747969536152>",
    "Virus":    "<:typevirus:1305196521058205766>"
}

# Define emojis for categories
category_emojis = {
    "Special":  "<:movespecial:1272535937104220180>",
    "Physical": "<:movephysical:1272535935279435968>",
    "Support":  "<:movestatus:1272535939465478235>",
}

# Define emojis for badges
badge_emojis = {
    "bronze": "<:badgebronze:1272532685197152349>",
    "silver": "<:badgesilver:1272533590697185391>",
    "gold": "<:badgegold:1272532681992962068>",
    "platinum": "<:badgeplatinum:1272533593750507570>",
    "diamond": "<:badgediamond:1272532683431481445>",
    "master": "<:badgemaster:1299338926431014913>",
}

def get_type_emoji(type_name):
    """Get the emoji for a specific type."""
    return type_emojis.get(type_name, "")

def get_category_emoji(category_name):
    """Get the emoji for a specific move category."""
    return category_emojis.get(category_name, "")

def get_badge_emoji(rank_name):
    """Get the emoji for a specific rank badge."""
    return badge_emojis.get(rank_name.lower(), "")
