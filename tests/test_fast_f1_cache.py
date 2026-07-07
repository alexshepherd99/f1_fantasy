from pathlib import Path

import fastf1
import pytest

from fast_f1.cache import (
    CACHE_LOCATION_CONFIG_FILE,
    DEFAULT_FASTF1_CACHEDIR,
    DEFAULT_FALLBACK_CACHEDIR,
    DEFAULT_LOCAL_CACHE_SUBDIR,
    get_default_cache_directories,
    select_cache_directory,
    setup_fastf1_cache,
)


def test_get_default_cache_directories():
    directories = get_default_cache_directories()

    assert len(directories) == 2
    assert directories[0] == DEFAULT_FASTF1_CACHEDIR.expanduser()
    assert directories[1] == DEFAULT_FALLBACK_CACHEDIR.expanduser()


def test_select_cache_directory_custom_path(monkeypatch, tmp_path):
    monkeypatch.setattr("builtins.input", lambda prompt="": "3" if "Enter choice" in prompt else str(tmp_path / "fastf1_custom"))

    selected = select_cache_directory(interactive=True)

    assert selected == tmp_path / "fastf1_custom"


def test_select_cache_directory_default_choice(monkeypatch, tmp_path):
    monkeypatch.setattr("builtins.input", lambda prompt="": "1")

    selected = select_cache_directory(interactive=True)

    assert selected == DEFAULT_FASTF1_CACHEDIR.expanduser()


def test_select_cache_directory_invalid_selection(monkeypatch, tmp_path):
    monkeypatch.setattr("builtins.input", lambda prompt="": "99")

    with pytest.raises(ValueError, match="out of range"):
        select_cache_directory(interactive=True)


def test_select_cache_directory_uses_persisted_path(monkeypatch, tmp_path):
    persisted_path = tmp_path / "persisted_cache"
    persisted_path.mkdir()
    config_file = tmp_path / ".fastf1_cache_dir"
    config_file.write_text(str(persisted_path))
    monkeypatch.setattr("fast_f1.cache.CACHE_LOCATION_CONFIG_FILE", config_file)

    selected = select_cache_directory(interactive=False)

    assert selected == persisted_path


def test_setup_fastf1_cache_persists_user_specified_directory(monkeypatch, tmp_path):
    monkeypatch.setattr("fast_f1.cache.fastf1.Cache.enable_cache", lambda _: None)
    config_file = tmp_path / ".fastf1_cache_dir"
    monkeypatch.setattr("fast_f1.cache.CACHE_LOCATION_CONFIG_FILE", config_file)

    cache_path, local_cache_path = setup_fastf1_cache(cache_dir=tmp_path, interactive=False)

    assert cache_path == tmp_path
    assert local_cache_path == tmp_path / DEFAULT_LOCAL_CACHE_SUBDIR
    assert config_file.read_text().strip() == str(tmp_path)


def test_setup_fastf1_cache_creates_directories(monkeypatch, tmp_path):
    monkeypatch.setattr("fast_f1.cache.fastf1.Cache.enable_cache", lambda _: None)
    cache_path, local_cache_path = setup_fastf1_cache(cache_dir=tmp_path, interactive=False)

    assert cache_path == tmp_path
    assert local_cache_path == tmp_path / DEFAULT_LOCAL_CACHE_SUBDIR
    assert cache_path.exists()
    assert local_cache_path.exists()
    assert local_cache_path.is_dir()


def test_setup_fastf1_cache_raises_for_invalid_directory(monkeypatch, tmp_path):
    monkeypatch.setattr("fast_f1.cache.fastf1.Cache.enable_cache", lambda _: None)
    invalid_dir = tmp_path / "nonexistent" / "restricted"

    monkeypatch.setattr(Path, "mkdir", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("permission denied")))

    with pytest.raises(RuntimeError, match="Failed to create FastF1 cache directory"):
        setup_fastf1_cache(cache_dir=invalid_dir, interactive=False)
