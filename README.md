# f1_fantasy

This module applies linear programming, using the Python PuLP library, to optimise team selection for the F1 Fantasy game.  This presents some interesting challenges in representing the team selection in a way that only linear algebra functions can be used - e.g. no min / max / abs.

The data is represented in a way that allows back-testing strategies against all possible starting team combinations for historic seasons, taking into account game mechanics such as unused transfers granting a free bonus transfer in the next race, and price variation throughout the season.

Drivers which are in the current team, but not available for selection in the upcoming race, will force the usage of a transfer to swap the driver out.

By default, the team DRS x2 selection will go to the highest value driver.  The Strategy class has the option to override this behaviour if desired.

The "how" is as important as the "what" here; everything has been developed on a minimal-spec budget Chromebook using Codespaces and a local Chromebook Linux dev environment.

There are some limitations to take into consideration:

- Chips are not handled.  Each individual strategy is focused on a single race, with the back-testing executing each race as a standalone decision point.  As such, chips, which require a view across the season, are not taken into account.
- The only exception to this, is that the P2PM strategy assumes playing the "unlimited moves" chip at race four.  Asset stats are built up as a rolling cumulative average over three races, so at race four, we take the opportunity to reset the team in case we started with some unfortunate picks at the start of the season.
- In the event that a driver switches teams part way through the season, when assessing their value for money (cumulative points, cumulative points per million) will only take into account their points in the context of a single team.  E.g. TSU and LAW swapping between VRB and RED in 2025, TSU's points history with RED will not be taken into account when assessing his value with VRB.
- For most strategies, concentration risk is not managed, i.e. there are no constraints on choosing a constructor alongside one or even two drivers from that constructor.  So far, the cost cap appears to mitigate the worst effects of concentration risk, in that it's difficult to afford top-flight drivers and constructors.  However this is one to watch, when the algo is used in the wild.  The exception strategy which does manage this is the betting odds one, detailed below.
- Application performance is not currently a consideration, meaning that it can take several hours to run a full back-test for all strategies against seasons 2023-2025.  Performance improvements usually come at the cost of increased code complexity, so ease of making further changes has been prioritised over execution speed. 

## Agentic engineering

After writing the initial version of the code mostly by hand, future iterations will be written by a coding agent, thus providing an experiment ground for agentic engineering in a brownfield environment.

## Usage scripts

- **run_single_team.py** : Run all strategies for a given team in a given season, saving the results out to Excel format.  Starting race can be specified within the script, so that you can predict from a particular point within the season against your team at that time.
- **run_multiple_teams.py** : Full back-testing script, running all strategies against all available seasons, for every possible starting team combination above a specified total value.  Outputs are written to a parquet format file every 100 simulations, in case of interuption; when re-running, any simulations already present in the output will be skipped.  For comparing a strategy against P2PM, the sampled **backtest** module below is quicker and reports paired results.
- **batch_results_xl.py** : convert the parquet output file from run_multiple_teams.py into a csv format, for analysis and importing into Tableau.
- **check_run_ppm.py** : generate an Excel version of the strategy input data, plus any derivation calculations.
- **select_starting_team.py** : identify the best starting line-up for a given season, based on cost ratio of driver to constructor.
- **select_odds_start.py** : similar to the above to identify a starting line-up for a given season, based on available betting odds.  Requires thinking about driver concentration risk. 

## Input data

The files **data/f1_fantasy_drivers.csv** and **data/f1_fantasy_constructors.csv** contain input data from the F1 Fantasy game: points and price, one row per driver or constructor per race, for every season.  Drivers have the columns `Season,Race,Constructor,Driver,Points,Price`, with `Driver` as the bare code (`NOR`); constructors have `Season,Race,Constructor,Points,Price`.  They replaced a spreadsheet on 2026-11-08 so that each race's data shows as a git diff.  Unit tests validate the files and fail if they are malformed.

A driver or constructor not taking part in a race has no row for it.  A race not yet run has its prices and an empty `Points`; the loader treats those points as 0.

Rows are grouped by season, then by driver or constructor, then by race, and that order matters: the back-tests sample starting teams by position, so reordered rows would quietly sample different teams.  A new race's row for each driver goes after that driver's previous race, and a driver new to a season goes after the season's last driver.  Numbers are written in their shortest form (`27`, `27.2`, `-14`).  Edit the files as text, not in a spreadsheet application, which can reorder rows or reformat numbers when it saves.

Each race's points and prices are captured from [BoxBox F1 Fantasy](https://boxboxf1fantasy.com)'s published data, a few days after the race weekend:

```bash
PYTHONPATH=. venv/bin/python -m boxbox.cli             # capture, or correct the next race's line-up
PYTHONPATH=. venv/bin/python -m boxbox.cli --dry-run   # show what it would write, write nothing
```

Once BoxBox shows the archive's latest race as held, a run fills that race's points and adds the next race at BoxBox's current prices, one row per priced driver and constructor.  Before then, a run corrects that race's line-up and prices from BoxBox, which is how a late driver change is put right.  It prints each driver's and constructor's previous and new values.  It refuses, writing nothing and exiting 1, when BoxBox has the results but not the new prices yet, when the line-up does not match BoxBox's results, or when anything else does not add up; run it again later or fix the rows by hand.  Every run, dry or not, saves the downloaded files under `outputs/boxbox/`, which keeps a history BoxBox does not.  Review the CSVs' git diff before committing.  Starting a new season is not handled yet.

**data/test_expected_values_2023.csv** and **data/test_expected_values_2024.csv** hold some pre-computed values of the derivation calculations, to support unit testing.  They replaced a spreadsheet on 2026-11-08.

**data/f1_betting_odds.csv** holds race-winner betting odds, one row per driver per race, and is used by the betting odds strategy and by the `fast_f1` odds indicator, see below; **data/test_betting_odds.csv** is its test fixture.  It replaced a spreadsheet on 2026-11-08 so that each race's odds show as a git diff.  Odds format is 100/1, 9/4, 5:2, 4-3.  Odds-on prices, where the stake exceeds the return (10/11, 4/6), are valid and are how a strong favourite is priced.  Fractional odds `a/b` are converted to an implied probability of `b/(a+b)`, and a blank price counts as no price.

**Odds** is the only column the strategies and the `fast_f1` indicator read.  It holds the odds the strategies optimise on — see the betting odds strategy below for the recommended timing.  The other columns record *when* prices were taken, so odds evolution through the weekend can be reviewed later; `fast_f1.indicator_analysis` compares them with **Odds** to tell which snapshot a race's odds came from.

### Capturing odds from Oddschecker

Odds are no longer typed in by hand.  Open the race's winner page on Oddschecker (from https://www.oddschecker.com/motorsport/formula-1), save it from the browser into `outputs/` as a single file (`.mhtml`), then run:

```bash
PYTHONPATH=. venv/bin/python -m odds_source.cli
```

It reads the newest saved page (or one named on the command line), asks FastF1 which race it is for and how far through the weekend the page was saved, matches the page's driver names to driver and constructor codes, and writes each driver's median price across the bookmakers into **Odds** and into the column for the last session finished.  A rerun overwrites.  A driver priced by fewer than half the bookmakers, usually one not in the race, is left out; a name it cannot match is written as the page spells it with a blank constructor, to fix by hand.  Review the file's git diff before committing it.  It needs the F1 account file, as the `fast_f1` module does.

| Column | Filled by a page saved |
| --- | --- |
| Odds_PreFP1 | before first practice |
| Odds_FP1, Odds_FP2, Odds_FP3 | after that practice session |
| Odds_SQ, Odds_Sprint | after sprint qualifying, after the sprint |
| Odds_Q | after qualifying, once the grid is known |

A session counts as finished an hour after its scheduled start.  The page is only fetched by the browser: Oddschecker refuses scripted requests, and getting round that is not something to build.

The legacy columns **Odds_Pre_Weekend**, **Odds_Post_FP2**, **Odds_Pre_Quali** and **Odds_Post_Quali** hold the hand-entered snapshots for 2026 races 1–20 and are no longer written.

## Strategies

These strategies are contained in the **linear** module:

- **Zero-stop** : Simple control strategy, assume the same starting line-up throughout the whole season.  The only permitted changes are when a selected team driver is not available.
- **Max budget** : Another simple control strategy, optimise to ensure the full budget is utilised.
- **Max P2PM** : Optimises for points per million over a rolling total of the previous three races.  PPM alone can make some pretty unusual choices, so points squared per million is used instead, with points squared using an absolute value to ensure that negative cumulative points is reflected correctly.  DRS x2 selection behaviour is overridden, so that the driver with the highest rolling cumulative points is selected.
- **Max points** : Experimental challenger to Max P2PM.  It maximises the rolling three-race points total directly and ignores price, apart from the budget cap.  Otherwise it copies Max P2PM, including the race-4 unlimited-moves chip and the DRS selection rule.  It tested whether dividing by price penalises expensive assets twice.  In back-testing it lost to Max P2PM in all three seasons, so it isn't used for live picks.  See the [back-test log](BACKTEST_LOG.md).
- **Betting odds** : Use bookies odds to pick the most likely winners, and optimise for the highest overall odds within the cost constraints.  Only the Odds column is used from the input file; the best odds to use will be after FP3 (and obviously before quali) as this is the time all the professional analysts update their models.  If not possible to wait for FP3, try to wait until after FP2, when the long-running pace will be more visible.  The constructor odds are a summation of the two drivers, which is not accurate from a pure stats perspective, but works when using as an LP optimise variable.  This strategy differs from Max P2PM in three key ways:
- - Betting odds are a forward-looking indicator as opposed to P2PM which is driven by historical performance;
- - The points-based strategies are less exposed to concentration risk in team selection (exposure to more than one constructor) because the game price is also based on performance from the last few races.  As such, the odds strategy has a concentration metric built in.  Building this in a way that could be modelled in PuLP was a bit hairy, so it has not yet been ported back into the base strategy;
- - No historical odds could be found during development, so it's not been back-tested. [2026-10-05: back-tested on 2026 races 1–16 only, with DRS chosen inside the LP. It lost to P2PM by about 12%. See `docs/odds_drs_v1/log.md`.]
- **FastF1** : Maximises a forward-looking signal from the `fast_f1` module (below), built in `fast_f1/signal.py`: each driver's recent points, their constructor's recent points and, on a normal weekend, their final practice (FP3) rank.  The signal is put on a championship points scale, so a driver well clear of the field stays well clear, and a constructor scores the sum of its two drivers.  DRS is chosen inside the LP.  It can also reward spending, penalise assets likely to score negative, and reward assets whose price is expected to rise under the game's price rules from 2025.  The chosen setting, `StrategyFastF1RuleRise`, uses only the price-rise reward, fixed at 2.5; it was back-tested under the label `FastF1_RuleRise2p5`.  It does not play the race-4 chip.  In back-testing it beat Max P2PM in 2025 and in 2026 through race 18, the season it was not tuned on, though one race carries most of the 2026 lead.  The live 2026 team stays on Max P2PM.  See the [back-test log](BACKTEST_LOG.md) and `docs/fastf1_v2/`.

Note on odds conversion (2026-07-26): fractional odds `a/b` are converted to an implied probability of `b/(a+b)`.  This previously used `b/a`, which over-weighted the front of the grid and rejected odds-on prices outright.  Correcting it changed the selected team in 3 of the 9 races of 2026 that previously solved, so team results logged below from before that date are not reproducible under the current code.  The `fast_f1` module also consumes these odds as a weighted indicator — see `docs/fastf1_v1/`.

## Back-testing against P2PM

The **backtest** module compares strategies against Max P2PM without simulating every starting team.  For each season it draws a seeded random sample of starting teams from three value bands — (90, 95], (95, 99.5] and (99.5, 100] — and simulates P2PM and each named challenger on the same teams, through the same engine as `run_single_team.py`.  Each challenger is then compared with P2PM team by team.

```bash
# 500 teams per band over 2023-2025, challengers named explicitly
PYTHONPATH=. venv/bin/python -m backtest.cli --strategies StrategyMaxBudget

# smaller and quicker, or other seasons and band edges
PYTHONPATH=. venv/bin/python -m backtest.cli --strategies StrategyZeroStop --sample-size 20
PYTHONPATH=. venv/bin/python -m backtest.cli --strategies StrategyZeroStop --seasons 2026 --bands 90 95 99.5 100
```

`--sample-size` is per band, so the default of 500 draws 1,500 teams a season.  At roughly 0.4 seconds a simulation, the default run takes about 30 minutes per strategy, P2PM included, so about 85 minutes with two challengers.  Seasons default to the completed ones, listed in `COMPLETED_SEASONS` in `backtest/cli.py`; add a season there once it has finished.

Three files are written to `outputs/`:

- **backtest_v1_results.parquet** : one row per simulated team, written every 100 simulations.  A re-run skips any team already in it, so an interrupted run resumes, and later runs reuse P2PM's results.  Rows from other seeds, sample sizes or strategies stay in the file but are ignored by a run that did not ask for them.
- **backtest_v1_summary.csv** : per strategy, season and band — mean, median, lower decile and max season points, then the mean, median and lower-decile difference from P2PM on the same teams, the mean percentage difference, and the share of teams beating P2PM.  Challengers are ranked by mean percentage difference within each season and band.
- **backtest_v1_summary_verdict.csv** : per challenger, whether it beats P2PM — a positive mean difference in every season — and whether the difference at least has the same sign every season.

Reading the results:

- The **pooled** row of each season covers all three bands together.  The bands are sampled equally but are far from equally common — the cheapest band holds 10-15 times as many teams as the most expensive — so a pooled figure is a mean over the sampled bands, not over every possible team.
- Seasons are never pooled or ranked together.  With three seasons, the season is what limits confidence, not the number of teams sampled.
- Whether a cheaper start does better is what the bands are there to show, so compare them rather than relying on the pooled row alone.

Full requirements, plan and development log are in `docs/backtest_v1/`.

Results of each strategy back-tested this way are summarised in **[BACKTEST_LOG.md](BACKTEST_LOG.md)**: a table of every strategy tested, then the key findings for each, with links to the full detail.

## FastF1 signal

The **fast_f1** module is a separate experiment from the strategies above: rather than optimising a team from fantasy points and prices, it tries to predict how a race will go using data available before it starts.  It works out practice lap time ranks (FP2 + FP3 on a normal weekend, FP1 + Sprint Qualifying on a sprint weekend, FP1 alone on a 2023 sprint weekend since its Sprint Shootout ran after teams locked, ignoring laps slower than 107% of the session best), rolling totals of driver and constructor points over the previous three races, and the betting odds described above, each normalised to 0-1 and all written out.

The AggregateRank it prints adds up the ones the indicator analysis found best predict fantasy points, at equal weight: driver points + constructor points + FP3 on a normal weekend, and driver points + constructor points on a sprint weekend.  Race 1 has no points history, so it ranks on betting odds alone, and every driver scores zero there when a race has no odds, as in every season before 2026.

AggregateRank itself is not wired into any strategy.  The **FastF1** strategy above reads the same stored metrics through `fast_f1/signal.py`, using the same combination after race 1.

Two modes:

```bash
# one race, writes to outputs/
PYTHONPATH=. venv/bin/python -m fast_f1.cli --season 2026 --race 10

# every race from 2023 onwards, or one season, writes to data/
PYTHONPATH=. venv/bin/python -m fast_f1.cli --historical
PYTHONPATH=. venv/bin/python -m fast_f1.cli --historical --season 2026
```

Historical mode skips season/race pairs already in the output file, so it can be interrupted and resumed; delete the file to regenerate from scratch.  Results land in **data/fastf1_practice_rolling_metrics.csv**, which keeps practice lap times in days (the unit the file held when it was a workbook).

On first run it will ask where to keep the FastF1 API cache and remember the answer.  The cache is large and lives outside the repo, and the file recording your choice is not committed.

Since October 2026 the F1 timing service only serves data to a signed-in F1 account (a free account worked when this was set up).  FastF1 3.9.0 signs in on its first download and keeps the token for about four days, so it needs your account details whenever the token has expired.  They are read from a credentials file outside the repo, which you create once:

```bash
mkdir -p ~/.config/f1_fantasy && chmod 700 ~/.config/f1_fantasy
# then create ~/.config/f1_fantasy/f1_credentials with two lines, no quotes:
#   F1_USERNAME=<your F1 account email>
#   F1_PASSWORD=<your F1 account password>
chmod 600 ~/.config/f1_fantasy/f1_credentials
```

Every `fast_f1.cli` run reads that file first and stops with an error if it is missing, readable by other users, or lacks either line.  The values are placed in that run's environment only and are never logged or written anywhere else; FastF1 keeps its own token, readable only by you, which `venv/bin/python -m fastf1 auth f1tv --clear` removes.  Never put the credentials in the repo or in a shell profile.

Full spec, plan and development log are in `docs/fastf1_v1/`.

## Modules

- **import_data** : load archive data from Excel inputs, and generate the derivations for points and price for use by the strategies.
- **races** : class representations for assets, teams, races, seasons.
- **linear** : linear programming strategies.
- **fast_f1** : FastF1 API access and the predictive indicators derived from it, see above.
- **backtest** : sampled, paired back-testing of strategies against Max P2PM, see above.

## Links

- https://fantasy.formula1.com/en/
- https://f1fantasytools.com/statistics
- https://docs.fastf1.dev/index.html (Free API with more data than you can shake a chequered flag at!  Used by the fast_f1 module for the forward-looking indicators described above, which the FastF1 strategy reads.)

## 2026 team

Strategy selection defined as soon as the fantasy prices were released pre-season, after pre-season testing.  Starting team selections made after FP2 in the first race.

(*) Max P2PM strategy selects the unlimited moves chip at race 4, as we then have the full three races of history required by the strategy, so a team reset at that point can mitigate an unlucky initial team selection.

| Race | Strategy | Chips | Drivers | Constructors | Total budget | Points | Points Total
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Betting odds, max concentration 1 | | RUS,LIN,COL,BOR,HAD | HAA,MER | 100.0 | 234 | 234 |
| 2 | Max P2PM | | RUS,LIN,COL,BOR,BEA | VRB,MER | 102.0 | 300 | 534 |
| 3 | Max P2PM | | RUS,LIN,COL,LAW,BEA | HAA,MER | 104.4 | 143 | 677 |
| 4 | Max P2PM | Unlimited moves (*) | ANT,HUL,LAW,OCO,PER| FER,MER | 107.6 | 237 | 914 |
| 5 | Max P2PM | | ANT,BOT,COL,OCO,PER | FER,MER | 109.7 | 303 | 1217 |
| 6 | Max P2PM | | ANT,BOT,COL,OCO,LAW | FER,MER | 111.4 | 214 | 1431 |
| 7 | Max P2PM | Free transfer | ANT,BOT,COL,OCO,LAW | FER,MER | 112.7 | 97 | 1528 |
| 8 | Max P2PM | Free transfer, 3x Boost | ANT,HAM,COL,HUL,LAW | VRB,MER | 114.4 | 296 | 1824 |
| 9 | Max P2PM | Auto pilot | ANT,HAM,HAD,HUL,LIN | VRB,MER | 115.7 | 270 | 2094 |
| 10 | Max P2PM | | RUS,HAM,HAD,HUL,LIN | VRB,FER | 118.0 | 166 | 2260 |
| 11 | Max P2PM | | COL,HAM,HAD,HUL,LIN | MER,FER | 120.1 | 223 | 2483 |
| 12 | Max P2PM | No negative | COL,LEC,LAW,HUL,LIN | MER,FER | 122.2 | 278 | 2761 |
| 13 | Max P2PM | | ALO,NOR,LAW,HUL,LIN | MER,FER | 122.7 | 256 | 3017 |
| 14 | Max P2PM | | ALO,NOR,LAW,HUL,ANT | MER,AUD | 125.2 | 212 | 3232 |
| 15 | Max P2PM | | COL,NOR,HAD,HUL,ANT | MER,AUD | 127.3 | 183 | 3415 |
| 16 | Max P2PM | | LIN,VER,HAD,HUL,ANT | MER,AUD | 128.8 | 264 | 3679 |
| 17 | Betting odds | Limitless | VER,ANT,HAM,NOR,LEC | RED,MER | | 364 | 4043 |
| 18 | Max P2PM | | BEA,HAD,HUL,LIN,VER | RED,MER | 134.6 | 184 | 4227 |
| 19 | Max P2PM | | LAW,HAD,HUL,LIN,VER | RED,FER | 136.4 | 283 | 4510 |
| 20 | Max P2PM | | LAW,LEC,HUL,PER,VER | RED,FER | 137.7 | | |
| 21 | Max P2PM | | | | | | |
| 22 | Max P2PM | | | | | | |
| 23 | Max P2PM | | | | | | |
| 24 | Max P2PM | | | | | | |
