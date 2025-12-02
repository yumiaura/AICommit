"""v0.1.0 MVP: read a staged diff, ask Ollama, print the suggested commit message."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

OLLAMA_URL = os.environ.get("AICOMMIT_OLLAMA_URL", "http://localhost:11434") + "/api/generate"
DEFAULT_MODEL = os.environ.get("AICOMMIT_MODEL", "qwen2.5-coder:7b")
TEMPERATURE = float(os.environ.get("AICOMMIT_TEMPERATURE", "0.2"))

PROMPT_TEMPLATE = """You are a senior engineer writing ONE Conventional Commit message for the staged diff below.

Rules:
- Subject line: imperative mood, <=72 chars, lowercase type (feat/fix/chore/docs/refactor/test/build/ci/perf/style/revert), optional (scope), no trailing period.
- Blank line, then an optional body explaining the *why*, wrapped at ~72 cols.
- Output ONLY the commit message. No markdown fences, no preamble, no commentary.

Diff:
---
{diff}
---
"""


def _read_diff() -> str:
    """Return the diff from stdin if piped, otherwise from `git diff --staged`."""
    if not sys.stdin.isatty():
        return sys.stdin.read()
    try:
        result = subprocess.run(
            ["git", "diff", "--staged"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        sys.stderr.write("error: `git` not found on PATH\n")
        sys.exit(127)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        sys.exit(result.returncode)
    return result.stdout


def _ask_ollama(diff: str, model: str = DEFAULT_MODEL) -> str:
    payload = {
        "model": model,
        "prompt": PROMPT_TEMPLATE.format(diff=diff),
        "stream": False,
        "options": {"temperature": TEMPERATURE},
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        sys.stderr.write(f"error: Ollama HTTP {e.code}: {detail}\n")
        sys.exit(2)
    except urllib.error.URLError as e:
        sys.stderr.write(
            f"error: cannot reach Ollama at {OLLAMA_URL}: {e.reason}\n"
            "hint: is `ollama serve` running?\n"
        )
        sys.exit(2)
    return body.get("response", "").strip()


def main() -> int:
    diff = _read_diff()
    if not diff.strip():
        sys.stderr.write("no staged changes (and nothing on stdin)\n")
        return 1
    message = _ask_ollama(diff)
    if not message:
        sys.stderr.write("error: empty response from LLM\n")
        return 2
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
