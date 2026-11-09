# readme_tidy_v1 — Log

A small effort, so requirements and plan sit inline here (see `agentic`'s
`shared/persistent-docs.md`, *Collapsing for small efforts*).

## Requirements

Raised by Alex 2026-11-09: the README has grown repetitive, and dated history and
superseded notes are cluttering it. Tidy it, and start a changelog in the repo root.

Agreed with Alex 2026-11-09:

- **Scope is `README.md` and `CLAUDE.md`.** The README covers what the project does
  and how to run it. CLAUDE.md covers code structure and the rules an agent must
  follow, pointing to the README for usage instead of repeating it. Neither carries
  dated history.
- **`CHANGELOG.md`** in the repo root holds dated one-liners, newest first: one per
  finished effort, plus a commit-only change that alters behaviour or results.
  Routine race-weekend data, odds and team updates never get one. A line goes in
  the commit that finishes the change.
- **Backfill one line per finished effort, keeping only what is material.** Alex
  left out the AggregateRank rule (`aggregate_rank_v1`), odds capture
  (`odds_source_v1`), the cancelled `data_capture_v1` and the LP's fixed variable
  order. `data_capture_v2` gets its line when it closes.
- **History notes in the README move to the changelog only where material**, and
  are otherwise dropped. What is still true today stays, undated.
- **The 2026 team table moves to its own file, `TEAM_2026.md`.** Each season gets
  its own.

Out of scope: finished efforts' docs and `BACKTEST_LOG.md` are left as they are.

## Plan

One commit per step. Docs only, so the test suite is not run. Each step checks
that the file paths, links and commands in the files it writes exist.

1. Open this effort.
2. Move the 2026 team table to `TEAM_2026.md` and link it from the README.
3. Add `CHANGELOG.md` with the backfill, and the changelog rule in `CLAUDE.md`.
4. Rewrite `README.md`.
5. Tidy `CLAUDE.md`.
6. Close the effort.

## 2026-11-09 — Done

All six steps landed, one commit each.

- **Step 2** also repointed CLAUDE.md's team-log reference and `BACKLOG.md`'s
  chips item, which named the README's *2026 team* section. The moved table was
  diffed against the README's and is byte-identical.
- **Step 3**'s backfill is the agreed list, dated by each effort's closing commit.
- **Step 4** states each topic once: the race-4 chip under *Limitations*, the odds
  conversion under *Input data*, back-test results by one link to
  `BACKTEST_LOG.md`. It adds the missing Max P2PM without reset strategy and the
  `scripts`, `boxbox` and `odds_source` modules, fixes `import_data`'s "Excel
  inputs", and drops the "several hours" run-time and "all possible" starting
  teams, which the sampled back-test no longer matches. The odds strategy's
  "never back-tested" line, and its bracketed correction, became one sentence
  stating why it was tested on 2026 alone; the odds file holds only 2026, which
  was checked.
- **Step 5** keeps CLAUDE.md's rules and drops what README.md already says: the
  `fast_f1` session list, the data file formats and back-test results.

Checked, and could have failed: every repo path, link target and CSV header the
new README names exists or matches; the 27 paths CLAUDE.md names exist; the four
CLIs it gives answer `--help`. Docs only, so the test suite was not run.
