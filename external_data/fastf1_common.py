import logging
from functools import wraps
import os
from pathlib import Path
import fastf1
from pickle import Pickler, Unpickler

_FASTF1_DEFAULT_CACHEDIR = "/mnt/chromeos/removable/sd256/linux/fastf1_cache"
# Additional cache layer, even when FastF1 API caches its results, it still takes a while to process
_FASTF1_DATAFRAME_CACHEDIR = f"{_FASTF1_DEFAULT_CACHEDIR}/dataframes"


def call_once(func):
    def wrapper(*args, **kwargs):
        if not getattr(wrapper, 'called', False):
            wrapper.called = True
            return func(*args, **kwargs)
    return wrapper


@call_once
def setup_fastf1_cache(cache_dir: str=_FASTF1_DEFAULT_CACHEDIR, dataframe_cache_dir=_FASTF1_DATAFRAME_CACHEDIR):
    fastf1.set_log_level('WARNING')

    os.makedirs(cache_dir, exist_ok=True)
    fastf1.Cache.enable_cache(cache_dir)
    logging.info(f"FastF1 cache enabled at: {cache_dir}")

    os.makedirs(dataframe_cache_dir, exist_ok=True)
    logging.info(f"FastF1 dataframe cache enabled at: {dataframe_cache_dir}")


def get_cache_filename(func, args: tuple, kwargs: dict) -> str:
    result = f"cache_{func.__name__}"

    # Unnamed arguments
    args_str = "_".join(str(a) for a in args)
    if len(args_str) > 0:
        args_str = "_" + args_str

    # Keyword arguments
    kwargs_list = [f"{k}-{v}" for k,v in kwargs.items()]
    kwargs_str = "_".join(a for a in kwargs_list)
    if len(kwargs_str) > 0:
        kwargs_str = "_" + kwargs_str

    return f"{result}{args_str}{kwargs_str}.pkl"


def filecache(func):
    @wraps(func)
    def wrapper(*args, use_cache=True, **kwargs):
        path_cache = Path(_FASTF1_DATAFRAME_CACHEDIR)
        path_full = path_cache / get_cache_filename(func, args, kwargs)

        # If cache already exists, use it
        if path_full.exists() and use_cache:
            with open(path_full, mode="rb") as cache_file:
                pkl = Unpickler(cache_file)
                obj = pkl.load()
                logging.info(f"Used {path_full}")
        # Otherwise, execute the function and write the cache
        else:
            obj = func(*args, **kwargs)
            with open(path_full, mode="wb") as cache_file:
                pkl = Pickler(cache_file)
                pkl.dump(obj)
                logging.info(f"Saved {path_full}")

        return obj
    return wrapper
