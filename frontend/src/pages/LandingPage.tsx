import { motion, useInView, useReducedMotion, type Variants } from "framer-motion";
import {
  ArrowRight,
  BookOpenCheck,
  Boxes,
  Code2,
  FileSearch,
  FileText,
  Gauge,
  GitBranch,
  Headphones,
  Lock,
  MessageSquareText,
  ScanText,
  ShieldCheck,
  Sparkles,
  Users,
  Wand2,
} from "lucide-react";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ThemeToggle } from "@/components/ThemeToggle";
import { TiltCard } from "@/components/TiltCard";
import { Logo } from "@/components/ui";
import { DemoButton } from "@/features/auth/AuthPages";

const HeroScene = lazy(() => import("@/components/three/HeroScene"));

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] as const } },
};

const features = [
  {
    icon: BookOpenCheck,
    title: "Every claim is cited",
    body: "Click a citation and the PDF opens at the exact page with the passage highlighted.",
  },
  {
    icon: FileSearch,
    title: "Hybrid search + reranking",
    body: "Meaning-based vector search and exact keyword search, fused with RRF and reordered by a cross-encoder.",
  },
  {
    icon: ScanText,
    title: "Scanned PDFs too",
    body: "Pages without a text layer are OCR'd. Uploads process in the background with live progress.",
  },
  {
    icon: Users,
    title: "Team workspaces",
    body: "Owners, editors and viewers with invite links. One workspace can never see another's data.",
  },
  {
    icon: Sparkles,
    title: "AI insights",
    body: "A 3D map of your documents' meaning, confidence scores, and the questions your docs can't answer yet.",
  },
  {
    icon: ShieldCheck,
    title: "Says “not found”",
    body: "When nothing relevant is retrieved, DocMind tells you, instead of inventing an answer.",
  },
];

const pipeline = [
  { icon: FileText, label: "Upload", detail: "PDF · DOCX · TXT · MD" },
  { icon: ScanText, label: "Read & OCR", detail: "page by page" },
  { icon: Boxes, label: "Chunk", detail: "by heading & sentence" },
  { icon: Wand2, label: "Embed", detail: "384-d vectors" },
  { icon: FileSearch, label: "Hybrid search", detail: "vector ‖ keyword → RRF" },
  { icon: Gauge, label: "Rerank & gate", detail: "cross-encoder" },
  { icon: MessageSquareText, label: "Cited answer", detail: "streamed live" },
];

const useCases = [
  {
    icon: Code2,
    title: "Engineering handbooks",
    body: "Ask runbooks, API guidelines and architecture docs: “What do I do in the first 15 minutes of a SEV1?”",
  },
  {
    icon: GitBranch,
    title: "Onboarding new developers",
    body: "New joiners ask the handbook instead of interrupting seniors, and every answer links to the source.",
  },
  {
    icon: Headphones,
    title: "Support & on-call",
    body: "Support engineers search product manuals and past postmortems, with citations they can paste into tickets.",
  },
  {
    icon: Lock,
    title: "Compliance & policy",
    body: "Tax law, GST circulars, security policies and HR rules, where quoting the exact clause matters.",
  },
];

function CountUp({ to, suffix = "" }: { to: number; suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const reduce = useReducedMotion();
  const [n, setN] = useState(reduce ? to : 0);
  useEffect(() => {
    if (!inView || reduce) return;
    let raf = 0;
    const start = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / 1200);
      setN(Math.round(to * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inView, reduce, to]);
  return (
    <span ref={ref} className="tabular-nums">
      {n}
      {suffix}
    </span>
  );
}

export function LandingPage() {
  return (
    <div className="min-h-full overflow-x-hidden bg-white dark:bg-slate-950">
      <header className="sticky top-0 z-30 border-b border-slate-200/60 bg-white/70 backdrop-blur-lg dark:border-slate-800/60 dark:bg-slate-950/70">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <Logo className="text-lg" />
          <nav className="flex items-center gap-2">
            <ThemeToggle />
            <Link
              to="/login"
              className="rounded-lg px-3 py-2 text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              Sign in
            </Link>
            <Link
              to="/register"
              className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
            >
              Get started
            </Link>
          </nav>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="relative isolate">
          <div
            aria-hidden
            className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top_right,rgb(99_102_241/0.18),transparent_55%),radial-gradient(ellipse_at_bottom_left,rgb(34_211_238/0.12),transparent_50%)]"
          />
          <div className="mx-auto grid max-w-6xl items-center gap-6 px-4 pb-10 pt-10 lg:grid-cols-[1.05fr_1fr] lg:pt-16">
            <motion.div
              initial="hidden"
              animate="show"
              variants={{ show: { transition: { staggerChildren: 0.08 } } }}
              className="text-center lg:text-left"
            >
              <motion.p
                variants={fadeUp}
                className="inline-flex items-center gap-1.5 rounded-full border border-brand-200 bg-brand-50/80 px-3 py-1 text-xs font-medium text-brand-700 dark:border-brand-900 dark:bg-brand-950/60 dark:text-brand-300"
              >
                <Sparkles className="size-3.5" aria-hidden /> Retrieval-augmented AI with page-level
                citations
              </motion.p>
              <motion.h1
                variants={fadeUp}
                className="mt-6 text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl"
              >
                Ask your documents.
                <br />
                <span className="bg-gradient-to-r from-brand-600 via-violet-500 to-cyan-500 bg-clip-text text-transparent">
                  Verify every answer.
                </span>
              </motion.h1>
              <motion.p
                variants={fadeUp}
                className="mx-auto mt-5 max-w-xl text-lg text-slate-600 lg:mx-0 dark:text-slate-400"
              >
                Upload tax law, GST circulars, engineering runbooks or company policies. DocMind
                answers in seconds and links every claim to the exact page it came from.
              </motion.p>
              <motion.div
                variants={fadeUp}
                className="mx-auto mt-8 flex max-w-lg flex-col items-stretch gap-3 sm:flex-row sm:items-start lg:mx-0"
              >
                <Link
                  to="/register"
                  className="inline-flex h-11 items-center justify-center gap-2 whitespace-nowrap rounded-lg bg-brand-600 px-5 text-sm font-medium text-white shadow-lg shadow-brand-600/25 transition hover:-translate-y-0.5 hover:bg-brand-700"
                >
                  Create free account <ArrowRight className="size-4" aria-hidden />
                </Link>
                <DemoButton className="" buttonClassName="h-11 w-full whitespace-nowrap px-5" />
              </motion.div>
              <motion.p variants={fadeUp} className="mt-4 text-xs text-slate-500">
                No sign-up needed for the demo · Runs entirely on free, open-source models
              </motion.p>
            </motion.div>
            <div className="relative h-[340px] sm:h-[440px] lg:h-[540px]">
              <Suspense
                fallback={
                  <div className="absolute inset-10 animate-pulse rounded-full bg-brand-500/10 blur-3xl" />
                }
              >
                <HeroScene />
              </Suspense>
            </div>
          </div>
        </section>

        {/* Stats */}
        <section className="border-y border-slate-200 bg-slate-50/70 dark:border-slate-800 dark:bg-slate-900/30">
          <dl className="mx-auto grid max-w-6xl grid-cols-2 gap-6 px-4 py-8 text-center md:grid-cols-4">
            {[
              { n: 2, s: "", label: "search engines fused (vector + keyword)" },
              { n: 20, s: "→6", label: "candidates reranked to the best six" },
              { n: 384, s: "-d", label: "embeddings, run on CPU" },
              { n: 0, s: " ₹", label: "hosting cost on free tiers" },
            ].map((x) => (
              <div key={x.label}>
                <dt className="sr-only">{x.label}</dt>
                <dd className="text-3xl font-bold text-brand-600">
                  <CountUp to={x.n} suffix={x.s} />
                </dd>
                <p className="mt-1 text-xs text-slate-500">{x.label}</p>
              </div>
            ))}
          </dl>
        </section>

        {/* Pipeline */}
        <section className="mx-auto max-w-6xl px-4 py-20">
          <motion.div
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-80px" }}
            variants={fadeUp}
            className="text-center"
          >
            <h2 className="text-3xl font-semibold tracking-tight">From PDF to cited answer</h2>
            <p className="mx-auto mt-3 max-w-2xl text-slate-600 dark:text-slate-400">
              The same pipeline production RAG systems use: background ingestion, hybrid retrieval,
              a reranker, and a relevance gate that refuses to guess.
            </p>
          </motion.div>
          <motion.ol
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-80px" }}
            variants={{ show: { transition: { staggerChildren: 0.09 } } }}
            className="relative mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-7"
          >
            <motion.div
              aria-hidden
              className="absolute left-0 right-0 top-7 hidden h-0.5 origin-left bg-gradient-to-r from-brand-500 via-violet-500 to-cyan-500 lg:block"
              initial={{ scaleX: 0 }}
              whileInView={{ scaleX: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 1.4, ease: "easeInOut" }}
            />
            {pipeline.map(({ icon: Icon, label, detail }, i) => (
              <motion.li
                key={label}
                variants={fadeUp}
                className="relative flex flex-col items-center text-center"
              >
                <span className="relative z-10 flex size-14 items-center justify-center rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
                  <Icon className="size-6 text-brand-600" aria-hidden />
                  <span className="absolute -right-1.5 -top-1.5 flex size-5 items-center justify-center rounded-full bg-brand-600 text-[10px] font-bold text-white">
                    {i + 1}
                  </span>
                </span>
                <p className="mt-3 text-sm font-semibold">{label}</p>
                <p className="text-xs text-slate-500">{detail}</p>
              </motion.li>
            ))}
          </motion.ol>
        </section>

        {/* Example */}
        <section className="mx-auto max-w-3xl px-4 pb-8">
          <TiltCard className="rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-xl shadow-brand-900/5 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-sm font-medium text-slate-500">Example answer</p>
            <div className="mt-3 flex justify-end">
              <div className="rounded-2xl rounded-br-md bg-brand-600 px-4 py-2 text-sm text-white">
                How much can I claim under Section 80D for my senior-citizen parents?
              </div>
            </div>
            <div className="mt-4 text-sm leading-relaxed">
              You can claim up to <strong>₹50,000</strong> for health-insurance premiums paid for
              senior-citizen parents
              <span className="mx-0.5 rounded bg-brand-100 px-1 text-[11px] font-semibold text-brand-800 dark:bg-brand-950 dark:text-brand-300">
                1
              </span>
              , on top of ₹25,000 for yourself and your family, so the total can reach{" "}
              <strong>₹1,00,000</strong>
              <span className="mx-0.5 rounded bg-brand-100 px-1 text-[11px] font-semibold text-brand-800 dark:bg-brand-950 dark:text-brand-300">
                1
              </span>
              .
            </div>
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <span className="rounded-md bg-brand-100 px-2 py-1 text-brand-800 dark:bg-brand-950 dark:text-brand-300">
                [1] Income-Tax-Deductions-Guide.pdf · p. 2
              </span>
            </div>
          </TiltCard>
        </section>

        {/* Features */}
        <section className="py-20">
          <div className="mx-auto max-w-6xl px-4">
            <motion.h2
              initial="hidden"
              whileInView="show"
              viewport={{ once: true }}
              variants={fadeUp}
              className="text-center text-3xl font-semibold tracking-tight"
            >
              Built like production software
            </motion.h2>
            <motion.ul
              initial="hidden"
              whileInView="show"
              viewport={{ once: true, margin: "-60px" }}
              variants={{ show: { transition: { staggerChildren: 0.07 } } }}
              className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
            >
              {features.map(({ icon: Icon, title, body }) => (
                <motion.li key={title} variants={fadeUp}>
                  <TiltCard className="h-full rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                    <span className="flex size-11 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-violet-500 text-white shadow-md shadow-brand-500/30">
                      <Icon className="size-5" aria-hidden />
                    </span>
                    <h3 className="mt-4 font-semibold">{title}</h3>
                    <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{body}</p>
                  </TiltCard>
                </motion.li>
              ))}
            </motion.ul>
          </div>
        </section>

        {/* Use cases */}
        <section className="border-t border-slate-200 bg-gradient-to-b from-slate-50 to-white py-20 dark:border-slate-800 dark:from-slate-900/40 dark:to-slate-950">
          <div className="mx-auto max-w-6xl px-4">
            <motion.div
              initial="hidden"
              whileInView="show"
              viewport={{ once: true }}
              variants={fadeUp}
              className="text-center"
            >
              <h2 className="text-3xl font-semibold tracking-tight">
                Not just for tax: built for tech teams too
              </h2>
              <p className="mx-auto mt-3 max-w-2xl text-slate-600 dark:text-slate-400">
                Any team with long documents and questions that need a trustworthy source. The demo
                includes an engineering handbook workspace.
              </p>
            </motion.div>
            <div className="mt-12 grid gap-6 md:grid-cols-2">
              {useCases.map(({ icon: Icon, title, body }, i) => (
                <motion.div
                  key={title}
                  initial={{ opacity: 0, x: i % 2 ? 24 : -24 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true, margin: "-60px" }}
                  transition={{ duration: 0.5, delay: (i % 2) * 0.08 }}
                  className="flex gap-4 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
                >
                  <Icon className="mt-0.5 size-6 shrink-0 text-brand-600" aria-hidden />
                  <div>
                    <h3 className="font-semibold">{title}</h3>
                    <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{body}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="px-4 py-20">
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="relative mx-auto max-w-4xl overflow-hidden rounded-3xl bg-gradient-to-br from-brand-600 via-violet-600 to-indigo-800 px-8 py-14 text-center text-white shadow-2xl shadow-brand-900/30"
          >
            <div
              aria-hidden
              className="absolute -right-20 -top-20 size-72 rounded-full bg-cyan-400/20 blur-3xl"
            />
            <h2 className="relative text-3xl font-semibold tracking-tight">
              See it answer, then check the source
            </h2>
            <p className="relative mx-auto mt-3 max-w-xl text-brand-100">
              The demo workspace is loaded with tax, GST and engineering documents and real
              conversations.
            </p>
            <div className="relative mx-auto mt-8 flex max-w-md flex-col gap-3 sm:flex-row sm:justify-center">
              <Link
                to="/register"
                className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-white px-5 text-sm font-semibold text-brand-700 hover:bg-brand-50"
              >
                Create free account <ArrowRight className="size-4" aria-hidden />
              </Link>
              <DemoButton
                className=""
                buttonClassName="h-11 w-full whitespace-nowrap border-white/40 bg-white/10 px-5 text-white hover:bg-white/20 dark:border-white/40 dark:bg-white/10"
              />
            </div>
          </motion.div>
        </section>
      </main>

      <footer className="border-t border-slate-200 py-8 text-center text-sm text-slate-500 dark:border-slate-800">
        DocMind · FastAPI · PostgreSQL + pgvector · Redis · React + Three.js ·{" "}
        <a
          className="underline hover:text-slate-800 dark:hover:text-slate-200"
          href="https://github.com/Rounak-Raghuwanshi/docmind"
        >
          Source on GitHub
        </a>
      </footer>
    </div>
  );
}
