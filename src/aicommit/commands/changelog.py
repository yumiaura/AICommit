"""`aicommit changelog <range>` — turn git log into a CHANGELOG entry."""
from __future__ import annotations

import sys

from aicommit import git
from aicommit.config import Config
from aicommit.llm import OllamaError, make_backend


CHANGELOG_PROMPT = """You are writing a CHANGELOG entry in the Keep a Changelog style.

Given the commits below, group them into these buckets (omit empty ones):
  ### Added
  ### Changed
  ### Deprecated
  ### Removed
  ### Fixed
  ### Security

Rules:
- One bullet per commit, written in past tense, starting with a verb.
- Strip Conventional Commit prefixes (feat:, fix(scope):, etc.) from the bullet text.
- Group semantically: feat → Added, fix → Fixed, perf/refactor → Changed,
  revert → Removed. Skip pure chore/docs/test/ci/style unless they user-facing.
- Do NOT include the section header `## Unreleased` — the caller prepends it.
- Output ONLY markdown. No preamble, no closing remarks.

Commits:
{commits}
"""


def _format_commits(commits: list[tuple[str, str, str]]) -> str:
    blocks = []
    for h, subject, body in commits:
        chunk = f"- {h} {subject}"
        if body.strip():
            indented = "\n  ".join(body.strip().splitlines())
            chunk += f"\n  {indented}"
        blocks.append(chunk)
    return "\n".join(blocks)


def run(rev_range: str, *, cfg: Config, out_path: str | None = None) -> int:
    try:
        commits = git.log_range(rev_range)
    except git.GitError as e:
        sys.stderr.write(f"error: {e}\n")
        return 1
    if not commits:
        sys.stderr.write(f"no commits in range {rev_range}\n")
        return 1

    backend = make_backend(
        cfg.llm_backend,
        url=cfg.llm_url,
        model=cfg.llm_model,
        temperature=cfg.llm_temperature,
        max_tokens=max(cfg.llm_max_tokens, 1024),
    )
    prompt = CHANGELOG_PROMPT.format(commits=_format_commits(commits))
    try:
        body = backend.generate(prompt, temperature=0.1).strip()
    except OllamaError as e:
        sys.stderr.write(f"error: {e}\n")
        return 2
    if not body:
        sys.stderr.write("error: empty response from LLM\n")
        return 2

    section = f"## Unreleased\n\n{body}\n"
    if out_path:
        _prepend_to_changelog(out_path, section)
        print(f"wrote Unreleased section to {out_path}", file=sys.stderr)
    else:
        print(section)
    return 0


def _prepend_to_changelog(path: str, section: str) -> None:
    """Place `section` near the top of `path`, replacing any existing Unreleased."""
    try:
        with open(path, "r") as f:
            existing = f.read()
    except FileNotFoundError:
        existing = "# Changelog\n\n"

    new = _merge_unreleased(existing, section)
    with open(path, "w") as f:
        f.write(new)


def _merge_unreleased(existing: str, section: str) -> str:
    """Replace an existing `## Unreleased` block, or insert after the H1 title."""
    lines = existing.splitlines(keepends=True)
    # find existing ## Unreleased and its end (next ## heading)
    start = None
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("## unreleased"):
            start = i
            break
    if start is not None:
        end = len(lines)
        for j in range(start + 1, len(lines)):
            if lines[j].startswith("## "):
                end = j
                break
        return "".join(lines[:start]) + section + ("\n" if not section.endswith("\n\n") else "") + "".join(lines[end:])

    # No existing Unreleased: insert after H1 title if present.
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            insert_at = i + 1
            # skip blank line after H1
            if insert_at < len(lines) and lines[insert_at].strip() == "":
                insert_at += 1
            break
    return "".join(lines[:insert_at]) + section + "\n" + "".join(lines[insert_at:])
