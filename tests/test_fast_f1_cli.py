from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

from fast_f1 import cli
from fast_f1.api import SessionDataUnavailable


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
                "RankPosition": [99.99],
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

    def fake_generate_historical_metrics(season_years, output_path=None):
        called["historical"] = (tuple(season_years), output_path)
        return pd.DataFrame()

    monkeypatch.setattr(cli, "setup_fastf1_cache", fake_setup_fastf1_cache)
    monkeypatch.setattr(cli, "generate_historical_metrics", fake_generate_historical_metrics)

    cli.main()

    assert called["cache"][1] is True
    assert called["historical"][1] == str(tmp_path / "historical.xlsx")
    assert called["historical"][0][0] == 2023


def test_cli_historical_mode_restricted_to_one_season(monkeypatch, tmp_path):
    monkeypatch.setattr(
        sys, "argv",
        ["fast_f1", "--historical", "--season", "2026", "--output", str(tmp_path / "historical.xlsx")],
    )
    called = {}

    def fake_setup_fastf1_cache(cache_dir=None, interactive=True):
        return tmp_path, tmp_path / "local_cache"

    def fake_generate_historical_metrics(season_years, output_path=None):
        called["historical"] = (tuple(season_years), output_path)
        return pd.DataFrame()

    monkeypatch.setattr(cli, "setup_fastf1_cache", fake_setup_fastf1_cache)
    monkeypatch.setattr(cli, "generate_historical_metrics", fake_generate_historical_metrics)

    cli.main()

    # Only the requested season is walked; its race range comes from the schedule
    assert called["historical"][0] == (2026,)
    assert called["historical"][1] == str(tmp_path / "historical.xlsx")


def test_cli_historical_mode_does_not_prompt_for_a_season(monkeypatch, tmp_path):
    """--historical must not fall through to the single-race interactive prompt."""
    monkeypatch.setattr(sys, "argv", ["fast_f1", "--historical"])
    called = {}

    def fake_setup_fastf1_cache(cache_dir=None, interactive=True):
        return tmp_path, tmp_path / "local_cache"

    def fake_generate_historical_metrics(season_years, output_path=None):
        called["historical"] = tuple(season_years)
        return pd.DataFrame()

    def explode(*args, **kwargs):
        raise AssertionError("historical mode must not prompt for input")

    monkeypatch.setattr(cli, "setup_fastf1_cache", fake_setup_fastf1_cache)
    monkeypatch.setattr(cli, "generate_historical_metrics", fake_generate_historical_metrics)
    monkeypatch.setattr("builtins.input", explode)

    cli.main()

    assert called["historical"][0] == 2023
    assert len(called["historical"]) > 1


@pytest.mark.parametrize(
    "raised",
    [
        SessionDataUnavailable("No event found for season 2025, race 99"),
        ValueError("Could not load event schedule for season 1850"),
        RuntimeError("Required practice session data missing"),
    ],
    ids=["round outside the season", "season with no schedule", "metrics not buildable"],
)
def test_cli_single_race_mode_exits_cleanly_when_data_is_missing(monkeypatch, tmp_path, raised):
    """Missing FastF1 data must exit(1), not surface a traceback.

    A round the season does not have and a season the API cannot schedule both
    reach the CLI as something other than RuntimeError, so catching only that
    left the two most likely user errors — a mistyped season or race — printing
    a stack trace.
    """
    monkeypatch.setattr(sys, "argv", ["fast_f1", "--season", "2025", "--race", "99"])

    def fake_generate_single_race_prediction(season, race, output_path=None):
        raise raised

    monkeypatch.setattr(cli, "setup_fastf1_cache", lambda **kwargs: (tmp_path, tmp_path))
    monkeypatch.setattr(cli, "generate_single_race_prediction", fake_generate_single_race_prediction)

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    assert exit_info.value.code == 1
