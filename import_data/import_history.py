import pandas as pd
from enum import Enum, auto

_FILE_ARCHIVE_INPUTS = "data/f1_fantasy_archive.xlsx"


class DataSheetType(Enum):
    POINTS = "Points"
    PRICES = "Price"


def convert_data_sheet(df_input: pd.DataFrame, season: int, id_cols: list, sheet_type: DataSheetType) -> pd.DataFrame:
    df_melted = df_input.melt(
        id_vars=id_cols,
        var_name="Race",
        value_name=sheet_type.value,
    )

    df_melted["Season"] = season
    df_melted["Race"] = df_melted["Race"].astype(int)

    return df_melted
