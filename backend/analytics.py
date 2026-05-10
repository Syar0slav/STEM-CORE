from uuid import UUID

from sqlalchemy.orm import Session

from models import Class, School, User
from services import compute_class_models_bulk
from user_roles import can_view_school_insights, filter_classes_by_staff_scope

STEM_LABELS_UK = {"S": "Наука", "T": "Технології", "E": "Інженерія", "M": "Математика"}


def build_per_discipline_classes(class_rows: list[dict]) -> list[dict]:
    """
    Окремі списки класів з середнім і кількістю «проголосувавших» (відстежених
    проходжень) для кожного предмета S / T / E / M.
    """
    keys = [("S", "s_avg"), ("T", "t_avg"), ("E", "e_avg"), ("M", "m_avg")]
    out: list[dict] = []
    for code, k in keys:
        items: list[dict] = []
        for row in class_rows:
            v = row.get(k)
            if v is None:
                continue
            try:
                vf = float(v)
            except (TypeError, ValueError):
                continue
            items.append(
                {
                    "class_id": row["class_id"],
                    "name": row["name"],
                    "grade": row["grade"],
                    "avg": round(vf, 2),
                    "response_count": row.get("response_count"),
                }
            )
        items.sort(key=lambda x: (-x["avg"], x["name"] or ""))
        out.append(
            {
                "code": code,
                "label": STEM_LABELS_UK.get(code, code),
                "classes": items,
            }
        )
    return out


def build_discipline_summary(class_rows: list[dict]) -> list[dict]:
    """
    Середні S/T/E/M по класах (середнє від середніх класів), ранг від найкращого до найгіршого,
    pct_share — частка кожної дисципліни в сумі чотирьох середніх (для кругової діаграми).
    """
    keys = [("S", "s_avg"), ("T", "t_avg"), ("E", "e_avg"), ("M", "m_avg")]
    vals: dict[str, float] = {}
    for code, k in keys:
        nums: list[float] = []
        for row in class_rows:
            v = row.get(k)
            if v is not None:
                try:
                    nums.append(float(v))
                except (TypeError, ValueError):
                    pass
        if nums:
            vals[code] = sum(nums) / len(nums)
    if not vals:
        return []
    total = sum(vals.values())
    sorted_codes = sorted(vals.keys(), key=lambda c: -vals[c])
    out: list[dict] = []
    for rank, code in enumerate(sorted_codes, start=1):
        avg = vals[code]
        pct = (avg / total * 100) if total > 0 else 0.0
        out.append(
            {
                "code": code,
                "label": STEM_LABELS_UK.get(code, code),
                "avg": round(avg, 2),
                "pct_share": round(pct, 1),
                "rank": rank,
            }
        )
    return out


def _can_access_school(user: User, school_id: UUID) -> bool:
    if not can_view_school_insights(user):
        return False
    if user.role == "admin":
        return True
    return user.school_id == school_id


def school_analytics(db: Session, user: User, school_id: str, survey_id: str) -> dict | None:
    sid = UUID(school_id)
    if not _can_access_school(user, sid):
        return None
    school = db.query(School).filter(School.id == sid).first()
    if not school:
        return None
    classes = db.query(Class).filter(Class.school_id == sid).all()
    classes = filter_classes_by_staff_scope(classes, user)
    if not classes:
        return {
            "school_id": school_id,
            "school_name": school.name,
            "survey_id": survey_id,
            "classes": [],
            "discipline_summary": [],
            "disciplines": [],
        }
    cids = [str(c.id) for c in classes]
    bulk = compute_class_models_bulk(db, cids, survey_id)
    empty_model = {
        "s_avg": None,
        "t_avg": None,
        "e_avg": None,
        "m_avg": None,
        "ranking": None,
        "response_count": None,
    }
    rows = []
    for c in classes:
        m = bulk.get(str(c.id)) or {}
        rows.append(
            {
                "class_id": str(c.id),
                "name": c.name,
                "grade": c.grade,
                **(m if m else empty_model),
            }
        )
    summary = build_discipline_summary(rows)
    per_disc = build_per_discipline_classes(rows)
    return {
        "school_id": school_id,
        "school_name": school.name,
        "survey_id": survey_id,
        "classes": rows,
        "discipline_summary": summary,
        "disciplines": per_disc,
    }


def school_compare(
    db: Session, user: User, school_id: str, survey_a: str, survey_b: str
) -> dict | None:
    a = school_analytics(db, user, school_id, survey_a)
    b = school_analytics(db, user, school_id, survey_b)
    if a is None or b is None:
        return None
    return {"semester_a": a, "semester_b": b}
