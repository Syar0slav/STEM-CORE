import csv
import io
import textwrap
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from analytics import school_analytics
from export_templates import school_stem_layout as L
from models import User


def _analytics_or_empty(db: Session, user: User, school_id: str, survey_id: str) -> dict | None:
    return school_analytics(db, user, school_id, survey_id)


def export_school_survey_csv(db: Session, user: User, school_id: str, survey_id: str) -> bytes:
    data = _analytics_or_empty(db, user, school_id, survey_id)
    if not data:
        return b""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["#", L.REPORT_TITLE])
    w.writerow([])
    w.writerow(["Секція", "Ключ", "Значення"])
    w.writerow(["Мета", "Назва школи", data.get("school_name", "")])
    w.writerow(["Мета", "ID опитування", survey_id])
    w.writerow(
        [
            "Мета",
            "Час експорту (UTC)",
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        ]
    )
    w.writerow([])
    w.writerow(
        [
            L.COL_DISC_CODE,
            L.COL_DISC_LABEL,
            L.COL_DISC_AVG,
            L.COL_DISC_PCT,
            L.COL_DISC_RANK,
        ]
    )
    for row in data.get("discipline_summary") or []:
        w.writerow(
            [
                row.get("code"),
                row.get("label"),
                row.get("avg"),
                row.get("pct_share"),
                row.get("rank"),
            ]
        )
    w.writerow([])
    w.writerow(
        [
            L.COL_CLASS_NAME,
            L.COL_CLASS_GRADE,
            L.COL_S,
            L.COL_T,
            L.COL_E,
            L.COL_M,
            L.COL_RANKING,
            L.COL_RESP_COUNT,
        ]
    )
    for row in data.get("classes", []):
        w.writerow(
            [
                row.get("name"),
                row.get("grade"),
                row.get("s_avg"),
                row.get("t_avg"),
                row.get("e_avg"),
                row.get("m_avg"),
                row.get("ranking"),
                row.get("response_count"),
            ]
        )
    w.writerow([])
    w.writerow(
        [
            L.COL_PD_CODE,
            L.COL_PD_LABEL,
            L.COL_PD_CLASS,
            L.COL_PD_GRADE,
            L.COL_PD_AVG,
            L.COL_PD_N,
        ]
    )
    for d in data.get("disciplines") or []:
        for c in d.get("classes") or []:
            w.writerow(
                [
                    d.get("code"),
                    d.get("label"),
                    c.get("name"),
                    c.get("grade"),
                    c.get("avg"),
                    c.get("response_count"),
                ]
            )
    w.writerow([])
    w.writerow(["#", L.NOTE_SCALE])
    return buf.getvalue().encode("utf-8-sig")


def export_school_survey_xlsx(db: Session, user: User, school_id: str, survey_id: str) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    data = _analytics_or_empty(db, user, school_id, survey_id)
    if not data:
        return b""
    wb = Workbook()
    meta = wb.active
    meta.title = L.SHEET_META[:31]
    bold = Font(bold=True)
    meta["A1"] = L.REPORT_TITLE
    meta["A1"].font = Font(bold=True, size=14)
    meta["A3"] = "Поле"
    meta["B3"] = "Значення"
    meta["A3"].font = bold
    meta["B3"].font = bold
    r = 4
    meta[f"A{r}"] = "Назва школи"
    meta[f"B{r}"] = data.get("school_name", "")
    r += 1
    meta[f"A{r}"] = "ID опитування"
    meta[f"B{r}"] = survey_id
    r += 1
    meta[f"A{r}"] = "Час експорту (UTC)"
    meta[f"B{r}"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    r += 2
    meta[f"A{r}"] = L.NOTE_SCALE
    meta[f"A{r}"].alignment = Alignment(wrap_text=True, vertical="top")
    meta.merge_cells(f"A{r}:F{r + 2}")
    meta.row_dimensions[r].height = 60

    ws_d = wb.create_sheet(L.SHEET_DISCIPLINES[:31])
    ws_d.append(
        [
            L.COL_DISC_CODE,
            L.COL_DISC_LABEL,
            L.COL_DISC_AVG,
            L.COL_DISC_PCT,
            L.COL_DISC_RANK,
        ]
    )
    for c in ws_d[1]:
        c.font = bold
    for row in data.get("discipline_summary") or []:
        ws_d.append(
            [
                row.get("code"),
                row.get("label"),
                row.get("avg"),
                row.get("pct_share"),
                row.get("rank"),
            ]
        )

    ws_c = wb.create_sheet(L.SHEET_CLASSES[:31])
    ws_c.append(
        [
            L.COL_CLASS_NAME,
            L.COL_CLASS_GRADE,
            L.COL_S,
            L.COL_T,
            L.COL_E,
            L.COL_M,
            L.COL_RANKING,
            L.COL_RESP_COUNT,
        ]
    )
    for c in ws_c[1]:
        c.font = bold
    for row in data.get("classes", []):
        ws_c.append(
            [
                row.get("name"),
                row.get("grade"),
                row.get("s_avg"),
                row.get("t_avg"),
                row.get("e_avg"),
                row.get("m_avg"),
                row.get("ranking"),
                row.get("response_count"),
            ]
        )

    ws_pd = wb.create_sheet(L.SHEET_PER_DISC[:31])
    ws_pd.append(
        [
            L.COL_PD_CODE,
            L.COL_PD_LABEL,
            L.COL_PD_CLASS,
            L.COL_PD_GRADE,
            L.COL_PD_AVG,
            L.COL_PD_N,
        ]
    )
    for c in ws_pd[1]:
        c.font = bold
    for d in data.get("disciplines") or []:
        for row in d.get("classes") or []:
            ws_pd.append(
                [
                    d.get("code"),
                    d.get("label"),
                    row.get("name"),
                    row.get("grade"),
                    row.get("avg"),
                    row.get("response_count"),
                ]
            )

    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


def export_school_survey_pdf(db: Session, user: User, school_id: str, survey_id: str) -> bytes:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    data = _analytics_or_empty(db, user, school_id, survey_id)
    if not data:
        return b""
    plt.rcParams["font.family"] = "DejaVu Sans"
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]

    lines: list[str] = []
    lines.append(L.REPORT_TITLE)
    lines.append("")
    lines.append(f"Назва школи: {data.get('school_name', '')}")
    lines.append(f"ID опитування: {survey_id}")
    lines.append(
        f"Час експорту (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
    )
    lines.append("")
    lines.append("— Зведення по дисциплінах (найкраща середня → найнижча) —")
    lines.append(
        f"{L.COL_DISC_CODE}\t{L.COL_DISC_LABEL}\t{L.COL_DISC_AVG}\t{L.COL_DISC_PCT}\t{L.COL_DISC_RANK}"
    )
    for row in data.get("discipline_summary") or []:
        lines.append(
            f"{row.get('code', '')}\t{row.get('label', '')}\t{row.get('avg', '')}\t"
            f"{row.get('pct_share', '')}\t{row.get('rank', '')}"
        )
    if not (data.get("discipline_summary") or []):
        lines.append("(немає зведення — недостатньо даних по класах)")
    lines.append("")
    lines.append("— Класи —")
    lines.append(
        f"{L.COL_CLASS_NAME}\t{L.COL_CLASS_GRADE}\t{L.COL_S}\t{L.COL_T}\t{L.COL_E}\t{L.COL_M}\t"
        f"{L.COL_RANKING}\t{L.COL_RESP_COUNT}"
    )
    for row in data.get("classes", []):
        lines.append(
            f"{row.get('name', '')}\t{row.get('grade', '')}\t{row.get('s_avg', '')}\t"
            f"{row.get('t_avg', '')}\t{row.get('e_avg', '')}\t{row.get('m_avg', '')}\t"
            f"{row.get('ranking', '')}\t{row.get('response_count', '')}"
        )
    lines.append("")
    lines.append("— По предметах (клас, середнє, проголосувало) —")
    lines.append(
        f"{L.COL_PD_CODE}\t{L.COL_PD_LABEL}\t{L.COL_PD_CLASS}\t{L.COL_PD_GRADE}\t{L.COL_PD_AVG}\t{L.COL_PD_N}"
    )
    for d in data.get("disciplines") or []:
        for row in d.get("classes") or []:
            lines.append(
                f"{d.get('code', '')}\t{d.get('label', '')}\t{row.get('name', '')}\t"
                f"{row.get('grade', '')}\t{row.get('avg', '')}\t{row.get('response_count', '')}"
            )
    lines.append("")
    lines.append(L.NOTE_SCALE)

    flat: list[str] = []
    for line in lines:
        if len(line) <= 96:
            flat.append(line)
        else:
            flat.extend(textwrap.wrap(line, width=96) or [""])

    buf = io.BytesIO()
    lines_per_page = 44
    with PdfPages(buf) as pdf:
        for start in range(0, len(flat), lines_per_page):
            chunk = flat[start : start + lines_per_page]
            fig = plt.figure(figsize=(8.27, 11.69))
            ax = fig.add_axes([0.08, 0.05, 0.88, 0.90])
            ax.axis("off")
            y = 1.0
            dy = 0.022
            fs = 9
            for line in chunk:
                ax.text(0, y, line, transform=ax.transAxes, fontsize=fs, va="top", ha="left")
                y -= dy
            pdf.savefig(fig)
            plt.close(fig)
    return buf.getvalue()


def export_school_survey_docx(db: Session, user: User, school_id: str, survey_id: str) -> bytes:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    data = _analytics_or_empty(db, user, school_id, survey_id)
    if not data:
        return b""
    doc = Document()
    t = doc.add_heading(L.REPORT_TITLE, 0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in t.runs:
        run.font.size = Pt(16)

    p = doc.add_paragraph()
    p.add_run("Назва школи: ").bold = True
    p.add_run(str(data.get("school_name", "")))
    p = doc.add_paragraph()
    p.add_run("ID опитування: ").bold = True
    p.add_run(survey_id)
    p = doc.add_paragraph()
    p.add_run("Час експорту (UTC): ").bold = True
    p.add_run(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))

    doc.add_heading("Зведення по дисциплінах", level=1)
    disc = data.get("discipline_summary") or []
    if disc:
        table = doc.add_table(rows=1, cols=5)
        table.style = "Table Grid"
        hdr = table.rows[0].cells
        hdr[0].text = L.COL_DISC_CODE
        hdr[1].text = L.COL_DISC_LABEL
        hdr[2].text = L.COL_DISC_AVG
        hdr[3].text = L.COL_DISC_PCT
        hdr[4].text = L.COL_DISC_RANK
        for row in disc:
            cells = table.add_row().cells
            cells[0].text = str(row.get("code", ""))
            cells[1].text = str(row.get("label", ""))
            cells[2].text = "" if row.get("avg") is None else str(row.get("avg"))
            cells[3].text = "" if row.get("pct_share") is None else str(row.get("pct_share"))
            cells[4].text = "" if row.get("rank") is None else str(row.get("rank"))
    else:
        doc.add_paragraph("Немає зведення (недостатньо даних по класах).")

    doc.add_heading("Класи", level=1)
    classes = data.get("classes") or []
    if classes:
        table = doc.add_table(rows=1, cols=8)
        table.style = "Table Grid"
        hdr = table.rows[0].cells
        hdr[0].text = L.COL_CLASS_NAME
        hdr[1].text = L.COL_CLASS_GRADE
        hdr[2].text = L.COL_S
        hdr[3].text = L.COL_T
        hdr[4].text = L.COL_E
        hdr[5].text = L.COL_M
        hdr[6].text = L.COL_RANKING
        hdr[7].text = L.COL_RESP_COUNT
        for row in classes:
            cells = table.add_row().cells
            cells[0].text = str(row.get("name", ""))
            cells[1].text = "" if row.get("grade") is None else str(row.get("grade"))
            for i, k in enumerate(["s_avg", "t_avg", "e_avg", "m_avg"], start=2):
                v = row.get(k)
                cells[i].text = "" if v is None else str(v)
            cells[6].text = str(row.get("ranking", "") or "")
            vrc = row.get("response_count")
            cells[7].text = "" if vrc is None else str(vrc)
    else:
        doc.add_paragraph("Немає рядків по класах.")

    disc_rows = data.get("disciplines") or []
    if disc_rows and any((d.get("classes") or []) for d in disc_rows):
        doc.add_heading("По предметах (клас, середнє, проголосувало)", level=1)
        t2 = doc.add_table(rows=1, cols=6)
        t2.style = "Table Grid"
        h2 = t2.rows[0].cells
        h2[0].text = L.COL_PD_CODE
        h2[1].text = L.COL_PD_LABEL
        h2[2].text = L.COL_PD_CLASS
        h2[3].text = L.COL_PD_GRADE
        h2[4].text = L.COL_PD_AVG
        h2[5].text = L.COL_PD_N
        for d in disc_rows:
            for row in d.get("classes") or []:
                c = t2.add_row().cells
                c[0].text = str(d.get("code", ""))
                c[1].text = str(d.get("label", ""))
                c[2].text = str(row.get("name", ""))
                c[3].text = "" if row.get("grade") is None else str(row.get("grade"))
                c[4].text = "" if row.get("avg") is None else str(row.get("avg"))
                vrc = row.get("response_count")
                c[5].text = "" if vrc is None else str(vrc)

    doc.add_paragraph("")
    note = doc.add_paragraph(L.NOTE_SCALE)
    for run in note.runs:
        run.italic = True
        run.font.size = Pt(9)

    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()
