import { AnimatePresence, motion } from "framer-motion";
import { LayoutGrid, LogOut } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { logout } from "@/api/auth";
import { useAuth } from "@/features/auth/AuthProvider";
import { notify } from "@/lib/notify";

/** Avatar button with the account menu (workspaces, sign out). Shown on every signed-in page. */
export function UserMenu() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) =>
      ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (!user) return null;
  const initials = user.full_name
    .split(/\s+/)
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  async function signOut() {
    setBusy(true);
    try {
      await logout();
      notify.success("Signed out");
      navigate("/", { replace: true });
    } finally {
      setBusy(false);
      setOpen(false);
    }
  }

  const item =
    "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-800";

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label={`Account menu for ${user.full_name}`}
        title={user.full_name}
        className="flex size-8 items-center justify-center rounded-full bg-brand-600 text-xs font-semibold text-white ring-offset-2 hover:ring-2 hover:ring-brand-300 dark:ring-offset-slate-950"
      >
        {initials}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            role="menu"
            initial={{ opacity: 0, y: -4, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.97 }}
            transition={{ duration: 0.12 }}
            className="absolute right-0 z-40 mt-2 w-60 origin-top-right rounded-xl border border-slate-200 bg-white p-1 shadow-lg dark:border-slate-700 dark:bg-slate-900"
          >
            <div className="border-b border-slate-100 px-3 py-2 text-sm dark:border-slate-800">
              <p className="font-medium">{user.full_name}</p>
              <p className="truncate text-slate-500">
                {user.is_guest ? "Guest account" : user.email}
              </p>
            </div>
            <Link role="menuitem" to="/w" onClick={() => setOpen(false)} className={`${item} mt-1`}>
              <LayoutGrid className="size-4" aria-hidden /> My workspaces
            </Link>
            <button
              role="menuitem"
              type="button"
              onClick={signOut}
              disabled={busy}
              className={item}
            >
              <LogOut className="size-4" aria-hidden /> {busy ? "Signing out…" : "Sign out"}
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
