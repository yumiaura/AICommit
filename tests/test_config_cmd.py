"""Tests for the `aicommit config` subcommand."""
from __future__ import annotations

import sys
import tomllib
from types import SimpleNamespace

from aicommit.commands.config import DEFAULT_TEMPLATE, run
from aicommit.config import load, user_config_path


def _force_tty(monkeypatch, value: bool) -> None:
    monkeypatch.setattr(sys.stdout, "isatty", lambda: value)


def test_creates_file_with_valid_toml(isolated_home, monkeypatch):
    _force_tty(monkeypatch, True)
    monkeypatch.setattr(
        "aicommit.commands.config.subprocess.run",
        lambda *a, **k: SimpleNamespace(returncode=0),
    )

    rc = run()

    assert rc == 0
    path = user_config_path()
    assert path.is_file()
    parsed = tomllib.loads(path.read_text())
    assert parsed["llm"]["backend"] == "ollama"
    assert parsed["commit"]["style"] == "conventional"


def test_template_matches_defaults(isolated_home, monkeypatch):
    """If a user re-creates the config, loaded values equal the bare defaults."""
    _force_tty(monkeypatch, True)
    monkeypatch.setattr(
        "aicommit.commands.config.subprocess.run",
        lambda *a, **k: SimpleNamespace(returncode=0),
    )
    run()

    cfg = load()
    assert cfg.llm_backend == "ollama"
    assert cfg.llm_url == "http://localhost:11434"
    assert cfg.commit_style == "conventional"
    assert cfg.commit_include_body is True


def test_does_not_clobber_existing(isolated_home, monkeypatch):
    path = user_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('[llm]\nurl = "http://existing.test:11434"\n')

    _force_tty(monkeypatch, True)
    monkeypatch.setattr(
        "aicommit.commands.config.subprocess.run",
        lambda *a, **k: SimpleNamespace(returncode=0),
    )

    rc = run()

    assert rc == 0
    assert "existing.test" in path.read_text()


def test_non_tty_prints_path_and_skips_editor(isolated_home, monkeypatch, capsys):
    _force_tty(monkeypatch, False)

    def _explode(*a, **k):  # editor must not be invoked
        raise AssertionError("editor should not run in non-tty mode")

    monkeypatch.setattr("aicommit.commands.config.subprocess.run", _explode)
    rc = run()

    assert rc == 0
    out = capsys.readouterr().out.strip()
    assert out.endswith("config.toml")


def test_editor_not_found_returns_127(isolated_home, monkeypatch):
    _force_tty(monkeypatch, True)

    def _raise(*a, **k):
        raise FileNotFoundError("no such editor")

    monkeypatch.setattr("aicommit.commands.config.subprocess.run", _raise)
    monkeypatch.setenv("EDITOR", "definitely-not-an-editor")
    rc = run()

    assert rc == 127
    # File still got created
    assert user_config_path().is_file()


def test_template_is_well_formed_toml():
    parsed = tomllib.loads(DEFAULT_TEMPLATE)
    assert set(parsed) >= {"llm", "commit", "review", "changelog"}
