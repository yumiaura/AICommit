from aicommit.commands.changelog import (
    _build_body,
    _classify_conventional,
    _merge_unreleased,
    _render_deterministic,
)
from aicommit.config import load


def test_classify_conventional_basic():
    assert _classify_conventional("feat: add thing") == ("Added", "add thing")
    assert _classify_conventional("fix(scope): something") == ("Fixed", "something")
    assert _classify_conventional("perf: speed up") == ("Changed", "speed up")
    assert _classify_conventional("refactor: cleanup") == ("Changed", "cleanup")
    assert _classify_conventional("chore: bump deps")[0] is None
    assert _classify_conventional("docs: explain")[0] is None
    assert _classify_conventional("not-a-prefix: meh") == ("?", "not-a-prefix: meh")


def test_classify_conventional_breaking_change():
    bucket, cleaned = _classify_conventional("feat!: rewrite API")
    assert bucket == "Changed"
    assert "rewrite API" in cleaned


def test_render_deterministic_orders_buckets():
    groups = {
        "Added": ["a"],
        "Changed": ["c"],
        "Deprecated": [],
        "Removed": ["r"],
        "Fixed": ["f"],
        "Security": [],
    }
    rendered = _render_deterministic(groups)
    assert rendered.index("Added") < rendered.index("Changed") < rendered.index("Removed") < rendered.index("Fixed")
    assert "Deprecated" not in rendered
    assert "Security" not in rendered


def test_merge_unreleased_inserts_when_missing():
    existing = "# Changelog\n\n## [0.1.0]\n- initial\n"
    section = "## Unreleased\n\n### Added\n- new\n"
    merged = _merge_unreleased(existing, section)
    assert merged.index("## Unreleased") < merged.index("## [0.1.0]")
    assert "- new" in merged


def test_merge_unreleased_replaces_existing():
    existing = "# Changelog\n\n## Unreleased\n\n### Added\n- old\n\n## [0.1.0]\n- initial\n"
    section = "## Unreleased\n\n### Added\n- new\n"
    merged = _merge_unreleased(existing, section)
    assert "- old" not in merged
    assert "- new" in merged
    assert merged.count("## Unreleased") == 1


def test_build_body_skips_llm_when_all_conventional(isolated_home):
    cfg = load()
    commits = [
        ("abc1", "feat: add foo", ""),
        ("def2", "fix(bar): handle null", ""),
        ("ghi3", "chore: bump deps", ""),
    ]
    body = _build_body(commits, cfg)
    assert body is not None
    assert "add foo" in body
    assert "handle null" in body
    assert "bump deps" not in body  # chore is skipped


def test_build_body_uses_llm_when_unknown_present(isolated_home, cassette):
    cas = cassette("changelog_mixed")
    cfg = load()
    commits = [
        ("abc1", "feat: add foo", ""),
        ("def2", "refactored database stuff", ""),  # no conventional prefix
    ]
    body = _build_body(commits, cfg)
    assert body is not None
    assert "add foo" in body
    assert "database" in body.lower()
    assert cas.idx == 1
