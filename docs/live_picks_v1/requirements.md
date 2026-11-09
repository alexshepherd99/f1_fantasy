# live_picks_v1 — Requirements

**Status**: agreed with Alex 2026-11-09, through a grilling session (see
`log.md`, *Effort opened*). Implementation plan in `plan.md`.

## The problem

Alex picks the live team each race by hand-editing `scripts/run_single_team.py`'s
settings, running the data captures one by one (`boxbox.cli`, `odds_source.cli`,
`fast_f1.cli`), and logging the result in `TEAM_2026.md`. Only P2PM can be run that
way: `StrategyFastF1RuleRise` beat P2PM in the back-test but nothing runs it live.

This effort builds one script, run before each race, that collects whatever data is
available at that point in the week, runs each strategy that data supports, and
records the pick Alex chooses in a committed team file. It also moves the shared
simulation code out of `run_single_team.py`.

## Original backlog entry (unchanged)

> ## Live mid-season picks with `StrategyFastF1`
>
> **Only if** `fastf1_v2`'s back-test finds `StrategyFastF1` more effective than
> `StrategyMaxP2PM`, and Alex wants to use it for mid-season picks. Otherwise drop
> this item. [2026-11-08: the first condition is met. `FastF1_RuleRise2p5` beat P2PM
> in 2025 and 2026 through race 18 (`BACKTEST_LOG.md`). The live 2026 team stays on
> P2PM, so this is for 2027 at the earliest. The chosen setting is now the class
> `StrategyFastF1RuleRise` in `linear/strategy_fastf1.py` (`fastf1_v2` step 27), so a
> script can pass it to `factory_strategy`. No script does yet.]
>
> The strategy reads only the stored metrics file,
> `data/fastf1_practice_rolling_metrics.csv`, and never calls FastF1. So a live pick
> is two stages: build the race's metrics rows (after FP3 on a normal weekend), then
> run the strategy. Today that route has three gaps, reasoned from the code on
> 2026-11-06 and not run:
>
> - **Single-race mode writes elsewhere.** `fast_f1.cli --season S --race N` saves to
>   `outputs/fastf1_race_S_N.csv`, which the strategy does not read. Pointing the
>   strategy at that file fails, as the expected-points tables need the 2023–25 rows.
> - **Historical mode freezes the row.** `--historical --season S` does add the race to
>   the strategy's file, but it skips stored races, so the row built before the race
>   had results is never rebuilt. Step 3b.3 of `fastf1_v2` had to check for such rows.
>   It also exits 1 for the rounds not yet run. Since the file became CSV, such a row
>   also reformats every stored line: its missing `Points` turn the column to floats,
>   so `15` is rewritten `15.0` (simulated on a copy 2026-11-08, values unchanged). A
>   run after the race only adds lines, so `git diff --numstat` on the file showing
>   any deletions marks a reformat or a cut-off write.
> - **A missing race fails quietly.** With no metrics rows for the race, the strategy
>   scores every asset zero and still returns a team. That is right for the back-test
>   (2026 race 19, plan step 6.5) and wrong for a live pick, which should raise.
>
> The work: a way to put the current race's rows into the strategy's file and rebuild
> them once results exist, a live-pick entry point that raises when the race has no
> signal, and one command or documented sequence running both stages.
> `load_signal_tables` caches per process, so a single process doing both stages
> would have to build the rows before its first strategy call.
>
> Raised by Alex 2026-11-06, during `fastf1_v2` step 6.

## Scope as widened by Alex (2026-11-09)

- Move `run_single_team.py`'s shared functions somewhere common, propose their
  structure, and review their tests.
- One pre-race script that collects data and runs the target strategies (P2PM and
  FastF1), taking whatever steps the data available that week allows.
- A team file in `data/` tracking the season's team, free moves, team value and
  unused budget; Alex chooses each race's pick and commits the file.
- Wildcard and Limitless chips offered; points predicted with an override.
- `run_single_team.py` keeps running throughout as the backup.
- The season starts with a team picked from betting odds.

## Decisions

Numbered in the order they were settled. Q-numbers in `log.md` refer to the grilling.

### Shared code

- **D1. `simulate/` package.** `simulate/pick.py` solves one race (strategy, team,
  race, previous race, season, max moves, optional cost cap) and returns the pick:
  drivers, constructors, DRS driver, moves used, cost, unused budget; it raises when
  the solver does not return optimal. It also holds the free-move rule and the
  Limitless cap. `simulate/season.py` holds `run_for_team` rebuilt on `pick.py`, plus
  `get_row_intermediate_results` and `get_strat_display_name`. `run_single_team.py`,
  `backtest/` and the tests import from `simulate/`. (Q21)
- **D2. `run_for_team` gains `bonus_free_transfer: bool = False`**, so a run can
  start mid-season with a carried move. Default keeps today's behaviour.
- **D3. Back-test results must not change.** A pinning test records today's
  per-race `run_for_team` output for P2PM and FastF1 on a fixed team before anything
  moves, and every step of the move keeps it identical.
- **D4. Test gaps to fill**, each on small hand-built races: the free-move carry-over;
  unused budget and DRS driver carried between races; a start after race 1; the error
  when the solver fails; the result row's columns; the name helper. The 2025
  real-archive run stays as the one integration test. (Q21)
- **D5. `run_single_team.py` stays as it is after the handover**: hand-edited
  settings, only its importable functions moved. (Q16)
- **D6. `factory_strategy` gains `max_cost: float | None = None`.** `None` keeps
  today's cap, `team.total_budget(race, race_prev)`. Chosen by Alex over a
  team-copy workaround that would have left `linear/` untouched (Q14). The change
  is verified as earlier `linear/` changes were: re-simulate the stored P2PM
  back-test rows and require exact equality, plus a before/after 2026 replay. (Q15)
- **D7. The Limitless cap is the sum of every available asset's price** for the
  race, computed in `simulate/`. It must stay finite and well below
  `COST_PROHIBITIVE`, which `StrategyBase` uses to force out a team driver no longer
  in the race; a cap at or above it would let the script keep that driver. A test
  covers that case. (Q15)

### The team file

- **D8. The file records only the pick Alex played.** Each run also saves every
  strategy's pick, with prices, under `outputs/` (not committed). Shadow teams per
  strategy went to the backlog. (Q3)
- **D9. Layout: `data/live_team.csv`, one row per race played**, written with the
  `csv` module so rows a run does not touch keep their bytes. Columns: `Season`,
  `Race`, `Strategy`, `Chip`, `D1`–`D5`, `C1`–`C2` (sorted), `DRS`, `FreeMoves`
  (available this race), `MovesUsed`, `TeamValue` (at this race's prices),
  `UnusedBudget` (after the pick), `PointsPredicted`, `Points` (the app's figure,
  which counts). `Strategy` holds the class name, `StrategyBettingOdds:<limit>` at
  race 1, or `Manual`. (Q18)
- **D10. A race's row is written when Alex chooses a pick** and replaced on a rerun
  before the race. Once `Points` is filled the row is final.
- **D11. The file takes over from `TEAM_2026.md`** at a race Alex chooses.
  `TEAM_2026.md` keeps the races before it and gains a pointer; it is not updated
  by hand after that. From 2027 there is no markdown team table; the script may
  print the season as one on request. No backfill of earlier races: the table lacks
  unused budget, DRS and free moves. (Q4)

### Confirmations, every run

- **D12. Every run asks Alex to confirm** the held team, the unused budget and the
  free moves, showing the script's figures as defaults. Not only the first run of a
  race week. (Q1, Q2)
- **D13. Prices are shown beside every asset at selection**, so they can be checked
  against the app. Team value is shown, not separately confirmed: it follows from
  the confirmed team and the shown prices. (Q1)
- **D14. The DRS driver recorded is the one Alex set**, defaulting to the strategy's
  choice. (Q1)

### Picks and chips

- **D15. Next race** is the first race of the season in the archive with prices and
  no points.
- **D16. Strategies after race 1:** `StrategyMaxP2PM` whenever the next race has
  prices; `StrategyFastF1RuleRise` only when its signal for the race exists, and
  otherwise skipped with the reason. The betting-odds strategy is not offered after
  race 1. (Q10)
- **D17. FastF1 waits for its sessions:** FP2 and FP3 on a normal weekend, FP1 and
  Sprint Qualifying on a sprint weekend (the fantasy lock is after Sprint
  Qualifying). No FP1-only fallback. (Q9)
- **D18. A strategy refuses a race with no signal**, in the live path, rather than
  scoring every asset zero. The check lives outside `linear/`.
- **D19. Chips are a fixed list:** Wildcard, Limitless, Extra DRS (3x), No Negative,
  Autopilot, Final Fix. One chip per race, each once per season; the script stops
  offering a chip once the file shows it used. ("Free transfer" in `TEAM_2026.md`
  was shorthand for a carried move, not a chip.) (Q7, Q18)
- **D20. `--chip wildcard` / `--chip limitless`** run every strategy with moves
  unlimited, and for Limitless the cap of D7.
- **D21. Chip bookkeeping:** Wildcard keeps the new team. After Limitless, the next
  race starts from the last row without Limitless; its unused budget is the
  default Alex confirms or corrects. Free moves carry over a chip race: race N+1
  gets what race N had. Otherwise fewer than 2 moves used gives 3 next race, else 2.
  (Q7)
- **D22. Race 4:** while the Wildcard is unused, show both `StrategyMaxP2PM` (it
  plays the Wildcard itself) and `StrategyMaxP2PMNoReset`; recording the first
  marks the Wildcard used. Once used, only NoReset is shown. Identical teams merge
  into one row. (Q8)
- **D23. Choosing is a prompt at the end of the run**, listing the picks side by
  side with prices, plus a manual option and "record nothing". Manual entry takes
  driver identifiers and constructor codes, checks them against the race, shows
  prices, and works out cost and moves. (Q10)

### Points

- **D24. The last race is scored** once the archive holds its points, and Alex
  accepts the prediction or types the app's figure. The prediction models Extra DRS
  (DRS driver x3), Autopilot (DRS to the highest-scoring driver) and Final Fix
  (through the team entered). No Negative works per scoring category, which the
  archive does not hold, so its race is predicted without the chip and the script
  says the app's figure must be entered. (Q19)

### Data collection and failures

- **D25. Each run collects in order:** BoxBox capture, every saved odds page for the
  next race (oldest first; pages for other races skipped with a note), then FastF1
  sessions and metrics. All writes finish before the first strategy runs, as
  `load_with_derivations` and `load_signal_tables` cache per process.
- **D26. Each step ends done, not yet, refused or failed.** The run carries on
  regardless, runs what it can, and ends with a summary; a refused or failed step
  makes the exit code 1 even when a pick was recorded. (Q11)
- **D27. Missing odds:** at race 1 an error and no picks; from race 2 a loud warning
  at the top and in the summary, saying the pick does not need odds but the record
  has a gap. It does not change the exit code. (Q13)
- **D28. Metrics rows for a race are written into
  `data/fastf1_practice_rolling_metrics.csv`** by a writer that replaces only that
  race's lines and keeps every other line's bytes. Once a race has results its rows
  are rebuilt whole, as `--historical` would build them, and the run reports any
  signal input that changed. The values a pick saw are kept in its `outputs/`
  record. (Q12)

### Race 1

- **D29. Race-1 mode** runs when the file has no row for the season. Odds are
  required. Only `StrategyBettingOdds` runs, at concentration limits 999.9, 4, 3, 2,
  1 and 0, shown side by side with identical teams merged; budget 100, moves
  unlimited. (Q5, Q6)
- **D30. Race-1 mode needs the new season in the archive.** BoxBox capture does not
  handle a new season; that is a separate backlog item, a prerequisite for real use,
  not part of this effort. (Q5)

### Verification

- **D31. Gate 1, the first real race:** for the same team, budget and free moves,
  the script's P2PM pick equals `run_single_team.py`'s next-race pick, and the
  prediction equals the app's points or differs by a nameable effect. Any other
  difference blocks the verified label and is investigated before the next pick, not
  overridden. (Q20)
- **D32. Gate 3, the first FastF1 race:** the same pick check against a
  back-test-style `StrategyFastF1RuleRise` run on the same inputs. (Q20)
- **D33. A 2026 handover is welcome, not a goal.** If it slips past race 23 the
  file starts at 2027 race 1. (Q17)

## Out of scope

- Shadow teams per strategy (backlog).
- BoxBox capture of a new season (backlog; D30).
- Changing `StrategyMaxP2PM` or switching the live 2026 team off it.
- Modelling chips inside the strategies (*Model the game's other chips*, backlog).
