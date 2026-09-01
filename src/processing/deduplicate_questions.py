from pathlib import Path
import json
import hashlib
import re
import unicodedata
from collections import Counter, defaultdict


INPUT = Path(
    "data/processed/question_records_v2.jsonl"
)

OUTPUT = Path(
    "data/processed/question_records_v3.jsonl"
)

DUPLICATES_OUTPUT = Path(
    "data/processed/question_duplicate_groups.json"
)

CONFLICTS_OUTPUT = Path(
    "data/processed/question_answer_conflicts.json"
)


MOJIBAKE = {
    "â€“": "–",
    "â€”": "—",
    "â€˜": "‘",
    "â€™": "’",
    "â€œ": "“",
    "â€\x9d": "”",
    "Â±": "±",
    "Â½": "½",
    "Â¼": "¼",
    "Â¾": "¾",
    "âˆš": "√",
    "Ï€": "π",
    "Î¸": "θ",
    "Â°": "°",
}


def normalize_text(text):
    if text is None:
        return ""

    text = str(text)

    for bad, good in MOJIBAKE.items():
        text = text.replace(bad, good)

    text = unicodedata.normalize(
        "NFKC",
        text,
    )

    text = text.lower()

    # Normalize common unicode variants.
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    text = text.replace("−", "-")

    # Collapse whitespace.
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    # Remove whitespace around punctuation/operators.
    text = re.sub(
        r"\s*([,.;:!?()[\]{}=+\-*/<>])\s*",
        r"\1",
        text,
    )

    return text.strip()


def fingerprint(record):
    question_type = (
        record.get("question_type")
        or "standard"
    )

    question = normalize_text(
        record.get("question_text")
        or ""
    )

    material = (
        question_type
        + "\n"
        + question
    )

    return hashlib.sha256(
        material.encode("utf-8")
    ).hexdigest()


def clean_answer(answer):
    if not answer:
        return ""

    return normalize_text(answer)


def load_records():
    records = []

    with INPUT.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            line = line.strip()

            if line:
                records.append(
                    json.loads(line)
                )

    return records


def choose_canonical(group):
    """
    Pick the most useful representative.

    Preference:
    1. Has an answer
    2. Has a solution
    3. Has longer question text
    """

    def score(record):
        return (
            bool(record.get("answer")),
            bool(record.get("solution")),
            len(
                record.get(
                    "question_text",
                    "",
                )
            ),
        )

    return max(
        group,
        key=score,
    )


def build_canonical(group):
    canonical = choose_canonical(
        group
    ).copy()

    answers = Counter(
        clean_answer(
            r.get("answer")
        )
        for r in group
        if r.get("answer")
    )

    solutions = [
        r.get("solution")
        for r in group
        if r.get("solution")
    ]

    source_records = []

    for record in group:
        source_records.append(
            {
                "question_id": record.get(
                    "question_id"
                ),
                "document_id": record.get(
                    "source",
                    {},
                ).get(
                    "document_id"
                ),
                "start_block": record.get(
                    "source",
                    {},
                ).get(
                    "start_block"
                ),
                "end_block": record.get(
                    "source",
                    {},
                ).get(
                    "end_block"
                ),
                "metadata": record.get(
                    "metadata",
                    {},
                ),
            }
        )

    metadata_variants = []

    seen_metadata = set()

    for record in group:
        metadata = record.get(
            "metadata",
            {},
        )

        key = json.dumps(
            metadata,
            sort_keys=True,
        )

        if key not in seen_metadata:
            seen_metadata.add(key)
            metadata_variants.append(
                metadata
            )

    canonical[
        "normalized_question"
    ] = normalize_text(
        canonical.get(
            "question_text"
        )
    )

    canonical[
        "question_fingerprint"
    ] = fingerprint(
        canonical
    )

    canonical[
        "duplicate_count"
    ] = len(group)

    canonical[
        "source_count"
    ] = len(source_records)

    canonical[
        "sources"
    ] = source_records

    canonical[
        "metadata_variants"
    ] = metadata_variants

    canonical[
        "answer_variants"
    ] = [
        {
            "answer": answer,
            "count": count,
        }
        for answer, count
        in answers.most_common()
        if answer
    ]

    canonical[
        "solution_count"
    ] = len(solutions)

    return canonical


def main():
    records = load_records()

    print("=" * 70)
    print("QUESTION-LEVEL DEDUPLICATION")
    print("=" * 70)

    print(
        f"Input records: {len(records)}"
    )

    groups = defaultdict(list)

    for record in records:
        groups[
            fingerprint(record)
        ].append(record)

    unique_count = len(groups)

    duplicate_groups = [
        group
        for group in groups.values()
        if len(group) > 1
    ]

    duplicate_records = sum(
        len(group) - 1
        for group in duplicate_groups
    )

    print(
        f"Unique question fingerprints: {unique_count}"
    )

    print(
        f"Duplicate groups: {len(duplicate_groups)}"
    )

    print(
        f"Duplicate records removed: {duplicate_records}"
    )

    canonical_records = []

    duplicate_report = []

    conflicts = []

    for fingerprint_value, group in groups.items():

        canonical = build_canonical(
            group
        )

        canonical_records.append(
            canonical
        )

        if len(group) > 1:
            duplicate_report.append(
                {
                    "question_fingerprint": (
                        fingerprint_value
                    ),
                    "count": len(group),
                    "canonical_question": (
                        canonical.get(
                            "question_text"
                        )
                    ),
                    "question_type": (
                        canonical.get(
                            "question_type"
                        )
                    ),
                    "sources": canonical[
                        "sources"
                    ],
                }
            )

        answers = set(
            clean_answer(
                r.get("answer")
            )
            for r in group
            if r.get("answer")
        )

        if len(answers) > 1:
            conflicts.append(
                {
                    "question_fingerprint": (
                        fingerprint_value
                    ),
                    "question": (
                        canonical.get(
                            "question_text"
                        )
                    ),
                    "answer_variants": (
                        canonical[
                            "answer_variants"
                        ]
                    ),
                    "sources": canonical[
                        "sources"
                    ],
                }
            )

    # Stable ordering.
    canonical_records.sort(
        key=lambda r: (
            r.get(
                "metadata",
                {},
            ).get("year")
            or 9999,
            r.get("question_type")
            or "",
            r.get("question_text")
            or "",
        )
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT.open(
        "w",
        encoding="utf-8",
    ) as file:

        for record in canonical_records:
            file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    with DUPLICATES_OUTPUT.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            duplicate_report,
            file,
            ensure_ascii=False,
            indent=2,
        )

    with CONFLICTS_OUTPUT.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            conflicts,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(
        f"Canonical records: {len(canonical_records)}"
    )

    print(
        f"Answer conflicts: {len(conflicts)}"
    )

    print()
    print("OUTPUTS")
    print("----------------------------------------")
    print(
        f"Canonical corpus: {OUTPUT}"
    )
    print(
        f"Duplicate report:  {DUPLICATES_OUTPUT}"
    )
    print(
        f"Conflict report:   {CONFLICTS_OUTPUT}"
    )


if __name__ == "__main__":
    main()
