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
