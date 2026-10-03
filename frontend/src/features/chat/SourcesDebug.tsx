import { useRetrievalDebug } from "@/api/chat";
import { ErrorState, Spinner } from "@/components/ui";
import { formatMs } from "@/lib/format";

const fmt = (v: number | null, digits = 3) =>
  v === null || v === undefined ? "—" : v.toFixed(digits);

/** Retrieval debug view: every retrieved chunk with its rank in each list and every score. */
export function SourcesDebug({ messageId }: { messageId: string }) {
  const { data, isLoading, error } = useRetrievalDebug(messageId, true);
  if (isLoading) return <Spinner className="m-3" />;
  if (error) return <ErrorState error={error} />;
  if (!data) return null;
  return (
    <div className="mt-3 rounded-lg border border-slate-200 text-xs dark:border-slate-800">
      <div className="flex flex-wrap gap-x-4 gap-y-1 border-b border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-800 dark:bg-slate-900">
        <span>Retrieval {formatMs(data.retrieval_ms)}</span>
        <span>Rerank {formatMs(data.rerank_ms)}</span>
        {data.rewritten_question && (
          <span className="min-w-0 truncate">
            Searched for: <em>“{data.rewritten_question}”</em>
          </span>
        )}
      </div>
      {data.chunks.length === 0 ? (
        <p className="p-3 text-slate-500">
          This answer came from the cache or no passages were retrieved.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="text-slate-500">
              <tr>
                <th className="px-3 py-1.5 font-medium">#</th>
                <th className="px-3 py-1.5 font-medium">Passage</th>
                <th
                  className="px-3 py-1.5 font-medium"
                  title="Rank in vector search (cosine similarity)"
                >
                  Vector
                </th>
                <th
                  className="px-3 py-1.5 font-medium"
                  title="Rank in full-text search (ts_rank_cd)"
                >
                  Keyword
                </th>
                <th className="px-3 py-1.5 font-medium" title="Reciprocal Rank Fusion score">
                  RRF
                </th>
                <th className="px-3 py-1.5 font-medium" title="Cross-encoder relevance (logit)">
                  Rerank
                </th>
              </tr>
            </thead>
            <tbody>
              {data.chunks.map((c, i) => (
                <tr
                  key={c.chunk_id}
                  className="border-t border-slate-100 align-top dark:border-slate-800"
                >
                  <td className="px-3 py-2 font-semibold">{i + 1}</td>
                  <td className="max-w-md px-3 py-2">
                    <p className="font-medium">
                      {c.filename} · p. {c.page_start}
                      {c.page_end !== c.page_start && `–${c.page_end}`}
                    </p>
                    <p className="mt-0.5 line-clamp-3 text-slate-500">{c.content}</p>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums">
                    {c.vector_rank ? `#${c.vector_rank} (${fmt(c.vector_score)})` : "—"}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums">
                    {c.keyword_rank ? `#${c.keyword_rank} (${fmt(c.keyword_score)})` : "—"}
                  </td>
                  <td className="px-3 py-2 tabular-nums">{fmt(c.rrf_score, 4)}</td>
                  <td className="px-3 py-2 font-semibold tabular-nums">{fmt(c.rerank_score, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
