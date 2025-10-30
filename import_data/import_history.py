import pandas as pd

_FILE_ARCHIVE_INPUTS = "data/f1_fantasy_archive.xlsx"


def convert_data_sheet(df_input: pd.DataFrame, season: int, id_cols: list, val_col: str) -> pd.DataFrame:
    df_melted = df_input.melt(
        id_vars=id_cols,
        var_name="Race",
        value_name=val_col,
    )
    df_melted["Season"] = season
    return df_melted
