from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from fast_f1 import cli


def test_cli_single_race_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["fast_f1", "--season", "2025", "--race", "2", "--output", str(tmp_path / "race.xlsx")])
    called = {}

    def fake_setup_fastf1_cache(cache_dir=None, interactive=True):
        called["cache"] = (cache_dir, interactive)
        return tmp_path, tmp_path / "local_cache"

    def fake_generate_single_race_prediction(season, race, output_path=None):
        called["single"] = (season, race, output_path)
        return Path(output_path), pd.DataFrame(
            {
                "Season": [season],
                "Race": [race],
                "Driver": ["TEST"],
                "Constructor": ["TEST"],
                "AggregateRank": [1.0],
                "FinalPosition": [99.99],
            }
        )

    monkeypatch.setattr(cli, "setup_fastf1_cache", fake_setup_fastf1_cache)
    monkeypatch.setattr(cli, "generate_single_race_prediction", fake_generate_single_race_prediction)

    cli.main()

    assert called["cache"][1] is True
    assert called["single"] == (2025, 2, str(tmp_path / "race.xlsx"))


def test_cli_historical_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["fast_f1", "--historical", "--output", str(tmp_path / "historical.xlsx")])
    called = {}

    def fake_setup_fastf1_cache(cache_dir=None, interactive=True):
        called["cache"] = (cache_dir, interactive)
        return tmp_path, tmp_path / "local_cache"

    def fake_generate_historical_metrics(season_years, race_numbers, output_path=None):
        called["historical"] = (tuple(season_years), tuple(race_numbers), output_path)
        return pd.DataFrame()

    monkeypatch.setattr(cli, "setup_fastf1_cache", fake_setup_fastf1_cache)
    monkeypatch.setattr(cli, "generate_historical_metrics", fake_generate_historical_metrics)

    cli.main()

    assert called["cache"][1] is True
    assert called["historical"][2] == str(tmp_path / "historical.xlsx")
    assert called["historical"][0][0] == 2023
