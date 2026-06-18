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

FILE_HEADER = re.compile(r"(?m)^(?=diff --git )")


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def truncate_diff(diff: str, max_tokens: int) -> tuple[str, bool]:
    """Trim a diff so its char-equivalent token count fits inside `max_tokens`.

    Strategy: fit as many *whole files* as the budget allows. If even the
    first file is too big, hard-truncate it and emit a marker explaining
    how much was dropped. The trailing
    `[... truncated N more file(s) ...]` line is always present when the
    diff was modified, so the LLM knows it didn't see everything.

    Returns (trimmed_diff, was_truncated).
    """
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    budget_chars = max_tokens * CHARS_PER_TOKEN
    if len(diff) <= budget_chars:
        return diff, False

    files = FILE_HEADER.split(diff)
    preamble = files[0] if files else ""
    file_chunks = files[1:] if len(files) > 1 else []
    if not file_chunks:
        # No `diff --git` headers — treat the whole thing as one blob.
        trimmed = diff[:budget_chars]
        skipped = len(diff) - budget_chars
        return f"{trimmed}\n[... truncated {skipped} chars ...]\n", True

    out: list[str] = []
    used = 0
    if preamble:
        out.append(preamble)
        used = len(preamble)

    kept = 0
    for chunk in file_chunks:
        if used + len(chunk) > budget_chars:
            break
        out.append(chunk)
        used += len(chunk)
        kept += 1

    if kept > 0:
        skipped_files = len(file_chunks) - kept
        skipped_bytes = sum(len(c) for c in file_chunks[kept:])
        out.append(
            f"\n[... truncated {skipped_files} more file(s), ~{skipped_bytes} chars ...]\n"
        )
        return "".join(out), True

    # Budget too tight to fit even the first file — hard-truncate it.
    first = file_chunks[0]
    keep_chars = max(0, budget_chars - used)
    trimmed = first[:keep_chars]
    out.append(trimmed)
    skipped_in_file = len(first) - keep_chars
    extra_files = len(file_chunks) - 1
    extra_bytes = sum(len(c) for c in file_chunks[1:])
    msg = f"\n[... truncated {skipped_in_file} chars within this file"
    if extra_files > 0:
        msg += f" + {extra_files} more file(s), ~{extra_bytes} chars"
    msg += " ...]\n"
    out.append(msg)
    return "".join(out), True


def summary_for_llm(diff: str) -> str:
    """Cheap shorthand for very large diffs: just list filenames + line counts."""
    files: list[str] = []
    for chunk in FILE_HEADER.split(diff)[1:]:
        first = chunk.splitlines()[0]
        adds = chunk.count("\n+") - chunk.count("\n+++")
        dels = chunk.count("\n-") - chunk.count("\n---")
        files.append(f"{first}  (+{max(adds, 0)}/-{max(dels, 0)})")
    return "\n".join(files)
