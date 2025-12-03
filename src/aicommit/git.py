"""Thin subprocess wrappers around `git`."""
from __future__ import annotations

import os
import subprocess
import tempfile


class GitError(RuntimeError):
    """`git` exited non-zero or could not be invoked."""


def run(*args: str, check: bool = True) -> str:
    """Run `git <args>` and return its stdout. Raises GitError if check=True and rc != 0."""
    try:
        proc = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as e:
        raise GitError("`git` not found on PATH") from e
    if check and proc.returncode != 0:
        raise GitError(proc.stderr.strip() or f"git {' '.join(args)} failed (rc={proc.returncode})")
    return proc.stdout


def staged_diff() -> str:
    return run("diff", "--staged")


def staged_stat() -> str:
    return run("diff", "--staged", "--stat")


def commit_with_message(message: str) -> None:
    """Invoke `git commit -F <tmpfile>` with the given message."""
    fd, path = tempfile.mkstemp(suffix=".COMMIT_EDITMSG")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(message)
        subprocess.run(["git", "commit", "-F", path], check=True)
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


def log_range(rev_range: str) -> list[tuple[str, str, str]]:
    """Return [(short_hash, subject, body)] for the given revision range."""
    output = run(
        "log",
        rev_range,
        "--pretty=format:%h%x00%s%x00%b%x1f",
    )
    commits: list[tuple[str, str, str]] = []
    for entry in output.split("\x1f"):
        entry = entry.strip("\n")
        if not entry:
            continue
        parts = entry.split("\x00")
        if len(parts) < 2:
            continue
        h, s, *rest = parts
        b = rest[0].strip() if rest else ""
        commits.append((h, s, b))
    return commits
