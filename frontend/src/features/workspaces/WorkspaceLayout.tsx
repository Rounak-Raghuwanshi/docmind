import { motion } from "framer-motion";
import { BarChart3, ChevronDown, FileText, MessageSquare, Settings, Sparkles } from "lucide-react";
import { Link, NavLink, Outlet, useLocation, useNavigate, useParams } from "react-router-dom";
import { useWorkspace, useWorkspaces } from "@/api/workspaces";
import { ThemeToggle } from "@/components/ThemeToggle";
import { UserMenu } from "@/components/UserMenu";
import { ErrorState, Logo, Spinner } from "@/components/ui";
import { useAuth } from "@/features/auth/AuthProvider";
import { useDocumentEvents } from "@/hooks/useDocumentEvents";
import { cn } from "@/lib/format";

function WorkspaceSwitcher({ current }: { current: string }) {
  const { data: workspaces } = useWorkspaces();
  const navigate = useNavigate();
  const active = workspaces?.find((w) => w.id === current);
  return (
    <label className="relative flex items-center">
      <span className="sr-only">Switch workspace</span>
      <select
        value={current}
        onChange={(e) =>
          e.target.value === "__all" ? navigate("/w") : navigate(`/w/${e.target.value}`)
        }
        className="max-w-[12rem] appearance-none truncate rounded-lg border border-slate-200 bg-white py-1.5 pl-3 pr-8 text-sm font-medium hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900"
      >
        {!active && <option value={current}>Loading…</option>}
        {workspaces?.map((w) => (
          <option key={w.id} value={w.id}>
            {w.name}
          </option>
        ))}
        <option value="__all">All workspaces…</option>
      </select>
      <ChevronDown
        className="pointer-events-none absolute right-2 size-4 text-slate-400"
        aria-hidden
      />
    </label>
  );
}

export function WorkspaceLayout() {
  const { ws = "" } = useParams();
  const { data: workspace, error, isLoading, refetch } = useWorkspace(ws);
  const { user } = useAuth();
  const { pathname } = useLocation();
  useDocumentEvents(workspace ? ws : undefined);

  const navItems = [
    {
      to: `/w/${ws}`,
      label: "Chat",
      icon: MessageSquare,
      end: false,
      match: (p: string) => p === `/w/${ws}` || p.startsWith(`/w/${ws}/c/`),
    },
    { to: `/w/${ws}/documents`, label: "Library", icon: FileText },
    ...(workspace && (workspace.role === "owner" || workspace.is_demo)
      ? [
          { to: `/w/${ws}/insights`, label: "AI Insights", icon: Sparkles },
          { to: `/w/${ws}/analytics`, label: "Analytics", icon: BarChart3 },
        ]
      : []),
    { to: `/w/${ws}/settings`, label: "Settings", icon: Settings },
  ];

  return (
    <div className="flex h-full flex-col">
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-3 sm:px-4 dark:border-slate-800 dark:bg-slate-950">
        <Link to="/w" aria-label="All workspaces">
          <Logo className="text-base [&>span]:hidden sm:[&>span]:inline" />
        </Link>
        <WorkspaceSwitcher current={ws} />
        <nav aria-label="Workspace" className="ml-1 flex items-center gap-1 overflow-x-auto">
          {navItems.map(({ to, label, icon: Icon, match }) => (
            <NavLink
              key={to}
              to={to}
              end={!match}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium whitespace-nowrap",
                  (match ? match(pathname) : isActive)
                    ? "bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800",
                )
              }
            >
              <Icon className="size-4" aria-hidden />
              <span className="hidden md:inline">{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-1">
          <ThemeToggle />
          <UserMenu />
        </div>
      </header>
      {user?.is_guest && (
        <div className="bg-brand-600 px-4 py-1.5 text-center text-xs text-white">
          You're exploring the demo as a guest.{" "}
          <Link to="/register" className="font-semibold underline">
            Create a free account
          </Link>{" "}
          to upload your own documents and invite your team.
        </div>
      )}
      <div className="min-h-0 flex-1">
        {isLoading ? (
          <div className="flex h-full items-center justify-center">
            <Spinner className="size-8" />
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={refetch} />
        ) : (
          <motion.div
            key={pathname.split("/c/")[0]}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="h-full"
          >
            <Outlet context={workspace} />
          </motion.div>
        )}
      </div>
    </div>
  );
}
