import { motion } from "framer-motion";
import { Box, Lightbulb, SearchX, Sparkles } from "lucide-react";
import { lazy, Suspense, useCallback, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from "recharts";
import { useInsights } from "@/api/chat";
import type { EmbeddingPoint, Insights } from "@/api/types";
import { EmptyState, ErrorState, Skeleton, Spinner } from "@/components/ui";
import { useCurrentWorkspace } from "@/features/workspaces/useWorkspaceContext";
import { cn } from "@/lib/format";

const EmbeddingMap = lazy(() =>
  import("./EmbeddingMap").then((m) => ({ default: m.EmbeddingMap })),
);

const SLOTS = ["var(--series-1)", "var(--series-2)", "var(--series-3)"];
const SLOT_VARS = ["--series-1", "--series-2", "--series-3"];

function readVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

const axisProps = {
  tick: { fill: "var(--chart-muted)", fontSize: 11 },
  axisLine: false,
  tickLine: false,
} as const;

function Card({
  title,
  icon,
  children,
  className,
  aside,
}: {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  aside?: React.ReactNode;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.45, ease: "easeOut" }}
      className={cn(
        "rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950",
        className,
      )}
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          {icon}
          {title}
        </h2>
        {aside}
      </div>
      {children}
    </motion.section>
  );
}

function SimpleTooltip({
  active,
  payload,
  label,
  labelFormat,
}: TooltipProps<number, string> & { labelFormat?: (l: string) => string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-md dark:border-slate-700 dark:bg-slate-900">
      <p className="mb-1 font-medium">{labelFormat ? labelFormat(String(label)) : label}</p>
      {payload.map((p) => (
        <p
          key={String(p.dataKey)}
          className="flex items-center gap-2 text-slate-600 dark:text-slate-300"
        >
          <span
            className="inline-block size-2 rounded-full"
            style={{ background: p.color }}
            aria-hidden
          />
          {p.name}:{" "}
          <span className="font-medium tabular-nums text-slate-900 dark:text-slate-100">
            {p.value}
          </span>
        </p>
      ))}
    </div>
  );
}

/** Top three documents (by chunks) get identity colours; the rest fold into "Other". */
function useMapColors(data: Insights) {
  const [focus, setFocus] = useState<string | null>(null);
  const ranked = useMemo(
    () => [...data.coverage].sort((a, b) => b.chunks - a.chunks),
    [data.coverage],
  );
  const slotOf = useMemo(() => {
    const m = new Map<string, number>();
    ranked.slice(0, 3).forEach((d, i) => m.set(d.document_id, i));
    return m;
  }, [ranked]);

  const colorOf = useCallback(
    (p: EmbeddingPoint) => {
      const other = readVar("--series-other");
      if (focus) {
        const on = p.document_id === focus;
        return { color: on ? readVar("--series-1") : other, dim: !on };
      }
      const slot = slotOf.get(p.document_id);
      return { color: slot === undefined ? other : readVar(SLOT_VARS[slot]!), dim: false };
    },
    [focus, slotOf],
  );

  return { ranked, slotOf, focus, setFocus, colorOf };
}

function MapCard({ data }: { data: Insights }) {
  const { ranked, slotOf, focus, setFocus, colorOf } = useMapColors(data);
  const kept = data.explained_variance.reduce((a, b) => a + b, 0);
  return (
    <Card
      title="Embedding space (3D)"
      icon={<Box className="size-4 text-brand-600" aria-hidden />}
      className="lg:col-span-2"
      aside={
        <span className="text-xs text-slate-500">
          {data.points.length} chunks · PCA keeps {Math.round(kept * 100)}% of the variation
        </span>
      }
    >
      <div className="grid gap-4 lg:grid-cols-[1fr_15rem]">
        <div
          className="h-[26rem] overflow-hidden rounded-xl bg-slate-50 dark:bg-slate-900/60"
          aria-label="3D scatter plot of document chunks"
        >
          {data.points.length ? (
            <Suspense
              fallback={
                <div className="flex h-full items-center justify-center">
                  <Spinner />
                </div>
              }
            >
              <EmbeddingMap points={data.points} colorOf={colorOf} />
            </Suspense>
          ) : (
            <EmptyState title="No indexed passages yet">
              Upload documents to see their map.
            </EmptyState>
          )}
        </div>
        <div className="text-sm">
          <p className="text-xs leading-relaxed text-slate-500">
            Each dot is one passage. Nearby dots mean similar meaning; this is the space vector
            search looks in. Drag to rotate, scroll to zoom, hover to read. Click a document to
            highlight it.
          </p>
          <ul className="mt-3 space-y-1" aria-label="Documents">
            {ranked.map((d) => {
              const slot = slotOf.get(d.document_id);
              const swatch = focus
                ? focus === d.document_id
                  ? SLOTS[0]
                  : "var(--series-other)"
                : slot === undefined
                  ? "var(--series-other)"
                  : SLOTS[slot];
              return (
                <li key={d.document_id}>
                  <button
                    type="button"
                    aria-pressed={focus === d.document_id}
                    onClick={() => setFocus(focus === d.document_id ? null : d.document_id)}
                    className={cn(
                      "flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left hover:bg-slate-100 dark:hover:bg-slate-800",
                      focus === d.document_id && "bg-slate-100 dark:bg-slate-800",
                    )}
                  >
                    <span
                      className="size-2.5 shrink-0 rounded-full"
                      style={{ background: swatch }}
                      aria-hidden
                    />
                    <span className="min-w-0 flex-1 truncate text-xs" title={d.filename}>
                      {d.filename}
                    </span>
                    <span className="text-xs tabular-nums text-slate-500">{d.chunks}</span>
                  </button>
                </li>
              );
            })}
          </ul>
          {ranked.length > 3 && !focus && (
            <p className="mt-2 text-[11px] text-slate-500">
              Grey = other documents (only three colours are used so they stay distinguishable).
            </p>
          )}
        </div>
      </div>
    </Card>
  );
}

function SourcesCard({ data }: { data: Insights }) {
  const s = data.retrieval_sources;
  const rows = [
    { name: "Both searches", value: s.both },
    { name: "Vector only", value: s.vector_only },
    { name: "Keyword only", value: s.keyword_only },
  ];
  const total = rows.reduce((a, r) => a + r.value, 0);
  return (
    <Card
      title="How cited passages were found"
      icon={<Sparkles className="size-4 text-brand-600" aria-hidden />}
    >
      {total === 0 ? (
        <p className="text-sm text-slate-500">No cited answers yet.</p>
      ) : (
        <>
          <div className="h-44">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={rows}
                layout="vertical"
                margin={{ top: 0, right: 40, left: 8, bottom: 0 }}
                barCategoryGap={8}
              >
                <XAxis type="number" hide allowDecimals={false} />
                <YAxis type="category" dataKey="name" {...axisProps} width={96} />
                <Tooltip
                  content={<SimpleTooltip />}
                  cursor={{ fill: "var(--chart-grid)", opacity: 0.5 }}
                />
                <Bar
                  dataKey="value"
                  name="Passages"
                  fill="var(--series-1)"
                  radius={[0, 4, 4, 0]}
                  maxBarSize={22}
                  label={{ position: "right", fill: "var(--chart-muted)", fontSize: 11 }}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Passages found by only one method would have been missed without hybrid search:{" "}
            <strong className="text-slate-700 dark:text-slate-300">
              {Math.round(((s.vector_only + s.keyword_only) / total) * 100)}%
            </strong>
            .
          </p>
        </>
      )}
    </Card>
  );
}

function ConfidenceCard({ data }: { data: Insights }) {
  const rows = data.confidence.map((b) => ({ ...b, label: `${b.start}` }));
  const any = rows.some((r) => r.answered || r.not_found);
  // Bins are 2 wide; place the gate line on the bin that contains the threshold.
  const gateBin = rows.find(
    (r) => data.relevance_threshold >= r.start && data.relevance_threshold < r.end,
  )?.label;
  return (
    <Card
      title="Answer confidence (reranker score)"
      icon={<Lightbulb className="size-4 text-brand-600" aria-hidden />}
      aside={
        <div className="flex gap-3 text-xs text-slate-600 dark:text-slate-400">
          <span className="flex items-center gap-1.5">
            <span
              className="size-2.5 rounded-sm"
              style={{ background: "var(--series-1)" }}
              aria-hidden
            />
            Answered
          </span>
          <span className="flex items-center gap-1.5">
            <span
              className="size-2.5 rounded-sm"
              style={{ background: "var(--series-2)" }}
              aria-hidden
            />
            “Not found”
          </span>
        </div>
      }
    >
      {!any ? (
        <p className="text-sm text-slate-500">No answered questions yet.</p>
      ) : (
        <>
          <div className="h-44">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={rows}
                margin={{ top: 14, right: 8, left: -24, bottom: 0 }}
                barGap={2}
                barCategoryGap={4}
              >
                <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
                <XAxis dataKey="label" {...axisProps} interval={1} />
                <YAxis allowDecimals={false} {...axisProps} />
                <Tooltip
                  content={<SimpleTooltip labelFormat={(l) => `Score ${l} to ${Number(l) + 2}`} />}
                  cursor={{ fill: "var(--chart-grid)", opacity: 0.5 }}
                />
                {gateBin && (
                  <ReferenceLine
                    x={gateBin}
                    stroke="var(--chart-muted)"
                    strokeDasharray="4 3"
                    label={{
                      value: "gate",
                      position: "top",
                      fill: "var(--chart-muted)",
                      fontSize: 10,
                    }}
                  />
                )}
                <Bar
                  dataKey="answered"
                  name="Answered"
                  fill="var(--series-1)"
                  radius={[4, 4, 0, 0]}
                />
                <Bar
                  dataKey="not_found"
                  name="Not found"
                  fill="var(--series-2)"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            The cross-encoder scores how well the best passage matches each question. Below the gate
            ({data.relevance_threshold}), DocMind says “not found” instead of asking the LLM.
          </p>
        </>
      )}
    </Card>
  );
}

function GapsCard({ data }: { data: Insights }) {
  return (
    <Card title="Knowledge gaps" icon={<SearchX className="size-4 text-brand-600" aria-hidden />}>
      {data.knowledge_gaps.length === 0 ? (
        <p className="text-sm text-slate-500">
          Every question so far was answered from your documents.
        </p>
      ) : (
        <>
          <p className="mb-3 text-xs text-slate-500">
            Questions your documents couldn't answer: a to-do list of what to upload next.
          </p>
          <ul className="divide-y divide-slate-100 text-sm dark:divide-slate-800">
            {data.knowledge_gaps.map((g) => (
              <li key={g.question} className="flex items-center gap-3 py-2">
                <span className="min-w-0 flex-1">{g.question}</span>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs tabular-nums text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  ×{g.count}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </Card>
  );
}

function CoverageCard({ data }: { data: Insights }) {
  const max = Math.max(1, ...data.coverage.map((d) => d.answers));
  return (
    <Card title="Document coverage">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Passages and answers per document</caption>
          <thead className="text-xs text-slate-500">
            <tr>
              <th className="py-1.5 pr-3 font-medium">Document</th>
              <th className="py-1.5 pr-3 text-right font-medium">Pages</th>
              <th className="py-1.5 pr-3 text-right font-medium">Passages</th>
              <th className="w-1/3 py-1.5 font-medium">Answers citing it</th>
            </tr>
          </thead>
          <tbody>
            {data.coverage.map((d) => (
              <tr key={d.document_id} className="border-t border-slate-100 dark:border-slate-800">
                <td className="max-w-[16rem] truncate py-2 pr-3" title={d.filename}>
                  {d.filename}
                </td>
                <td className="py-2 pr-3 text-right tabular-nums">{d.pages ?? "—"}</td>
                <td className="py-2 pr-3 text-right tabular-nums">{d.chunks}</td>
                <td className="py-2">
                  <div className="flex items-center gap-2">
                    <div className="h-2 flex-1 rounded-full bg-slate-100 dark:bg-slate-800">
                      <div
                        className="h-2 rounded-full"
                        style={{
                          width: `${(d.answers / max) * 100}%`,
                          background: "var(--series-1)",
                        }}
                      />
                    </div>
                    <span className="w-6 text-right text-xs tabular-nums">{d.answers}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

export function InsightsPage() {
  const ws = useCurrentWorkspace();
  const [days, setDays] = useState(90);
  const { data, isLoading, error, refetch } = useInsights(ws.id, days);

  return (
    <main className="h-full overflow-y-auto bg-slate-50/60 dark:bg-slate-950">
      <div className="mx-auto max-w-6xl space-y-6 px-4 py-8">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-semibold">
              <Sparkles className="size-6 text-brand-600" aria-hidden /> AI insights
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              What the AI sees in {ws.name}, and how retrieval behaves on real questions.
            </p>
          </div>
          <div
            role="group"
            aria-label="Time range"
            className="flex rounded-lg border border-slate-300 bg-white p-0.5 dark:border-slate-700 dark:bg-slate-900"
          >
            {[30, 90, 365].map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => setDays(d)}
                aria-pressed={days === d}
                className={cn(
                  "rounded-md px-3 py-1 text-sm",
                  days === d
                    ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                    : "text-slate-600 dark:text-slate-400",
                )}
              >
                {d === 365 ? "1y" : `${d}d`}
              </button>
            ))}
          </div>
        </div>

        {error ? (
          <ErrorState error={error} onRetry={refetch} />
        ) : isLoading || !data ? (
          <div className="grid gap-6 lg:grid-cols-2">
            <Skeleton className="h-28 lg:col-span-2" />
            <Skeleton className="h-[30rem] lg:col-span-2" />
          </div>
        ) : (
          <div className="grid gap-6 lg:grid-cols-2">
            {data.highlights.length > 0 && (
              <Card
                title="Findings"
                icon={<Sparkles className="size-4 text-brand-600" aria-hidden />}
                className="bg-gradient-to-br from-brand-50 to-white lg:col-span-2 dark:from-brand-950/40 dark:to-slate-950"
              >
                <ul className="space-y-2 text-sm">
                  {data.highlights.map((h, i) => (
                    <motion.li
                      key={h}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.1 * i }}
                      className="flex gap-2"
                    >
                      <span
                        className="mt-1.5 size-1.5 shrink-0 rounded-full bg-brand-500"
                        aria-hidden
                      />
                      {h}
                    </motion.li>
                  ))}
                </ul>
              </Card>
            )}
            <MapCard data={data} />
            <SourcesCard data={data} />
            <ConfidenceCard data={data} />
            <GapsCard data={data} />
            <CoverageCard data={data} />
          </div>
        )}
      </div>
    </main>
  );
}
