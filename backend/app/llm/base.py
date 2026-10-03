from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Usage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@dataclass
class StreamResult:
    """Filled in while streaming; read after the iterator is exhausted."""

    usage: Usage = field(default_factory=Usage)


class LLMError(Exception):
    pass


class LLMClient(Protocol):
    model: str

    def stream(
        self, messages: list[dict[str, str]], *, max_tokens: int, result: StreamResult
    ) -> AsyncIterator[str]: ...

    async def complete(self, messages: list[dict[str, str]], *, max_tokens: int) -> str: ...
