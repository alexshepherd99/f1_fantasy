from __future__ import annotations

import pandas as pd


def save_metrics_to_excel(df: pd.DataFrame, file_path: str, sheet_name: str = "PracticeRollingMetrics") -> None:
    """Persist a metrics dataframe to an Excel file."""
    df = df.sort_values(by=["Season", "Race", "AggregateRank"], ascending=[True, True, False])
    df.to_excel(file_path, sheet_name=sheet_name, index=False)
