import { FileText, FolderPlus, Users } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useCreateWorkspace, useWorkspaces } from "@/api/workspaces";
import { ThemeToggle } from "@/components/ThemeToggle";
import { UserMenu } from "@/components/UserMenu";
import { TiltCard } from "@/components/TiltCard";
import { Badge, Button, ErrorState, Field, Logo, Skeleton } from "@/components/ui";
import { useAuth } from "@/features/auth/AuthProvider";
import { ApiError } from "@/lib/api";

export function WorkspacesPage() {
  const { data, isLoading, error, refetch } = useWorkspaces();
  const { user } = useAuth();
  const create = useCreateWorkspace();
  const [name, setName] = useState("");
  const navigate = useNavigate();

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    const ws = await create.mutateAsync(name.trim());
    navigate(`/w/${ws.id}/documents`);
  }

  return (
    <div className="min-h-full bg-slate-50 dark:bg-slate-950">
      <header className="flex h-14 items-center justify-between border-b border-slate-200 bg-white px-4 dark:border-slate-800 dark:bg-slate-950">
        <Logo />
        <div className="flex items-center gap-1">
          <ThemeToggle />
          <UserMenu />
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-10">
        <h1 className="text-2xl font-semibold">Your workspaces</h1>
        <p className="mt-1 text-sm text-slate-500">
          A workspace holds documents and the people allowed to ask questions about them.
        </p>

        {error ? (
          <ErrorState error={error} onRetry={refetch} />
        ) : (
          <ul className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {isLoading &&
              Array.from({ length: 3 }, (_, i) => (
                <li key={i}>
                  <Skeleton className="h-32" />
                </li>
              ))}
            {data?.map((w) => (
              <li key={w.id}>
                <TiltCard className="h-full rounded-2xl">
                  <Link
                    to={`/w/${w.id}`}
                    className="block h-full rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-brand-300 hover:shadow-lg dark:border-slate-800 dark:bg-slate-900 dark:hover:border-brand-700"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <h2 className="font-semibold">{w.name}</h2>
                      <Badge tone={w.role === "owner" ? "brand" : "slate"}>{w.role}</Badge>
                    </div>
                    <div className="mt-6 flex gap-4 text-sm text-slate-500">
                      <span className="flex items-center gap-1">
                        <FileText className="size-4" aria-hidden /> {w.document_count} docs
                      </span>
                      <span className="flex items-center gap-1">
                        <Users className="size-4" aria-hidden /> {w.member_count}
                      </span>
                    </div>
                    {w.is_demo && (
                      <p className="mt-3 text-xs font-medium text-brand-600">
                        ✦ Public demo workspace
                      </p>
                    )}
                  </Link>
                </TiltCard>
              </li>
            ))}
          </ul>
        )}

        {!user?.is_guest && (
          <form
            onSubmit={onCreate}
            className="mt-10 max-w-md rounded-2xl border border-dashed border-slate-300 p-5 dark:border-slate-700"
          >
            <h2 className="flex items-center gap-2 font-semibold">
              <FolderPlus className="size-5 text-brand-600" aria-hidden /> New team workspace
            </h2>
            <div className="mt-4 flex items-end gap-2">
              <Field
                className="flex-1"
                label="Name"
                name="workspace-name"
                placeholder="e.g. Finance team"
                value={name}
                maxLength={80}
                onChange={(e) => setName(e.target.value)}
                error={create.error instanceof ApiError ? create.error.message : null}
              />
              <Button type="submit" loading={create.isPending} disabled={!name.trim()}>
                Create
              </Button>
            </div>
          </form>
        )}
      </main>
    </div>
  );
}
