from pathlib import Path
from zipfile import ZipFile
from lxml import etree
import hashlib
import json
import posixpath


RAW_FILE = Path(
    r"C:\Users\Prince\Downloads\SMQ BIBLES\SMQ BIBLES"
    r"\2018 Eastern Regional Contests\CONTEST 1.docx"
)

OUTPUT_DIR = Path("data/processed/documents")


NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "v": "urn:schemas-microsoft-com:vml",
}


def sha256_file(path):
    sha256 = hashlib.sha256()

    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            sha256.update(chunk)

    return sha256.hexdigest()


def detect_document_type(archive):
    content_types = archive.read(
        "[Content_Types].xml"
    ).decode(
        "utf-8",
        errors="replace",
    )

    if "macroEnabled.main+xml" in content_types:
        return "macro_enabled_ooxml"

    if "wordprocessingml.document.main+xml" in content_types:
        return "standard_ooxml"

    return "unknown_ooxml"


def load_relationships(archive):
    relationships = {}

    try:
        xml = archive.read(
            "word/_rels/document.xml.rels"
        )

    except KeyError:
        return relationships

    root = etree.fromstring(xml)

    for relationship in root:

        rel_id = relationship.get("Id")
        rel_type = relationship.get("Type")
        target = relationship.get("Target")

        if not rel_id or not target:
            continue

        target_path = posixpath.normpath(
            posixpath.join("word", target)
        )

        relationships[rel_id] = {
            "type": rel_type,
            "target": target_path,
        }

    return relationships


def paragraph_text(paragraph):
    parts = []

    for node in paragraph.iter():

        if node.tag == f"{{{NS['w']}}}t":

            if node.text:
                parts.append(node.text)

        elif node.tag == f"{{{NS['w']}}}tab":

            parts.append("\t")

        elif node.tag == f"{{{NS['w']}}}br":

            parts.append("\n")

        elif node.tag == f"{{{NS['w']}}}cr":

            parts.append("\n")

    return "".join(parts).strip()


def paragraph_style(paragraph):
    style = paragraph.find(
        "w:pPr/w:pStyle",
        namespaces=NS,
    )

    if style is None:
        return None

    return style.get(
        f"{{{NS['w']}}}val"
    )


def paragraph_images(paragraph, relationships):
    images = []

    # Modern DrawingML images.
    for blip in paragraph.findall(
        ".//a:blip",
        namespaces=NS,
    ):

        rel_id = blip.get(
            f"{{{NS['r']}}}embed"
        )

        if rel_id and rel_id in relationships:

            relationship = relationships[rel_id]

            images.append({
                "relationship_id": rel_id,
                "target": relationship["target"],
            })

    # Older VML images.
    for image_data in paragraph.findall(
        ".//v:imagedata",
        namespaces=NS,
    ):

        rel_id = image_data.get(
            f"{{{NS['r']}}}id"
        )

        if rel_id and rel_id in relationships:

            relationship = relationships[rel_id]

            images.append({
                "relationship_id": rel_id,
                "target": relationship["target"],
            })

    # Remove duplicates while preserving order.
    unique = []
    seen = set()

    for image in images:

        key = (
            image["relationship_id"],
            image["target"],
        )

        if key not in seen:
            seen.add(key)
            unique.append(image)

    return unique


def extract_paragraph(paragraph, relationships):
    text = paragraph_text(paragraph)

    return {
        "type": "paragraph",
        "text": text,
        "style": paragraph_style(paragraph),
        "images": paragraph_images(
            paragraph,
            relationships,
        ),
    }


def extract_table(table, relationships):
    rows = []

    for row in table.findall(
        "w:tr",
        namespaces=NS,
    ):

        cells = []

        for cell in row.findall(
            "w:tc",
            namespaces=NS,
        ):

            paragraphs = []

            for paragraph in cell.findall(
                ".//w:p",
                namespaces=NS,
            ):

                paragraphs.append(
                    extract_paragraph(
                        paragraph,
                        relationships,
                    )
                )

            cells.append({
                "paragraphs": paragraphs,
                "text": "\n".join(
                    item["text"]
                    for item in paragraphs
                    if item["text"]
                ),
            })

        rows.append({
            "cells": cells
        })

    return {
        "type": "table",
        "rows": rows,
    }


def extract_story(root, relationships):
    blocks = []

    body = root.find(
        "w:body",
        namespaces=NS,
    )

    if body is None:
        return blocks

    for child in body:

        if child.tag == f"{{{NS['w']}}}p":

            paragraph = extract_paragraph(
                child,
                relationships,
            )

            if paragraph["text"] or paragraph["images"]:
                blocks.append(paragraph)

        elif child.tag == f"{{{NS['w']}}}tbl":

            blocks.append(
                extract_table(
                    child,
                    relationships,
                )
            )

    return blocks


def extract_header_footer(archive, relationships):
    result = {
        "headers": {},
        "footers": {},
    }

    for name in archive.namelist():

        if not (
            name.startswith("word/header")
            or name.startswith("word/footer")
        ):
            continue

        try:
            xml = archive.read(name)
            root = etree.fromstring(xml)

        except Exception:
            continue

        paragraphs = []

        for paragraph in root.findall(
            ".//w:p",
            namespaces=NS,
        ):

            item = extract_paragraph(
                paragraph,
                relationships,
            )

            if item["text"] or item["images"]:
                paragraphs.append(item)

        if name.startswith("word/header"):
            result["headers"][name] = paragraphs

        else:
            result["footers"][name] = paragraphs

    return result


def list_media(archive):
    media = []

    for name in archive.namelist():

        if not name.startswith("word/media/"):
            continue

        # Ignore directory entries.
        if name.endswith("/"):
            continue

        info = archive.getinfo(name)

        media.append({
            "path": name,
            "size_bytes": info.file_size,
        })

    return media


def extract_document(path):
    document_hash = sha256_file(path)

    with ZipFile(path) as archive:

        document_xml = archive.read(
            "word/document.xml"
        )

        root = etree.fromstring(
            document_xml
        )

        relationships = load_relationships(
            archive
        )

        blocks = extract_story(
            root,
            relationships,
        )

        headers_footers = extract_header_footer(
            archive,
            relationships,
        )

        media = list_media(archive)

        document_type = detect_document_type(
            archive
        )

    paragraph_count = sum(
        1
        for block in blocks
        if block["type"] == "paragraph"
    )

    table_count = sum(
        1
        for block in blocks
        if block["type"] == "table"
    )

    return {
        "document_id": document_hash[:16],
        "sha256": document_hash,
        "filename": path.name,
        "source_path": str(path),
        "document_type": document_type,
        "blocks": blocks,
        "headers_footers": headers_footers,
        "media": media,
        "statistics": {
            "paragraphs": paragraph_count,
            "tables": table_count,
            "media_files": len(media),
        },
    }


def save_document(document):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        OUTPUT_DIR
        / f"{document['document_id']}.json"
    )

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            document,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return output_file


def main():

    if not RAW_FILE.exists():
        raise FileNotFoundError(
            f"File not found: {RAW_FILE}"
        )

    document = extract_document(
        RAW_FILE
    )

    output = save_document(
        document
    )

    print("=" * 70)
    print("DOCX EXTRACTION COMPLETE")
    print("=" * 70)

    print(
        f"\nFile: {document['filename']}"
    )

    print(
        f"Type: {document['document_type']}"
    )

    print(
        f"SHA-256: {document['sha256']}"
    )

    print("\nStatistics:")

    for key, value in (
        document["statistics"].items()
    ):
        print(f"  {key}: {value}")

    print("\nMedia:")

    for media in document["media"]:
        print(
            f"  {media['path']} "
            f"({media['size_bytes']:,} bytes)"
        )

    print("\nOutput:")
    print(f"  {output}")


if __name__ == "__main__":
    main()
