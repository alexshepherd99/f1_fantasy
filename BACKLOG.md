# Backlog

Efforts under `docs/`:

| Effort | State |
| --- | --- |
| [`aggregate_rank_v1`](docs/aggregate_rank_v1/) | done |
| [`backtest_v1`](docs/backtest_v1/) | done |
| [`data_capture_v1`](docs/data_capture_v1/) | cancelled; replaced by `data_capture_v2` |
| [`fastf1_v1`](docs/fastf1_v1/) | done |
| [`fastf1_v2`](docs/fastf1_v2/) | done |
| [`indicator_analysis_v1`](docs/indicator_analysis_v1/) | done |
| [`max_points_v1`](docs/max_points_v1/) | done |
| [`odds_drs_v1`](docs/odds_drs_v1/) | done |
| [`odds_source_v1`](docs/odds_source_v1/) | done (dev); Gate 2 at the next race weekend |

Global list of not-yet-started work. Freeform. When an item is picked up, create `docs/<effort-name>/` (see `docs/` and `agentic`'s `shared/persistent-docs.md`) and move the item there.

An entry that runs past ~350 words gets its own `docs/<effort-name>/proposal.md`, leaving a short pointer entry in this list. Picking the item up then adds `requirements.md` / `plan.md` / `log.md` beside it as usual. The threshold is a prompt to judge, not a gate — it is where the entries here actually split (2026-07-30: seven at 110-330 words, two at 537 and 766), not a target. Note this puts a `docs/<effort-name>/` directory in place before work starts, which `agentic`'s `shared/persistent-docs.md` does not describe; it is a deliberate local extension, worth proposing upstream if it sticks.

## Lift concentration calculation into `StrategyBase`

`StrategyBettingOdds.get_problem()` (`linear/strategy_odds.py:36-88`) builds
the concentration measure inline: for every constructor it enumerates
driver-driver and driver-constructor pairs, creates a binary auxiliary
variable per pair and adds the three linearisation constraints by hand,
then sums them into `VarType.Concentration` and caps it at
`self.max_concentration`. It's ~50 lines of near-duplicated pair logic
sitting in the middle of an otherwise short objective function.

Simplify it — the two pair loops differ only in which selection variables
they reference, so one helper for "binary AND of two selection variables"
collapses most of it — and move it up to `StrategyBase`, where
`VarType.Concentration` is already declared. Every strategy would then get
concentration for free; leaving `max_concentration` at its permissive
default keeps the other strategies' behaviour unchanged.

2026-09-20: `max_points_v1` called this a likely prerequisite and then
deliberately declined to treat it as one, requiring evidence first (its R7).
*Verification* 1 measured high variance in `StrategyMaxPoints` — it wins most
starting teams in 2025 and still loses on the mean — which *looks* like
concentration risk but does not measure it. **Concentration itself has not been
counted**, so this item is not yet justified by that effort; see
`docs/max_points_v1/log.md`, *Concentration is still an assumption* and *Next —
the per-race re-simulation*. The definition to reuse when measuring is the one
already in `strategy_odds.py`, so the metric does not need inventing.

2026-09-21: **counted, and it does not support this item.** The per-race
re-simulation measured concentration over all 210,000 team-races.
`StrategyMaxPoints` is not the more concentrated strategy — in 2024, the season
it loses worst, it holds a constructor with both its drivers ten times *less*
often than `StrategyMaxP2PM` — and concentration correlates positively with the
per-team season delta in all three seasons, with the worst teams the less
concentrated ones. So there is no measured concentration risk to constrain, and
`max_points_v1` supplies no argument for this lift. See
`docs/max_points_v1/log.md`, *The per-race re-simulation*.

**The item still stands on its own terms** — it was a simplification and reuse
argument before it was ever a risk argument, and `StrategyBettingOdds` keeps its
concentration constraint regardless. What has gone is the claim that another
strategy needs it. The metric now also exists as
`backtest/per_race.py:concentration`, matching the odds strategy's definition, so
a lift has a tested reference to check itself against.

## `get_race_results` downloads sessions it then discards

`get_race_results` warms a session cache as a side effect, loading
FP1/FP2/FP3/SQ in full after the race — since 2026-07-27 in
`_warm_practice_session_cache` (`fast_f1/api.py:253`). When no local cache
directory is configured `_get_local_cache_path()` returns `None`, nothing is
written and those four loads are pure waste — in the validation test that was
~19s of a 27s run. Skip the warming when there is nowhere to write it.

The related concern about the loads themselves is already resolved: `_load_session`
(`fast_f1/api.py:110`) passes `telemetry=False, weather=False` as of 2026-07-25,
which cut a session load from ~4.2s to ~1.5s. `messages=True` is kept
deliberately — it is what populates a lap's `Deleted` flag.

## No test exercises any script's `__main__` block

Tests reach into `scripts/` for individual functions — `run_multiple_teams`,
`run_single_team` (`tests/test_run_batch.py:9-10`), `check_run_ppm`
(`tests/test_derivations.py:11`) and `select_starting_team`
(`tests/test_select_starting_team.py:1`) — but a `__main__` block never runs on
import, so the wiring inside one is exercised by nothing. That is true of all
six scripts, including the four whose functions are covered. Two have no
test importing them at all: `batch_results_xl.py` and `select_odds_start.py`.

The gap is not theoretical. `scripts/get_fastf1_data.py` was deleted on
2026-07-27 (recoverable at `1282518~1`) after drifting twice without a single
red test: its season list stopped at 2025, and it still passed a `race_numbers`
argument that had been removed from `generate_historical_metrics` hours
earlier, so it would have raised `TypeError` on its first real call. Both
defects sat in its `__main__` block and were found by grepping for callers.

Two live instances of the same shape:

- `batch_results_xl.py:7` imports `_FILE_BATCH_RESULTS_PARQET` and
  `_FILE_BATCH_RESULTS_EXCEL` from `scripts.run_multiple_teams` — private
  names, across module boundaries. Renaming either breaks the script and
  nothing fails.
- `select_odds_start.py:73` hardcodes `select_odds_start_for_season(2026)` in
  its `__main__` block, the same stale-constant shape that made
  `get_fastf1_data.py` wrong.

Worth deciding the standard rather than patching case by case: either keep
`__main__` blocks to a single call into a tested function so there is nothing
in them to drift, or add an import smoke test over `scripts/` that would at
least catch a broken signature or a renamed import. The first is cheaper and
matches what `fast_f1/cli.py` already does.

`scripts/scratch.py` was raised alongside this and is already resolved —
deleted 2026-07-27, having been four lines putting a hardcoded
`/workspaces/f1_fantasy` on `sys.path` that nothing imported.

Raised 2026-07-27, immediately after deleting `get_fastf1_data.py`, when the
question "what else is unprotected in the same way" turned out to have a
concrete answer.

## Refine P2PM: better DRS nomination

Not a priority. P2PM must not change before the 2026 season ends, so build this as a
subclass.

A perfect-hindsight DRS pick would have scored +226 (2023), +103 (2024) and +98
(2025) points a season more than P2PM's current rule. That rule nominates the
selected driver with the highest rolling three-race points, and it already picks
the best driver in 60-76% of team-races. For comparison, the whole objective
change `max_points_v1` tested was worth −4 to −156. See `docs/max_points_v1/log.md`,
*The DRS nomination ceiling, measured while the data was to hand*.

`StrategyBase` now has an opt-in DRS helper: `get_drs_objective_term()` models the
boost inside the LP objective, and `get_drs_nominee()` reads it back. It was added
in `max_points_v1` step 5 and nothing calls it yet. [2026-10-05: `odds_drs_v1`
made `StrategyBettingOdds` its first caller, with odds as the values. P2PM still
does not use it. See `docs/odds_drs_v1/log.md`.] What it can and cannot buy:

- **With rolling points as the values, it nominates the same driver as today's
  rule.** For a fixed team, the LP gives DRS to the highest-valued selected driver.
  So it cannot collect any of the ceiling above. Its only effect is on team
  selection, since it rewards teams with one strong driver. Reasoned from the LP's
  structure, not run.
- **With P2PM values, it would nominate worse than today's rule**, because a value
  ratio predicts a points payoff less well than recent points do.
- **The ceiling needs a better signal, not a better mechanism.** Candidates are
  betting odds (already loaded by `StrategyBettingOdds`) or `fast_f1`'s
  `AggregateRank`. Either works as a post-hoc `get_drs_driver()` override, or as
  the helper's values if team selection should respond too. This overlaps with
  *Build a strategy on the FastF1 indicators* and its regression prerequisite
  above. [2026-11-01: that prerequisite is answered, in
  `docs/indicator_analysis_v1/log.md`, and is off this list. The strategy item has moved
  to `docs/fastf1_v2/`. 2026-11-08: `fastf1_v2` is done. Its strategy chooses DRS inside
  the LP from its own signal, not `AggregateRank`, and dropping that DRS term lost
  points in every season of its step 16. It did not test DRS for P2PM.] A DRS signal is a
  narrower first use of `AggregateRank`.
- Perfect hindsight is not achievable, so the realistic gain is some unknown
  fraction of the ceiling.

Raised 2026-09-28, from `max_points_v1`.

## Live mid-season picks with `StrategyFastF1`

**Only if** `fastf1_v2`'s back-test finds `StrategyFastF1` more effective than
`StrategyMaxP2PM`, and Alex wants to use it for mid-season picks. Otherwise drop
this item. [2026-11-08: the first condition is met. `FastF1_RuleRise2p5` beat P2PM
in 2025 and 2026 through race 18 (`BACKTEST_LOG.md`). The live 2026 team stays on
P2PM, so this is for 2027 at the earliest. The chosen setting is now the class
`StrategyFastF1RuleRise` in `linear/strategy_fastf1.py` (`fastf1_v2` step 27), so a
script can pass it to `factory_strategy`. No script does yet.]

The strategy reads only the stored metrics file,
`data/fastf1_practice_rolling_metrics.csv`, and never calls FastF1. So a live pick
is two stages: build the race's metrics rows (after FP3 on a normal weekend), then
run the strategy. Today that route has three gaps, reasoned from the code on
2026-11-06 and not run:

- **Single-race mode writes elsewhere.** `fast_f1.cli --season S --race N` saves to
  `outputs/fastf1_race_S_N.csv`, which the strategy does not read. Pointing the
  strategy at that file fails, as the expected-points tables need the 2023–25 rows.
- **Historical mode freezes the row.** `--historical --season S` does add the race to
  the strategy's file, but it skips stored races, so the row built before the race
  had results is never rebuilt. Step 3b.3 of `fastf1_v2` had to check for such rows.
  It also exits 1 for the rounds not yet run. Since the file became CSV, such a row
  also reformats every stored line: its missing `Points` turn the column to floats,
  so `15` is rewritten `15.0` (simulated on a copy 2026-11-08, values unchanged). A
  run after the race only adds lines, so `git diff --numstat` on the file showing
  any deletions marks a reformat or a cut-off write.
- **A missing race fails quietly.** With no metrics rows for the race, the strategy
  scores every asset zero and still returns a team. That is right for the back-test
  (2026 race 19, plan step 6.5) and wrong for a live pick, which should raise.

The work: a way to put the current race's rows into the strategy's file and rebuild
them once results exist, a live-pick entry point that raises when the race has no
signal, and one command or documented sequence running both stages.
`load_signal_tables` caches per process, so a single process doing both stages
would have to build the rows before its first strategy call.

Raised by Alex 2026-11-06, during `fastf1_v2` step 6.

## Re-assess `StrategyFastF1`'s tuning values when 2026 finishes

**For Alex, once the 2026 season is over.** `fastf1_v2` step 15.1 set the
three values tried for each lever from measures on 2023–25 only:

- negative penalty 6.5, 13 and 26;
- budget reward 0.1, 0.25 and 0.5;
- price-rise reward 5, 10 and 20.

[2026-11-08: the price-rise reward was later rebuilt from the game's rules and
tried at 5, 10 and 20, then 2.5 and 1.25, on 2025 alone. 2.5 was chosen
(`docs/fastf1_v2/log.md`, *Step 23*). Its values were not set from these
measures.]

2026 was left out deliberately, as it is the season the verdict is judged on.
Once it finishes, re-run the measures with 2026 included and decide whether the
values, and the setting steps 16 and 23 chose from them, still hold. The measures are:

- fantasy points per value unit;
- what a negative costs, in value units;
- value per 1m of price;
- races left after each race.

The method and the 2023–25 figures are in `docs/fastf1_v2/log.md`, *Step 15.1*.
2026's results so far went negative more often than earlier seasons': 18.5% of
driver results and 18.2% of constructor results. In 2023–25 the figures were 10%
to 16% (`docs/fastf1_v2/log.md`, *Sizing the two levers in the brief*). So the
penalty's values are the likeliest to move.

This sits beside *Rerun `fastf1_v2`'s 2026 back-test when the season finishes*,
below. Do this one first, as it may change what that rerun tests.

Raised by Alex 2026-11-07, during `fastf1_v2` step 15.1.

## Rerun `fastf1_v2`'s 2026 back-test when the season finishes

**For Alex, once the 2026 season is over, after the re-assessment above.**
`fastf1_v2` step 17 ran 2026 only through race 18, the last race with a signal
in `data/fastf1_practice_rolling_metrics.csv`. `FastF1_RuleRise2p5` was +338.0
points a team ahead of P2PM there, with 205 of that from race 13
(`docs/fastf1_v2/log.md`, *Step 17* and *Step 26*). `requirements.md` question 7
agreed the rerun.

- **Build the missing races first:** `fast_f1.cli --historical --season 2026`,
  then check the metrics file holds every 2026 race with results, as step 3b.3
  checked for rows built before a race had results.
- **Add 2026 to `COMPLETED_SEASONS`** in `backtest/cli.py`.
- **Run once,** seed 1, 500 teams a band, `FastF1_RuleRise2p5` and
  `StrategyMaxP2PMNoReset`, into a new store, not `outputs/fastf1_v2_results.parquet`:
  stored rows are keyed without the last race, so that store would return the
  race-18 rows as if they were final.
- **Read it as partly seen.** Races 1–18 are the ones already reported, so only
  the races after 18 are new evidence, and a strategy that leads by 338 at race
  18 is very likely to stay ahead. Report the lead gained or lost after race 18
  on its own.

Raised as `fastf1_v2` question 7, agreed 2026-11-01, and moved here at its close
on 2026-11-08.

## Model the game's other chips

The only chip any strategy plays is the race-4 unlimited-moves chip: P2PM has it
built in, and `fastf1_v2` step 25 tested it for FastF1 and did not keep it, as it
helped in two seasons and cost points in two. The live game has others,
including Limitless, the 3x boost, No Negative, Autopilot and the free transfer.
Alex played several in 2026 (`README.md`, *2026 team*). None is modelled, so
the back-tests cannot say when to play them or what they are worth. Unlike the
race-4 chip, most need a view across the season of when to play them, which no
strategy here takes (`README.md`, caveats).

Agreed with Alex 2026-11-08, during `fastf1_v2` step 25.

## Check a heavier FP3 weight on 2027

**For Alex, once 2027's normal weekends are in.** The signal weights its inputs
equally, and that stays the default. Fitting weights was already tried and did
not help: +0.006 on normal weekends and −0.040 on sprints, scored on seasons the
fit had not seen (`docs/indicator_analysis_v1/log.md`, *Findings*).

The reason to look again is that practice predicted fantasy points much better in
2026. On normal weekends, Spearman for FP2 was 0.41–0.45 a season in 2023–25 and
0.62 in 2026. FP3 was 0.46–0.53, then 0.65. Rolling points did not rise. Alex's
hypothesis is that under the new regulations, teams need more from practice and
hide less of their true pace. The pattern fits: in 2026, practice held at about
0.60–0.64 from race 2 to race 16 instead of fading as teams learned their cars.
In 2023–25, how well practice predicted showed no link to race number. That came
from a throwaway script on 2026-11-08, which scored each slot with
`indicator_analysis.race_scores`. It was not kept and has not been cross-checked.

The check is decided now so that 2027 tests it blind:

- **One alternative only:** on normal weekends, driver rolling + constructor
  rolling + **2 × FP3**. Sprint weekends are unchanged. Don't change this after
  seeing 2027 data.
- **Score on 2027 alone,** per race against fantasy points, against today's
  equal-weight signal, using the bootstrap interval from `indicator_analysis`.
  Set `HOLDOUT_SEASON` to 2027 first, or 2027 joins the seasons the winners are
  chosen on (see that log, *Race 1 odds scored for every season*).
- **Also report FP2 and FP3 on their own for 2027.** If they fall back to about
  0.45–0.5, the hypothesis fails, whatever the weight comparison shows.
- **A pass is a reason for a back-test, not a change of weights.** Using the
  rule of thumb of 15–25 points a season per 0.01 of Spearman, the gain will
  probably be smaller than one season's noise.

Raised by Alex 2026-11-08.

## Get fantasy points and prices from BoxBox F1 Fantasy

Points and prices are typed into `data/f1_fantasy_archive.xlsx` by hand today.
Get them from these two JSON files instead:

- <https://boxboxf1fantasy.com/data/driver_history.json>
- <https://boxboxf1fantasy.com/data/season_summary.json>

Neither has been looked at yet. Overlaps `data_capture_v1`, which is moving
the archive to CSV and chose hand-typed input over scraping (2026-07-30), so
settle with that effort which route wins first.

Raised by Alex 2026-11-08.
