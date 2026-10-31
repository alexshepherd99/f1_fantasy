# indicator_analysis_v1 — Plan

**Status**: agreed 2026-10-31. Requirements: `requirements.md`.

One commit per step. Each behavioural change is seen failing before it passes, and
the full suite is green at the end of every step. Code lives in
`fast_f1/indicator_analysis.py`, tests in `tests/test_indicator_analysis.py`.

## Step 1 — Effort docs

`docs/indicator_analysis_v1/{requirements,plan,log}.md`, a row in the `BACKLOG.md`
efforts table, and a pointer on the backlog item this effort answers.

## Step 2 — Analysis frame (R1–R4)

Join fantasy points onto the metrics, classify each weekend's format, build the
slots and targets, and apply the exclusions.

## Step 3 — Scoring (R5)

Per-race Spearman and top-k hit rates for a signal, plus equal-weight combination
signals.

## Step 4 — The bar (R8)

Paired per-race gains, the bootstrap interval and the verdict.

## Step 5 — Selection and fitted weights (R6, R7)

Choosing the winner on a set of seasons, leave-one-season-out selection, and
leave-one-season-out fitted weights.

## Step 6 — Run it (R9, R10)

The entry point that produces every table, including the odds comparison and the
sensitivities, written to `outputs/`.

## Step 7 — Findings and close-out

Findings in `log.md`, a plain-language summary, and the backlog gate closed with
the result.
