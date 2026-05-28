import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _mapping_json() -> Path:
    """Репозиторій: backend/moodle_mapping.py → ../moodle/… ; Docker: /app + COPY moodle → /app/moodle/…"""
    candidates = (
        _HERE / "moodle" / "question_mapping.json",
        _HERE.parent / "moodle" / "question_mapping.json",
    )
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError(
        "question_mapping.json не знайдено; очікувані шляхи: "
        + ", ".join(str(c) for c in candidates)
    )


_path = _mapping_json()
with open(_path, encoding="utf-8") as f:
    _data = json.load(f)

BLOCKS = _data["blocks"]
MODEL_DISCIPLINES = _data["model_class_disciplines"]
SCALE_MIN = _data["scale_min"]
SCALE_MAX = _data["scale_max"]
