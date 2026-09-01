from pathlib import Path
from collections import defaultdict
import csv


INVENTORY = Path("data/raw_inventory.csv")

DUPLICATE_REPORT = Path("data/duplicate_groups.csv")
CANONICAL_REPORT = Path("data/canonical_files.csv")


def load_inventory():
    with INVENTORY.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def group_by_hash(records):
    groups = defaultdict(list)

    for record in records:
        groups[record["sha256"]].append(record)

    return groups


def canonical_score(record):
    """
    Lower score = better candidate for the canonical copy.
    """

    path = record["relative_path"].lower()
    name = record["filename"].lower()

    score = 0

    # Avoid obvious copies.
    if "copy of" in path:
        score += 10

    if "(2)" in name or "(3)" in name or "(4)" in name:
        score += 5

    # Avoid temporary/backup-looking names.
    if name.startswith("copy"):
        score += 5

    # Prefer DOCX over legacy DOC where exact content is identical.
    if record["extension"] == ".doc":
        score += 2

    return score


def choose_canonical(records):
    return min(records, key=canonical_score)


def main():
    records = load_inventory()
    groups = group_by_hash(records)

    duplicate_groups = {
        digest: members
        for digest, members in groups.items()
        if len(members) > 1
    }

    canonical_files = []

    for digest, members in groups.items():

        canonical = choose_canonical(members)

        canonical_files.append({
            "sha256": digest,
            "canonical_path": canonical["relative_path"],
            "canonical_extension": canonical["extension"],
            "duplicate_count": len(members),
        })

    # ---------------------------------------------------------
    # Duplicate report
    # ---------------------------------------------------------

    with DUPLICATE_REPORT.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "sha256",
            "duplicate_count",
            "filename",
            "extension",
            "relative_path",
            "canonical",
        ])

        for digest, members in sorted(
            duplicate_groups.items(),
            key=lambda item: len(item[1]),
            reverse=True,
        ):

            canonical = choose_canonical(members)

            for member in members:

                writer.writerow([
                    digest,
                    len(members),
                    member["filename"],
                    member["extension"],
                    member["relative_path"],
                    member["relative_path"]
                    == canonical["relative_path"],
                ])

    # ---------------------------------------------------------
    # Canonical report
    # ---------------------------------------------------------

    with CANONICAL_REPORT.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "sha256",
                "canonical_path",
                "canonical_extension",
                "duplicate_count",
            ],
        )

        writer.writeheader()
        writer.writerows(canonical_files)

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------

    total_files = len(records)
    unique_contents = len(groups)
    duplicate_groups_count = len(duplicate_groups)

    duplicate_files = sum(
        len(members)
        for members in duplicate_groups.values()
    )

    print("=" * 70)
    print("DOCUMENT DEDUPLICATION ANALYSIS")
    print("=" * 70)

    print(f"\nTotal indexed files: {total_files}")
    print(f"Unique file contents: {unique_contents}")
    print(f"Exact duplicate groups: {duplicate_groups_count}")
    print(f"Files in duplicate groups: {duplicate_files}")

    print("\nCanonical files:")
    print(f"  {unique_contents}")

    print("\nReports:")
    print(f"  {DUPLICATE_REPORT}")
    print(f"  {CANONICAL_REPORT}")

    print("\nLargest duplicate groups:")

    for digest, members in sorted(
        duplicate_groups.items(),
        key=lambda item: len(item[1]),
        reverse=True,
    )[:20]:

        canonical = choose_canonical(members)

        print(
            f"\n{len(members)} copies:"
        )

        print(
            f"  CANONICAL: {canonical['relative_path']}"
        )

        for member in members:
            if member["relative_path"] != canonical["relative_path"]:
                print(
                    f"  duplicate: {member['relative_path']}"
                )


if __name__ == "__main__":
    main()