"""
Unified LLM Provider supporting Groq (primary) and OpenAI (alternative/fallback).
Provides synchronous and streaming chat completions.
"""

import os
from typing import List, Dict, Generator, Optional, Any
from yt_agent.config import (
    GROQ_API_KEY,
    OPENAI_API_KEY,
    DEFAULT_GROQ_MODEL,
    DEFAULT_OPENAI_MODEL,
    AVAILABLE_GROQ_MODELS,
    AVAILABLE_OPENAI_MODELS,
)


class LLMProviderError(Exception):
    """Raised for errors in LLM API interaction."""
    pass


class LLMProvider:
    """Unified client for interacting with Groq and OpenAI LLMs."""

    def __init__(
        self,
        provider: str = "groq",
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.provider = provider.lower()
        self.api_key = api_key or (GROQ_API_KEY if self.provider == "groq" else OPENAI_API_KEY)
        self.model = model or (DEFAULT_GROQ_MODEL if self.provider == "groq" else DEFAULT_OPENAI_MODEL)
        self._client: Any = None
        self._init_client()

    def _init_client(self):
        """Initializes client SDK based on provider."""
        if self.provider == "groq":
            if not self.api_key:
                raise LLMProviderError(
                    "Groq API key not found. Please set GROQ_API_KEY in your .env or pass it to the agent."
                )
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except ImportError:
                raise LLMProviderError("Package 'groq' is not installed. Run 'pip install groq'.")

        elif self.provider == "openai":
            if not self.api_key:
                raise LLMProviderError(
                    "OpenAI API key not found. Please set OPENAI_API_KEY in your .env or pass it to the agent."
                )
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise LLMProviderError("Package 'openai' is not installed. Run 'pip install openai'.")
        else:
            raise LLMProviderError(f"Unsupported provider: '{self.provider}'. Use 'groq' or 'openai'.")

    def switch_provider(self, provider: str, api_key: Optional[str] = None, model: Optional[str] = None):
        """Dynamically switches provider (e.g. from Groq to OpenAI or vice-versa)."""
        self.provider = provider.lower()
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = GROQ_API_KEY if self.provider == "groq" else OPENAI_API_KEY

        if model:
            self.model = model
        else:
            self.model = DEFAULT_GROQ_MODEL if self.provider == "groq" else DEFAULT_OPENAI_MODEL

        self._init_client()

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generates a complete response synchronously."""
        tokens = max_tokens or (850 if self.provider == "groq" else 2500)
        if self.provider == "groq" and tokens > 950:
            tokens = 850

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMProviderError(f"[{self.provider.upper()} API Error] {str(e)}") from e

    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: Optional[int] = None
    ) -> Generator[str, None, None]:
        """Generates a streaming response token by token."""
        tokens = max_tokens or (850 if self.provider == "groq" else 2500)
        if self.provider == "groq" and tokens > 950:
            tokens = 850

        try:
            stream = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=tokens,
                stream=True
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise LLMProviderError(f"[{self.provider.upper()} Streaming Error] {str(e)}") from e
