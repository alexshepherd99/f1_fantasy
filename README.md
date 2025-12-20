# f1_fantasy

This module applies linear programming, using the Python PuLP library, to optimise team selection for the F! Fantasy game.  The data is represented in a way that allows back-testing strategies against all possible starting team combinations for historic seasons, taking into account game mechanics such as unused transfers granting a free bonus transfer in the next race, and price variation throughout the season.

Drivers which are in the current team, but not available for selection in the upcoming race, force the usage of a transfer to swap the driver out

Excluded drivers

Limitation if driver moves team

no chips

performance not a consideration

The "how" is as important as the "what" here; everything has been developed on a minimal-spec budget Chromebook using Codespaces and a local Chromebook Linux dev environment.  Co=pilot has helped with some of the unit tests. 

## To do

- readme
- script to run for a specific individual race, all strategies
- script to identify best N starting teams
- re-run all outputs
- git repo public, main branch protected
- drop and re-create venv on local dev

## Usage scripts

- **run_single_team.py** : Run all strategies for a given team in a given season, saving the results out to Excel format.
- **run_multiple_teams.py** : Full back-testing script, running all strategies against all available seasons, for every possible starting team combination above a specified total value.  Outputs are written to a parquet format file every 100 simulations, in case of interuption; when re-running, any simulations already present in the output will be skipped.
- **batch_results_xl.py** : convert the parquet output file from run_multiple_teams.py into a csv format, for analysis and importing into Tableau.
- **check_run_ppm.py** : generate an Excel version of the strategy input data, plus any derivation calculations.

## Input data

The file **data/f1_fantasy_archive.xlsx** contains input data from the F1 Fantasy game; points and price, broken down into separate tabs for drivers and constructors, for each season.  The format is sensitive and should be consistent with the existing seasons; unit tests will validate and fail if this is not the case.

Drivers who are not participating in a given race must have no value for either points or price for that race.

If updating race data in the middle of a season, drivers and constructors will have a price for the next race but no points yet.  In this period, the points column must be populated with a value of 0 for that race, for all drivers which are expected to participate.

**data/test_expected_values.xlsx** has some pre-computed values of the derivation calculations, to support testing.

## Strategies

- **Zero-stop** :
- **Max budget** :
- **Max P2PM** :

## Modules

- **import_data** : 
- **races** : 
- **linear** : 

## Links

- https://fantasy.formula1.com/en/
- https://f1fantasytools.com/statistics
