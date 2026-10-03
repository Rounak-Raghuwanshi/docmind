import { motion } from "framer-motion";
import { lazy, Suspense, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { demoLogin, login, register } from "@/api/auth";
import { Button, Field, Logo } from "@/components/ui";
import { ApiError } from "@/lib/api";

const HeroScene = lazy(() => import("@/components/three/HeroScene"));

function AuthCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <main className="grid min-h-full bg-slate-50 lg:grid-cols-2 dark:bg-slate-950">
      <div className="flex items-center justify-center px-4 py-12">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
          className="w-full max-w-sm"
        >
          <Link to="/" className="mb-8 flex justify-center">
            <Logo className="text-xl" />
          </Link>
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-xl shadow-brand-900/5 backdrop-blur dark:border-slate-800 dark:bg-slate-900/90">
            <h1 className="text-xl font-semibold">{title}</h1>
            <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
            <div className="mt-6">{children}</div>
          </div>
        </motion.div>
      </div>
      <div className="relative hidden overflow-hidden bg-gradient-to-br from-indigo-950 via-brand-900 to-slate-950 lg:block">
        <Suspense fallback={null}>
          <HeroScene compact />
        </Suspense>
        <div className="pointer-events-none absolute inset-x-0 bottom-0 p-10 text-white">
          <p className="text-2xl font-semibold">Answers you can verify.</p>
          <p className="mt-2 max-w-sm text-sm text-brand-100">
            Every claim links to the exact page it came from, in your own documents.
          </p>
        </div>
      </div>
    </main>
  );
}

const DEMO_ACCOUNTS = [
  { email: "aarav@docmind.dev", role: "Owner: sees everything" },
  { email: "priya@docmind.dev", role: "Editor: uploads & chats" },
  { email: "rohan@docmind.dev", role: "Viewer: chat only" },
];

/** Local development only: one-click sign-in with the accounts created by `make seed`. */
function DevAccounts({ onPick }: { onPick: (email: string) => void }) {
  if (!import.meta.env.DEV) return null;
  return (
    <div className="mt-6 rounded-xl border border-dashed border-slate-300 p-3 text-xs dark:border-slate-700">
      <p className="font-medium text-slate-600 dark:text-slate-300">
        Seeded demo accounts (dev only) · password Demo@12345
      </p>
      <ul className="mt-2 space-y-1">
        {DEMO_ACCOUNTS.map((a) => (
          <li key={a.email}>
            <button
              type="button"
              onClick={() => onPick(a.email)}
              className="flex w-full justify-between gap-2 rounded-md px-2 py-1 text-left hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              <span className="font-mono">{a.email}</span>
              <span className="text-slate-500">{a.role}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function useAfterLogin() {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from;
  return () => navigate(from && from !== "/login" ? from : "/w", { replace: true });
}

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const done = useAfterLogin();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      done();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't reach the server");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthCard
      title="Welcome back"
      subtitle={
        <>
          New here?{" "}
          <Link className="font-medium text-brand-600 hover:underline" to="/register">
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Field
          label="Password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && (
          <p role="alert" className="text-sm text-red-600 dark:text-red-400">
            {error}
          </p>
        )}
        <Button type="submit" className="w-full" loading={busy}>
          Sign in
        </Button>
      </form>
      <DemoButton />
      <DevAccounts
        onPick={(e) => {
          setEmail(e);
          setPassword("Demo@12345");
        }}
      />
    </AuthCard>
  );
}

export function DemoButton({
  className,
  buttonClassName,
}: {
  className?: string;
  buttonClassName?: string;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  return (
    <div className={className ?? "mt-4"}>
      <Button
        variant="secondary"
        className={buttonClassName ?? "w-full"}
        loading={busy}
        onClick={async () => {
          setBusy(true);
          setError(null);
          try {
            await demoLogin();
            navigate("/w", { replace: true });
          } catch (err) {
            setError(err instanceof ApiError ? err.message : "Demo unavailable right now");
          } finally {
            setBusy(false);
          }
        }}
      >
        Try the demo — no sign-up
      </Button>
      {error && <p className="mt-2 text-center text-sm text-red-600">{error}</p>}
    </div>
  );
}

function validate(name: string, email: string, password: string) {
  const errors: Record<string, string> = {};
  if (!name.trim()) errors.name = "Tell us what to call you";
  if (!/^\S+@\S+\.\S+$/.test(email)) errors.email = "Enter a valid email address";
  if (password.length < 8) errors.password = "At least 8 characters";
  else if (new TextEncoder().encode(password).length > 72) errors.password = "At most 72 bytes";
  return errors;
}

export function RegisterPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [touched, setTouched] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const done = useAfterLogin();
  const errors = validate(name, email, password);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (Object.keys(errors).length) return;
    setBusy(true);
    setServerError(null);
    try {
      await register(name, email, password);
      await login(email, password);
      done();
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Couldn't reach the server");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthCard
      title="Create your account"
      subtitle={
        <>
          Already have one?{" "}
          <Link className="font-medium text-brand-600 hover:underline" to="/login">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field
          label="Full name"
          name="name"
          autoComplete="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          error={touched ? errors.name : null}
        />
        <Field
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={touched ? errors.email : null}
        />
        <Field
          label="Password"
          name="password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={touched ? errors.password : null}
          hint="At least 8 characters"
        />
        {serverError && (
          <p role="alert" className="text-sm text-red-600 dark:text-red-400">
            {serverError}
          </p>
        )}
        <Button type="submit" className="w-full" loading={busy}>
          Create account
        </Button>
      </form>
    </AuthCard>
  );
}
