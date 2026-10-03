import { QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { lazy, Suspense, type ReactNode } from "react";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";
import { Toaster, toast } from "sonner";
import { Logo } from "@/components/ui";
import { AuthProvider } from "@/features/auth/AuthProvider";
import { LoginPage, RegisterPage } from "@/features/auth/AuthPages";
import { RedirectIfAuthed, RequireAuth } from "@/features/auth/guards";
import { ChatPage } from "@/features/chat/ChatPage";
import { LibraryPage } from "@/features/documents/LibraryPage";
import { InvitePage } from "@/features/workspaces/InvitePage";
import { SettingsPage } from "@/features/workspaces/SettingsPage";
import { WorkspaceLayout } from "@/features/workspaces/WorkspaceLayout";
import { WorkspacesPage } from "@/features/workspaces/WorkspacesPage";
import { useServerWake } from "@/hooks/useServerWake";
import { ApiError } from "@/lib/api";
import { LandingPage } from "@/pages/LandingPage";
import { NotFound } from "@/pages/NotFound";
import { useUi } from "@/stores/ui";

const InsightsPage = lazy(() =>
  import("@/features/insights/InsightsPage").then((m) => ({ default: m.InsightsPage })),
);
const AnalyticsPage = lazy(() =>
  import("@/features/analytics/AnalyticsPage").then((m) => ({ default: m.AnalyticsPage })),
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (count, error) =>
        !(error instanceof ApiError && error.status >= 400 && error.status < 500) && count < 2,
    },
  },
  queryCache: new QueryCache({
    // Background refetch failures surface as a toast; first-load failures render inline.
    onError: (error, query) => {
      if (query.state.data !== undefined) toast.error(`Couldn't refresh: ${error.message}`);
    },
  }),
});

const router = createBrowserRouter([
  { path: "/", element: <LandingPage /> },
  {
    element: <RedirectIfAuthed />,
    children: [
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <RegisterPage /> },
    ],
  },
  {
    element: <RequireAuth />,
    children: [
      { path: "/w", element: <WorkspacesPage /> },
      { path: "/invite/:token", element: <InvitePage /> },
      {
        path: "/w/:ws",
        element: <WorkspaceLayout />,
        children: [
          { index: true, element: <ChatPage /> },
          { path: "c/:conv", element: <ChatPage /> },
          { path: "documents", element: <LibraryPage /> },
          { path: "settings", element: <SettingsPage /> },
          {
            path: "insights",
            element: (
              <Suspense fallback={null}>
                <InsightsPage />
              </Suspense>
            ),
          },
          {
            path: "analytics",
            element: (
              <Suspense fallback={null}>
                <AnalyticsPage />
              </Suspense>
            ),
          },
          { path: "*", element: <Navigate to="." replace /> },
        ],
      },
    ],
  },
  { path: "*", element: <NotFound /> },
]);

function ServerWakeGate({ children }: { children: ReactNode }) {
  const { ready, waking } = useServerWake();
  if (ready) return <>{children}</>;
  if (!waking) return null;
  return (
    <div
      className="flex h-full flex-col items-center justify-center gap-4 px-4 text-center"
      role="status"
    >
      <Logo className="text-xl" />
      <Loader2 className="size-6 animate-spin text-brand-600" aria-hidden />
      <p className="font-medium">Waking up the server…</p>
      <p className="max-w-sm text-sm text-slate-500">
        DocMind runs on free hosting that sleeps when idle. This takes up to a minute the first
        time.
      </p>
    </div>
  );
}

export default function App() {
  const theme = useUi((s) => s.theme);
  return (
    <QueryClientProvider client={queryClient}>
      <ServerWakeGate>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </ServerWakeGate>
      <Toaster richColors position="bottom-right" theme={theme} />
    </QueryClientProvider>
  );
}
