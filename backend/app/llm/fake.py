"""Deterministic LLM used by tests and for offline UI development (LLM_PROVIDER=fake)."""

import asyncio
import json
from collections.abc import AsyncIterator

from app.llm.base import StreamResult

FAKE_ANSWER = (
    "According to the documents, the answer is stated clearly [1]. It also notes a detail [2]."
)


class FakeLLM:
    model = "fake-llm"

    def __init__(self, answer: str = FAKE_ANSWER, delay: float = 0.0) -> None:
        self.answer = answer
        self.delay = delay
        self.calls: list[list[dict[str, str]]] = []

    async def stream(
        self, messages: list[dict[str, str]], *, max_tokens: int, result: StreamResult
    ) -> AsyncIterator[str]:
        self.calls.append(messages)
        words = self.answer.split(" ")
        for i, word in enumerate(words):
            if self.delay:
                await asyncio.sleep(self.delay)
            yield word if i == 0 else " " + word
        result.usage.prompt_tokens = sum(len(m["content"].split()) for m in messages)
        result.usage.completion_tokens = len(words)

    async def complete(self, messages: list[dict[str, str]], *, max_tokens: int) -> str:
        self.calls.append(messages)
        system = messages[0]["content"]
        if "JSON" in system:
            return json.dumps(
                {
                    "summary": "A short summary of the document.",
                    "questions": [
                        "What is covered?",
                        "Who does it apply to?",
                        "What are the limits?",
                    ],
                }
            )
        if "title" in system.lower():
            return "Fake conversation title"
        return messages[-1]["content"].rsplit("Latest question:", 1)[-1].strip()
