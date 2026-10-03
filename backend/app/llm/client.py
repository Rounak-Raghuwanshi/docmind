"""One client for every OpenAI-compatible provider (Ollama, Groq, Gemini, OpenRouter, ...).

Switching provider is a change of LLM_BASE_URL / LLM_API_KEY / LLM_MODEL, not code.
"""

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any, cast

import openai
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import ChatCompletionChunk

from app.config import get_settings
from app.llm.base import LLMClient, LLMError, StreamResult


class OpenAICompatibleClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float,
        temperature: float,
        stream_usage: bool,
    ) -> None:
        self._client = AsyncOpenAI(
            base_url=base_url, api_key=api_key, timeout=timeout, max_retries=2
        )
        self.model = model
        self._temperature = temperature
        self._stream_usage = stream_usage

    async def stream(
        self, messages: list[dict[str, str]], *, max_tokens: int, result: StreamResult
    ) -> AsyncIterator[str]:
        kwargs: dict[str, Any] = {}
        if self._stream_usage:
            kwargs["stream_options"] = {"include_usage": True}
        try:
            stream = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=self._temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )
            stream = cast(AsyncStream[ChatCompletionChunk], stream)
            try:
                async for event in stream:
                    if event.usage is not None:
                        result.usage.prompt_tokens = event.usage.prompt_tokens
                        result.usage.completion_tokens = event.usage.completion_tokens
                    if event.choices:
                        delta = event.choices[0].delta.content
                        if delta:
                            yield delta
            finally:
                # Closing the HTTP stream is what actually stops generation upstream
                # when the user presses Stop.
                await stream.close()
        except openai.APIError as e:
            raise LLMError(_friendly(e)) from e

    async def complete(self, messages: list[dict[str, str]], *, max_tokens: int) -> str:
        try:
            resp = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=self._temperature,
                max_tokens=max_tokens,
            )
        except openai.APIError as e:
            raise LLMError(_friendly(e)) from e
        return (resp.choices[0].message.content or "").strip()


def _friendly(e: openai.APIError) -> str:
    if isinstance(e, openai.RateLimitError):
        return "The language model is rate limited right now. Please try again in a minute."
    if isinstance(e, openai.APIConnectionError | openai.APITimeoutError):
        return "Could not reach the language model. Is the LLM server running?"
    if isinstance(e, openai.AuthenticationError):
        return "The language model rejected the API key (check LLM_API_KEY)."
    if isinstance(e, openai.NotFoundError):
        return "The configured model was not found (check LLM_MODEL)."
    return "The language model returned an error."


@lru_cache
def get_llm() -> LLMClient:
    s = get_settings()
    if s.llm_provider == "fake":
        from app.llm.fake import FakeLLM

        return FakeLLM()
    return OpenAICompatibleClient(
        base_url=s.llm_base_url,
        api_key=s.llm_api_key.get_secret_value(),
        model=s.llm_model,
        timeout=s.llm_timeout_seconds,
        temperature=s.llm_temperature,
        stream_usage=s.llm_stream_usage,
    )
