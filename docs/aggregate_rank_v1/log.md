# aggregate_rank_v1 — Log

A small effort, so requirements and plan sit inline here (see `agentic`'s
`shared/persistent-docs.md`, *Collapsing for small efforts*).

## Requirements

Picked up from `BACKLOG.md`'s *Bring `AggregateRank` into line with the indicator
conclusions* (raised by Alex 2026-11-01), and removed from that list.

`AggregateRank` adds every rank column at weight 1.0, with only `METRIC_WEIGHTS` in
`fast_f1/metrics.py` setting constructor rolling points to zero. The conclusions in
`docs/indicator_analysis_v1/log.md` want:

- **Normal weekends:** driver rolling + constructor rolling + FP3, equally weighted.
- **Sprint weekends**, 2023's FP1-only ones included: driver rolling + constructor
  rolling.
- **Race 1:** betting odds alone.

`fastf1_v2` already defines the first two as `SIGNAL_SLOTS`, so reuse that rather than
writing a second definition.

Agreed with Alex 2026-11-08:

- A missing input counts as zero, as it does today. The stored file has no gaps in
  these inputs, so this only matters for a live run made before FP3.
- **Race 1 with no odds scores zero for every driver**, which is every race 1 before
  2026. Its order is then arbitrary. Accepted, as the conclusions say odds alone.
- **Rewrite `AggregateRank` and `RankPosition` in the stored
  `data/fastf1_practice_rolling_metrics.xlsx`** from its own columns, with no FastF1
  calls. Historical runs skip races already computed, so the file would otherwise keep
  the old values for good.

## Plan

One commit per step.

1. **Move the slot definition down.** `output.py` cannot import `signal.py` or
   `indicator_analysis.py`, as both import `output.py`. Move `add_signal_inputs`, its
   helpers, the format constants, `FIRST_RACE` and `SIGNAL_SLOTS` into
   `fast_f1/metrics.py`, changing nothing else. Check that the strategy's signal is
   unchanged for every stored race, as well as the suite.
2. **Change `aggregate_metrics`, test first,** to the rule above, and drop
   `METRIC_WEIGHTS`.
3. **Recompute the stored file.** Check that, sorted by season, race and driver, every
   cell is unchanged except `AggregateRank` and `RankPosition`.
4. **Docs:** `CLAUDE.md`, `README.md`, `fast_f1/__init__.py`, `BACKLOG.md`.

## 2026-11-08 — Effort opened

Suite green at the start: 540 passed.
