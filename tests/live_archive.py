"""A small archive for tests, cut from the real 2023 season so its values never change."""

import csv
from pathlib import Path

from import_data.import_history import _ARCHIVE_FILES, _DIR_ARCHIVE_INPUTS
from common import AssetType

SEASON = 2023


def write_archive(directory: Path, last_race: int, unscored: tuple[int, ...] = (),
                  price_changes: dict[tuple[int, str], str] | None = None) -> Path:
    """Write 2023's races 1 to `last_race` into `directory` as an archive.

    Args:
        directory: Where to write the two CSVs.
        last_race: The last race kept.
        unscored: Races whose points are blanked, as for a race not yet held.
        price_changes: New price text by (race, asset), the asset as the file names it
            (driver code, or constructor code), applied to drivers and constructors alike.

    Returns:
        `directory`.
    """
    price_changes = price_changes or {}
    for asset_type in (AssetType.DRIVER, AssetType.CONSTRUCTOR):
        name = _ARCHIVE_FILES[asset_type]
        with open(Path(_DIR_ARCHIVE_INPUTS) / name, newline="", encoding="utf-8") as handle:
            lines = list(csv.DictReader(handle))
        header = list(lines[0].keys())
        asset_column = "Driver" if asset_type == AssetType.DRIVER else "Constructor"
        kept = []
        for row in lines:
            if int(row["Season"]) != SEASON or int(row["Race"]) > last_race:
                continue
            race = int(row["Race"])
            if race in unscored:
                row["Points"] = ""
            row["Price"] = price_changes.get((race, row[asset_column]), row["Price"])
            kept.append(row)
        with open(directory / name, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
            writer.writeheader()
            writer.writerows(kept)
    return directory
