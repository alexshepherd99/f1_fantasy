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


@pytest.fixture(autouse=True)
def isolate_betting_odds(monkeypatch):
    """Keep `fast_f1` metric tests off the real betting odds spreadsheet.

    `build_race_metrics` reads `data/f1_betting_odds.xlsx` for whatever season
    and race it is given, so a test using real codes for a covered race would
    silently score them from live data. Tests that want odds re-patch
    `fast_f1.output.load_odds` themselves, which overrides this.

    Patching the loader rather than `import_data.odds._FILE_BETTING_ODDS` is
    deliberate: that constant is bound as `load_odds`'s default argument at
    definition time, so rebinding it later has no effect.
    """
    monkeypatch.setattr("fast_f1.output.load_odds", lambda *args, **kwargs: {})
    yield
