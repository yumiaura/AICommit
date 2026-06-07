from aicommit.prompts import build_commit_prompt


def test_conventional_includes_type_list():
    p = build_commit_prompt("diff --git a/x b/x\n+a\n", style="conventional")
    assert "feat" in p and "fix" in p and "chore" in p


def test_plain_style_omits_conventional_types():
    p = build_commit_prompt("diff --git a/x b/x\n+a\n", style="plain")
    assert "feat/fix" not in p


def test_no_body_changes_rules():
    full = build_commit_prompt("diff --git a/x b/x\n+a\n", include_body=True)
    short = build_commit_prompt("diff --git a/x b/x\n+a\n", include_body=False)
    assert "DO NOT write a body" in short
    assert "DO NOT write a body" not in full


def test_prompt_includes_truncated_diff_for_huge_input():
    huge = "diff --git a/big b/big\n" + ("+x" * 30000)
    p = build_commit_prompt(huge, diff_token_budget=200)
    assert "truncated" in p
    assert len(p) < len(huge)
