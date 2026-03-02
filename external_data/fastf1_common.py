import logging
from functools import wraps
import os
import fastf1

_FASTF1_DEFAULT_CACHEDIR = "/mnt/chromeos/removable/sd256/linux/fastf1_cache"


def call_once(func):
    def wrapper(*args, **kwargs):
        if not getattr(wrapper, 'called', False):
            wrapper.called = True
            return func(*args, **kwargs)
    return wrapper


@call_once
def setup_fastf1_cache(cache_dir: str=_FASTF1_DEFAULT_CACHEDIR):
    fastf1.set_log_level('WARNING')

    os.makedirs(cache_dir, exist_ok=True)
    fastf1.Cache.enable_cache(cache_dir)
    logging.info(f"FastF1 cache enabled at: {cache_dir}")


# Initialize only once on first import
setup_fastf1_cache()


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
        logging.info(func.__name__)
        logging.info(args)
        logging.info(kwargs)
        #if self.filepath.exists() and use_cache:
        #    return self.filepath
        return func(*args, **kwargs)  # Also added return here
    return wrapper
