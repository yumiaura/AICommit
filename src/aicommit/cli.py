"""aicommit CLI entry point."""
from __future__ import annotations

import sys

from aicommit import config as cfgmod
from aicommit import git, ui
from aicommit.git import GitError
from aicommit.llm import OllamaError, make_backend
from aicommit.prompts import build_commit_prompt


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
    cfg = cfgmod.load()
    diff, from_stdin = _read_diff()
    if not diff.strip():
        sys.stderr.write("no staged changes (and nothing on stdin)\n")
        return 1

    backend = make_backend(
        cfg.llm_backend,
        url=cfg.llm_url,
        model=cfg.llm_model,
        temperature=cfg.llm_temperature,
        max_tokens=cfg.llm_max_tokens,
    )
    prompt = build_commit_prompt(
        diff,
        style=cfg.commit_style,
        include_body=cfg.commit_include_body,
    )

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
        pass  # non-fatal — the stat is just decoration

    state = {"temperature": cfg.llm_temperature}

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
