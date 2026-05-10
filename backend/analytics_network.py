"""Агреговані показники по школах (мережа) — лише для admin, без персональних даних."""

from sqlalchemy.orm import Session

from models import Class, School
from services import compute_class_models_bulk


def network_schools_snapshot(db: Session, survey_id: str) -> list[dict]:
    """По кожній школі — середні середніх по класах із даними для цього опитування."""
    out: list[dict] = []
    for school in db.query(School).order_by(School.name).all():
        classes = db.query(Class).filter(Class.school_id == school.id).all()
        if not classes:
            continue
        cids = [str(c.id) for c in classes]
        bulk = compute_class_models_bulk(db, cids, survey_id)
        s_vals: list[float] = []
        t_vals: list[float] = []
        e_vals: list[float] = []
        m_vals: list[float] = []
        classes_with_data = 0
        for c in classes:
            m = bulk.get(str(c.id), {})
            if not m:
                continue
            if None in (
                m.get("s_avg"),
                m.get("t_avg"),
                m.get("e_avg"),
                m.get("m_avg"),
            ):
                continue
            s_vals.append(float(m["s_avg"]))
            t_vals.append(float(m["t_avg"]))
            e_vals.append(float(m["e_avg"]))
            m_vals.append(float(m["m_avg"]))
            classes_with_data += 1
        if not s_vals:
            continue
        out.append(
            {
                "school_id": str(school.id),
                "school_name": school.name,
                "city": school.city,
                "classes_with_responses": classes_with_data,
                "s_avg": round(sum(s_vals) / len(s_vals), 2),
                "t_avg": round(sum(t_vals) / len(t_vals), 2),
                "e_avg": round(sum(e_vals) / len(e_vals), 2),
                "m_avg": round(sum(m_vals) / len(m_vals), 2),
            }
        )
    return out
