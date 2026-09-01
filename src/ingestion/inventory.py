from pathlib import Path
import hashlib
import csv


RAW_ROOT = Path(r"C:\Users\Prince\Downloads\SMQ BIBLES")
OUTPUT = Path("data/raw_inventory.csv")

SUPPORTED_EXTENSIONS = {
    ".docx",
    ".doc",
    ".pdf",
    ".xls",
    ".zip",
}


def calculate_sha256(path, chunk_size=1024 * 1024):
    sha256 = hashlib.sha256()

    with path.open("rb") as file:
        while chunk := file.read(chunk_size):
            sha256.update(chunk)

    return sha256.hexdigest()


def should_include(path):
    """
    Decide whether this file belongs in the corpus inventory.
    """

    # Microsoft Office temporary/lock files.
    if path.name.startswith("~$"):
        return False

    # Only inventory formats we currently plan to process.
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return False

    return True


def build_inventory():
    records = []

    all_files = list(RAW_ROOT.rglob("*"))

    for path in all_files:

        if not path.is_file():
            continue

        if not should_include(path):
            continue

        print(f"Processing: {path}")

        records.append({
            "filename": path.name,
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
            "relative_path": str(path.relative_to(RAW_ROOT)),
            "sha256": calculate_sha256(path),
        })

    return records


def save_inventory(records):
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "filename",
        "extension",
        "size_bytes",
        "relative_path",
        "sha256",
    ]

    with OUTPUT.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


if __name__ == "__main__":
    records = build_inventory()
    save_inventory(records)

    print()
    print("=" * 60)
    print("INVENTORY COMPLETE")
    print("=" * 60)
    print(f"Files indexed: {len(records)}")
    print(f"Output: {OUTPUT}")