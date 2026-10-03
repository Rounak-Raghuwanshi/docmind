/**
 * Minimal SSE client over fetch.
 *
 * The browser's EventSource can't POST a body or send an Authorization header, so streams
 * are read with fetch + ReadableStream and parsed here. An AbortSignal stops the stream
 * (the Stop button), which the server sees as a disconnect.
 */
export interface SseEvent {
  event: string;
  data: string;
}

/** Incremental parser: feed it decoded text chunks, get complete events back. */
export class SseParser {
  private buffer = "";

  push(chunk: string): SseEvent[] {
    this.buffer += chunk.replace(/\r\n?/g, "\n");
    const events: SseEvent[] = [];
    let sep: number;
    while ((sep = this.buffer.indexOf("\n\n")) !== -1) {
      const frame = this.buffer.slice(0, sep);
      this.buffer = this.buffer.slice(sep + 2);
      const parsed = parseFrame(frame);
      if (parsed) events.push(parsed);
    }
    return events;
  }
}

function parseFrame(frame: string): SseEvent | null {
  let event = "message";
  const data: string[] = [];
  for (const line of frame.split("\n")) {
    if (!line || line.startsWith(":")) continue; // comments are heartbeats
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    if (field === "event") event = value;
    else if (field === "data") data.push(value);
  }
  return data.length ? { event, data: data.join("\n") } : null;
}

/** Read an SSE response body, calling onEvent for each event until the stream ends. */
export async function readSse(
  res: Response,
  onEvent: (event: string, data: unknown) => void,
): Promise<void> {
  if (!res.body) throw new Error("Response has no body");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  const parser = new SseParser();
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const ev of parser.push(decoder.decode(value, { stream: true }))) {
        let payload: unknown = ev.data;
        try {
          payload = JSON.parse(ev.data);
        } catch {
          /* plain-text data */
        }
        onEvent(ev.event, payload);
      }
    }
  } finally {
    reader.releaseLock();
  }
}
