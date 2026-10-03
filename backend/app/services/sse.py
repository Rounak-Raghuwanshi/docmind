import json
from typing import Any

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "X-Accel-Buffering": "no",  # tell nginx-style proxies not to buffer the stream
    "Connection": "keep-alive",
}


def sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'), default=str)}\n\n"


def sse_comment(text: str = "ping") -> str:
    return f": {text}\n\n"
