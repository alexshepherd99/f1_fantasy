import pandas as pd
import logging

from common import setup_logging
from scripts.run_multiple_teams import _FILE_BATCH_RESULTS_PARQET, _FILE_BATCH_RESULTS_EXCEL

if __name__ == "__main__":
    setup_logging()

    logging.info(f"Reading {_FILE_BATCH_RESULTS_PARQET}...")
    df = pd.read_parquet(_FILE_BATCH_RESULTS_PARQET)
    logging.info(f"... read {df.shape}")

    logging.info(f"Writing {_FILE_BATCH_RESULTS_EXCEL}...")
    df.to_excel(_FILE_BATCH_RESULTS_EXCEL, index=False)
    logging.info(f"... done")
