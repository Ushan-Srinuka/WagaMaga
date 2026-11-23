"""Extract plain text in a disposable subprocess with bounded output."""

import io
import json
import sys
from collections import Counter
from typing import NamedTuple

from sinhalanorm import legacy_to_unicode

# Bounded for the full 89-page DOA Chilli Cultivation - 2023 guide.
MAX_BYTES = 6 * 1024 * 1024
MAX_PAGES = 100
MAX_TEXT = 120_000
LINE_TOLERANCE = 2.0


class TextRun(NamedTuple):
    x: float
    y: float
    text: str


def convert_legacy_span(text: str, font) -> str:
    """Convert the supported FM font runs using embedded PDF metadata."""
    base = str(font.get("/BaseFont", "")) if font else ""
    name = base.rsplit("+", maxsplit=1)[-1].lstrip("/").casefold()
    if name.startswith(("fmabhaya", "fmababld", "fmemanee", "fmsamantha")):
        return legacy_to_unicode(text, font="fm-abhaya")
    return text


def lines_from_runs(runs: list[TextRun]) -> list[str]:
    lines = []
    line_parts = []
    line_y = None
    for run in sorted(runs, key=lambda item: (-item.y, item.x)):
        if line_y is not None and abs(run.y - line_y) > LINE_TOLERANCE:
            lines.append(" ".join(line_parts))
            line_parts = []
        line_parts.append(run.text)
        line_y = run.y
    if line_parts:
        lines.append(" ".join(line_parts))
    return lines


def column_anchor(
    runs: list[TextRun], lower: float, upper: float, tolerance: float
) -> list[TextRun]:
    # Count paragraph lines rather than short labels, numbers or inline font runs.
    starts = Counter(
        round(run.x / tolerance)
        for run in runs
        if lower <= run.x <= upper and len(run.text.strip()) >= 20
    )
    if not starts:
        return []
    anchor = starts.most_common(1)[0][0] * tolerance
    return [run for run in runs if abs(run.x - anchor) <= tolerance]


def page_lines(runs: list[TextRun], left: float, width: float) -> list[str]:
    """Read parallel prose blocks in column order when their margins are clear."""
    if width <= 0:
        return lines_from_runs(runs)
    tolerance = width * 0.01
    first = column_anchor(runs, left, left + width * 0.3, tolerance)
    second = column_anchor(runs, left + width * 0.5, left + width * 0.65, tolerance)
    first_rows, second_rows = (
        {round(run.y / LINE_TOLERANCE) for run in column if len(run.text.strip()) >= 20}
        for column in (first, second)
    )
    if min(len(first_rows), len(second_rows)) < 6:
        return lines_from_runs(runs)
    # Repeated margins must occur over the same body area, not in successive blocks.
    shared_rows = min(max(first_rows), max(second_rows)) - max(min(first_rows), min(second_rows))
    if shared_rows * LINE_TOLERANCE < 70:
        return lines_from_runs(runs)

    top = max(run.y for run in first + second) + LINE_TOLERANCE
    bottom = min(run.y for run in first + second) - LINE_TOLERANCE
    right_start = min(run.x for run in second) - tolerance
    header, left_column, right_column, footer = [], [], [], []
    for run in runs:
        if run.y > top:
            header.append(run)
        elif run.y < bottom:
            footer.append(run)
        elif run.x < right_start:
            left_column.append(run)
        else:
            right_column.append(run)
    return [
        *lines_from_runs(header),
        *lines_from_runs(left_column),
        *lines_from_runs(right_column),
        *lines_from_runs(footer),
    ]


def extract(raw: bytes) -> dict:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(raw), strict=True)
    if reader.is_encrypted:
        return {"error": "encrypted"}
    if not 1 <= len(reader.pages) <= MAX_PAGES:
        return {"error": "page_limit"}
    pages = []
    total = 0
    for page in reader.pages:
        chunks: list[TextRun] = []

        def collect(text, cm, tm, font, font_size, target=chunks):
            if not text or not text.strip():
                return
            text = convert_legacy_span(text, font)
            # Apply the current PDF transformation to the text origin.
            x = float(tm[4] * cm[0] + tm[5] * cm[2] + cm[4])
            y = float(tm[4] * cm[1] + tm[5] * cm[3] + cm[5])
            target.append(TextRun(x, y, text))

        page.extract_text(visitor_text=collect)
        lines = (
            lines_from_runs(chunks)
            if page.rotation
            else page_lines(chunks, float(page.mediabox.left), float(page.mediabox.width))
        )
        content = "\n".join(lines).replace("\x00", "").strip()
        # Some font maps yield isolated surrogate code points.
        content = content.encode("utf-8", errors="replace").decode("utf-8")
        total += len(content)
        if total > MAX_TEXT:
            return {"error": "text_limit"}
        pages.append(content)
    return {"pages": pages} if any(pages) else {"error": "no_text"}


def main():
    if sys.platform.startswith("linux"):
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024**2, 256 * 1024**2))
        resource.setrlimit(resource.RLIMIT_CPU, (6, 6))
    try:
        result = extract(sys.stdin.buffer.read(MAX_BYTES + 1))
    except Exception:
        result = {"error": "invalid_pdf"}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
