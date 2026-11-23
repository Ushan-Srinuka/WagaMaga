import io

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.modules.knowledge.pdf_text import extract


def pdf_with_text(runs):
    writer = PdfWriter()
    page = writer.add_blank_page(600, 800)
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {
                    NameObject("/F1"): DictionaryObject(
                        {
                            NameObject("/Type"): NameObject("/Font"),
                            NameObject("/Subtype"): NameObject("/Type1"),
                            NameObject("/BaseFont"): NameObject("/Helvetica"),
                        }
                    )
                }
            )
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(
        "\n".join(f"BT /F1 9 Tf {x} {y} Td ({body}) Tj ET" for x, y, body in runs).encode()
    )
    page[NameObject("/Contents")] = stream
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_parallel_columns_preserve_heading_inline_text_and_footer():
    left = [f"Left column body line {i}." for i in range(7)]
    right = [f"Right column body line {i}." for i in range(7)]
    runs = [(55, 730, "Page heading"), (295, 72, "12")]
    for i, (a, b) in enumerate(zip(left, right, strict=True)):
        runs.extend(((320, 660 - i * 18, b), (55, 655 - i * 18, a)))
    runs.append((175, 655, "Continued text."))

    result = extract(pdf_with_text(runs))

    expected = ["Page heading", left[0] + " Continued text.", *left[1:], *right, "12"]
    assert result["pages"][0].splitlines() == expected


def test_short_table_cells_stay_in_row_order():
    runs = []
    expected = []
    for i in range(7):
        label = f"Seed sample description {i}"
        runs.extend(((320, 670 - i * 18, str(i)), (55, 670 - i * 18, label)))
        expected.append(f"{label} {i}")

    assert extract(pdf_with_text(runs))["pages"][0].splitlines() == expected
