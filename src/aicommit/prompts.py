"""Prompt templates used by aicommit subcommands."""
from __future__ import annotations

COMMIT_SYSTEM = (
    "You are a senior engineer writing ONE Conventional Commit message for the staged diff below."
)

COMMIT_RULES_CONVENTIONAL = """Rules:
- Subject line: imperative mood, <=72 chars, lowercase type
  (feat/fix/chore/docs/refactor/test/build/ci/perf/style/revert),
  optional (scope), no trailing period.
- Blank line, then an optional body explaining the *why*, wrapped at ~72 cols.
- Output ONLY the commit message. No markdown fences, no preamble, no commentary."""

COMMIT_RULES_PLAIN = """Rules:
- Subject line: imperative mood, <=72 chars, no type prefix, no trailing period.
- Blank line, then an optional body explaining the *why*, wrapped at ~72 cols.
- Output ONLY the commit message. No markdown fences, no preamble, no commentary."""


def build_commit_prompt(
    diff: str,
    *,
    style: str = "conventional",
    include_body: bool = True,
) -> str:
    rules = COMMIT_RULES_CONVENTIONAL if style == "conventional" else COMMIT_RULES_PLAIN
    if not include_body:
        rules = rules.replace(
            "- Blank line, then an optional body explaining the *why*, wrapped at ~72 cols.\n",
            "- Subject line only — DO NOT write a body.\n",
        )
    return f"{COMMIT_SYSTEM}\n\n{rules}\n\nDiff:\n---\n{diff}\n---\n"
