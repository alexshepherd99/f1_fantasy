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
