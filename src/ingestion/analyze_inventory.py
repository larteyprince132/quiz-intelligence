from pathlib import Path
import csv
import re
from collections import Counter, defaultdict


INVENTORY = Path("data/raw_inventory.csv")


def load_inventory():
    with INVENTORY.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def format_bytes(value):
    value = float(value)

    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024:
            return f"{value:.2f} {unit}"
        value /= 1024

    return f"{value:.2f} TB"


def main():
    records = load_inventory()

    print("=" * 70)
    print("QUIZ INTELLIGENCE CORPUS ANALYSIS")
    print("=" * 70)

    print(f"\nTotal indexed files: {len(records)}")

    total_size = sum(
        int(record["size_bytes"])
        for record in records
    )

    print(f"Total indexed size: {format_bytes(total_size)}")

    # ---------------------------------------------------------
    # File types
    # ---------------------------------------------------------

    extensions = Counter(
        record["extension"]
        for record in records
    )

    print("\nFILE TYPES")
    print("-" * 40)

    for extension, count in extensions.most_common():
        print(f"{extension:8} {count}")

    # ---------------------------------------------------------
    # Exact duplicate files
    # ---------------------------------------------------------

    hashes = defaultdict(list)

    for record in records:
        hashes[record["sha256"]].append(record["relative_path"])

    duplicate_groups = {
        digest: paths
        for digest, paths in hashes.items()
        if len(paths) > 1
    }

    duplicate_file_count = sum(
        len(paths)
        for paths in duplicate_groups.values()
    )

    print("\nEXACT DUPLICATES")
    print("-" * 40)
    print(f"Duplicate groups: {len(duplicate_groups)}")
    print(f"Files belonging to duplicate groups: {duplicate_file_count}")

    for index, paths in enumerate(
        sorted(
            duplicate_groups.values(),
            key=len,
            reverse=True
        )[:10],
        start=1,
    ):
        print(f"\nDuplicate group {index} ({len(paths)} files):")

        for path in paths[:5]:
            print(f"  {path}")

        if len(paths) > 5:
            print(f"  ... and {len(paths) - 5} more")

    # ---------------------------------------------------------
    # Years found in paths
    # ---------------------------------------------------------

    years = Counter()

    for record in records:
        matches = re.findall(
            r"\b(?:19|20)\d{2}\b",
            record["relative_path"],
        )

        for year in set(matches):
            years[year] += 1

    print("\nYEARS MENTIONED IN PATHS")
    print("-" * 40)

    for year, count in sorted(years.items()):
        print(f"{year}: {count}")

    # ---------------------------------------------------------
    # Competition hints
    # ---------------------------------------------------------

    nsmq = 0
    sharks = 0

    for record in records:
        path = record["relative_path"].lower()

        if "nsmq" in path or "smq" in path:
            nsmq += 1

        if "sharks" in path:
            sharks += 1

    print("\nCOMPETITION HINTS FROM PATHS")
    print("-" * 40)
    print(f"NSMQ/SMQ mentions: {nsmq}")
    print(f"Sharks mentions:    {sharks}")

    # ---------------------------------------------------------
    # Reference-material warning
    # ---------------------------------------------------------

    reference_keywords = [
        "book",
        "coursebook",
        "calculus",
        "solved problems",
        "cambridge",
        "bpoc",
    ]

    reference_files = []

    for record in records:
        path = record["relative_path"].lower()

        if any(
            keyword in path
            for keyword in reference_keywords
        ):
            reference_files.append(record["relative_path"])

    print("\nPOSSIBLE REFERENCE MATERIAL")
    print("-" * 40)
    print(f"Possible reference files: {len(reference_files)}")

    for path in reference_files[:20]:
        print(f"  {path}")

    if len(reference_files) > 20:
        print(f"  ... and {len(reference_files) - 20} more")

    # ---------------------------------------------------------
    # Largest files
    # ---------------------------------------------------------

    largest = sorted(
        records,
        key=lambda record: int(record["size_bytes"]),
        reverse=True,
    )

    print("\n20 LARGEST FILES")
    print("-" * 40)

    for record in largest[:20]:
        print(
            f"{format_bytes(record['size_bytes']):>10}  "
            f"{record['relative_path']}"
        )


if __name__ == "__main__":
    main()