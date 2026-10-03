import { FileText, MessageSquare, PanelLeft } from "lucide-react";
import { useParams } from "react-router-dom";
import { DocumentsPanel } from "@/features/documents/DocumentsPanel";
import { useCurrentWorkspace } from "@/features/workspaces/useWorkspaceContext";
import { cn } from "@/lib/format";
import { useUi } from "@/stores/ui";
import { ChatPanel } from "./ChatPanel";
import { ConversationList } from "./ConversationList";

/** Three panels on desktop; on mobile they collapse into tabs. */
export function ChatPage() {
  const ws = useCurrentWorkspace();
  const { conv } = useParams();
  const { mobileTab, setMobileTab, sidebarOpen, toggleSidebar } = useUi();

  const tabs = [
    { id: "conversations", label: "Chats", icon: PanelLeft },
    { id: "chat", label: "Chat", icon: MessageSquare },
    { id: "documents", label: "Sources", icon: FileText },
  ] as const;

  return (
    <div className="flex h-full flex-col">
      <div className="flex min-h-0 flex-1">
        <aside
          className={cn(
            "w-full shrink-0 border-r border-slate-200 bg-slate-50 lg:w-64 dark:border-slate-800 dark:bg-slate-900/40",
            mobileTab === "conversations" ? "block" : "hidden",
            sidebarOpen ? "lg:block" : "lg:hidden",
          )}
        >
          <ConversationList ws={ws.id} />
        </aside>
        <main
          className={cn(
            "relative min-w-0 flex-1",
            mobileTab === "chat" ? "block" : "hidden lg:block",
          )}
        >
          <button
            type="button"
            onClick={toggleSidebar}
            className="absolute left-2 top-2 z-10 hidden rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 lg:block dark:hover:bg-slate-800"
            aria-label={sidebarOpen ? "Hide conversations" : "Show conversations"}
          >
            <PanelLeft className="size-4" />
          </button>
          <ChatPanel key={conv ?? "new"} conversationId={conv} />
        </main>
        <aside
          className={cn(
            "w-full shrink-0 border-l border-slate-200 bg-white lg:w-[28rem] xl:w-[32rem] dark:border-slate-800 dark:bg-slate-950",
            mobileTab === "documents" ? "block" : "hidden lg:block",
          )}
        >
          <DocumentsPanel />
        </aside>
      </div>
      <nav
        aria-label="Panels"
        className="flex border-t border-slate-200 lg:hidden dark:border-slate-800"
      >
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setMobileTab(id)}
            aria-current={mobileTab === id}
            className={cn(
              "flex flex-1 flex-col items-center gap-0.5 py-2 text-xs",
              mobileTab === id ? "text-brand-600" : "text-slate-500",
            )}
          >
            <Icon className="size-5" aria-hidden />
            {label}
          </button>
        ))}
      </nav>
    </div>
  );
}
