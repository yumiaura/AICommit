"""Shared pytest fixtures — small VCR-style helper for Ollama HTTP calls."""
from __future__ import annotations

import io
import json
import sys
import urllib.request
from pathlib import Path

import pytest

# Make src/ importable without installing
SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

FIXTURES = Path(__file__).parent / "fixtures" / "transcripts"


class FakeResponse:
    """File-like object that mimics urllib.request.urlopen's return value."""

    def __init__(self, body: bytes) -> None:
        self.buf = io.BytesIO(body)

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self.buf.getvalue()

    def __iter__(self):  # NDJSON streaming
        yield from self.buf.getvalue().splitlines(keepends=True)


class Cassette:
    """Replay-only cassette: yields the next recorded response on each request."""

    def __init__(self, name: str) -> None:
        self.name = name
        path = FIXTURES / f"{name}.json"
        if not path.is_file():
            raise FileNotFoundError(f"transcript {path} not found")
        self.recorded = json.loads(path.read_text())
        self.idx = 0
        self.requests: list[dict] = []

    def next_response(self, request_payload: dict) -> bytes:
        if self.idx >= len(self.recorded):
            raise AssertionError(
                f"cassette {self.name!r} exhausted at request #{self.idx + 1}"
            )
        item = self.recorded[self.idx]
        self.idx += 1
        self.requests.append(request_payload)

        if request_payload.get("stream"):
            # Emit each chunk as a separate NDJSON line.
            response_text = item["response"]
            chunks = []
            mid = len(response_text) // 2 or len(response_text)
            for piece in (response_text[:mid], response_text[mid:]):
                if piece:
                    chunks.append(json.dumps({"response": piece, "done": False}))
            chunks.append(json.dumps({"response": "", "done": True}))
            return ("\n".join(chunks) + "\n").encode("utf-8")
        return json.dumps({"response": item["response"], "done": True}).encode("utf-8")


@pytest.fixture
def cassette(monkeypatch):
    """Install a fake urlopen that replays from a named JSON transcript."""
    holder: dict = {}

    def install(name: str) -> Cassette:
        cas = Cassette(name)
        holder["cas"] = cas

        def fake_urlopen(req, timeout=None):
            try:
                payload = json.loads(req.data.decode("utf-8"))
            except Exception:
                payload = {}
            return FakeResponse(cas.next_response(payload))

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        return cas

    return install


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    """Point HOME / XDG_CONFIG_HOME at tmp so user config doesn't leak in."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    # Strip every AICOMMIT_* env override so tests start from defaults.
    import os
    for k in list(os.environ):
        if k.startswith("AICOMMIT_"):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.chdir(tmp_path)
    return home
