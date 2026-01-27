def odds_to_pct(odds: str) -> float:
    odds = odds.replace(":", "/")
    odds = odds.replace("-", "/")
    
    if odds.count("/") != 1:
        raise ValueError(f"odds_to_pct invalid input {odds}")

    odds_values = odds.split("/")
    if len(odds_values) != 2:
        raise ValueError(f"odds_to_pct invalid input {odds}")
    
    odds_left = int(odds_values[0])
    odds_right = int(odds_values[1])

    if odds_right > odds_left:
        raise ValueError(f"odds_to_pct invalid input {odds}")
    
    if (odds_right == 0) or (odds_left == 0):
        raise ValueError(f"odds_to_pct invalid input {odds}")

    return 1 / (odds_left / odds_right)
