from linear.strategy_p2pm import StrategyMaxP2PM


class StrategyMaxP2PMNoReset(StrategyMaxP2PM):
    """StrategyMaxP2PM without the race-4 unlimited-moves chip.

    The chip is played in `StrategyMaxP2PM.__init__`, not through a parameter, and
    that class picks the live 2026 team so is not edited. This restores the moves
    it was given once the parent has run, so race 4 is an ordinary race and every
    other race is exactly as the parent leaves it.
    """
    def __init__(self, *args, max_moves: int, **kwargs):
        super().__init__(*args, max_moves=max_moves, **kwargs)
        self._max_moves = max_moves
