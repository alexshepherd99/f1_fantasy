import pytest


@pytest.fixture(autouse=True)
def isolate_fastf1_cache_config(monkeypatch, tmp_path):
    """Keep FastF1 cache config writes inside a temporary test path."""
    config_file = tmp_path / ".fastf1_cache_dir"
    monkeypatch.setattr("fast_f1.cache.CACHE_LOCATION_CONFIG_FILE", config_file)
    yield
