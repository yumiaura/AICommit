"""llama-cpp-python in-process backend (optional — install with [llama-cpp] extra)."""
from __future__ import annotations

import os
from collections.abc import Iterator


class LlamaCppBackend:
    """In-process backend backed by llama-cpp-python.

    `model` is the path to a GGUF file, not an Ollama tag.
    """

    def __init__(
        self,
        *,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 512,
        n_ctx: int | None = None,
        n_threads: int | None = None,
    ) -> None:
        try:
            from llama_cpp import Llama
        except ImportError as e:
            raise RuntimeError(
                "llama-cpp-python is not installed; install with `pip install 'aicommit[llama-cpp]'`"
            ) from e
        if not os.path.isfile(model):
            raise FileNotFoundError(
                f"model path {model!r} does not exist; llama-cpp expects a local GGUF file"
            )
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        kwargs: dict = {"model_path": model, "verbose": False}
        if n_ctx is not None:
            kwargs["n_ctx"] = n_ctx
        if n_threads is not None:
            kwargs["n_threads"] = n_threads
        self.llm = Llama(**kwargs)

    def generate(self, prompt: str, *, temperature: float | None = None) -> str:
        result = self.llm(
            prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature if temperature is None else temperature,
            stream=False,
        )
        return result["choices"][0]["text"].strip()

    def stream(self, prompt: str, *, temperature: float | None = None) -> Iterator[str]:
        for chunk in self.llm(
            prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature if temperature is None else temperature,
            stream=True,
        ):
            piece = chunk["choices"][0]["text"]
            if piece:
                yield piece
