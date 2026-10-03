import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def workspace_analytics(
    session: AsyncSession, workspace_id: uuid.UUID, days: int
) -> dict[str, Any]:
    since = datetime.now(UTC) - timedelta(days=days)
    params = {"ws": workspace_id, "since": since}

    daily = (
        (
            await session.execute(
                text(
                    """
                SELECT date_trunc('day', m.created_at AT TIME ZONE 'UTC')::date AS day,
                       count(*) AS questions,
                       avg(m.total_ms) FILTER (WHERE NOT m.cached AND NOT m.not_found)
                           AS avg_total_ms,
                       avg(m.first_token_ms) FILTER (WHERE NOT m.cached AND NOT m.not_found)
                           AS avg_first_token_ms,
                       count(*) FILTER (WHERE m.not_found) AS not_found
                FROM messages m JOIN conversations c ON c.id = m.conversation_id
                WHERE c.workspace_id = :ws AND m.role = 'assistant' AND m.created_at >= :since
                GROUP BY 1 ORDER BY 1
                """
                ),
                params,
            )
        )
        .mappings()
        .all()
    )

    totals = (
        (
            await session.execute(
                text(
                    """
                SELECT count(*) AS total,
                       avg(m.total_ms) FILTER (WHERE NOT m.cached AND NOT m.not_found)
                           AS avg_total_ms,
                       avg(m.first_token_ms) FILTER (WHERE NOT m.cached AND NOT m.not_found)
                           AS avg_first_token_ms,
                       count(*) FILTER (WHERE m.not_found) AS not_found,
                       count(*) FILTER (WHERE m.cached) AS cached
                FROM messages m JOIN conversations c ON c.id = m.conversation_id
                WHERE c.workspace_id = :ws AND m.role = 'assistant' AND m.created_at >= :since
                """
                ),
                params,
            )
        )
        .mappings()
        .one()
    )

    feedback = (
        (
            await session.execute(
                text(
                    """
                SELECT count(*) FILTER (WHERE f.rating = 1) AS up,
                       count(*) FILTER (WHERE f.rating = -1) AS down
                FROM message_feedback f
                JOIN messages m ON m.id = f.message_id
                JOIN conversations c ON c.id = m.conversation_id
                WHERE c.workspace_id = :ws AND f.created_at >= :since
                """
                ),
                params,
            )
        )
        .mappings()
        .one()
    )

    top_docs = (
        (
            await session.execute(
                text(
                    """
                SELECT cit->>'document_id' AS document_id,
                       max(cit->>'filename') AS filename,
                       count(DISTINCT m.id) AS citations
                FROM messages m
                JOIN conversations c ON c.id = m.conversation_id
                CROSS JOIN LATERAL jsonb_array_elements(m.citations) AS cit
                WHERE c.workspace_id = :ws AND m.role = 'assistant' AND m.created_at >= :since
                GROUP BY 1 ORDER BY 3 DESC LIMIT 5
                """
                ),
                params,
            )
        )
        .mappings()
        .all()
    )

    total = int(totals["total"] or 0)
    up, down = int(feedback["up"] or 0), int(feedback["down"] or 0)
    return {
        "days": days,
        "total_questions": total,
        "avg_total_ms": _f(totals["avg_total_ms"]),
        "avg_first_token_ms": _f(totals["avg_first_token_ms"]),
        "not_found_rate": (int(totals["not_found"]) / total) if total else None,
        "cache_hit_rate": (int(totals["cached"]) / total) if total else None,
        "feedback_up": up,
        "feedback_down": down,
        "feedback_score": (up / (up + down)) if (up + down) else None,
        "daily": [
            {
                "day": r["day"],
                "questions": int(r["questions"]),
                "avg_total_ms": _f(r["avg_total_ms"]),
                "avg_first_token_ms": _f(r["avg_first_token_ms"]),
                "not_found": int(r["not_found"]),
            }
            for r in daily
        ],
        "top_documents": [dict(r) for r in top_docs],
    }


def _f(v: Any) -> float | None:
    return round(float(v), 1) if v is not None else None
