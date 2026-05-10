"""
Шаблон звіту «STEM — зведення по школі»: назви аркушів, колонок і секцій для усіх форматів експорту.
"""

from __future__ import annotations

REPORT_TITLE = "STEM — зведення по школі"

# Microsoft Excel / LibreOffice
SHEET_META = "Мета"
SHEET_DISCIPLINES = "Зведення_дисципліни"
SHEET_CLASSES = "Класи"
SHEET_PER_DISC = "По_предметах"

# Колонки: зведення по дисциплінах (як у API discipline_summary)
COL_DISC_CODE = "Код"
COL_DISC_LABEL = "Дисципліна"
COL_DISC_AVG = "Середнє"
COL_DISC_PCT = "Частка_%"
COL_DISC_RANK = "Місце"

# Колонки: класи
COL_CLASS_NAME = "Клас"
COL_CLASS_GRADE = "Паралель"
COL_S = "S"
COL_T = "T"
COL_E = "E"
COL_M = "M"
COL_RANKING = "Ранжування"
COL_RESP_COUNT = "Проголосувало"

COL_PD_CODE = "Код"
COL_PD_LABEL = "Предмет"
COL_PD_CLASS = "Клас"
COL_PD_GRADE = "Паралель"
COL_PD_AVG = "Середнє"
COL_PD_N = "Проголосувало"

NOTE_SCALE = (
    "Примітка: середні S/T/E/M — за шкалою опитування 1–7; зведення по дисциплінах — "
    "середнє від середніх по класах у вашому полі зору; частка_% — внесок дисципліни в суму "
    "чотирьох середніх (для порівняння на діаграмі). «Проголосувало» — кількість збережених "
    "проходжень опитування по класу (для оцінки учасників, не для атестації з предмета)."
)
