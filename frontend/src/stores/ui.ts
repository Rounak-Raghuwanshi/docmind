import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Citation } from "@/api/types";

type Theme = "light" | "dark" | "system";
type MobileTab = "conversations" | "chat" | "documents";

interface UiState {
  theme: Theme;
  setTheme: (t: Theme) => void;
  /** Citation opened in the viewer panel. */
  activeCitation: Citation | null;
  openCitation: (c: Citation | null) => void;
  /** Document opened in the viewer without a citation (e.g. from the document list). */
  viewerDocumentId: string | null;
  openDocument: (id: string | null) => void;
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  mobileTab: MobileTab;
  setMobileTab: (t: MobileTab) => void;
  /** Text to pre-fill in the chat composer (e.g. "Ask this" on a suggested question). */
  draft: string;
  setDraft: (text: string) => void;
}

export function applyTheme(theme: Theme): void {
  const dark =
    theme === "dark" ||
    (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", dark);
}

export const useUi = create<UiState>()(
  persist(
    (set) => ({
      theme: "system",
      setTheme: (theme) => {
        applyTheme(theme);
        set({ theme });
      },
      activeCitation: null,
      openCitation: (c) =>
        set({
          activeCitation: c,
          viewerDocumentId: c?.document_id ?? null,
          mobileTab: c ? "documents" : "chat",
        }),
      viewerDocumentId: null,
      openDocument: (id) => set({ viewerDocumentId: id, activeCitation: null }),
      sidebarOpen: true,
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      mobileTab: "chat",
      setMobileTab: (mobileTab) => set({ mobileTab }),
      draft: "",
      setDraft: (draft) => set({ draft }),
    }),
    // Only preferences persist; open citations etc. are per-session state.
    { name: "docmind-ui", partialize: (s) => ({ theme: s.theme, sidebarOpen: s.sidebarOpen }) },
  ),
);
