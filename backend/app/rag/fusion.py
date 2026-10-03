from collections.abc import Hashable, Sequence


def reciprocal_rank_fusion[T: Hashable](
    ranked_lists: Sequence[Sequence[T]], k: int = 60
) -> list[tuple[T, float]]:
    """Fuse ranked lists using only rank positions: score(d) = sum 1 / (k + rank).

    Raw scores (cosine similarity vs ts_rank_cd) live on unrelated scales, so adding them is
    meaningless; RRF needs no calibration. Ranks are 1-based. Ties keep first-seen order.
    """
    scores: dict[T, float] = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
