import pandas as pd
from enum import Enum
from typing import NamedTuple

_FILE_ARCHIVE_INPUTS = "../data/f1_fantasy_archive.xlsx"


class DataSheetType(Enum):
    POINTS = "Points"
    PRICE = "Price"


class ArchiveSheetInfo(NamedTuple):
    season: int
    sheet_name: str
    id_cols: list
    sheet_type: DataSheetType


_ARCHIVE_SHEETS = [
    ArchiveSheetInfo(2023, "2023 Drivers Points", ["Team", "Driver"], DataSheetType.POINTS),
    ArchiveSheetInfo(2023, "2023 Constructors Points", ["Team"], DataSheetType.POINTS),
    ArchiveSheetInfo(2023, "2023 Drivers Price", ["Driver"], DataSheetType.PRICE),
    ArchiveSheetInfo(2023, "2023 Constructors Price", ["Team"], DataSheetType.PRICE),
]


def convert_data_sheet(df_input: pd.DataFrame, season: int, id_cols: list, sheet_type: DataSheetType) -> pd.DataFrame:
    df_melted = df_input.melt(
        id_vars=id_cols,
        var_name="Race",
        value_name=sheet_type.value,
    )

    df_melted["Season"] = season
    df_melted["Race"] = df_melted["Race"].astype(int)

    return df_melted


def load_archive_sheet(sheet_info: ArchiveSheetInfo) -> pd.DataFrame:
    df_input = pd.read_excel(_FILE_ARCHIVE_INPUTS, sheet_name=sheet_info.sheet_name)

    df_converted = convert_data_sheet(
        df_input=df_input,
        season=sheet_info.season,
        id_cols=sheet_info.id_cols,
        sheet_type=sheet_info.sheet_type,
    )

    return df_converted


def load_all_archive_data() -> pd.DataFrame:
    df_list = []
    for sheet_info in _ARCHIVE_SHEETS:
        df_sheet = load_archive_sheet(sheet_info)
        df_list.append(df_sheet)

    df_all = pd.concat(df_list, ignore_index=True)
    return df_all
