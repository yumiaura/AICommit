"""Terminal UI: proposal rendering + the [Enter/e/r/q] interactive loop."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from typing import Callable

from aicommit import git


def _editor() -> list[str]:
    """Return the editor invocation (split on whitespace; fallback to `vi`)."""
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"
    return editor.split()


def edit_message(initial: str) -> str:
    """Open `initial` in $EDITOR and return the resulting (stripped) text."""
    fd, path = tempfile.mkstemp(suffix=".COMMIT_EDITMSG", prefix="aicommit-")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(initial)
            if not initial.endswith("\n"):
                f.write("\n")
        subprocess.run([*_editor(), path], check=False)
        with open(path, "r") as f:
            return f.read().strip()
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


def print_proposal(message: str) -> None:
    bar = "─" * 56
    print(bar)
    print("proposed commit message:")
    print(bar)
    print(message)
    print(bar)


def _prompt_choice() -> str:
    """Read a single keystroke-y choice. Empty input == Enter == commit."""
    print()
    print("[ Enter = commit · e = edit · r = regenerate · q = quit ]")
    while True:
        try:
            raw = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return "q"
        if raw == "":
            return "enter"
        if raw in {"e", "r", "q"}:
            return raw
        print(f"unknown choice {raw!r}; expected Enter / e / r / q")


def run_interactive(initial: str, *, regenerate: Callable[[], str]) -> int:
    """Drive the approve/edit/regen/quit loop. Returns a process exit code."""
    message = initial
    while True:
        print_proposal(message)
        choice = _prompt_choice()
        if choice == "enter":
            try:
                git.commit_with_message(message)
            except subprocess.CalledProcessError as e:
                sys.stderr.write(f"error: git commit failed (rc={e.returncode})\n")
                return e.returncode or 1
            return 0
        if choice == "e":
            new = edit_message(message)
            if not new.strip():
                sys.stderr.write("aborted: empty message\n")
                return 1
            message = new
            continue
        if choice == "r":
            try:
                message = regenerate()
            except Exception as e:  # surfaced from backend
                sys.stderr.write(f"error: {e}\n")
                return 2
            continue
        if choice == "q":
            sys.stderr.write("aborted by user\n")
            return 130
