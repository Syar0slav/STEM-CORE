from collections import defaultdict
from sqlalchemy.orm import Session
from uuid import UUID

from models import SurveyAnswer, SurveyResponse, ClassModel
from moodle_mapping import BLOCKS, MODEL_DISCIPLINES


def _finalize_stem_model(s_vals: list, t_vals: list, e_vals: list, m_vals: list) -> dict:
    s_avg = sum(s_vals) / len(s_vals) if s_vals else None
    t_avg = sum(t_vals) / len(t_vals) if t_vals else None
    e_avg = sum(e_vals) / len(e_vals) if e_vals else None
    m_avg = sum(m_vals) / len(m_vals) if m_vals else None
    scores = [("S", s_avg), ("T", t_avg), ("E", e_avg), ("M", m_avg)]
    scores = [(c, v) for c, v in scores if v is not None]
    scores.sort(key=lambda x: (-x[1], x[0]))
    ranking = "-".join(c for c, _ in scores)
    return {
        "s_avg": round(s_avg, 2) if s_avg else None,
        "t_avg": round(t_avg, 2) if t_avg else None,
        "e_avg": round(e_avg, 2) if e_avg else None,
        "m_avg": round(m_avg, 2) if m_avg else None,
        "ranking": ranking,
    }


def _extend_stem_from_by_code(
    by_code: dict,
    s_vals: list,
    t_vals: list,
    e_vals: list,
    m_vals: list,
) -> None:
    for block in BLOCKS:
        code = block["code"]
        if code not in MODEL_DISCIPLINES:
            continue
        qs = block["questions"]
        vals = [by_code.get(q) for q in qs if by_code.get(q) is not None]
        if code == "S":
            s_vals.extend(vals)
        elif code == "T":
            t_vals.extend(vals)
        elif code == "E":
            e_vals.extend(vals)
        elif code == "M":
            m_vals.extend(vals)


def _aggregate_from_responses(responses: list, by_resp_answers: dict) -> dict:
    s_vals, t_vals, e_vals, m_vals = [], [], [], []
    for r in responses:
        answers = by_resp_answers.get(r.id, [])
        by_code = {a.question_code: a.value for a in answers}
        _extend_stem_from_by_code(by_code, s_vals, t_vals, e_vals, m_vals)
    if not s_vals and not t_vals and not e_vals and not m_vals:
        return {}
    return _finalize_stem_model(s_vals, t_vals, e_vals, m_vals)


def compute_class_model(db: Session, class_id: str, survey_id: str) -> dict:
    out = compute_class_models_bulk(db, [class_id], survey_id)
    return out.get(class_id, {})


def compute_class_models_bulk(
    db: Session, class_ids: list[str], survey_id: str
) -> dict[str, dict]:
    """Один прохід по БД для кількох класів (той самий survey_id)."""
    if not class_ids:
        return {}
    su = UUID(survey_id)
    uuids = [UUID(cid) for cid in class_ids]
    responses = (
        db.query(SurveyResponse)
        .filter(
            SurveyResponse.survey_id == su,
            SurveyResponse.class_id.in_(uuids),
        )
        .all()
    )
    by_class: dict[str, list] = defaultdict(list)
    for r in responses:
        if r.class_id is None:
            continue
        by_class[str(r.class_id)].append(r)
    if not responses:
        return {cid: {} for cid in class_ids}

    resp_ids = [r.id for r in responses]
    all_answers = (
        db.query(SurveyAnswer).filter(SurveyAnswer.response_id.in_(resp_ids)).all()
    )
    by_resp: dict = defaultdict(list)
    for a in all_answers:
        by_resp[a.response_id].append(a)

    out: dict[str, dict] = {}
    for cid in class_ids:
        rs = by_class.get(cid, [])
        if not rs:
            out[cid] = {}
            continue
        agg = _aggregate_from_responses(rs, by_resp) or {}
        if not isinstance(agg, dict):
            agg = {}
        agg["response_count"] = len(rs)
        out[cid] = agg
    return out


def compute_student_model(db: Session, student_id: UUID, survey_id: UUID) -> dict:
    """Індивідуальні середні S/T/E/M і ранжування за одним проходженням опитування."""
    r = (
        db.query(SurveyResponse)
        .filter(
            SurveyResponse.student_id == student_id,
            SurveyResponse.survey_id == survey_id,
        )
        .first()
    )
    if not r:
        return {}
    answers = db.query(SurveyAnswer).filter(SurveyAnswer.response_id == r.id).all()
    by_code = {a.question_code: a.value for a in answers}
    s_vals, t_vals, e_vals, m_vals = [], [], [], []
    _extend_stem_from_by_code(by_code, s_vals, t_vals, e_vals, m_vals)
    if not s_vals and not t_vals and not e_vals and not m_vals:
        return {}
    return _finalize_stem_model(s_vals, t_vals, e_vals, m_vals)


def upsert_class_model(db: Session, class_id: UUID, survey_id: UUID) -> dict | None:
    data = compute_class_model(db, str(class_id), str(survey_id))
    if not data or not data.get("ranking"):
        return None
    row = (
        db.query(ClassModel)
        .filter(ClassModel.class_id == class_id, ClassModel.survey_id == survey_id)
        .first()
    )
    if row:
        row.s_avg = data["s_avg"]
        row.t_avg = data["t_avg"]
        row.e_avg = data["e_avg"]
        row.m_avg = data["m_avg"]
        row.ranking = data["ranking"]
    else:
        row = ClassModel(
            class_id=class_id,
            survey_id=survey_id,
            s_avg=data["s_avg"],
            t_avg=data["t_avg"],
            e_avg=data["e_avg"],
            m_avg=data["m_avg"],
            ranking=data["ranking"],
        )
        db.add(row)
    db.commit()
    return data
