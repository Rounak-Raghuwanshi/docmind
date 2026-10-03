import { Link } from "react-router-dom";

export function NotFound() {
  return (
    <main className="flex h-full flex-col items-center justify-center gap-3 px-4 text-center">
      <p className="text-5xl font-bold text-brand-600">404</p>
      <h1 className="text-xl font-semibold">Page not found</h1>
      <p className="text-sm text-slate-500">
        The page you're looking for doesn't exist or you don't have access to it.
      </p>
      <Link
        to="/w"
        className="mt-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white"
      >
        Go to my workspaces
      </Link>
    </main>
  );
}
