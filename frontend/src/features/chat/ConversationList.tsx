import { MessageSquare, Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { NavLink, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { useConversations, useDeleteConversation, useUpdateConversation } from "@/api/chat";
import { Button, EmptyState, Skeleton } from "@/components/ui";
import { cn, relativeTime } from "@/lib/format";

export function ConversationList({ ws }: { ws: string }) {
  const { data, isLoading } = useConversations(ws);
  const { conv } = useParams();
  const rename = useUpdateConversation(ws);
  const remove = useDeleteConversation(ws);
  const navigate = useNavigate();
  const [editing, setEditing] = useState<string | null>(null);
  const [title, setTitle] = useState("");

  function commitRename(id: string) {
    const t = title.trim();
    setEditing(null);
    if (t) rename.mutate({ id, title: t }, { onError: (e) => toast.error(e.message) });
  }

  return (
    <nav aria-label="Conversations" className="flex h-full flex-col">
      <div className="p-3">
        <Button className="w-full" variant="secondary" onClick={() => navigate(`/w/${ws}`)}>
          <Plus className="size-4" aria-hidden /> New chat
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {isLoading ? (
          <div className="space-y-2 px-1">
            {Array.from({ length: 5 }, (_, i) => (
              <Skeleton key={i} className="h-9" />
            ))}
          </div>
        ) : !data?.length ? (
          <EmptyState icon={<MessageSquare className="size-6" />} title="No chats yet">
            Your conversations will appear here.
          </EmptyState>
        ) : (
          <ul className="space-y-0.5">
            {data.map((c) => (
              <li key={c.id} className="group relative">
                {editing === c.id ? (
                  <input
                    autoFocus
                    aria-label="Conversation title"
                    value={title}
                    maxLength={200}
                    onChange={(e) => setTitle(e.target.value)}
                    onBlur={() => commitRename(c.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") commitRename(c.id);
                      if (e.key === "Escape") setEditing(null);
                    }}
                    className="w-full rounded-lg border border-brand-400 bg-white px-2.5 py-2 text-sm focus:outline-none dark:bg-slate-900"
                  />
                ) : (
                  <NavLink
                    to={`/w/${ws}/c/${c.id}`}
                    className={({ isActive }) =>
                      cn(
                        "block rounded-lg py-2 pl-2.5 pr-14 text-sm",
                        isActive || conv === c.id
                          ? "bg-slate-200/70 font-medium dark:bg-slate-800"
                          : "hover:bg-slate-100 dark:hover:bg-slate-800/60",
                      )
                    }
                  >
                    <span className="block truncate">{c.title}</span>
                    <span className="block text-[11px] text-slate-500">
                      {relativeTime(c.updated_at)}
                    </span>
                  </NavLink>
                )}
                {editing !== c.id && (
                  <div className="absolute right-1 top-1.5 hidden gap-0.5 group-focus-within:flex group-hover:flex">
                    <button
                      type="button"
                      aria-label={`Rename ${c.title}`}
                      onClick={() => {
                        setEditing(c.id);
                        setTitle(c.title);
                      }}
                      className="rounded p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-700 dark:hover:bg-slate-700"
                    >
                      <Pencil className="size-3.5" />
                    </button>
                    <button
                      type="button"
                      aria-label={`Delete ${c.title}`}
                      onClick={() => {
                        if (!confirm("Delete this conversation?")) return;
                        remove.mutate(c.id, { onError: (e) => toast.error(e.message) });
                        if (conv === c.id) navigate(`/w/${ws}`);
                      }}
                      className="rounded p-1 text-slate-400 hover:bg-slate-200 hover:text-red-600 dark:hover:bg-slate-700"
                    >
                      <Trash2 className="size-3.5" />
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </nav>
  );
}
