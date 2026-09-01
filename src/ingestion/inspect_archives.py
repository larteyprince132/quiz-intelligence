from pathlib import Path
from zipfile import ZipFile


RAW_ROOT = Path(
    r"C:\Users\Prince\Downloads\SMQ BIBLES"
)


def inspect_zip(path):
    print()
    print("=" * 70)
    print(f"ZIP: {path.name}")
    print(f"SIZE: {path.stat().st_size:,} bytes")
    print("=" * 70)

    try:
        with ZipFile(path) as archive:

            members = archive.infolist()

            print(f"Files inside archive: {len(members)}")

            print("\nFirst 50 members:")

            for member in members[:50]:
                print(
                    f"{member.file_size:>10,} bytes  "
                    f"{member.filename}"
                )

    except Exception as error:
        print(f"ERROR: {error}")


def main():
    zip_files = list(RAW_ROOT.rglob("*.zip"))

    print(f"ZIP archives found: {len(zip_files)}")

    for path in zip_files:
        inspect_zip(path)


if __name__ == "__main__":
    main()