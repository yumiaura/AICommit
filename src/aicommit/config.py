"""Hierarchical config: defaults → user → repo → env → CLI flags."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULTS: dict[str, dict[str, Any]] = {
    "llm": {
        "backend": "ollama",
        "model": "qwen2.5-coder:7b",
        "url": "http://localhost:11434",
        "temperature": 0.2,
        "max_tokens": 512,
    },
    "commit": {
        "style": "conventional",
        "max_subject_len": 72,
        "include_body": True,
    },
    "review": {
        "enabled": False,
    },
    "changelog": {
        "skip_conventional": True,
    },
}


# Maps env var → (section, key). Env always overrides files but not CLI flags.
ENV_OVERRIDES: dict[str, tuple[str, str]] = {
    "AICOMMIT_BACKEND": ("llm", "backend"),
    "AICOMMIT_MODEL": ("llm", "model"),
    "AICOMMIT_OLLAMA_URL": ("llm", "url"),
    "AICOMMIT_URL": ("llm", "url"),
    "AICOMMIT_TEMPERATURE": ("llm", "temperature"),
    "AICOMMIT_MAX_TOKENS": ("llm", "max_tokens"),
    "AICOMMIT_STYLE": ("commit", "style"),
    "AICOMMIT_INCLUDE_BODY": ("commit", "include_body"),
}


@dataclass
class Config:
    llm_backend: str
    llm_model: str
    llm_url: str
    llm_temperature: float
    llm_max_tokens: int
    commit_style: str
    commit_max_subject_len: int
    commit_include_body: bool
    review_enabled: bool
    changelog_skip_conventional: bool
    sources: list[str] = field(default_factory=list)


def user_config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "aicommit" / "config.toml"


def repo_config_path(start: Path | None = None) -> Path | None:
    """Walk up from `start` (cwd by default) looking for `.aicommit.toml`."""
    cur = (start or Path.cwd()).resolve()
    for parent in [cur, *cur.parents]:
        candidate = parent / ".aicommit.toml"
        if candidate.is_file():
            return candidate
        if (parent / ".git").exists():
            break
    return None


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _load_toml(path: Path | None) -> dict:
    if path is None or not path.is_file():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f)


def _coerce(val: str, default: Any) -> Any:
    if isinstance(default, bool):
        return val.lower() in {"1", "true", "yes", "y", "on"}
    if isinstance(default, int) and not isinstance(default, bool):
        return int(val)
    if isinstance(default, float):
        return float(val)
    return val


def load(cli_overrides: dict[str, dict[str, Any]] | None = None) -> Config:
    """Resolve a Config from defaults + files + env + CLI overrides.

    Precedence (lowest → highest):
      1. DEFAULTS
      2. ~/.config/aicommit/config.toml
      3. <repo>/.aicommit.toml
      4. AICOMMIT_* environment variables
      5. cli_overrides (dict shaped like DEFAULTS)
    """
    sources: list[str] = ["defaults"]
    merged: dict = {k: dict(v) for k, v in DEFAULTS.items()}

    user_path = user_config_path()
    user_cfg = _load_toml(user_path)
    if user_cfg:
        merged = _deep_merge(merged, user_cfg)
        sources.append(f"user({user_path})")

    repo_path = repo_config_path()
    repo_cfg = _load_toml(repo_path)
    if repo_cfg:
        merged = _deep_merge(merged, repo_cfg)
        sources.append(f"repo({repo_path})")

    env_changes: dict[str, dict[str, Any]] = {}
    for env_var, (section, key) in ENV_OVERRIDES.items():
        raw = os.environ.get(env_var)
        if raw is None:
            continue
        env_changes.setdefault(section, {})[key] = _coerce(raw, DEFAULTS[section][key])
    if env_changes:
        merged = _deep_merge(merged, env_changes)
        sources.append("env")

    if cli_overrides:
        merged = _deep_merge(merged, cli_overrides)
        sources.append("cli")

    return Config(
        llm_backend=str(merged["llm"]["backend"]),
        llm_model=str(merged["llm"]["model"]),
        llm_url=str(merged["llm"]["url"]),
        llm_temperature=float(merged["llm"]["temperature"]),
        llm_max_tokens=int(merged["llm"]["max_tokens"]),
        commit_style=str(merged["commit"]["style"]),
        commit_max_subject_len=int(merged["commit"]["max_subject_len"]),
        commit_include_body=bool(merged["commit"]["include_body"]),
        review_enabled=bool(merged["review"]["enabled"]),
        changelog_skip_conventional=bool(merged["changelog"]["skip_conventional"]),
        sources=sources,
    )
