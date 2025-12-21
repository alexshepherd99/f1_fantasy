# f1_fantasy

This module applies linear programming, using the Python PuLP library, to optimise team selection for the F! Fantasy game.  This presents some interesting challenges in representing the team selection in a way that only linear algebra functions can be used - e.g. no min / max / abs.

The data is represented in a way that allows back-testing strategies against all possible starting team combinations for historic seasons, taking into account game mechanics such as unused transfers granting a free bonus transfer in the next race, and price variation throughout the season.

Drivers which are in the current team, but not available for selection in the upcoming race, will force the usage of a transfer to swap the driver out.

By default, the team DRS x2 selection will go to the highest value driver.  The Strategy class has the option to override this behaviour if desired.

The "how" is as important as the "what" here; everything has been developed on a minimal-spec budget Chromebook using Codespaces and a local Chromebook Linux dev environment.  Co-pilot has helped with some of the unit tests.

There are some limitations to take into consideration:

- Chips are not handled.  Each individual strategy is focused on a single race, with the back-testing executing each race as a standalone decision point.  As such, chips, which require a view across the season, are not taken into account.
- It is rare, but not impossible, for a driver to switch teams mid-season, e.g. Tsunoda in 2025 from VRB to RED.  In this instance, the algo will not force a "driver unavailable" situation, and will assume that the driver has simply changed value.  This behaviour is different to the game itself, which forces TSU/RED to be unavailable, and TSU/VRB to appear as a different driver at a different price.
- Application performance is not currently a consideration, meaning that it can take several hours to run a full back-test for all strategies against seasons 2023-2025.  Performance improvements usually come at the cost of increased code complexity, so the ability to make further changes has been prioritised over execution speed. 

## Usage scripts

- **run_single_team.py** : Run all strategies for a given team in a given season, saving the results out to Excel format.
- **run_multiple_teams.py** : Full back-testing script, running all strategies against all available seasons, for every possible starting team combination above a specified total value.  Outputs are written to a parquet format file every 100 simulations, in case of interuption; when re-running, any simulations already present in the output will be skipped.
- **batch_results_xl.py** : convert the parquet output file from run_multiple_teams.py into a csv format, for analysis and importing into Tableau.
- **check_run_ppm.py** : generate an Excel version of the strategy input data, plus any derivation calculations.

## Input data

The file **data/f1_fantasy_archive.xlsx** contains input data from the F1 Fantasy game; points and price, broken down into separate tabs for drivers and constructors, for each season.  The format is sensitive and should be consistent with the existing seasons; unit tests will validate and fail if this is not the case.

Drivers who are not participating in a given race must have no value populated (i.e. null) for either points or price for that race.

If updating race data in the middle of a season, drivers and constructors will have a price for the next race but no points yet.  In this period, the driver and constructor points columns must be populated with a value of 0 for that race, for all drivers which are expected to participate.

**data/test_expected_values.xlsx** has some pre-computed values of the derivation calculations, to support unit testing.

## Strategies

These strategies are contained in the **linear** module:

- **Zero-stop** : Simple control strategy, assume the same starting line-up throughout the whole season.  The only permitted changes are when a selected team driver is not available.
- **Max budget** : Another simple control strategy, optimise to ensure the full budget is utilised.
- **Max P2PM** : Optimises for points per million over a rolling total of the previous three races.  PPM alone can make some pretty unusual choices, so points squared per million is used instead, with points squared using an absolute value to ensure that negative cumulative points is reflected correctly.  DRS x2 selection behaviour is overridden, so that the driver with the highest rolling cumulative points is selected.

## Modules

- **import_data** : load archive data from Excel inputs, and generate the derivations for points and price for use by the strategies.
- **races** : class representations for assets, teams, races, seasons.
- **linear** : linear programming strategies.

## Links

- https://fantasy.formula1.com/en/
- https://f1fantasytools.com/statistics

## To do

- script to run for a specific individual race, all strategies
- script to identify best N starting teams
- re-run all outputs
- git repo public, main branch protected
- drop and re-create venv on local dev
