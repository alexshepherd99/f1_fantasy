# live_picks_v1 — Log

## 2026-11-09 — Effort opened

Picked *Live mid-season picks with `StrategyFastF1`* off `BACKLOG.md`, removed it
from that list, and quoted it unchanged in `requirements.md`. Alex widened the scope
the same day: move `run_single_team.py`'s shared code somewhere common and review
its tests, and build one pre-race script that collects the week's data, runs P2PM and
FastF1, and records the chosen pick in a committed team file with free moves, team
value and unused budget.

Settled through a grilling session of 21 questions, recorded as D1–D33 in
`requirements.md`. The reasoning that mattered:

- **The app is the truth, not the script** (Q1). Team, unused budget and free moves
  are confirmed every run, as a wrong budget would give a pick the app rejects.
- **Only the played pick is committed** (Q3). A strategy's pick is made from Alex's
  team, chosen by whichever strategy he played, so a season of them does not show
  how that strategy would do alone. That needs shadow teams, moved to the backlog.
- **The file replaces `TEAM_2026.md` without backfill** (Q4): the table lacks
  unused budget, DRS and free moves, so a backfill would invent them.
- **P2PM's race-4 Wildcard spends Alex's real chip** (Q8), free in a back-test but
  not live. `StrategyMaxP2PMNoReset` already gives the no-chip pick, so nothing in
  `linear/` changes for it.
- **Nothing the script runs after race 1 reads odds** (Q13), so missing odds is a
  warning for the record from race 2, an error only at race 1.
- **Limitless needs a finite cap** (Q15). A cap at or above `COST_PROHIBITIVE`
  would make a driver who has left the race affordable, so the cap is the sum of
  every available asset's price.

Race-1 odds check, run 2026-11-09 with `scripts/select_odds_start.py` on today's
data: limit 4 gave the same team as no limit, limits 3, 2, 1 and 0 each a different
one. One season cannot show 4 never matters, so all six limits are kept and
identical teams merged (D29). The limit-1 team today is not the one Alex played at
race 1 (`TEAM_2026.md`), most likely because the stored race-1 odds were replaced
after he picked. Not investigated: live use reads whatever odds are stored at the
time.

Core-module grants for this effort, from Alex 2026-11-09: the move of
`run_single_team.py`'s shared functions (D1, D2), and `max_cost` on
`factory_strategy` (D6), chosen over a team-copy workaround.

Added to `BACKLOG.md`: shadow teams per strategy, and BoxBox capture of a new
season, which race-1 mode needs for real use (D30).

No code written.
