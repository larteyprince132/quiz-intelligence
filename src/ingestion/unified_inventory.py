from pathlib import Path
from collections import defaultdict
import csv


LOOSE_INVENTORY = Path("data/raw_inventory.csv")
ARCHIVE_INVENTORY = Path("data/archive_inventory.csv")

UNIFIED_OUTPUT = Path("data/unified_corpus.csv")
DUPLICATE_OUTPUT = Path("data/cross_source_duplicates.csv")


def load_csv(path):
    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def canonical_score(record):
    """
    Lower score = better canonical source.
    """

    score = 0

    source_type = record["source_type"]
    extension = record["extension"]
    filename = record["filename"].lower()
    source_path = record["source_path"].lower()

    # Prefer files that exist directly on disk.
    if source_type == "archive_member":
        score += 10

    # Prefer modern Word format over legacy Word format.
    if extension == ".doc":
        score += 2

    # Avoid obvious copies when an equally valid original exists.
    if "copy of" in source_path:
        score += 10

    if "(2)" in filename or "(3)" in filename or "(4)" in filename:
        score += 5

    return score


def prepare_loose_records(records):
    prepared = []

    for record in records:

        extension = record["extension"].lower()
        filename = record["filename"]

        # ZIP containers are handled through their members.
        if extension == ".zip":
            continue

        # Temporary Office files should never enter the corpus.
        if filename.startswith("~$"):
            continue

        prepared.append({
            "sha256": record["sha256"],
            "source_type": "loose_file",
            "filename": filename,
            "extension": extension,
            "size_bytes": record["size_bytes"],
            "source_path": record["relative_path"],
        })

    return prepared


def prepare_archive_records(records):
    prepared = []

    for record in records:

        filename = Path(record["member_path"]).name

        # Ignore Office temporary files stored inside archives.
        if filename.startswith("~$"):
            continue

        prepared.append({
            "sha256": record["sha256"],
            "source_type": "archive_member",
            "filename": filename,
            "extension": record["extension"].lower(),
            "size_bytes": record["size_bytes"],
            "source_path": (
                f"{record['archive']}::"
                f"{record['member_path']}"
            ),
        })

    return prepared


def main():

    loose_records = prepare_loose_records(
        load_csv(LOOSE_INVENTORY)
    )

    archive_records = prepare_archive_records(
        load_csv(ARCHIVE_INVENTORY)
    )

    all_records = loose_records + archive_records

    groups = defaultdict(list)

    for record in all_records:
        groups[record["sha256"]].append(record)

    # ---------------------------------------------------------
    # Build unified corpus
    # ---------------------------------------------------------

    unified = []

    for sha256, members in groups.items():

        canonical = min(
            members,
            key=canonical_score
        )

        source_paths = sorted(
            record["source_path"]
            for record in members
        )

        unified.append({
            "sha256": sha256,
            "canonical_source_type": canonical["source_type"],
            "canonical_filename": canonical["filename"],
            "canonical_extension": canonical["extension"],
            "canonical_path": canonical["source_path"],
            "size_bytes": canonical["size_bytes"],
            "source_count": len(members),
            "all_sources": " | ".join(source_paths),
        })

    unified.sort(
        key=lambda record: record["canonical_path"].lower()
    )

    # ---------------------------------------------------------
    # Save unified inventory
    # ---------------------------------------------------------

    UNIFIED_OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with UNIFIED_OUTPUT.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "sha256",
                "canonical_source_type",
                "canonical_filename",
                "canonical_extension",
                "canonical_path",
                "size_bytes",
                "source_count",
                "all_sources",
            ],
        )

        writer.writeheader()
        writer.writerows(unified)

    # ---------------------------------------------------------
    # Save all duplicate groups
    # ---------------------------------------------------------

    duplicate_groups = {
        sha256: members
        for sha256, members in groups.items()
        if len(members) > 1
    }

    with DUPLICATE_OUTPUT.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "sha256",
            "source_count",
            "source_type",
            "filename",
            "extension",
            "source_path",
        ])

        for sha256, members in sorted(
            duplicate_groups.items(),
            key=lambda item: len(item[1]),
            reverse=True,
        ):

            for member in members:
                writer.writerow([
                    sha256,
                    len(members),
                    member["source_type"],
                    member["filename"],
                    member["extension"],
                    member["source_path"],
                ])

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------

    total_candidates = len(all_records)
    unique_contents = len(groups)

    duplicate_groups_count = len(duplicate_groups)

    duplicate_records = sum(
        len(members)
        for members in duplicate_groups.values()
    )

    cross_source_groups = 0

    for members in duplicate_groups.values():

        source_types = {
            member["source_type"]
            for member in members
        }

        if len(source_types) > 1:
            cross_source_groups += 1

    print("=" * 70)
    print("UNIFIED CORPUS ANALYSIS")
    print("=" * 70)

    print(f"\nLoose content files: {len(loose_records)}")
    print(f"Archive member files: {len(archive_records)}")
    print(f"Total candidate contents: {total_candidates}")

    print(f"\nUnique contents across ALL sources: {unique_contents}")

    print(f"\nExact duplicate groups: {duplicate_groups_count}")
    print(f"Files in duplicate groups: {duplicate_records}")

    print(
        "\nDuplicate groups crossing loose files "
        f"and archives: {cross_source_groups}"
    )

    print("\nSaved:")
    print(f"  {UNIFIED_OUTPUT}")
    print(f"  {DUPLICATE_OUTPUT}")


if __name__ == "__main__":
    main()