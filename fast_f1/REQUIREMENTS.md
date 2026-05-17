# fast_f1

This module provides cached access to the FastF1 API data and derivations thereof.

The `external_data` sub-module within this repo contains sample experimental code that can be used as an indicator of the desired outputs and API calls needed.  The `get_fastf1_data.py` script in the scripts module creates outputs similar to that required here, and can also be used as an indication of how to use the APIs.

## Purpose

Predict the outcome of a Formula 1 race, given data available before the race.  There are two formats of race weekend, with different data available for each.

When considering lap times, any laps which are greater than 107% of the fastest lap time across all drivers are discarded.

### Standard race weekend

**Data available to predict outcome:** Free Practice 2 fastest lap time, Free Practice 3 fastest lap time. 

### Sprint race weekend

**Data available to predict outcome:** Free Practice 1 fastest lap time, Sprint Qualifying fastest lap time.

### All race weekends

Formula 1 results can reasonably be judged by past performance within the same season, so previous points can be used as an indicator:

**Data available to predict outcome:** Rolling total of points from the previous three races for the driver, rolling total of points from the previous three races for the driver's constructor.

## Combining indicators

Within a race, the individual indicators for each driver are normalised to a range 0-1, with 1 being the best value.

For lap times, this is calculated as: 1 - ((this driver's min lap time - fastest driver's min lap time) / (slowest driver's lap time - fastest driver's min lap time))

For points, this is calculated as: (this driver's points - lowest driver's points) / (highest driver's points - lowest driver's points)

The ranks for each indicator are summed to provide a single aggregate rank.

## FastF1 API

### API-level cache

All data for these indicators are obtained through the FastF1 API.

The FastF1 API maintains a cache of calls made to its server.  This cache location is set by fastf1.Cache.enable_cache(), which must be called before any other FastF1 API is invoked.  The location of the cache will be determined on the local system.  The cache location will be set the first time this module is executed on the local system, and the cache location will be persisted somewhere.  The user will be prompted the first time the cache is set, offering two default directory options and the option for the user to provide their own value:

/mnt/chromeos/removable/sd256/linux/fastf1_cache
~/fastf1_cache

These directories will be checked and created if they do not exist, and the module will throw an exception if the directory cannot be created.

### Module-level cache

Even with cache data, the FastF1 API is slow.  The results to all calls to the FastF1 API will be cached locally to disk, in a separate directory called "local_cache" under the main cache directory specified above.  The module will create that subdirectory if it does not exist.

## Operation

The module will provide two modes of operation, which will be implemented in scripts contained within the top-level module `scripts` directory.

### Run for specific race

The user is promoted for a season (e.g. 2025) and a race number (e.g. 2).  The module will calculate the expected race result based on the indicators above.

The module will determine the type of race weekend (sprint vs. normal) based on the available data.  If the data is not available yet, e.g. if the session has not completed or the session data has not been published, the module will stop and inform the user.

The module will display the expected aggregate rank and race ordering by default, and write all the underlying detail to an Excel file in the main module `outputs` directory.  This output file will simply overwrite any previous file of the same name.

### Gather historical data

The module will run for all races in all seasons from 2023 to current, calculating the aggregate metric for each race.  All the interim data and final outputs will be written to a new Excel file in the main module `data` directory.

A single output file will contain all historical results, allowing for statistical analysis.  The module will check this file for each season/race combination before re-generating the results, to allow the script to be interupted and resumed.  The user can delete the output file if they want to regenerate all the statistics.

## Testing

Unit tests must be independent from calls to the FastF1 API, with one exception:  a unit test is provided for each function call to the FastF1 API to confirm the columns and data types returned by each call.