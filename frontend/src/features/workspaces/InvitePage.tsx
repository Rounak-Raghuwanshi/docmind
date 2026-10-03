import { useNavigate, useParams } from "react-router-dom";
import { useAcceptInvite, useInvitePreview } from "@/api/workspaces";
import { Button, Logo, Spinner } from "@/components/ui";
import { ApiError } from "@/lib/api";

export function InvitePage() {
  const { token = "" } = useParams();
  const preview = useInvitePreview(token);
  const accept = useAcceptInvite(token);
  const navigate = useNavigate();

  return (
    <main className="flex min-h-full items-center justify-center bg-slate-50 px-4 dark:bg-slate-950">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <Logo className="justify-center text-lg" />
        {preview.isLoading ? (
          <div className="mt-8">
            <Spinner />
          </div>
        ) : preview.error ? (
          <>
            <h1 className="mt-6 text-lg font-semibold">This invite can't be used</h1>
            <p className="mt-2 text-sm text-slate-500">
              {preview.error instanceof ApiError ? preview.error.message : "Invite not found."} Ask
              the workspace owner for a new link.
            </p>
            <Button className="mt-6" variant="secondary" onClick={() => navigate("/w")}>
              Go to my workspaces
            </Button>
          </>
        ) : (
          preview.data && (
            <>
              <h1 className="mt-6 text-lg font-semibold">Join “{preview.data.workspace_name}”</h1>
              <p className="mt-2 text-sm text-slate-500">
                {preview.data.invited_by} invited you as <strong>{preview.data.role}</strong>.
              </p>
              {accept.error && (
                <p role="alert" className="mt-4 text-sm text-red-600">
                  {accept.error.message}
                </p>
              )}
              <Button
                className="mt-6 w-full"
                loading={accept.isPending}
                onClick={async () => {
                  const ws = await accept.mutateAsync();
                  navigate(`/w/${ws.id}`, { replace: true });
                }}
              >
                Accept invite
              </Button>
            </>
          )
        )}
      </div>
    </main>
  );
}
