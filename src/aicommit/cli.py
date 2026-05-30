"""aicommit CLI entry point."""
from __future__ import annotations

import argparse
import sys
from typing import Any

from aicommit import __version__
from aicommit import config as cfgmod
from aicommit import git, ui
from aicommit.git import GitError
from aicommit.llm import LLMError, OllamaError, make_backend
from aicommit.prompts import build_commit_prompt


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aicommit",
        description="AI commit messages from your local LLM (Ollama or llama-cpp).",
    )
    p.add_argument("--version", action="version", version=f"aicommit {__version__}")

    # LLM overrides
    p.add_argument("--backend", choices=["ollama", "llama-cpp"], help="LLM backend")
    p.add_argument("--model", help="model name (or path for llama-cpp)")
    p.add_argument("--url", help="Ollama base URL (e.g. http://10.0.0.5:11434)")
    p.add_argument("--temperature", type=float, help="sampling temperature")
    p.add_argument("--max-tokens", type=int, dest="max_tokens", help="max tokens in response")

    # Commit shape
    p.add_argument("--style", choices=["conventional", "plain"], help="commit message style")
    p.add_argument(
        "--no-body",
        action="store_true",
        help="subject line only (no body)",
    )

    # Behaviour
    p.add_argument(
        "--print",
        action="store_true",
        dest="print_only",
        help="print the message and exit (skip the interactive loop)",
    )
    p.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="commit immediately without prompting",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help="print the resolved config sources to stderr",
    )
    return p


def _cli_overrides(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    overrides: dict[str, dict[str, Any]] = {}
    llm: dict[str, Any] = {}
    if args.backend:
        llm["backend"] = args.backend
    if args.model:
        llm["model"] = args.model
    if args.url:
        llm["url"] = args.url
    if args.temperature is not None:
        llm["temperature"] = args.temperature
    if args.max_tokens is not None:
        llm["max_tokens"] = args.max_tokens
    if llm:
        overrides["llm"] = llm

    commit: dict[str, Any] = {}
    if args.style:
        commit["style"] = args.style
    if args.no_body:
        commit["include_body"] = False
    if commit:
        overrides["commit"] = commit
    return overrides


def _read_diff() -> tuple[str, bool]:
    if not sys.stdin.isatty():
        return sys.stdin.read(), True
    try:
        return git.staged_diff(), False
    except GitError as e:
        sys.stderr.write(f"error: {e}\n")
        sys.exit(1)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    cfg = cfgmod.load(_cli_overrides(args))
    if args.debug:
        sys.stderr.write(f"[debug] config sources: {' < '.join(cfg.sources)}\n")
        sys.stderr.write(f"[debug] backend={cfg.llm_backend} url={cfg.llm_url} model={cfg.llm_model}\n")

    diff, from_stdin = _read_diff()
    if not diff.strip():
        sys.stderr.write("no staged changes (and nothing on stdin)\n")
        return 1

    try:
        backend = make_backend(
            cfg.llm_backend,
            url=cfg.llm_url,
            model=cfg.llm_model,
            temperature=cfg.llm_temperature,
            max_tokens=cfg.llm_max_tokens,
        )
    except LLMError as e:
        sys.stderr.write(f"error: {e}\n")
        return 2

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

    if from_stdin or args.print_only:
        print(message)
        return 0

    if args.yes:
        try:
            git.commit_with_message(message)
        except Exception as e:
            sys.stderr.write(f"error: git commit failed: {e}\n")
            return 1
        return 0

    try:
        ui.print_diff_stat(git.staged_stat())
    except GitError:
        pass

    state = {"temperature": cfg.llm_temperature}

    def _regenerate() -> str:
        state["temperature"] = min(1.0, state["temperature"] + 0.15)
        return _ask(temperature=state["temperature"])

    return ui.run_interactive(message, regenerate=_regenerate)


def _emit_ollama_error(e: OllamaError) -> int:
    sys.stderr.write(f"error: {e}\n")
    if "cannot reach" in str(e):
        sys.stderr.write("hint: is `ollama serve` running and reachable?\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
