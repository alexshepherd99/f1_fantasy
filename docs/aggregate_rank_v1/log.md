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

## 2026-11-08 — Done

All four steps landed, one commit each. Suite green at the end: 543 passed.

**Step 1, the move.** The strategy signal for all 1,794 stored rows over 88 races,
snapshotted before and after, came out identical, as did `add_signal_inputs` over the
whole stored file.

**Step 2, the rule.** Seven new unit tests and two reworked output tests all failed on
their assertions before the change. Two things came up:

- `test_build_race_metrics_works_when_race_results_missing` passed before the change. In
  its fixture, constructor points and FP2 put the drivers in the same order, so trading one
  for the other left the sum alone. PER now tops FP2, and the test fails on the old rule.
- Three output-test fixtures returned FP2-labelled laps for both practice sessions. Those
  merged into suffixed columns no weekend format can be read from, so the new rule raised.
  They now label laps with the session asked for, as `get_session_laps` does.

Mutations, each restored from a copy with the suite green between: dropping the race 1
rule, adding FP2 to the normal slots, leaving out the absent session columns, and not
zero-filling a missing input each turned tests red. **Computing the aggregate after the
zero-fill survived, as an equivalent mutant.** Zero-filling first makes a sprint race read
as a normal weekend, but the normal rule then adds a zero FP3 rank to the same sum. The
code keeps the safer order, which matters if `SIGNAL_SLOTS` ever gives a sprint weekend a
practice slot or weights FP3 differently.

**Step 3, the stored file.** Recomputed one race at a time, as `build_race_metrics` does,
taking back only the two columns. Checked, and each check shown able to fail:

1. Sorted by season, race and driver, every other cell of the 1,794 rows and 35 columns is
   unchanged. A copy with the absent sprint qualifying ranks zero-filled failed this.
2. After race 1, `AggregateRank` matches the strategy signal, built through separate
   code, to within 5e-10 over 1,712 rows. The old file failed this by up to 2.6.
3. Race 1 equals `OddsRank`. 2023, 2024 and 2025 have no race 1 odds, so are all zero.
4. `RankPosition` runs 1 to n in every race and follows `AggregateRank`.

1,748 rows changed one or both columns. The strategy signal read from the rewritten file is
identical to before, as the row order within a race has changed.

**Not run:** `fast_f1.cli` against the live API. The single-race path through
`build_race_metrics` is covered by the output tests, with FastF1 faked. The first real run
will be the next race weekend's.
