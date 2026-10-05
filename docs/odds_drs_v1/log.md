# odds_drs_v1 — Log

Execution log for the odds_drs_v1 effort. Newest entries at the bottom.
Requirements and plan live alongside in `requirements.md` and `plan.md`.

## Status summary

- Effort started 2026-10-05. Step 1 (docs) is complete, with requirements and
  plan agreed. Step 2 is in progress.

## 2026-10-05 — Scoping

Scope agreed in conversation before writing anything:

- Edit `StrategyBettingOdds` only, with DRS always on, and leave the rest of
  `linear/` alone. The live team is mid-season.
- Run the back-test through the existing harness rather than writing a new
  per-race limitless comparison. It covers 2026 through race 16.
- Keep the code. The findings go here, and the results are discarded.

Found while scoping:

- Odds exist only for 2026 races 1–17, so no other season can be back-tested.
- The harness skips teams already in its store, so this run must not use the
  default store. If it did, the end-of-season run would silently reuse its
  partial-season rows (R7).

Q1 settled as (a): when the LP's DRS nominee has no odds, return `""` so
`Team` keeps its highest-price fallback. The fallback sits in the odds
strategy, not in `StrategyBase`.
