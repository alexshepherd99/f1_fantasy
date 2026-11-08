import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def isolate_fastf1_cache_config(monkeypatch, tmp_path):
    """Keep FastF1 cache config writes inside a temporary test path."""
    config_file = tmp_path / ".fastf1_cache_dir"
    monkeypatch.setattr("fast_f1.cache.CACHE_LOCATION_CONFIG_FILE", config_file)
    yield


@pytest.fixture(autouse=True)
def isolate_f1_credentials(monkeypatch, tmp_path_factory):
    """Keep tests off the real F1 credentials file and environment.

    Points the loader at a dummy file in a tmp dir of its own, so tests that
    assert on the contents of ``tmp_path`` never see it, and sets the variables
    it writes so that monkeypatch restores them afterwards.
    """
    credentials_file = tmp_path_factory.mktemp("f1_credentials") / "f1_credentials"
    credentials_file.write_text("F1_USERNAME=test-user\nF1_PASSWORD=test-password\n")
    credentials_file.chmod(0o600)
    monkeypatch.setattr("fast_f1.auth.CREDENTIALS_FILE", credentials_file)
    for key in ("F1_USERNAME", "F1_PASSWORD"):
        monkeypatch.setenv(key, "")
    yield


@pytest.fixture(scope="session")
def empty_odds_file(tmp_path_factory):
    """A betting odds workbook with the real columns and no rows."""
    path = tmp_path_factory.mktemp("betting_odds") / "empty_betting_odds.xlsx"
    pd.DataFrame(columns=["Driver", "Constructor", "Season", "Race", "Odds"]).to_excel(path, index=False)
    return path


@pytest.fixture(autouse=True)
def isolate_betting_odds(monkeypatch, empty_odds_file):
    """Keep `fast_f1` metric tests off the real betting odds spreadsheet.

    `build_race_metrics` reads the odds file for whatever season and race it is
    given, so a test using real codes for a covered race would silently score
    them from live data. Pointing its default at an empty file gives every race
    no odds; tests that want odds pass `odds_file` themselves.
    """
    monkeypatch.setattr("fast_f1.output.ODDS_FILE", empty_odds_file)
    yield
