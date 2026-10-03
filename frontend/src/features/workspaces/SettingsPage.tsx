import { Check, Copy, Link2, LogOut, Trash2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import type { Role } from "@/api/types";
import {
  useChangeRole,
  useCreateInvite,
  useDeleteWorkspace,
  useMembers,
  useRemoveMember,
  useRenameWorkspace,
} from "@/api/workspaces";
import { Badge, Button, ErrorState, Field, Skeleton } from "@/components/ui";
import { useAuth } from "@/features/auth/AuthProvider";
import { hasRole, useCurrentWorkspace } from "./useWorkspaceContext";

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-slate-200 p-6 dark:border-slate-800">
      <h2 className="font-semibold">{title}</h2>
      {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}

const roleHelp: Record<Role, string> = {
  owner: "Manage members, settings and analytics",
  editor: "Upload documents and chat",
  viewer: "Chat only",
};

function Members() {
  const ws = useCurrentWorkspace();
  const { user } = useAuth();
  const { data, isLoading, error, refetch } = useMembers(ws.id);
  const changeRole = useChangeRole(ws.id);
  const remove = useRemoveMember(ws.id);
  const isOwner = hasRole(ws, "owner");
  const navigate = useNavigate();

  if (error) return <ErrorState error={error} onRetry={refetch} />;
  return (
    <ul className="divide-y divide-slate-200 dark:divide-slate-800">
      {isLoading && <Skeleton className="h-10" />}
      {data?.map((m) => {
        const me = m.user_id === user?.id;
        return (
          <li key={m.user_id} className="flex flex-wrap items-center gap-3 py-3">
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">
                {m.full_name} {me && <span className="text-slate-500">(you)</span>}
              </p>
              <p className="truncate text-xs text-slate-500">{m.email}</p>
            </div>
            {isOwner && !me ? (
              <select
                aria-label={`Role for ${m.full_name}`}
                value={m.role}
                onChange={(e) =>
                  changeRole.mutate(
                    { userId: m.user_id, role: e.target.value as Role },
                    { onError: (err) => toast.error(err.message) },
                  )
                }
                className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900"
              >
                {(["owner", "editor", "viewer"] as const).map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            ) : (
              <Badge tone={m.role === "owner" ? "brand" : "slate"}>{m.role}</Badge>
            )}
            {((isOwner && !me) || (me && !ws.is_personal)) && (
              <Button
                variant="ghost"
                size="sm"
                aria-label={me ? "Leave workspace" : `Remove ${m.full_name}`}
                onClick={() => {
                  if (!confirm(me ? "Leave this workspace?" : `Remove ${m.full_name}?`)) return;
                  remove.mutate(m.user_id, {
                    onSuccess: () => me && navigate("/w"),
                    onError: (err) => toast.error(err.message),
                  });
                }}
              >
                {me ? <LogOut className="size-4" /> : <Trash2 className="size-4" />}
              </Button>
            )}
          </li>
        );
      })}
    </ul>
  );
}

function Invites() {
  const ws = useCurrentWorkspace();
  const create = useCreateInvite(ws.id);
  const [role, setRole] = useState<Role>("viewer");
  const [copied, setCopied] = useState(false);

  return (
    <div>
      <div className="flex flex-wrap items-end gap-2">
        <label className="text-sm">
          <span className="mb-1 block font-medium text-slate-700 dark:text-slate-300">Role</span>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as Role)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
          >
            <option value="viewer">Viewer — {roleHelp.viewer}</option>
            <option value="editor">Editor — {roleHelp.editor}</option>
          </select>
        </label>
        <Button
          onClick={() => create.mutate(role, { onError: (e) => toast.error(e.message) })}
          loading={create.isPending}
        >
          <Link2 className="size-4" aria-hidden /> Create invite link
        </Button>
      </div>
      {create.data && (
        <div className="mt-4 rounded-lg bg-slate-50 p-3 dark:bg-slate-900">
          <div className="flex items-center gap-2">
            <input
              readOnly
              value={create.data.url}
              aria-label="Invite link"
              className="min-w-0 flex-1 bg-transparent font-mono text-xs"
              onFocus={(e) => e.target.select()}
            />
            <Button
              size="sm"
              variant="secondary"
              onClick={async () => {
                await navigator.clipboard.writeText(create.data!.url);
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
              }}
            >
              {copied ? <Check className="size-4" /> : <Copy className="size-4" />}{" "}
              {copied ? "Copied" : "Copy"}
            </Button>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Single use · joins as <strong>{create.data.role}</strong> · expires{" "}
            {new Date(create.data.expires_at).toLocaleDateString()}
          </p>
        </div>
      )}
    </div>
  );
}

export function SettingsPage() {
  const ws = useCurrentWorkspace();
  const isOwner = hasRole(ws, "owner");
  const rename = useRenameWorkspace(ws.id);
  const del = useDeleteWorkspace(ws.id);
  const [name, setName] = useState(ws.name);
  const [confirmName, setConfirmName] = useState("");
  const navigate = useNavigate();

  function onRename(e: FormEvent) {
    e.preventDefault();
    if (name.trim() && name.trim() !== ws.name) {
      rename.mutate(name.trim(), {
        onSuccess: () => toast.success("Workspace renamed"),
        onError: (err) => toast.error(err.message),
      });
    }
  }

  return (
    <main className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-6 px-4 py-8">
        <h1 className="text-2xl font-semibold">Workspace settings</h1>
        {isOwner && (
          <Section title="General">
            <form onSubmit={onRename} className="flex items-end gap-2">
              <Field
                className="flex-1"
                label="Workspace name"
                name="ws-name"
                value={name}
                maxLength={80}
                onChange={(e) => setName(e.target.value)}
              />
              <Button
                type="submit"
                variant="secondary"
                loading={rename.isPending}
                disabled={!name.trim() || name.trim() === ws.name}
              >
                Save
              </Button>
            </form>
          </Section>
        )}
        <Section
          title="Members"
          description="Owners manage the workspace, editors upload documents, viewers can only ask questions."
        >
          <Members />
        </Section>
        {isOwner && !ws.is_personal && (
          <Section
            title="Invite people"
            description="Anyone with the link can join once, with the role you choose."
          >
            <Invites />
          </Section>
        )}
        {isOwner && !ws.is_personal && (
          <Section
            title="Danger zone"
            description="Deleting a workspace removes every document, passage and conversation in it."
          >
            <div className="flex flex-wrap items-end gap-2">
              <Field
                className="flex-1"
                label={`Type “${ws.name}” to confirm`}
                name="confirm-delete"
                value={confirmName}
                onChange={(e) => setConfirmName(e.target.value)}
              />
              <Button
                variant="danger"
                disabled={confirmName !== ws.name}
                loading={del.isPending}
                onClick={() =>
                  del.mutate(undefined, {
                    onSuccess: () => {
                      toast.success("Workspace deleted");
                      navigate("/w", { replace: true });
                    },
                    onError: (err) => toast.error(err.message),
                  })
                }
              >
                Delete workspace
              </Button>
            </div>
          </Section>
        )}
      </div>
    </main>
  );
}
