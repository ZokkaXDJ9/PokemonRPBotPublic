def get_rank(level):
    """Get the rank name based on the level."""
    if level >= 20:
        return 'Master'
    elif level >= 16:
        return 'Diamond'
    elif level >= 8:
        return 'Platinum'
    elif level >= 4:
        return 'Gold'
    elif level >= 2:
        return 'Silver'
    elif level == 1:
        return 'Bronze'
    else:
        return 'Unknown'
