# f1_fantasy

This module applies linear programming, using the Python PuLP library, to optimise team selection for the F1 Fantasy game.  This presents some interesting challenges in representing the team selection in a way that only linear algebra functions can be used - e.g. no min / max / abs.

The data is represented in a way that allows back-testing strategies against all possible starting team combinations for historic seasons, taking into account game mechanics such as unused transfers granting a free bonus transfer in the next race, and price variation throughout the season.

Drivers which are in the current team, but not available for selection in the upcoming race, will force the usage of a transfer to swap the driver out.

By default, the team DRS x2 selection will go to the highest value driver.  The Strategy class has the option to override this behaviour if desired.

The "how" is as important as the "what" here; everything has been developed on a minimal-spec budget Chromebook using Codespaces and a local Chromebook Linux dev environment.  Co-pilot has helped with some of the unit tests.

There are some limitations to take into consideration:

- Chips are not handled.  Each individual strategy is focused on a single race, with the back-testing executing each race as a standalone decision point.  As such, chips, which require a view across the season, are not taken into account.
- The only exception to this, is that the P2PM strategy assumes playing the "unlimited moves" chip at race four.  Asset stats are built up as a rolling cumulative average over three races, so at race four, we take the opportunity to reset the team in case we started with some unfortunate picks at the start of the season.
- In the event that a driver switches teams part way through the season, when assessing their value for money (cumulative points, cumulative points per million) will only take into account their points in the context of a single team.  E.g. TSU and LAW swapping between VRB and RED in 2025, TSU's points history with RED will not be taken into account when assessing his value with VRB.
- For most strategies, concentration risk is not managed, i.e. there are no constraints on choosing a constructor alongside one or even two drivers from that constructor.  So far, the cost cap appears to mitigate the worst effects of concentration risk, in that it's difficult to afford top-flight drivers and constructors.  However this is one to watch, when the algo is used in the wild.  The exception strategy which does manage this is the betting odds one, detailed below.
- Application performance is not currently a consideration, meaning that it can take several hours to run a full back-test for all strategies against seasons 2023-2025.  Performance improvements usually come at the cost of increased code complexity, so ease of making further changes has been prioritised over execution speed. 

## Usage scripts

- **run_single_team.py** : Run all strategies for a given team in a given season, saving the results out to Excel format.  Starting race can be specified within the script, so that you can predict from a particular point within the season against your team at that time.
- **run_multiple_teams.py** : Full back-testing script, running all strategies against all available seasons, for every possible starting team combination above a specified total value.  Outputs are written to a parquet format file every 100 simulations, in case of interuption; when re-running, any simulations already present in the output will be skipped.
- **batch_results_xl.py** : convert the parquet output file from run_multiple_teams.py into a csv format, for analysis and importing into Tableau.
- **check_run_ppm.py** : generate an Excel version of the strategy input data, plus any derivation calculations.
- **select_starting_team.py** : identify the best starting line-up for a given season, based on cost ratio of driver to constructor.
- **select_odds_start.py** : similar to the above to identify a starting line-up for a given season, based on available betting odds.  Requires thinking about driver concentration risk. 

## Input data

The file **data/f1_fantasy_archive.xlsx** contains input data from the F1 Fantasy game; points and price, broken down into separate tabs for drivers and constructors, for each season.  The format is sensitive and should be consistent with the existing seasons; unit tests will validate and fail if this is not the case.

Drivers who are not participating in a given race must have no value populated (i.e. null) for either points or price for that race.

If updating race data in the middle of a season, drivers and constructors will have a price for the next race but no points yet.  In this period, the driver and constructor points columns must be populated with a value of 0 for that race, for all drivers which are expected to participate.

**data/test_expected_values.xlsx** has some pre-computed values of the derivation calculations, to support unit testing.

**f1_betting_odds.xlsx** and **test_betting_odds.xlsx** are used by the betting odds strategy, see below.  Odds input format is 100/1, 9/4, 5:2, 4-3.

## Strategies

These strategies are contained in the **linear** module:

- **Zero-stop** : Simple control strategy, assume the same starting line-up throughout the whole season.  The only permitted changes are when a selected team driver is not available.
- **Max budget** : Another simple control strategy, optimise to ensure the full budget is utilised.
- **Max P2PM** : Optimises for points per million over a rolling total of the previous three races.  PPM alone can make some pretty unusual choices, so points squared per million is used instead, with points squared using an absolute value to ensure that negative cumulative points is reflected correctly.  DRS x2 selection behaviour is overridden, so that the driver with the highest rolling cumulative points is selected.
- **Betting odds** : Use bookies odds to pick the most likely winners, and optimise for the highest overall odds within the cost constraints.  Only the Odds column is used from the input file; the best odds to use will be after FP3 (and obviously before quali) as this is the time all the professional analysts update their models.  If not possible to wait for FP3, try to wait until after FP2, when the long-running pace will be more visible.  The constructor odds are a summation of the two drivers, which is not accurate from a pure stats perspective, but works when using as an LP optimise variable.  This strategy differs from Max P2PM in three key ways:
- - Betting odds are a forward-looking indicator as opposed to P2PM which is driven by historical performance;
- - The points-based strategies are less exposed to concentration risk in team selection (exposure to more than one constructor) because the game price is also based on performance from the last few races.  As such, the odds strategy has a concentration metric built in.  Building this in a way that could be modelled in PuLP was a bit hairy, so it has not yet been ported back into the base strategy;
- - No historical odds could be found during development, so it's not been back-tested.

## Modules

- **import_data** : load archive data from Excel inputs, and generate the derivations for points and price for use by the strategies.
- **races** : class representations for assets, teams, races, seasons.
- **linear** : linear programming strategies.

## Links

- https://fantasy.formula1.com/en/
- https://f1fantasytools.com/statistics
- https://docs.fastf1.dev/index.html (Free API with more data than you can shake a chequered flag at!  Not currently used by any of the strategies in this module, but definite potential to develop some forward-looking indicators.)

## 2026 teams

Strategy selection defined as soon as the fantasy prices were released pre-season, after pre-season testing.  Starting team selections made after FP2 in the first race.

(*) Max P2PM strategy selects the unlimited moves chip at race 4, as we then have the full three races of history required by the strategy, so a team reset at that point can mitigate an unlucky initial team selection.

### Primary team

| Race | Strategy | Chips | Drivers | Constructors | Total value | Points | Points Total
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Betting odds, max concentration 1 | | RUS,LIN,COL,BOR,HAD | HAA,MER | 98.0 | | |
| 2 | Max P2PM | | | | | | |
| 3 | Max P2PM | | | | | | |
| 4 | Max P2PM | Unlimited moves (*) | | | | | |
| 5 | Max P2PM | | | | | | |
| 6 | Max P2PM | | | | | | |
| 7 | Max P2PM | | | | | | |
| 8 | Max P2PM | | | | | | |
| 9 | Max P2PM | | | | | | |
| 10 | Max P2PM | | | | | | |
| 11 | Max P2PM | | | | | | |
| 12 | Max P2PM | | | | | | |
| 13 | Max P2PM | | | | | | |
| 14  | Max P2PM | | | | | | |
| 15  | Max P2PM | | | | | | |
| 16 | Max P2PM | | | | | | |
| 17 | Max P2PM | | | | | | |
| 18 | Max P2PM | | | | | | |
| 19 | Max P2PM | | | | | | |
| 20 | Max P2PM | | | | | | |
| 21 | Max P2PM | | | | | | |
| 22 | Max P2PM | | | | | | |
| 23 | Max P2PM | | | | | | |
| 24 | Max P2PM | | | | | | |

### Secondary team

| Race | Strategy | Chips | Drivers | Constructors | Total value | Points | Points Total
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Max constructor/driver cost ratio| | BOR,BOT,HAD,LIN,STR | MER,MCL | 99.8 | | |
| 2 | Max P2PM | | | | | | |
| 3 | Max P2PM | | | | | | |
| 4 | Max P2PM | Unlimited moves (*) | | | | | |
| 5 | Max P2PM | | | | | | |
| 6 | Max P2PM | | | | | | |
| 7 | Max P2PM | | | | | | |
| 8 | Max P2PM | | | | | | |
| 9 | Max P2PM | | | | | | |
| 10 | Max P2PM | | | | | | |
| 11 | Max P2PM | | | | | | |
| 12 | Max P2PM | | | | | | |
| 13 | Max P2PM | | | | | | |
| 14  | Max P2PM | | | | | | |
| 15  | Max P2PM | | | | | | |
| 16 | Max P2PM | | | | | | |
| 17 | Max P2PM | | | | | | |
| 18 | Max P2PM | | | | | | |
| 19 | Max P2PM | | | | | | |
| 20 | Max P2PM | | | | | | |
| 21 | Max P2PM | | | | | | |
| 22 | Max P2PM | | | | | | |
| 23 | Max P2PM | | | | | | |
| 24 | Max P2PM | | | | | | |
