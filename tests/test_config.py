from aicommit.config import load


def test_defaults_when_nothing_set(isolated_home):
    cfg = load()
    assert cfg.llm_backend == "ollama"
    assert cfg.llm_url == "http://localhost:11434"
    assert cfg.llm_temperature == 0.2
    assert cfg.sources == ["defaults"]


def test_user_config_overrides_defaults(isolated_home, tmp_path, monkeypatch):
    cfg_dir = isolated_home / ".config" / "aicommit"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "config.toml").write_text(
        '[llm]\nurl = "http://example.test:11434"\nmodel = "tiny"\n'
    )
    cfg = load()
    assert cfg.llm_url == "http://example.test:11434"
    assert cfg.llm_model == "tiny"
    assert any("user(" in s for s in cfg.sources)


def test_repo_config_overrides_user(isolated_home, tmp_path):
    cfg_dir = isolated_home / ".config" / "aicommit"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "config.toml").write_text('[llm]\nmodel = "user-model"\n')
    (tmp_path / ".aicommit.toml").write_text('[llm]\nmodel = "repo-model"\n')
    cfg = load()
    assert cfg.llm_model == "repo-model"


def test_env_overrides_files(isolated_home, monkeypatch):
    cfg_dir = isolated_home / ".config" / "aicommit"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "config.toml").write_text('[llm]\nmodel = "from-file"\n')
    monkeypatch.setenv("AICOMMIT_MODEL", "from-env")
    cfg = load()
    assert cfg.llm_model == "from-env"
    assert "env" in cfg.sources


def test_cli_overrides_env(isolated_home, monkeypatch):
    monkeypatch.setenv("AICOMMIT_MODEL", "from-env")
    cfg = load(cli_overrides={"llm": {"model": "from-cli"}})
    assert cfg.llm_model == "from-cli"
    assert cfg.sources[-1] == "cli"


def test_env_temperature_coerced_to_float(isolated_home, monkeypatch):
    monkeypatch.setenv("AICOMMIT_TEMPERATURE", "0.7")
    cfg = load()
    assert cfg.llm_temperature == 0.7


def test_env_include_body_coerced_to_bool(isolated_home, monkeypatch):
    monkeypatch.setenv("AICOMMIT_INCLUDE_BODY", "false")
    cfg = load()
    assert cfg.commit_include_body is False
