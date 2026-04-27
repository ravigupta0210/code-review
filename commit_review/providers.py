"""LLM provider adapters. Each provider takes (system, user) text and returns the reply.

Designed to be dependency-light: uses httpx directly so users don't need to install
provider SDKs unless they want to. BYO API key via env vars.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol

import httpx


class ProviderError(RuntimeError):
    pass


class Provider(Protocol):
    name: str

    def chat(self, system: str, user: str) -> str: ...


@dataclass
class AnthropicProvider:
    model: str = "claude-sonnet-4-6"
    api_key_env: str = "ANTHROPIC_API_KEY"
    name: str = "anthropic"

    def chat(self, system: str, user: str) -> str:
        key = os.environ.get(self.api_key_env)
        if not key:
            raise ProviderError(f"missing {self.api_key_env}")
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        try:
            r = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=120,
            )
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise ProviderError(f"anthropic request failed: {e}") from e
        data = r.json()
        try:
            return data["content"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ProviderError(f"unexpected anthropic response: {data}") from e


@dataclass
class OpenAIProvider:
    model: str = "gpt-4o-mini"
    api_key_env: str = "OPENAI_API_KEY"
    name: str = "openai"

    def chat(self, system: str, user: str) -> str:
        key = os.environ.get(self.api_key_env)
        if not key:
            raise ProviderError(f"missing {self.api_key_env}")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
        }
        headers = {
            "Authorization": f"Bearer {key}",
            "content-type": "application/json",
        }
        try:
            r = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=120,
            )
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise ProviderError(f"openai request failed: {e}") from e
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ProviderError(f"unexpected openai response: {data}") from e


@dataclass
class GeminiProvider:
    model: str = "gemini-1.5-flash"
    api_key_env: str = "GEMINI_API_KEY"
    name: str = "gemini"

    def chat(self, system: str, user: str) -> str:
        key = os.environ.get(self.api_key_env)
        if not key:
            raise ProviderError(f"missing {self.api_key_env}")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={key}"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
        }
        try:
            r = httpx.post(url, json=payload, timeout=120)
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise ProviderError(f"gemini request failed: {e}") from e
        data = r.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ProviderError(f"unexpected gemini response: {data}") from e


def build_provider(name: str, model: str | None = None) -> Provider:
    name = (name or "").lower()
    if name == "anthropic":
        return AnthropicProvider(model=model or "claude-sonnet-4-6")
    if name == "openai":
        return OpenAIProvider(model=model or "gpt-4o-mini")
    if name == "gemini":
        return GeminiProvider(model=model or "gemini-1.5-flash")
    raise ProviderError(f"unknown provider: {name!r} (use anthropic|openai|gemini)")
