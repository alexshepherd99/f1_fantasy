import logging
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
