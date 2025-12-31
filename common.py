from enum import Enum
import logging

F1_SEASON_CONSTRUCTORS = {
    2023: 10,
    2024: 10,
    2025: 10,
}

DEFAULT_STARTING_BUDGET = 100.0


class AssetType(Enum):
    DRIVER = "Driver"
    CONSTRUCTOR = "Constructor"


def setup_logging():
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S%z",
    )

    handlerStream = logging.StreamHandler()
    handlerStream.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handlerStream)
