from pathlib import Path
from zipfile import ZipFile
from lxml import etree


FILE = Path(
    r"C:\Users\Prince\Downloads\SMQ BIBLES\SMQ BIBLES"
    r"\2018 Eastern Regional Contests\CONTEST 1.docx"
)


NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def text_from_paragraph(paragraph):
    parts = []

    for node in paragraph.iter():
        if node.tag == f"{{{NS['w']}}}t":
            if node.text:
                parts.append(node.text)

        elif node.tag == f"{{{NS['w']}}}tab":
            parts.append("\t")

        elif node.tag == f"{{{NS['w']}}}br":
            parts.append("\n")

    return "".join(parts).strip()


def paragraph_style(paragraph):
    style = paragraph.find("w:pPr/w:pStyle", namespaces=NS)

    if style is None:
        return ""

    return style.get(
        f"{{{NS['w']}}}val",
        ""
    )


def inspect_document(path):
    print("=" * 80)
    print("DOCUMENT INSPECTION")
    print("=" * 80)

    print(f"\nFile: {path}")
    print(f"Size: {path.stat().st_size:,} bytes")

    with ZipFile(path) as archive:

        names = archive.namelist()

        print(f"Internal package files: {len(names)}")

        print("\nMEDIA FILES")
        print("-" * 40)

        media = [
            name
            for name in names
            if name.startswith("word/media/")
        ]

        print(f"Media files: {len(media)}")

        for name in media:
            info = archive.getinfo(name)
            print(
                f"  {name} "
                f"({info.file_size:,} bytes)"
            )

        document_xml = archive.read(
            "word/document.xml"
        )

        root = etree.fromstring(document_xml)

        body = root.find("w:body", namespaces=NS)

        if body is None:
            print("\nERROR: No document body found.")
            return

        paragraphs = []
        tables = []

        # Preserve document order.
        for child in body:

            if child.tag == f"{{{NS['w']}}}p":

                text = text_from_paragraph(child)

                if text:
                    paragraphs.append({
                        "text": text,
                        "style": paragraph_style(child),
                    })

            elif child.tag == f"{{{NS['w']}}}tbl":
                tables.append(child)

        print("\nDOCUMENT STRUCTURE")
        print("-" * 40)
        print(f"Non-empty paragraphs: {len(paragraphs)}")
        print(f"Tables: {len(tables)}")

        print("\nFIRST 100 PARAGRAPHS")
        print("-" * 80)

        for number, item in enumerate(
            paragraphs[:100],
            start=1,
        ):

            style = item["style"]

            if style:
                print(
                    f"[{number:03}] "
                    f"[style={style}] "
                    f"{item['text']}"
                )
            else:
                print(
                    f"[{number:03}] "
                    f"{item['text']}"
                )

        if tables:

            print("\nTABLES")
            print("-" * 80)

            for table_number, table in enumerate(
                tables,
                start=1,
            ):

                rows = table.findall(
                    "w:tr",
                    namespaces=NS,
                )

                print(
                    f"\nTable {table_number}: "
                    f"{len(rows)} rows"
                )

                for row_number, row in enumerate(
                    rows[:10],
                    start=1,
                ):

                    cells = row.findall(
                        "w:tc",
                        namespaces=NS,
                    )

                    values = []

                    for cell in cells:

                        cell_text = []

                        for paragraph in cell.findall(
                            ".//w:p",
                            namespaces=NS,
                        ):
                            text = text_from_paragraph(
                                paragraph
                            )

                            if text:
                                cell_text.append(text)

                        values.append(
                            " ".join(cell_text)
                        )

                    print(
                        f"  Row {row_number}: "
                        f"{values}"
                    )

        print("\nHEADERS / FOOTERS")
        print("-" * 40)

        header_footer_files = [
            name
            for name in names
            if name.startswith("word/header")
            or name.startswith("word/footer")
        ]

        for name in header_footer_files:

            xml = archive.read(name)

            tree = etree.fromstring(xml)

            texts = []

            for paragraph in tree.findall(
                ".//w:p",
                namespaces=NS,
            ):

                text = text_from_paragraph(
                    paragraph
                )

                if text:
                    texts.append(text)

            print(f"\n{name}")

            for text in texts[:20]:
                print(f"  {text}")


if __name__ == "__main__":

    if not FILE.exists():
        raise FileNotFoundError(
            f"File not found: {FILE}"
        )

    inspect_document(FILE)