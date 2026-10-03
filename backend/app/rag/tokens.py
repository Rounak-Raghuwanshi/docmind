import re

_WORD = re.compile(r"\S+")


def count_tokens(text: str) -> int:
    """Cheap, deterministic token estimate (~1.3 WordPiece tokens per English word).

    Exact counts would need the model tokenizer on every sentence; chunk sizing only needs
    to be roughly right, and the eval harness tunes the target anyway.
    """
    words = len(_WORD.findall(text))
    return int(words * 1.3 + 0.5)
