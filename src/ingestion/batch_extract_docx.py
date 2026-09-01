from pathlib import Path
from zipfile import ZipFile, BadZipFile
from io import BytesIO
from lxml import etree
from collections import Counter
import csv
import json
import hashlib
import re


RAW_ROOT = Path(
    r"C:\Users\Prince\Downloads\SMQ BIBLES"
)

CORPUS_FILE = Path(
    "data/unified_corpus.csv"
)

OUTPUT_DIR = Path(
    "data/processed/documents"
)

REPORT_FILE = Path(
    "data/processed/docx_extraction_report.csv"
)


NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def load_corpus():
    with CORPUS_FILE.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def find_archive(archive_name):
    matches = list(
        RAW_ROOT.rglob(archive_name)
    )

    if not matches:
        raise FileNotFoundError(
            f"Archive not found: {archive_name}"
        )

    return matches[0]


def read_source_bytes(record):
    source_type = record[
        "canonical_source_type"
    ]

    source_path = record[
        "canonical_path"
    ]

    if source_type == "loose_file":

        path = RAW_ROOT / source_path

        if not path.exists():
            raise FileNotFoundError(
                f"Loose file not found: {path}"
            )

        return path.read_bytes()

    if source_type == "archive_member":

        archive_name, member_path = (
            source_path.split("::", 1)
        )

        archive_path = find_archive(
            archive_name
        )

        with ZipFile(archive_path) as archive:

            if member_path not in archive.namelist():
                raise FileNotFoundError(
                    f"Archive member not found: "
                    f"{member_path}"
                )

            return archive.read(
                member_path
            )

    raise ValueError(
        f"Unsupported source type: {source_type}"
    )


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


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


def document_relationships(archive):
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
        target = relationship.get("Target")

        if not rel_id or not target:
            continue

        relationships[rel_id] = target

    return relationships


def paragraph_images(
    paragraph,
    relationships,
):
    images = []

    for blip in paragraph.findall(
        ".//a:blip",
        namespaces=NS,
    ):

        rel_id = blip.get(
            f"{{{NS['r']}}}embed"
        )

        if rel_id:

            images.append({
                "relationship_id": rel_id,
                "target": relationships.get(
                    rel_id
                ),
            })

    return images


def extract_paragraph(
    paragraph,
    relationships,
):
    text = paragraph_text(
        paragraph
    )

    return {
        "type": "paragraph",
        "text": text,
        "style": paragraph_style(
            paragraph
        ),
        "images": paragraph_images(
            paragraph,
            relationships,
        ),
    }


def extract_table(
    table,
    relationships,
):
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

            cell_paragraphs = []

            for paragraph in cell.findall(
                ".//w:p",
                namespaces=NS,
            ):

                cell_paragraphs.append(
                    extract_paragraph(
                        paragraph,
                        relationships,
                    )
                )

            cells.append({
                "text": "\n".join(
                    item["text"]
                    for item in cell_paragraphs
                    if item["text"]
                ),
                "paragraphs": cell_paragraphs,
            })

        rows.append({
            "cells": cells
        })

    return {
        "type": "table",
        "rows": rows,
    }


def extract_body(
    root,
    relationships,
):
    body = root.find(
        "w:body",
        namespaces=NS,
    )

    if body is None:
        raise ValueError(
            "Document body not found"
        )

    blocks = []

    for child in body:

        if child.tag == f"{{{NS['w']}}}p":

            item = extract_paragraph(
                child,
                relationships,
            )

            if item["text"] or item["images"]:
                blocks.append(item)

        elif child.tag == f"{{{NS['w']}}}tbl":

            blocks.append(
                extract_table(
                    child,
                    relationships,
                )
            )

    return blocks


def extract_headers_footers(
    archive,
):
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

        texts = []

        for paragraph in root.findall(
            ".//w:p",
            namespaces=NS,
        ):

            text = paragraph_text(
                paragraph
            )

            if text:
                texts.append(text)

        if name.startswith("word/header"):

            result["headers"][name] = texts

        else:

            result["footers"][name] = texts

    return result


def extract_media(archive):
    media = []

    for name in archive.namelist():

        if not name.startswith(
            "word/media/"
        ):
            continue

        if name.endswith("/"):
            continue

        info = archive.getinfo(name)

        media.append({
            "path": name,
            "size_bytes": info.file_size,
        })

    return media


def extract_docx(
    record,
    source_bytes,
):
    source_hash = sha256_bytes(
        source_bytes
    )

    with ZipFile(
        BytesIO(source_bytes)
    ) as archive:

        if "word/document.xml" not in archive.namelist():
            raise ValueError(
                "Not a valid WordprocessingML "
                "document: word/document.xml missing"
            )

        document_xml = archive.read(
            "word/document.xml"
        )

        root = etree.fromstring(
            document_xml
        )

        relationships = (
            document_relationships(
                archive
            )
        )

        blocks = extract_body(
            root,
            relationships,
        )

        headers_footers = (
            extract_headers_footers(
                archive
            )
        )

        media = extract_media(
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

        image_paragraphs = sum(
            1
            for block in blocks
            if block["type"] == "paragraph"
            and block["images"]
        )

    document_id = source_hash[:16]

    return {
        "document_id": document_id,
        "sha256": source_hash,

        "source": {
            "source_type": record[
                "canonical_source_type"
            ],
            "canonical_path": record[
                "canonical_path"
            ],
            "canonical_filename": record[
                "canonical_filename"
            ],
            "extension": record[
                "canonical_extension"
            ],
        },

        "blocks": blocks,

        "headers_footers": (
            headers_footers
        ),

        "media": media,

        "statistics": {
            "paragraphs": paragraph_count,
            "tables": table_count,
            "media_files": len(media),
            "paragraphs_with_images": (
                image_paragraphs
            ),
        },
    }


def extract_year_hints(text):
    return sorted(
        set(
            re.findall(
                r"\b(?:19|20)\d{2}\b",
                text,
            )
        )
    )


def process_record(record):
    source_bytes = read_source_bytes(
        record
    )

    document = extract_docx(
        record,
        source_bytes,
    )

    year_text = (
        record["canonical_path"]
        + " "
        + record["canonical_filename"]
    )

    document["metadata_hints"] = {
        "years_from_path": (
            extract_year_hints(year_text)
        ),
    }

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

    return document, output_file


def main():

    records = load_corpus()

    docx_records = [
        record
        for record in records
        if record["canonical_extension"]
        == ".docx"
    ]

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 70)
    print("BATCH DOCX EXTRACTION")
    print("=" * 70)

    print(
        f"\nCanonical DOCX documents: "
        f"{len(docx_records)}"
    )

    results = []

    success = 0
    failed = 0

    statistics = Counter()

    for index, record in enumerate(
        docx_records,
        start=1,
    ):

        try:

            document, output_file = (
                process_record(record)
            )

            success += 1

            statistics[
                "paragraphs"
            ] += document[
                "statistics"
            ]["paragraphs"]

            statistics[
                "tables"
            ] += document[
                "statistics"
            ]["tables"]

            statistics[
                "media_files"
            ] += document[
                "statistics"
            ]["media_files"]

            results.append({
                "status": "success",
                "document_id": document[
                    "document_id"
                ],
                "source_type": record[
                    "canonical_source_type"
                ],
                "source": record[
                    "canonical_path"
                ],
                "paragraphs": document[
                    "statistics"
                ]["paragraphs"],
                "tables": document[
                    "statistics"
                ]["tables"],
                "media_files": document[
                    "statistics"
                ]["media_files"],
                "output": str(
                    output_file
                ),
                "error": "",
            })

        except Exception as error:

            failed += 1

            results.append({
                "status": "failed",
                "document_id": "",
                "source_type": record[
                    "canonical_source_type"
                ],
                "source": record[
                    "canonical_path"
                ],
                "paragraphs": "",
                "tables": "",
                "media_files": "",
                "output": "",
                "error": (
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            })

        if (
            index == 1
            or index % 25 == 0
            or index == len(docx_records)
        ):

            print(
                f"[{index}/{len(docx_records)}] "
                f"Success={success} "
                f"Failed={failed}"
            )

    with REPORT_FILE.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "status",
                "document_id",
                "source_type",
                "source",
                "paragraphs",
                "tables",
                "media_files",
                "output",
                "error",
            ],
        )

        writer.writeheader()
        writer.writerows(results)

    print()
    print("=" * 70)
    print("BATCH EXTRACTION COMPLETE")
    print("=" * 70)

    print(
        f"\nAttempted: {len(docx_records)}"
    )

    print(
        f"Successful: {success}"
    )

    print(
        f"Failed: {failed}"
    )

    print(
        f"Total paragraphs extracted: "
        f"{statistics['paragraphs']}"
    )

    print(
        f"Total tables extracted: "
        f"{statistics['tables']}"
    )

    print(
        f"Total media files found: "
        f"{statistics['media_files']}"
    )

    print(
        f"\nReport: {REPORT_FILE}"
    )

    print(
        f"JSON directory: {OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()