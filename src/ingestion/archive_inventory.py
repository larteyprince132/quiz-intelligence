from pathlib import Path
from zipfile import ZipFile
from collections import Counter
import hashlib
import csv
import re


RAW_ROOT = Path(
    r"C:\Users\Prince\Downloads\SMQ BIBLES"
)

OUTPUT = Path(
    "data/archive_inventory.csv"
)


def calculate_member_sha256(archive, member):
    sha256 = hashlib.sha256()

    with archive.open(member) as file:
        while chunk := file.read(1024 * 1024):
            sha256.update(chunk)

    return sha256.hexdigest()


def detect_year(text):
    matches = re.findall(
        r"\b(?:19|20)\d{2}\b",
        text,
    )

    years = sorted(set(matches))

    if not years:
        return ""

    return ";".join(years)


def inspect_archive(path):
    records = []

    with ZipFile(path) as archive:
        members = archive.infolist()

        for member in members:

            # Skip directory entries.
            if member.is_dir():
                continue

            name = member.filename

            extension = Path(name).suffix.lower()

            record = {
                "archive": path.name,
                "member_path": name,
                "extension": extension,
                "size_bytes": member.file_size,
                "year_hint": detect_year(name),
                "sha256": calculate_member_sha256(
                    archive,
                    member,
                ),
            }

            records.append(record)

    return records


def main():

    zip_files = sorted(
        RAW_ROOT.rglob("*.zip")
    )

    all_records = []

    print("=" * 70)
    print("ARCHIVE INVENTORY")
    print("=" * 70)

    print(
        f"\nArchives found: {len(zip_files)}"
    )

    for path in zip_files:

        print(
            f"\nProcessing archive: {path.name}"
        )

        records = inspect_archive(path)

        all_records.extend(records)

        print(
            f"Files inside: {len(records)}"
        )

        extensions = Counter(
            record["extension"]
            for record in records
        )

        print("File types:")

        for extension, count in (
            extensions.most_common()
        ):
            print(
                f"  {extension or '[no extension]':10} "
                f"{count}"
            )

        years = Counter()

        for record in records:

            if record["year_hint"]:

                for year in (
                    record["year_hint"].split(";")
                ):
                    years[year] += 1

        if years:

            print("Year hints:")

            for year, count in sorted(
                years.items()
            ):
                print(
                    f"  {year}: {count}"
                )

    # ---------------------------------------------------------
    # Save unified archive inventory
    # ---------------------------------------------------------

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "archive",
        "member_path",
        "extension",
        "size_bytes",
        "year_hint",
        "sha256",
    ]

    with OUTPUT.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(all_records)

    # ---------------------------------------------------------
    # Duplicate members INSIDE archives
    # ---------------------------------------------------------

    hashes = {}

    for record in all_records:

        digest = record["sha256"]

        hashes.setdefault(
            digest,
            []
        ).append(
            f"{record['archive']} :: "
            f"{record['member_path']}"
        )

    duplicate_groups = [
        paths
        for paths in hashes.values()
        if len(paths) > 1
    ]

    print()
    print("=" * 70)
    print("ARCHIVE SUMMARY")
    print("=" * 70)

    print(
        f"\nTotal archive files indexed: "
        f"{len(all_records)}"
    )

    print(
        f"Unique archive file contents: "
        f"{len(hashes)}"
    )

    print(
        f"Exact duplicate groups inside archives: "
        f"{len(duplicate_groups)}"
    )

    print(
        f"\nInventory saved to: {OUTPUT}"
    )

    if duplicate_groups:

        print(
            "\nFirst 10 duplicate groups:"
        )

        for index, group in enumerate(
            duplicate_groups[:10],
            start=1,
        ):

            print(
                f"\nDuplicate group {index}:"
            )

            for item in group:
                print(
                    f"  {item}"
                )


if __name__ == "__main__":
    main()