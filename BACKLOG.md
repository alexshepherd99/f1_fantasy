# Backlog

Global list of not-yet-started work. Freeform. When an item is picked up, create `docs/<effort-name>/` (see `docs/` and `agentic`'s `shared/persistent-docs.md`) and move the item there.

## Unported FastF1 signals from the removed `external_data` prototype

The `external_data/` prototype was removed 2026-07-25; its code is recoverable
at commit `a6616d5` (e.g. `git show a6616d5:external_data/temp.py`). Three
signals in it have no `fast_f1/` equivalent and may be worth porting:

- **Stint / tyre pace** — per-stint lap-time analysis pulling `Compound`,
  `TyreLife` and `FreshTyre`, aggregated to a best-stint-per-driver frame.
  `fast_f1/metrics.py` ranks single fastest laps only, so tyre state and
  pace-over-a-stint are unmodelled.
- **Reliability ratio** — per-driver share of prior races in the season
  actually finished, ranked within each race. A DNF-risk signal with no
  current equivalent.
- **Season aggregate points rank** — cumulative season-to-date points per
  driver, dense-ranked per race; broader than `fast_f1`'s 3-race window.

## Simplify in-season data capture

Points and prices for each race are currently entered by hand into
`data/f1_fantasy_archive.xlsx`, which holds wide-format Points/Price sheets
per season with a column per race. Editing that layout race-by-race is
fiddly and easy to get wrong — in particular the null-vs-zero convention
(non-participants need both points and price null; expected participants
with a known price but no result yet need points `0`) that
`import_data/import_history.py` validates against.

Replace the manual step with a helper script that takes one race's worth of
points and prices and writes them into the archive, applying the
null/zero convention itself. That likely needs the workbook simplifying
first — a tidy long-format layout would be a much easier write target than
the current wide sheets, but `import_data/import_history.py` melts the wide
format today, so the loader and its integrity checks change with it.

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
