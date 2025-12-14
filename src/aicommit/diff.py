"""Token-budget aware diff trimming.

The Ollama API will happily accept a 200kB diff and burn 30s of GPU on it
before timing out. Capping the prompt at a sensible size keeps latency
predictable and keeps small models from drifting off into noise.
"""
from __future__ import annotations

import re


# A reasonable rule of thumb for code-heavy English: ~3.5 chars/token for
# llama-family tokenizers. Round up to 4 to err on the side of *truncating
# more*, not less.
CHARS_PER_TOKEN = 4

_FILE_HEADER = re.compile(r"(?m)^(?=diff --git )")


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def truncate_diff(diff: str, max_tokens: int) -> tuple[str, bool]:
    """Trim a diff so its char-equivalent token count fits inside `max_tokens`.

    Truncation is at file boundaries — never mid-hunk — and appends a single
    `[... truncated N more files (M chars) ...]` marker so the LLM knows it
    didn't see everything.

    Returns (trimmed_diff, was_truncated).
    """
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    budget_chars = max_tokens * CHARS_PER_TOKEN
    if len(diff) <= budget_chars:
        return diff, False

    files = _FILE_HEADER.split(diff)
    # files[0] is anything before the first `diff --git` (usually empty
    # for diffs from `git diff --staged`); keep it verbatim.
    out: list[str] = []
    used = 0
    if files and files[0]:
        out.append(files[0])
        used = len(files[0])

    kept_files = 0
    for chunk in files[1:]:
        if used + len(chunk) > budget_chars and kept_files > 0:
            break
        out.append(chunk)
        used += len(chunk)
        kept_files += 1

    skipped_files = max(0, len(files) - 1 - kept_files)
    if skipped_files == 0 and len(diff) > used:
        # The first file alone exceeds the budget — hard-truncate it.
        single = files[1] if len(files) > 1 else diff
        out = [files[0] if files else ""]
        out.append(single[: budget_chars - len(out[0])])
        skipped_bytes = len(single) - (budget_chars - len(out[0]))
        out.append(f"\n[... truncated {skipped_bytes} chars within this file ...]\n")
        return "".join(out), True

    skipped_bytes = len(diff) - used
    out.append(f"\n[... truncated {skipped_files} more file(s), ~{skipped_bytes} chars ...]\n")
    return "".join(out), True


def summary_for_llm(diff: str) -> str:
    """Cheap shorthand for very large diffs: just list filenames + line counts."""
    files: list[str] = []
    for chunk in _FILE_HEADER.split(diff)[1:]:
        first = chunk.splitlines()[0]
        adds = chunk.count("\n+") - chunk.count("\n+++")
        dels = chunk.count("\n-") - chunk.count("\n---")
        files.append(f"{first}  (+{max(adds, 0)}/-{max(dels, 0)})")
    return "\n".join(files)
