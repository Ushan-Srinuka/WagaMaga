"""The fixed fictional material permitted in Gemini preview requests."""

from hashlib import sha256
from typing import Literal

PreviewQuestion = Literal["nursery", "records", "forecast"]
QUESTIONS = {
    "nursery": ("What label does the fictional nursery use?", "nursery label"),
    "records": ("What details does the fictional field record contain?", "field record"),
    "forecast": ("What is tomorrow's rainfall forecast?", "rainfall forecast"),
}
TITLE = "Fictional chilli field notebook"
PAGES = (
    "The fictional nursery uses the label DEMO-NURSERY-A for its example seedling tray.",
    "The fictional field record contains a plot label and an observation date.",
)


def fixture_pdf(pages: tuple[str, ...] = PAGES) -> bytes:
    page_ids = range(4, 4 + 2 * len(pages), 2)
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode("ascii"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for page_id, line in zip(page_ids, pages, strict=True):
        content_id = page_id + 1
        commands = f"BT /F1 11 Tf 36 700 Td ({line}) Tj ET".encode("ascii")
        objects.extend(
            [
                (
                    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                    f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
                ).encode("ascii"),
                f"<< /Length {len(commands)} >>\nstream\n".encode() + commands + b"\nendstream",
            ]
        )
    document = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(document)
    document.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        document.extend(f"{offset:010} 00000 n \n".encode())
    document.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(document)


PDF = fixture_pdf()
CHECKSUM = sha256(PDF).hexdigest()
