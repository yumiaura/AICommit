"""aicommit CLI entry point."""
from __future__ import annotations

import os
import sys

from aicommit import git
from aicommit.git import GitError
from aicommit.llm import OllamaError
from aicommit.llm.ollama import OllamaBackend
from aicommit.prompts import build_commit_prompt

DEFAULT_URL = os.environ.get("AICOMMIT_OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("AICOMMIT_MODEL", "qwen2.5-coder:7b")
DEFAULT_TEMPERATURE = float(os.environ.get("AICOMMIT_TEMPERATURE", "0.2"))


def _read_diff() -> str:
    if not sys.stdin.isatty():
        return sys.stdin.read()
    try:
        return git.staged_diff()
    except GitError as e:
        sys.stderr.write(f"error: {e}\n")
        sys.exit(1)


def main() -> int:
    diff = _read_diff()
    if not diff.strip():
        sys.stderr.write("no staged changes (and nothing on stdin)\n")
        return 1
    backend = OllamaBackend(
        url=DEFAULT_URL,
        model=DEFAULT_MODEL,
        temperature=DEFAULT_TEMPERATURE,
    )
    prompt = build_commit_prompt(diff)
    try:
        message = backend.generate(prompt)
    except OllamaError as e:
        sys.stderr.write(f"error: {e}\n")
        if "cannot reach" in str(e):
            sys.stderr.write("hint: is `ollama serve` running?\n")
        return 2
    if not message:
        sys.stderr.write("error: empty response from LLM\n")
        return 2
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
