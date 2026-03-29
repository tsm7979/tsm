"""
TSM Runtime Inference Stub
===========================

Placeholder for local model inference.
In production, this would connect to vLLM, Ollama, or TSM's own runtime.
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class InferenceResult:
    """Result from TSM Runtime inference."""
    text: str
    tokens_generated: int


class TSMInferenceClient:
    """Stub TSM Runtime client."""

    def generate(
        self,
        prompt: str,
        model: str = "llama3.2",
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> InferenceResult:
        """
        Generate text using TSM Runtime.

        For now, returns intelligent placeholder.
        TODO: Connect to real vLLM/Ollama endpoint.
        """
        # Placeholder response
        text = f"[TSM Runtime - {model}] This is a placeholder response. " \
               f"To enable real inference, deploy vLLM or Ollama and update this client."

        # Estimate tokens
        tokens = len(prompt.split()) + len(text.split())

        return InferenceResult(text=text, tokens_generated=tokens)


# Global client
_tsm_client = None


def get_tsm_client() -> TSMInferenceClient:
    """Get singleton TSM Runtime client."""
    global _tsm_client
    if _tsm_client is None:
        _tsm_client = TSMInferenceClient()
    return _tsm_client
