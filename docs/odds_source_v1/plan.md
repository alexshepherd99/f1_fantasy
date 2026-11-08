# odds_source_v1 — Plan

Requirements and decisions D1–D17 in `requirements.md`. One commit per step,
test first for every behaviour change, suite green at the end of each.

## Shape

A new package, `odds_source/`, run as
`PYTHONPATH=. venv/bin/python -m odds_source.cli`. It reads Alex's saved page,
asks FastF1 where the weekend is, and writes one race's rows into
`data/f1_betting_odds.csv`. FastF1 calls go through `fast_f1/api.py`, and
credentials through `fast_f1.auth`, as `fast_f1.cli` does. Nothing in `races/`,
`linear/` or `scripts/` changes. `import_data/odds.py` changes under D7.

## Steps

1. ~~Thread the odds file path through `fast_f1.output`~~ — done 2026-11-08,
   see log *Step 1*.

2. ~~Convert the real odds workbook to CSV, beside it~~ — done 2026-11-08,
   see log *Step 2*. Its `load_odds` comparison runs in step 3.

3. ~~Switch the loader to CSV~~ — done 2026-11-08, see log *Step 3*.

4. ~~Parse the saved page~~ — done 2026-11-08, see log *Step 4*.

5. ~~Find the race and the column~~ — done 2026-11-08, see log *Step 5*.

6. ~~Map names and teams~~ — done 2026-11-08, see log *Step 6*.

7. ~~Write the race's rows~~ — done 2026-11-08, see log *Step 7*.

8. **The CLI.** `odds_source/cli.py` loads the credentials first, as
   `fast_f1.cli` does, takes the page path (default: newest `.mhtml` in
   `outputs/`) and `--odds-file` (default: the real CSV), and prints the race,
   the column, the drivers written and any warnings.

10. **Teach `indicator_analysis` the new columns**, test first, before step 9.
   It finds which snapshot each race's `Odds` came from by matching columns,
   then excludes races whose odds knew qualifying (`ODDS_LEAK_SNAPSHOT`,
   `Odds_Post_Quali`) and splits out pre-weekend ones
   (`ODDS_PRE_WEEKEND_SNAPSHOT`, `Odds_Pre_Weekend`). A captured race would
   match `Odds_Q` or `Odds_PreFP1` instead, so neither rule would apply.

9. **Docs.** `README.md` (odds input: CSV, new columns, the capture command),
   `CLAUDE.md` (the workbook references and the new package), `BACKLOG.md`
   (mark done), log close.

## Gates

**Gate 1 — the Brazil sample, live FastF1.** Run the CLI against Alex's saved
Brazil page with `--odds-file` pointing at a scratch copy of the CSV. Expect
column `Odds_Q`, 22 drivers, Ocon dropped, Camara on `HAA`, and medians
matching the survey in `requirements.md`. The real CSV is not touched.

**Gate 2 — the first real run**, at the next race weekend. Alex reviews the
git diff of the CSV before committing it.
