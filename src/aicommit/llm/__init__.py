"""LLM backends. v0.1+: Ollama HTTP. v0.6+: optional llama-cpp-python."""
from __future__ import annotations

from aicommit.llm.ollama import OllamaBackend, OllamaError


class LLMError(RuntimeError):
    """Raised when no usable backend can be constructed."""


def make_backend(
    backend: str,
    *,
    url: str,
    model: str,
    temperature: float,
    max_tokens: int = 512,
):
    if backend == "ollama":
        return OllamaBackend(url=url, model=model, temperature=temperature, max_tokens=max_tokens)
    if backend == "llama-cpp":
        try:
            from aicommit.llm.llama_cpp import LlamaCppBackend
            return LlamaCppBackend(model=model, temperature=temperature, max_tokens=max_tokens)
        except ImportError as e:
            raise LLMError(
                "llama-cpp backend requested but llama-cpp-python is not installed; "
                "install with `pip install 'aicommit[llama-cpp]'`"
            ) from e
        except (RuntimeError, FileNotFoundError) as e:
            raise LLMError(f"llama-cpp backend failed to initialise: {e}") from e
    raise LLMError(f"unknown backend: {backend!r}")


__all__ = ["OllamaBackend", "OllamaError", "LLMError", "make_backend"]
