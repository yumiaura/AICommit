"""aicommit CLI entry point."""
from __future__ import annotations

import os
import sys

from aicommit import git, ui
from aicommit.git import GitError
from aicommit.llm import OllamaError
from aicommit.llm.ollama import OllamaBackend
from aicommit.prompts import build_commit_prompt

DEFAULT_URL = os.environ.get("AICOMMIT_OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("AICOMMIT_MODEL", "qwen2.5-coder:7b")
DEFAULT_TEMPERATURE = float(os.environ.get("AICOMMIT_TEMPERATURE", "0.2"))


def _read_diff() -> tuple[str, bool]:
    """Return (diff_text, came_from_stdin)."""
    if not sys.stdin.isatty():
        return sys.stdin.read(), True
    try:
        return git.staged_diff(), False
    except GitError as e:
        sys.stderr.write(f"error: {e}\n")
        sys.exit(1)


def main() -> int:
    diff, from_stdin = _read_diff()
    if not diff.strip():
        sys.stderr.write("no staged changes (and nothing on stdin)\n")
        return 1

    backend = OllamaBackend(
        url=DEFAULT_URL,
        model=DEFAULT_MODEL,
        temperature=DEFAULT_TEMPERATURE,
    )
    prompt = build_commit_prompt(diff)

    def _ask(temperature: float | None = None) -> str:
        try:
            return backend.generate(prompt, temperature=temperature)
        except OllamaError as e:
            raise SystemExit(_emit_ollama_error(e))

    message = _ask()
    if not message:
        sys.stderr.write("error: empty response from LLM\n")
        return 2

    if from_stdin:
        print(message)
        return 0

    try:
        ui.print_diff_stat(git.staged_stat())
    except GitError:
        pass  # already showed; non-fatal

    # Interactive: each `r` bumps temperature slightly so re-rolls differ.
    state = {"temperature": DEFAULT_TEMPERATURE}

    def _regenerate() -> str:
        state["temperature"] = min(1.0, state["temperature"] + 0.15)
        return _ask(temperature=state["temperature"])

    return ui.run_interactive(message, regenerate=_regenerate)


def _emit_ollama_error(e: OllamaError) -> int:
    sys.stderr.write(f"error: {e}\n")
    if "cannot reach" in str(e):
        sys.stderr.write("hint: is `ollama serve` running?\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
