import { create } from "zustand";
import type { Citation } from "@/api/types";

export interface StreamingAnswer {
  question: string;
  messageId: string | null;
  rewritten: string | null;
  text: string;
  citations: Citation[] | null;
  status: "streaming" | "complete" | "stopped" | "error";
  error: string | null;
  notFound: boolean;
  cached: boolean;
  totalMs: number | null;
}

/**
 * In-flight answers, keyed by conversation id. Lives outside React components so a stream
 * survives navigation (e.g. the first question of a new chat changes the URL mid-stream).
 */
interface ChatStore {
  streams: Record<string, StreamingAnswer>;
  controllers: Record<string, AbortController>;
  start: (convId: string, question: string, controller: AbortController) => void;
  update: (convId: string, patch: Partial<StreamingAnswer>) => void;
  appendText: (convId: string, text: string) => void;
  clear: (convId: string) => void;
  stop: (convId: string) => void;
}

export const useChatStore = create<ChatStore>()((set, get) => ({
  streams: {},
  controllers: {},
  start: (convId, question, controller) =>
    set((s) => ({
      streams: {
        ...s.streams,
        [convId]: {
          question,
          messageId: null,
          rewritten: null,
          text: "",
          citations: null,
          status: "streaming",
          error: null,
          notFound: false,
          cached: false,
          totalMs: null,
        },
      },
      controllers: { ...s.controllers, [convId]: controller },
    })),
  update: (convId, patch) =>
    set((s) => {
      const cur = s.streams[convId];
      return cur ? { streams: { ...s.streams, [convId]: { ...cur, ...patch } } } : s;
    }),
  appendText: (convId, text) =>
    set((s) => {
      const cur = s.streams[convId];
      return cur ? { streams: { ...s.streams, [convId]: { ...cur, text: cur.text + text } } } : s;
    }),
  clear: (convId) =>
    set((s) => {
      const streams = { ...s.streams };
      const controllers = { ...s.controllers };
      delete streams[convId];
      delete controllers[convId];
      return { streams, controllers };
    }),
  stop: (convId) => get().controllers[convId]?.abort(),
}));
