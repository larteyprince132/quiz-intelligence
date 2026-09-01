from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET


FILE = Path(
    r"C:\Users\Prince\Downloads\SMQ BIBLES\SMQ BIBLES"
    r"\2018 Eastern Regional Contests\CONTEST 1.docx"
)

WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def extract_text_from_xml(xml_bytes):
    root = ET.fromstring(xml_bytes)

    paragraphs = []

    for paragraph in root.iter(f"{{{WORD_NAMESPACE}}}p"):
        text_parts = []

        for text_node in paragraph.iter(f"{{{WORD_NAMESPACE}}}t"):
            if text_node.text:
                text_parts.append(text_node.text)

        text = "".join(text_parts).strip()

        if text:
            paragraphs.append(text)

    return paragraphs


def inspect_file(path):
    print("=" * 70)
    print(f"FILE: {path}")
    print("=" * 70)

    with ZipFile(path) as archive:

        document_xml = archive.read("word/document.xml")

        paragraphs = extract_text_from_xml(document_xml)

        print(f"\nExtracted paragraphs: {len(paragraphs)}")

        print("\n" + "=" * 70)
        print("DOCUMENT CONTENT")
        print("=" * 70)

        for number, paragraph in enumerate(paragraphs, start=1):
            print(f"[{number}] {paragraph}")


if __name__ == "__main__":
    inspect_file(FILE)