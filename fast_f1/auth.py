"""Supply F1 account credentials to FastF1's sign-in.

Since October 2026 the F1 timing service needs a signed-in F1TV account.
FastF1 signs in by itself on the first download it makes, and keeps the
resulting token for about four days; it reads the account details from the
``F1_USERNAME`` and ``F1_PASSWORD`` environment variables. This module reads
them from a credentials file outside the repo and places them in this
process's environment only, so nothing is written to the shell or to disk.
"""

from __future__ import annotations

import logging
import os
import stat
from pathlib import Path

logger = logging.getLogger(__name__)

CREDENTIALS_FILE = Path.home() / ".config" / "f1_fantasy" / "f1_credentials"
CREDENTIAL_KEYS = ("F1_USERNAME", "F1_PASSWORD")


class F1CredentialsError(Exception):
    """Raised when the F1 credentials file is missing, exposed or incomplete.

    Messages name the file and the keys involved, never their values.
    """


def _fail(message: str) -> F1CredentialsError:
    logger.error(message)
    return F1CredentialsError(message)


def load_f1_credentials(path: Path | str | None = None) -> None:
    """Read the F1 account credentials into this process's environment.

    The file holds one ``KEY=value`` line per key in ``CREDENTIAL_KEYS``, with
    no quotes; blank lines and lines starting with ``#`` are ignored. It must
    be readable by its owner only.

    Args:
        path: the credentials file, defaulting to ``CREDENTIALS_FILE``.

    Raises:
        F1CredentialsError: if the file is missing, unreadable, accessible to
            other users, or lacks a value for either key.
    """
    path = Path(path) if path is not None else CREDENTIALS_FILE

    if not path.is_file():
        raise _fail(f"F1 credentials file not found: {path}")

    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise _fail(
            f"F1 credentials file {path} is accessible by other users "
            f"(mode {mode:o}); restrict it with: chmod 600 {path}"
        )

    try:
        text = path.read_text()
    except OSError as exc:
        raise _fail(f"Could not read F1 credentials file {path}: {type(exc).__name__}") from exc

    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator and key.strip() in CREDENTIAL_KEYS:
            values[key.strip()] = value.strip()

    missing = [key for key in CREDENTIAL_KEYS if not values.get(key)]
    if missing:
        raise _fail(f"F1 credentials file {path} has no value for: {', '.join(missing)}")

    os.environ.update(values)
    logger.info("Loaded F1 account credentials from %s", path)
