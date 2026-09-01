from pathlib import Path
from collections import Counter
import csv
import re


INPUT = Path("data/unified_corpus.csv")


def load_records():
    with INPUT.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def extract_years(text):
    return sorted(
        set(
            re.findall(
                r"\b(?:19|20)\d{2}\b",
                text,
            )
        )
    )


def main():

    records = load_records()

    print("=" * 70)
    print("QUIZ INTELLIGENCE CANONICAL CORPUS REPORT")
    print("=" * 70)

    print(f"\nCanonical documents: {len(records)}")

    # ---------------------------------------------------------
    # Source types
    # ---------------------------------------------------------

    source_types = Counter(
        record["canonical_source_type"]
        for record in records
    )

    print("\nSOURCE TYPE")
    print("-" * 40)

    for source_type, count in source_types.most_common():
        print(f"{source_type:20} {count}")

    # ---------------------------------------------------------
    # Extensions
    # ---------------------------------------------------------

    extensions = Counter(
        record["canonical_extension"]
        for record in records
    )

    print("\nFILE TYPES")
    print("-" * 40)

    for extension, count in extensions.most_common():
        print(f"{extension:10} {count}")

    # ---------------------------------------------------------
    # Years
    # ---------------------------------------------------------

    years = Counter()

    for record in records:

        text = (
            record["canonical_path"]
            + " "
            + record["all_sources"]
        )

        for year in extract_years(text):
            years[year] += 1

    print("\nYEAR HINTS IN CANONICAL SOURCES")
    print("-" * 40)

    for year, count in sorted(years.items()):
        print(f"{year}: {count}")

    # ---------------------------------------------------------
    # Competition
    # ---------------------------------------------------------

    competition_hints = Counter()

    for record in records:

        text = (
            record["canonical_path"]
            + " "
            + record["all_sources"]
        ).lower()

        if "shark" in text:
            competition_hints["Sharks"] += 1

        if "nsmq" in text or "smq" in text:
            competition_hints["NSMQ/SMQ"] += 1

    print("\nCOMPETITION HINTS")
    print("-" * 40)

    for name, count in competition_hints.most_common():
        print(f"{name:20} {count}")

    # ---------------------------------------------------------
    # Question-format hints
    # ---------------------------------------------------------

    keywords = {
        "round_1": [
            "round 1",
            "round1",
        ],
        "round_2": [
            "round 2",
            "round2",
        ],
        "round_3": [
            "round 3",
            "round3",
        ],
        "round_4": [
            "round 4",
            "round4",
        ],
        "round_5": [
            "round 5",
            "round5",
        ],
        "speed_race": [
            "speed race",
        ],
        "true_false": [
            "true or false",
            "true or false",
        ],
        "riddles": [
            "riddle",
            "riddles",
        ],
        "problem_of_day": [
            "problem of the day",
            "potd",
        ],
        "final": [
            "final",
            "finals",
        ],
        "prelim": [
            "prelim",
            "preliminary",
        ],
        "regional": [
            "regional",
            "regionals",
        ],
    }

    format_counts = Counter()

    for record in records:

        text = (
            record["canonical_path"]
            + " "
            + record["canonical_filename"]
        ).lower()

        for category, terms in keywords.items():

            if any(term in text for term in terms):
                format_counts[category] += 1

    print("\nFORMAT / ROUND HINTS")
    print("-" * 40)

    for category, count in format_counts.most_common():
        print(f"{category:20} {count}")

    # ---------------------------------------------------------
    # Subject hints
    # ---------------------------------------------------------

    subjects = {
        "biology": [
            "biology",
        ],
        "chemistry": [
            "chemistry",
        ],
        "mathematics": [
            "math",
            "maths",
            "mathematics",
        ],
        "physics": [
            "physics",
        ],
    }

    subject_counts = Counter()

    for record in records:

        text = (
            record["canonical_path"]
            + " "
            + record["canonical_filename"]
        ).lower()

        for subject, terms in subjects.items():

            if any(term in text for term in terms):
                subject_counts[subject] += 1

    print("\nSUBJECT HINTS")
    print("-" * 40)

    for subject, count in subject_counts.most_common():
        print(f"{subject:20} {count}")

    # ---------------------------------------------------------
    # Likely non-question material
    # ---------------------------------------------------------

    reference_terms = [
        "coursebook",
        "calculus",
        "solved problems",
        "cambridge",
        "bpoc",
        "textbook",
    ]

    reference_candidates = []

    for record in records:

        text = (
            record["canonical_path"]
            + " "
            + record["canonical_filename"]
        ).lower()

        if any(term in text for term in reference_terms):
            reference_candidates.append(
                record["canonical_path"]
            )

    print("\nPOSSIBLE REFERENCE MATERIAL")
    print("-" * 40)
    print(
        f"Candidates: {len(reference_candidates)}"
    )

    for path in reference_candidates[:30]:
        print(f"  {path}")

    # ---------------------------------------------------------
    # Archive members
    # ---------------------------------------------------------

    archive_records = [
        record
        for record in records
        if record["canonical_source_type"]
        == "archive_member"
    ]

    print("\nCANONICAL DOCUMENTS FROM ARCHIVES")
    print("-" * 40)
    print(f"Count: {len(archive_records)}")

    # ---------------------------------------------------------
    # Largest canonical documents
    # ---------------------------------------------------------

    largest = sorted(
        records,
        key=lambda record: int(record["size_bytes"]),
        reverse=True,
    )

    print("\n20 LARGEST CANONICAL DOCUMENTS")
    print("-" * 40)

    for record in largest[:20]:

        size_mb = (
            int(record["size_bytes"])
            / (1024 * 1024)
        )

        print(
            f"{size_mb:8.2f} MB  "
            f"{record['canonical_path']}"
        )


if __name__ == "__main__":
    main()
