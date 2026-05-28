from collections import Counter, defaultdict
from sqlalchemy.orm import Session

from models import SurveyAnswer, SurveyResponse
from services import compute_class_model

DISC = ["S", "T", "E", "M"]


def _rank_four(avgs: dict[str, float]) -> list[str]:
    items = [(c, avgs[c]) for c in DISC]
    items.sort(key=lambda x: (-x[1], DISC.index(x[0])))
    return [c for c, _ in items]


def _stem_avgs_from_base(base: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    for code, key in (("S", "s_avg"), ("T", "t_avg"), ("E", "e_avg"), ("M", "m_avg")):
        v = base.get(key)
        out[code] = float(v) if v is not None else float("-inf")
    return out


def _normalize_article_ranking(order: list[str], avgs: dict[str, float]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for x in order:
        L = (x or "").strip().upper()
        if L not in DISC or L in seen:
            continue
        seen.add(L)
        result.append(L)
    missing = [c for c in DISC if c not in seen]
    missing.sort(key=lambda c: (-avgs.get(c, float("-inf")), DISC.index(c)))
    result.extend(missing)
    return result


def _mode_at_position(rankings_per_k: list[list[str]], pos: int) -> str:
    letters = [r[pos] for r in rankings_per_k if len(r) > pos]
    if not letters:
        return ""
    cnt = Counter(letters)
    best = max(cnt.values())
    candidates = [L for L, n in cnt.items() if n == best]
    if len(candidates) == 1:
        return candidates[0]
    return min(candidates, key=lambda L: DISC.index(L))


def compute_class_model_article(db: Session, class_id: str, survey_id: str) -> dict:
    base = compute_class_model(db, class_id, survey_id)
    if not base:
        return {}
    responses = (
        db.query(SurveyResponse)
        .filter(
            SurveyResponse.survey_id == survey_id,
            SurveyResponse.class_id == class_id,
        )
        .all()
    )
    if not responses:
        return {**base, "ranking_article": "", "k_table": []}

    response_ids = [r.id for r in responses]
    all_answers = (
        db.query(SurveyAnswer)
        .filter(SurveyAnswer.response_id.in_(response_ids))
        .all()
    )
    by_resp: dict = defaultdict(dict)
    for a in all_answers:
        by_resp[a.response_id][a.question_code] = a.value

    rankings_per_k: list[list[str]] = []
    for k in range(1, 6):
        avgs: dict[str, float] = {}
        for d in DISC:
            code = f"{d}{k}"
            vals = []
            for r in responses:
                v = by_resp[r.id].get(code)
                if v is not None:
                    vals.append(v)
            avgs[d] = sum(vals) / len(vals) if vals else 0.0
        rankings_per_k.append(_rank_four(avgs))
    raw_order = [_mode_at_position(rankings_per_k, p) for p in range(4)]
    avgs = _stem_avgs_from_base(base)
    final_order = _normalize_article_ranking(raw_order, avgs)
    return {
        **base,
        "ranking_article": "-".join(final_order),
        "k_table": [
            {"k": f"K{i + 1}", "order": rankings_per_k[i]}
            for i in range(5)
        ],
    }
