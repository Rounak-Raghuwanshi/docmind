import { Table2, BarChart3 } from "lucide-react";
import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from "recharts";
import { useAnalytics } from "@/api/chat";
import type { Analytics } from "@/api/types";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui";
import { useCurrentWorkspace } from "@/features/workspaces/useWorkspaceContext";
import { cn, formatMs } from "@/lib/format";

const pct = (v: number | null) => (v === null ? "—" : `${Math.round(v * 100)}%`);
const dayLabel = (d: string) =>
  new Date(`${d}T00:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" });

function StatTile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

function ChartTooltip({
  active,
  payload,
  label,
  unit,
}: TooltipProps<number, string> & { unit: "ms" | "count" }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-md dark:border-slate-700 dark:bg-slate-900">
      <p className="mb-1 font-medium">{dayLabel(String(label))}</p>
      {payload.map((p) => (
        <p
          key={p.dataKey as string}
          className="flex items-center gap-2 text-slate-600 dark:text-slate-300"
        >
          <span
            className="inline-block size-2 rounded-full"
            style={{ background: p.color }}
            aria-hidden
          />
          {p.name}:{" "}
          <span className="font-medium tabular-nums text-slate-900 dark:text-slate-100">
            {unit === "ms" ? formatMs(p.value as number) : p.value}
          </span>
        </p>
      ))}
    </div>
  );
}

function ChartCard({
  title,
  children,
  legend,
}: {
  title: string;
  children: React.ReactNode;
  legend?: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-slate-200 p-5 dark:border-slate-800">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold">{title}</h2>
        {legend}
      </div>
      <div className="h-64">{children}</div>
    </section>
  );
}

function LegendItem({ color, label, dashed }: { color: string; label: string; dashed?: boolean }) {
  return (
    <span className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400">
      <svg width="16" height="8" aria-hidden>
        <line
          x1="0"
          y1="4"
          x2="16"
          y2="4"
          stroke={color}
          strokeWidth="2"
          strokeDasharray={dashed ? "4 3" : undefined}
        />
      </svg>
      {label}
    </span>
  );
}

const axisProps = {
  tick: { fill: "var(--chart-muted)", fontSize: 11 },
  axisLine: false,
  tickLine: false,
} as const;

function Charts({ data }: { data: Analytics }) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <ChartCard title="Questions per day">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data.daily}
            margin={{ top: 4, right: 8, left: -16, bottom: 0 }}
            barCategoryGap={2}
          >
            <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
            <XAxis dataKey="day" tickFormatter={dayLabel} {...axisProps} minTickGap={24} />
            <YAxis allowDecimals={false} {...axisProps} />
            <Tooltip
              content={<ChartTooltip unit="count" />}
              cursor={{ fill: "var(--chart-grid)", opacity: 0.5 }}
            />
            <Bar
              dataKey="questions"
              name="Questions"
              fill="var(--series-1)"
              radius={[4, 4, 0, 0]}
              maxBarSize={28}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
      <ChartCard
        title="Answer latency"
        legend={
          <div className="flex gap-3">
            <LegendItem color="var(--series-1)" label="Full answer" />
            <LegendItem color="var(--series-2)" label="First token" dashed />
          </div>
        }
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data.daily} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
            <XAxis dataKey="day" tickFormatter={dayLabel} {...axisProps} minTickGap={24} />
            <YAxis {...axisProps} tickFormatter={(v: number) => formatMs(v)} width={56} />
            <Tooltip
              content={<ChartTooltip unit="ms" />}
              cursor={{ stroke: "var(--chart-muted)", strokeDasharray: "3 3" }}
            />
            <Line
              type="monotone"
              dataKey="avg_total_ms"
              name="Full answer"
              stroke="var(--series-1)"
              strokeWidth={2}
              dot={{ r: 4, strokeWidth: 2, fill: "var(--chart-surface)" }}
              activeDot={{ r: 5 }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="avg_first_token_ms"
              name="First token"
              stroke="var(--series-2)"
              strokeWidth={2}
              strokeDasharray="5 4"
              dot={{ r: 4, strokeWidth: 2, fill: "var(--chart-surface)" }}
              activeDot={{ r: 5 }}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}

function DataTable({ data }: { data: Analytics }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Daily usage</caption>
        <thead className="bg-slate-50 text-xs text-slate-500 dark:bg-slate-900">
          <tr>
            <th className="px-4 py-2 font-medium">Day</th>
            <th className="px-4 py-2 text-right font-medium">Questions</th>
            <th className="px-4 py-2 text-right font-medium">Not found</th>
            <th className="px-4 py-2 text-right font-medium">Avg full answer</th>
            <th className="px-4 py-2 text-right font-medium">Avg first token</th>
          </tr>
        </thead>
        <tbody>
          {data.daily.map((d) => (
            <tr
              key={d.day}
              className="border-t border-slate-100 tabular-nums dark:border-slate-800"
            >
              <td className="px-4 py-2">{dayLabel(d.day)}</td>
              <td className="px-4 py-2 text-right">{d.questions}</td>
              <td className="px-4 py-2 text-right">{d.not_found}</td>
              <td className="px-4 py-2 text-right">{formatMs(d.avg_total_ms)}</td>
              <td className="px-4 py-2 text-right">{formatMs(d.avg_first_token_ms)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AnalyticsPage() {
  const ws = useCurrentWorkspace();
  const [days, setDays] = useState(30);
  const [view, setView] = useState<"charts" | "table">("charts");
  const { data, isLoading, error, refetch } = useAnalytics(ws.id, days);
  const maxCitations = Math.max(1, ...(data?.top_documents.map((d) => d.citations) ?? [1]));

  return (
    <main className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl space-y-6 px-4 py-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold">Analytics</h1>
            <p className="mt-1 text-sm text-slate-500">
              How {ws.name} is being used, and how well it answers.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div
              role="group"
              aria-label="Time range"
              className="flex rounded-lg border border-slate-300 p-0.5 dark:border-slate-700"
            >
              {[7, 30, 90].map((d) => (
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
                  {d}d
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={() => setView((v) => (v === "charts" ? "table" : "charts"))}
              className="flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-700"
            >
              {view === "charts" ? (
                <Table2 className="size-4" aria-hidden />
              ) : (
                <BarChart3 className="size-4" aria-hidden />
              )}
              {view === "charts" ? "Table view" : "Chart view"}
            </button>
          </div>
        </div>

        {error ? (
          <ErrorState error={error} onRetry={refetch} />
        ) : isLoading || !data ? (
          <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
            {Array.from({ length: 6 }, (_, i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
        ) : data.total_questions === 0 ? (
          <EmptyState icon={<BarChart3 className="size-10" />} title="No questions yet">
            Metrics appear here once people start asking questions in this workspace.
          </EmptyState>
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
              <StatTile
                label="Questions"
                value={String(data.total_questions)}
                hint={`last ${days} days`}
              />
              <StatTile
                label="Avg full answer"
                value={formatMs(data.avg_total_ms)}
                hint="generated answers"
              />
              <StatTile label="Avg first token" value={formatMs(data.avg_first_token_ms)} />
              <StatTile
                label="Not found"
                value={pct(data.not_found_rate)}
                hint="answered “not in documents”"
              />
              <StatTile label="Cache hits" value={pct(data.cache_hit_rate)} />
              <StatTile
                label="Helpful"
                value={pct(data.feedback_score)}
                hint={`${data.feedback_up} 👍 · ${data.feedback_down} 👎`}
              />
            </div>
            {view === "charts" ? <Charts data={data} /> : <DataTable data={data} />}
            <section className="rounded-2xl border border-slate-200 p-5 dark:border-slate-800">
              <h2 className="text-sm font-semibold">Most cited documents</h2>
              {data.top_documents.length === 0 ? (
                <p className="mt-3 text-sm text-slate-500">No citations yet.</p>
              ) : (
                <ol className="mt-4 space-y-3">
                  {data.top_documents.map((d) => (
                    <li
                      key={d.document_id}
                      className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 text-sm"
                    >
                      <span className="truncate">{d.filename}</span>
                      <span className="tabular-nums text-slate-600 dark:text-slate-400">
                        {d.citations} {d.citations === 1 ? "answer" : "answers"}
                      </span>
                      <div className="col-span-2 h-2 rounded-full bg-slate-100 dark:bg-slate-800">
                        <div
                          className="h-2 rounded-full"
                          style={{
                            width: `${(d.citations / maxCitations) * 100}%`,
                            background: "var(--series-1)",
                          }}
                        />
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </section>
          </>
        )}
      </div>
    </main>
  );
}
