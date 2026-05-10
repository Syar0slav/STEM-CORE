STEM_LABELS = {"S": "Наука", "T": "Технології", "E": "Інженерія", "M": "Математика"}

# Відкриті освітні ресурси (YouTube / курси) — орієнтири для учнів і вчителів
STEM_MEDIA = {
    "S": {
        "video_url": "https://www.youtube.com/results?search_query=STEM+science+experiments+for+students+ukrainian",
        "video_title": "Підбірка: наукові досліди та пояснення",
        "course_title": "Khan Academy — природничі науки (англ.)",
        "course_url": "https://www.khanacademy.org/science",
        "course_note": "Можна обрати розділ і проходити теми власним темпом; батьки можуть допомогти з перекладом термінів.",
    },
    "T": {
        "video_url": "https://www.youtube.com/results?search_query=technology+education+for+kids",
        "video_title": "Підбірка: технології та цифрова грамотність",
        "course_title": "CS50 Introduction to Computer Science (Harvard, безкоштовно)",
        "course_url": "https://cs50.harvard.edu/x/2025/",
        "course_note": "Вступ до інформатики; для старших класів — разом із учителем інформатики.",
    },
    "E": {
        "video_url": "https://www.youtube.com/results?search_query=engineering+projects+for+students",
        "video_title": "Підбірка: інженерні ідеї та макети",
        "course_title": "MIT OpenCourseWare — вступ до інженерії",
        "course_url": "https://ocw.mit.edu/courses/introductory-programming/",
        "course_note": "Обирайте вступні курси; частина матеріалів англійською.",
    },
    "M": {
        "video_url": "https://www.youtube.com/results?search_query=mathematics+explained+visual",
        "video_title": "Підбірка: математика наочно",
        "course_title": "Khan Academy — математика",
        "course_url": "https://www.khanacademy.org/math",
        "course_note": "Рівні від початкової школи до старших класів; зручно повторювати теми.",
    },
}


def build_recommendations(ranking: str) -> list[dict]:
    if not ranking:
        return []
    parts = ranking.split("-")
    if len(parts) < 4:
        return []
    third, fourth = parts[2], parts[3]
    out = []
    for code in (third, fourth):
        media = STEM_MEDIA.get(code, {})
        out.append(
            {
                "discipline": code,
                "title": STEM_LABELS.get(code, code),
                "hints": [
                    "Додайте короткі проєкти та демонстрації на уроках.",
                    "Запропонуйте учням переглянути відео та матеріали з реальними застосуваннями (посилання нижче).",
                    "Проведіть інтегрований урок з іншими предметами STEM.",
                ],
                **media,
            }
        )
    return out


def build_student_recommendations(ranking: str) -> list[dict]:
    """Орієнтири для учня з посиланнями на відео та курси для самостійного розвитку."""
    base = build_recommendations(ranking)
    out = []
    for item in base:
        hints = [
            "Переглянь короткі відео з підбірки та обери одну тему для вивчення цього тижня.",
            "Спробуй невеликий проєкт або головоломку з обраного напряму.",
            "Покажи учителю обраний курс — разом можна скласти план на місяць.",
        ]
        out.append({**item, "hints": hints})
    return out
