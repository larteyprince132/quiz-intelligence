from pathlib import Path
from zipfile import ZipFile
from lxml import etree
import csv
import re


RAW_ROOT = Path(
    r"C:\Users\Prince\Downloads\SMQ BIBLES"
)

CORPUS_FILE = Path(
    "data/unified_corpus.csv"
)


NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
}


YEARS = [
    "2009",
    "2012",
    "2013",
    "2014",
    "2015",
    "2016",
    "2017",
    "2018",
    "2019",
    "2020",
    "2021",
    "2022",
]


SPECIAL_PATTERNS = [
    "riddle",
    "speed race",
    "true or false",
    "problem of the day",
]


def load_corpus():
    with CORPUS_FILE.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def load_docx_xml(record):
    """
    Return the document.xml bytes regardless of whether
    the source is a loose file or an archive member.
    """

    source_type = record["canonical_source_type"]
    source_path = record["canonical_path"]

    if source_type == "loose_file":

        path = RAW_ROOT / source_path

        with ZipFile(path) as archive:
            return archive.read("word/document.xml")

    if source_type == "archive_member":

        archive_name, member_path = source_path.split(
            "::",
            1,
        )

        archive_path = RAW_ROOT / archive_name

        with ZipFile(archive_path) as archive:
            return archive.read(
                f"{member_path.rsplit('/', 1)[0]}/"
                f"{'document.xml' if '/' in member_path else 'document.xml'}"
            )

    raise ValueError(
        f"Unknown source type: {source_type}"
    )


def get_document_xml(record):
    """
    Handles OOXML path variations inside archives.
    """

    source_type = record["canonical_source_type"]

    if source_type == "loose_file":

        path = RAW_ROOT / record["canonical_path"]

        with ZipFile(path) as archive:
            return archive.read("word/document.xml")

    archive_name, member_path = record[
        "canonical_path"
    ].split("::", 1)

    archive_path = RAW_ROOT / archive_name

    with ZipFile(archive_path) as outer_archive:

        document_bytes = outer_archive.read(
            member_path
        )

    # The archive member itself is another DOCX zip.
    from io import BytesIO

    with ZipFile(BytesIO(document_bytes)) as inner_archive:
        return inner_archive.read(
            "word/document.xml"
        )


def get_media_count(record):
    source_type = record["canonical_source_type"]

    if source_type == "loose_file":

        path = RAW_ROOT / record["canonical_path"]

        with ZipFile(path) as archive:

            return len([
                name
                for name in archive.namelist()
                if name.startswith("word/media/")
                and not name.endswith("/")
            ])

    archive_name, member_path = record[
        "canonical_path"
    ].split("::", 1)

    archive_path = RAW_ROOT / archive_name

    from io import BytesIO

    with ZipFile(archive_path) as outer_archive:

        document_bytes = outer_archive.read(
            member_path
        )

    with ZipFile(BytesIO(document_bytes)) as inner_archive:

        return len([
            name
            for name in inner_archive.namelist()
            if name.startswith("word/media/")
            and not name.endswith("/")
        ])


def extract_paragraphs(xml_bytes):
    root = etree.fromstring(xml_bytes)

    paragraphs = []

    for paragraph in root.findall(
        ".//w:body/w:p",
        namespaces=NS,
    ):

        parts = []

        for node in paragraph.iter():

            if node.tag == f"{{{NS['w']}}}t":

                if node.text:
                    parts.append(node.text)

            elif node.tag == f"{{{NS['w']}}}tab":
                parts.append("\t")

            elif node.tag == f"{{{NS['w']}}}br":
                parts.append("\n")

        text = "".join(parts).strip()

        if text:
            paragraphs.append(text)

    return paragraphs


def has_tables(xml_bytes):
    root = etree.fromstring(xml_bytes)

    return len(
        root.findall(
            ".//w:tbl",
            namespaces=NS,
        )
    )


def score_document(record):
    """
    Prefer ordinary contest material over books/reference material.
    """

    text = (
        record["canonical_path"]
        + " "
        + record["canonical_filename"]
    ).lower()

    score = 0

    bad_terms = [
        "coursebook",
        "calculus",
        "solved problems",
        "bpoc",
        "textbook",
    ]

    for term in bad_terms:
        if term in text:
            score -= 100

    good_terms = [
        "contest",
        "nsmq",
        "round",
        "final",
        "prelim",
        "question",
    ]

    for term in good_terms:
        if term in text:
            score += 10

    return score


def select_year_samples(records):

    samples = []

    docx_records = [
        record
        for record in records
        if record["canonical_extension"]
        == ".docx"
    ]

    for year in YEARS:

        candidates = [
            record
            for record in docx_records
            if year in (
                record["canonical_path"]
                + " "
                + record["canonical_filename"]
            )
        ]

        candidates.sort(
            key=score_document,
            reverse=True,
        )

        if candidates:
            samples.append(candidates[0])

    return samples


def select_special_samples(records):

    samples = []

    docx_records = [
        record
        for record in records
        if record["canonical_extension"]
        == ".docx"
    ]

    for pattern in SPECIAL_PATTERNS:

        candidates = [
            record
            for record in docx_records
            if pattern in (
                record["canonical_path"]
                + " "
                + record["canonical_filename"]
            ).lower()
        ]

        candidates.sort(
            key=score_document,
            reverse=True,
        )

        if candidates:
            samples.append(candidates[0])

    return samples


def inspect(record):

    print()
    print("=" * 80)
    print("SAMPLE")
    print("=" * 80)

    print(
        f"Source type: "
        f"{record['canonical_source_type']}"
    )

    print(
        f"Path: "
        f"{record['canonical_path']}"
    )

    try:

        xml = get_document_xml(record)

        paragraphs = extract_paragraphs(xml)

        tables = has_tables(xml)

        media = get_media_count(record)

        print(
            f"\nParagraphs: {len(paragraphs)}"
        )

        print(
            f"Tables: {tables}"
        )

        print(
            f"Media files: {media}"
        )

        print("\nFirst 20 non-empty paragraphs:")

        for number, paragraph in enumerate(
            paragraphs[:20],
            start=1,
        ):
            print(
                f"[{number:02}] {paragraph}"
            )

    except Exception as error:

        print(
            "\n!!! EXTRACTION ERROR !!!"
        )

        print(
            f"{type(error).__name__}: {error}"
        )


def main():

    records = load_corpus()

    samples = (
        select_year_samples(records)
        + select_special_samples(records)
    )

    # Remove duplicate records while preserving order.
    seen = set()
    unique_samples = []

    for record in samples:

        key = record["sha256"]

        if key not in seen:
            seen.add(key)
            unique_samples.append(record)

    print(
        f"Selected samples: "
        f"{len(unique_samples)}"
    )

    for record in unique_samples:
        inspect(record)


if __name__ == "__main__":
    main()