# fast_f1

This module provides cached access to the FastF1 API data and derivations thereof.

The `external_data` sub-module within this repo contains sample experimental code that can be used.  The `get_fastf1_data.py` script in the scripts module creates outputs similar to that required here.

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

## Testing

Unit tests must be independent from calls to the FastF1 API, with one exception:  a unit test is provided for each function call to the FastF1 API to confirm the columns and data types returned by each call.