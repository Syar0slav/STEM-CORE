import json
from pathlib import Path

_path = Path(__file__).parent.parent / "moodle" / "question_mapping.json"
with open(_path, encoding="utf-8") as f:
    _data = json.load(f)

BLOCKS = _data["blocks"]
MODEL_DISCIPLINES = _data["model_class_disciplines"]
SCALE_MIN = _data["scale_min"]
SCALE_MAX = _data["scale_max"]
