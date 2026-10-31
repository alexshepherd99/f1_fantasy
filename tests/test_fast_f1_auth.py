from __future__ import annotations

import os

import pytest

from fast_f1.auth import CREDENTIAL_KEYS, F1CredentialsError, load_f1_credentials

USERNAME = "test-user@example.invalid"
PASSWORD = "not-a-real-password"


@pytest.fixture(autouse=True)
def restore_credential_env(monkeypatch):
    """Undo whatever ``load_f1_credentials`` writes to the environment."""
    for key in CREDENTIAL_KEYS:
        monkeypatch.setenv(key, "")
    yield


def _write_credentials(path, text, mode=0o600):
    path.write_text(text)
    path.chmod(mode)
    return path


def test_loads_both_values_into_the_environment(tmp_path):
    path = _write_credentials(
        tmp_path / "creds",
        f"# F1 account\n\nF1_USERNAME={USERNAME}\nF1_PASSWORD={PASSWORD}\n",
    )

    load_f1_credentials(path)

    assert os.environ["F1_USERNAME"] == USERNAME
    assert os.environ["F1_PASSWORD"] == PASSWORD


def test_missing_file_fails_naming_the_path(tmp_path, caplog):
    path = tmp_path / "absent"

    with pytest.raises(F1CredentialsError, match="not found") as excinfo:
        load_f1_credentials(path)

    assert str(path) in str(excinfo.value)
    assert str(path) in caplog.text


@pytest.mark.parametrize("mode", [0o640, 0o604, 0o660])
def test_file_readable_by_others_fails(tmp_path, mode):
    path = _write_credentials(tmp_path / "creds", f"F1_USERNAME={USERNAME}\nF1_PASSWORD={PASSWORD}\n", mode)

    with pytest.raises(F1CredentialsError, match="chmod 600"):
        load_f1_credentials(path)

    assert os.environ["F1_PASSWORD"] == ""


def test_missing_value_fails_without_revealing_the_other(tmp_path, caplog):
    path = _write_credentials(tmp_path / "creds", f"F1_USERNAME={USERNAME}\nF1_PASSWORD=\n")

    with pytest.raises(F1CredentialsError, match="F1_PASSWORD") as excinfo:
        load_f1_credentials(path)

    assert USERNAME not in str(excinfo.value)
    assert USERNAME not in caplog.text
    assert os.environ["F1_USERNAME"] == ""


def test_success_log_does_not_contain_the_values(tmp_path, caplog):
    path = _write_credentials(tmp_path / "creds", f"F1_USERNAME={USERNAME}\nF1_PASSWORD={PASSWORD}\n")

    caplog.set_level("DEBUG")
    load_f1_credentials(path)

    assert USERNAME not in caplog.text
    assert PASSWORD not in caplog.text
