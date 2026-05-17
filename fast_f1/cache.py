from __future__ import annotations

import logging
from pathlib import Path

import fastf1

DEFAULT_FASTF1_CACHEDIR = Path("/mnt/chromeos/removable/sd256/linux/fastf1_cache")
DEFAULT_FALLBACK_CACHEDIR = Path("~/fastf1_cache")
DEFAULT_LOCAL_CACHE_SUBDIR = "local_cache"


def get_default_cache_directories() -> list[Path]:
    """Return the supported default FastF1 cache directory options."""
    return [DEFAULT_FASTF1_CACHEDIR.expanduser(), DEFAULT_FALLBACK_CACHEDIR.expanduser()]


def ensure_directory(path: Path) -> Path:
    """Create a directory if it does not exist."""
    path = path.expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def select_cache_directory(
    cache_dir: Path | str | None = None,
    *,
    interactive: bool = True,
) -> Path:
    """Select the FastF1 cache directory.

    If ``cache_dir`` is provided, it is returned after expansion.
    If ``interactive`` is True and no cache_dir is provided, the user is prompted.
    """
    if cache_dir is not None:
        return Path(cache_dir).expanduser()

    default_dirs = get_default_cache_directories()
    if not interactive:
        return default_dirs[0]

    print("Choose a FastF1 cache directory:")
    for index, default_dir in enumerate(default_dirs, start=1):
        print(f"  {index}) {default_dir}")
    print(f"  {len(default_dirs) + 1}) Custom path")

    choice = input(f"Enter choice [1-{len(default_dirs) + 1}]: ").strip()
    if not choice:
        raise ValueError("No cache directory selection provided")

    try:
        selection = int(choice)
    except ValueError as exc:
        raise ValueError("Cache directory selection must be a number") from exc

    if 1 <= selection <= len(default_dirs):
        return default_dirs[selection - 1]

    if selection == len(default_dirs) + 1:
        custom_path = input("Enter custom cache directory path: ").strip()
        if not custom_path:
            raise ValueError("Custom cache directory path cannot be empty")
        return Path(custom_path).expanduser()

    raise ValueError("Cache directory selection is out of range")


def setup_fastf1_cache(
    cache_dir: Path | str | None = None,
    local_cache_subdir: str = DEFAULT_LOCAL_CACHE_SUBDIR,
    interactive: bool = True,
) -> tuple[Path, Path]:
    """Enable FastF1 cache and create a module-level local cache directory."""
    selected_cache_dir = select_cache_directory(cache_dir, interactive=interactive)

    try:
        cache_path = ensure_directory(selected_cache_dir)
    except OSError as exc:
        raise RuntimeError(f"Failed to create FastF1 cache directory: {selected_cache_dir}") from exc

    fastf1.Cache.enable_cache(str(cache_path))
    logging.info("FastF1 cache enabled at: %s", cache_path)

    try:
        local_cache_path = ensure_directory(cache_path / local_cache_subdir)
    except OSError as exc:
        raise RuntimeError(
            f"Failed to create FastF1 local cache subdirectory: {cache_path / local_cache_subdir}"
        ) from exc

    logging.info("FastF1 local cache enabled at: %s", local_cache_path)
    return cache_path, local_cache_path
