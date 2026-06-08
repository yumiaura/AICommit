from aicommit.commands.review import _parse_findings
from aicommit.commands.review import run as run_review
from aicommit.config import load


def test_parse_findings_no_issues():
    assert _parse_findings("NO_ISSUES") == []
    assert _parse_findings("") == []
    assert _parse_findings("\n\n") == []


def test_parse_findings_structured():
    raw = "[critical] foo.py:1 — bug\n[warning] foo.py:2 — risky\n[nit] foo.py:3 — style"
    out = _parse_findings(raw)
    assert out == [
        ("critical", "foo.py:1 — bug"),
        ("warning", "foo.py:2 — risky"),
        ("nit", "foo.py:3 — style"),
    ]


def test_parse_findings_unstructured_defaults_to_warning():
    out = _parse_findings("looks suspicious somewhere")
    assert out == [("warning", "looks suspicious somewhere")]


def test_run_review_only_clean(isolated_home, cassette, capsys):
    cassette("review_clean")
    cfg = load()
    rc = run_review("diff --git a/x b/x\n+a\n", cfg=cfg, review_only=True)
    assert rc == 0


def test_run_review_only_findings(isolated_home, cassette, capsys):
    cassette("review_findings")
    cfg = load()
    rc = run_review("diff --git a/x b/x\n+a\n", cfg=cfg, review_only=True)
    assert rc == 1  # findings present
    err = capsys.readouterr().err
    assert "3 finding" in err
    assert "critical" in err
