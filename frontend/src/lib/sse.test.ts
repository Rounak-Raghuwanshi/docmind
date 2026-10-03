import { describe, expect, it } from "vitest";
import { readSse, SseParser } from "./sse";

describe("SseParser", () => {
  it("parses events split across arbitrary chunk boundaries", () => {
    const p = new SseParser();
    const raw =
      'event: meta\ndata: {"message_id":"m1"}\n\nevent: token\ndata: {"text":"Hel"}\n\nevent: token\ndata: {"text":"lo"}\n\n';
    const events = [];
    for (let i = 0; i < raw.length; i += 7) events.push(...p.push(raw.slice(i, i + 7)));
    expect(events.map((e) => e.event)).toEqual(["meta", "token", "token"]);
    expect(JSON.parse(events[2]!.data)).toEqual({ text: "lo" });
  });

  it("ignores heartbeat comments and handles CRLF and multi-line data", () => {
    const p = new SseParser();
    const events = p.push(": ping\r\n\r\nevent: x\r\ndata: a\r\ndata: b\r\n\r\n");
    expect(events).toEqual([{ event: "x", data: "a\nb" }]);
  });

  it("defaults the event name to message", () => {
    expect(new SseParser().push("data: hi\n\n")).toEqual([{ event: "message", data: "hi" }]);
  });
});

describe("readSse", () => {
  it("reads a streamed Response and parses JSON payloads", async () => {
    const enc = new TextEncoder();
    const body = new ReadableStream({
      start(c) {
        c.enqueue(enc.encode('event: token\ndata: {"text":"A"}\n'));
        c.enqueue(enc.encode('\nevent: done\ndata: {"total_ms":5}\n\n'));
        c.close();
      },
    });
    const seen: [string, unknown][] = [];
    await readSse(new Response(body), (e, d) => seen.push([e, d]));
    expect(seen).toEqual([
      ["token", { text: "A" }],
      ["done", { total_ms: 5 }],
    ]);
  });
});
