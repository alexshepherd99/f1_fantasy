from pathlib import Path
import logging

import pandas as pd

from external_data.fastf1_common import setup_fastf1_cache
from external_data.process_data import get_practice_and_rolling_metrics
from common import setup_logging


_FILE_FASTF1_METRICS = "data/fastf1_practice_rolling_metrics.xlsx"
_SHEET_NAME = "PracticeRollingMetrics"


def load_existing_metrics(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    if not path.exists():
        return pd.DataFrame()

    try:
        return pd.read_excel(path, sheet_name=_SHEET_NAME, engine="openpyxl")
    except ValueError:
        return pd.read_excel(path, engine="openpyxl")


def save_metrics(df: pd.DataFrame, file_path: str) -> None:
    df = df.sort_values(
        by=["Season", "Race", "AggregateRank"],
        ascending=[True, True, False],
    ).reset_index(drop=True)

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=_SHEET_NAME, index=False)


def update_fastf1_metrics(
    season_years: list[int],
    race_numbers: list[int],
    file_path: str = _FILE_FASTF1_METRICS,
) -> pd.DataFrame:
    existing = load_existing_metrics(file_path)
    updated = existing.copy()

    for season_year in season_years:
        for race_num in race_numbers:
            already_present = False
            if not updated.empty:
                already_present = (
                    (updated["Season"] == season_year) &
                    (updated["Race"] == race_num)
                ).any()

            if already_present:
                logging.info("Skipping existing metrics for season %s race %s", season_year, race_num)
                continue

            logging.info("Computing metrics for season %s race %s", season_year, race_num)
            df_metrics = get_practice_and_rolling_metrics(season_year, race_num)
            if df_metrics.empty:
                logging.warning("No practice/rolling metrics generated for season %s race %s", season_year, race_num)
                continue

            updated = pd.concat([updated, df_metrics], ignore_index=True, sort=False)
            save_metrics(updated, file_path)
            logging.info("Saved updated metrics to %s", file_path)

    return updated


if __name__ == "__main__":
    setup_logging()
    setup_fastf1_cache()

    update_fastf1_metrics(season_years=[2023,2024,2025], race_numbers=[x for x in range(1,23)])
