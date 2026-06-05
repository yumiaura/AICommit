"""Ollama HTTP backend — uses only stdlib (urllib + json)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Iterator


class OllamaError(RuntimeError):
    """Raised when Ollama is unreachable or returns a non-2xx response."""


class OllamaBackend:
    def __init__(
        self,
        *,
        url: str,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 512,
        timeout: float = 120.0,
    ) -> None:
        self.url = url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def _payload(self, prompt: str, *, temperature: float | None, stream: bool) -> dict:
        return {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": self.temperature if temperature is None else temperature,
                "num_predict": self.max_tokens,
            },
        }

    def generate(self, prompt: str, *, temperature: float | None = None) -> str:
        req = self._build_request(self._payload(prompt, temperature=temperature, stream=False))
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise OllamaError(f"Ollama HTTP {e.code}: {detail.strip()}") from e
        except urllib.error.URLError as e:
            raise OllamaError(f"cannot reach Ollama at {self.url}: {e.reason}") from e
        return body.get("response", "").strip()

    def stream(self, prompt: str, *, temperature: float | None = None) -> Iterator[str]:
        """Yield response chunks as they arrive from Ollama's NDJSON stream."""
        req = self._build_request(self._payload(prompt, temperature=temperature, stream=True))
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                for raw in resp:
                    if not raw.strip():
                        continue
                    try:
                        chunk = json.loads(raw.decode("utf-8"))
                    except json.JSONDecodeError:
                        continue
                    piece = chunk.get("response", "")
                    if piece:
                        yield piece
                    if chunk.get("done"):
                        return
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise OllamaError(f"Ollama HTTP {e.code}: {detail.strip()}") from e
        except urllib.error.URLError as e:
            raise OllamaError(f"cannot reach Ollama at {self.url}: {e.reason}") from e

    def _build_request(self, payload: dict) -> urllib.request.Request:
        return urllib.request.Request(
            f"{self.url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
