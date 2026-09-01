from pathlib import Path
import argparse
import json
import re


DOCUMENT_DIR = Path("data/processed/documents")
OUTPUT_DIR = Path("data/processed/segmentation_v2")
FLAT_OUTPUT = Path("data/processed/question_records_v2.jsonl")


ROUND_RE = re.compile(
    r"^\s*(?:PRE\s*C\s*(?P<contest>\d+)\s+)?"
    r"ROUND\s+(?P<round>[1-5](?:[A-Z])?)"
    r"(?:\s*:\s*(?P<label>.*))?\s*$",
    re.I,
)

CONTEST_RE = re.compile(
    r"^\s*CONTEST\s+(?P<contest>\d+)(?P<variant>[A-Z])?\s*$",
    re.I,
)

PRE_CONTEST_RE = re.compile(
    r"^\s*PRE\s*C\s*(?P<contest>\d+)\s*$",
    re.I,
)

SUBJECT_RE = re.compile(
    r"^\s*(BIOLOGY|CHEMISTRY|PHYSICS|MATHEMATICS|MATHS)"
    r"(?:\s+\d+)?\s*$",
    re.I,
)

NUMBER_RE = re.compile(
    r"^\s*(?P<number>\d+)[\.\)]?\s+(?P<text>.+)$"
)

LETTER_RE = re.compile(
    r"^\s*(?P<number>[a-z])[\.\)]\s*(?P<text>.+)$",
    re.I,
)

ANSWER_RE = re.compile(
    r"^\s*(?:ANSWER|ANS|A)\s*[:=\-\.]?\s*(?P<answer>.*)$",
    re.I,
)

SOLUTION_RE = re.compile(
    r"^\s*SOLUTION\s*[:=\-\.]?\s*(?P<solution>.*)$",
    re.I,
)


SPECIAL_LABELS = {
    "speed race": "speed_race",
    "riddle": "riddle",
    "riddles": "riddle",
    "true or false": "true_false",
    "problem of the day": "problem_of_day",
}


def clean(text):
    if text is None:
        return ""

    text = str(text)

    replacements = {
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

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def infer_year(source):
    matches = re.findall(r"\b(?:19|20)\d{2}\b", source)

    if not matches:
        return None

    return int(matches[0])


def infer_subject(source):
    text = source.lower()

    if "chemistry" in text:
        return "chemistry"

    if "physics" in text:
        return "physics"

    if "biology" in text:
        return "biology"

    if "mathematics" in text or "maths" in text or "math" in text:
        return "mathematics"

    return None


def detect_subject(text):
    match = SUBJECT_RE.match(clean(text))

    if not match:
        return None

    value = match.group(1).lower()

    if value == "maths":
        return "mathematics"

    return value


def detect_round(text):
    match = ROUND_RE.match(clean(text))

    if not match:
        return None

    label = match.group("label")

    section_type = None

    if label:
        lower = label.lower()
        for key, value in SPECIAL_LABELS.items():
            if key in lower:
                section_type = value
                break

    contest = match.group("contest")

    return {
        "contest": int(contest) if contest else None,
        "round": match.group("round").upper(),
        "label": clean(label) if label else None,
        "section_type": section_type,
    }


def detect_contest(text):
    text = clean(text)

    match = CONTEST_RE.match(text)

    if match:
        return {
            "contest": int(match.group("contest")),
            "variant": (
                match.group("variant").upper()
                if match.group("variant")
                else None
            ),
        }

    match = PRE_CONTEST_RE.match(text)

    if match:
        return {
            "contest": int(match.group("contest")),
            "variant": None,
        }

    return None


def detect_item(text):
    text = clean(text)

    match = NUMBER_RE.match(text)

    if match:
        return {
            "number": int(match.group("number")),
            "text": clean(match.group("text")),
        }

    match = LETTER_RE.match(text)

    if match:
        return {
            "number": match.group("number").lower(),
            "text": clean(match.group("text")),
        }

    return None


def detect_answer(text):
    match = ANSWER_RE.match(clean(text))

    if not match:
        return None

    return clean(match.group("answer"))


def detect_solution(text):
    match = SOLUTION_RE.match(clean(text))

    if not match:
        return None

    return clean(match.group("solution"))


def special_type_from_round(label):
    if not label:
        return None

    lower = label.lower()

    for key, value in SPECIAL_LABELS.items():
        if key in lower:
            return value

    return None


def looks_like_question(text):
    text = clean(text)

    if not text:
        return False

    if text.endswith("?"):
        return True

    starters = (
        "what ",
        "which ",
        "who ",
        "where ",
        "when ",
        "why ",
        "how ",
        "find ",
        "calculate ",
        "determine ",
        "state ",
        "give ",
        "name ",
        "define ",
        "explain ",
        "identify ",
        "solve ",
        "evaluate ",
        "describe ",
        "arrange ",
        "mention ",
        "distinguish ",
        "select ",
        "choose ",
        "factorize ",
        "factorise ",
        "simplify ",
        "differentiate ",
        "prove ",
        "show ",
    )

    return text.lower().startswith(starters)


def load_document(document_id):
    path = DOCUMENT_DIR / f"{document_id}.json"

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_lines(document):
    lines = []

    for block_index, block in enumerate(
        document.get("blocks", []),
        start=1,
    ):
        if block.get("type") != "paragraph":
            continue

        text = clean(block.get("text", ""))

        if not text:
            continue

        lines.append(
            {
                "block": block_index,
                "text": text,
                "images": block.get("images", []),
            }
        )

    return lines


def make_group(context, start_block):
    return {
        "group_type": context["section_type"] or "standard",
        "metadata": {
            "year": context["year"],
            "contest": context["contest"],
            "round": context["round"],
            "subject": context["subject"],
        },
        "prompt": None,
        "items": [],
        "standalone": [],
        "source": {
            "start_block": start_block,
            "end_block": None,
        },
    }


def make_item(number, text, block):
    return {
        "number": number,
        "question": clean(text),
        "answer": None,
        "solution": None,
        "images": [],
        "source": {
            "start_block": block,
            "end_block": None,
        },
    }


def segment(document):
    source = document.get("source", {}).get("canonical_path", "")

    context = {
        "year": infer_year(source),
        "contest": None,
        "round": None,
        "subject": infer_subject(source),
        "section_type": None,
    }

    groups = []
    current = None
    current_item = None

    lines = get_lines(document)

    def close_item(block):
        nonlocal current_item

        if current_item is None:
            return

        current_item["source"]["end_block"] = block

        if current is not None:
            current["items"].append(current_item)

        current_item = None

    def close_group(block):
        nonlocal current

        if current is None:
            return

        close_item(block)

        current["source"]["end_block"] = block

        if current["items"] or current["standalone"] or current["prompt"]:
            groups.append(current)

        current = None

    for line in lines:
        block = line["block"]
        text = line["text"]

        # -------------------------------
        # ROUND HEADER
        # -------------------------------

        round_info = detect_round(text)

        if round_info:
            close_group(block - 1)

            if round_info["contest"] is not None:
                context["contest"] = round_info["contest"]

            context["round"] = round_info["round"]

            if round_info["section_type"]:
                context["section_type"] = round_info["section_type"]
            else:
                context["section_type"] = None

            continue

        # -------------------------------
        # CONTEST HEADER
        # -------------------------------

        contest_info = detect_contest(text)

        if contest_info:
            close_group(block - 1)

            context["contest"] = contest_info["contest"]

            continue

        # -------------------------------
        # SUBJECT HEADER
        # -------------------------------

        subject = detect_subject(text)

        if subject:
            context["subject"] = subject
            continue

        # -------------------------------
        # ANSWER
        # -------------------------------

        answer = detect_answer(text)

        if answer is not None:
            if current_item is not None:
                current_item["answer"] = answer
                continue

            if current and current["standalone"]:
                current["standalone"][-1]["answer"] = answer
                continue

        # -------------------------------
        # SOLUTION
        # -------------------------------

        solution = detect_solution(text)

        if solution is not None:
            if current_item is not None:
                current_item["solution"] = solution
                continue

            if current and current["standalone"]:
                current["standalone"][-1]["solution"] = solution
                continue

        # -------------------------------
        # NUMBERED ITEM
        # -------------------------------

        item = detect_item(text)

        if item:
            if current is None:
                current = make_group(context, block)

            close_item(block - 1)

            current_item = make_item(
                item["number"],
                item["text"],
                block,
            )

            if line["images"]:
                current_item["images"].extend(line["images"])

            continue

        # -------------------------------
        # RIDDLE ENDING
        # -------------------------------

        if (
            current is not None
            and current["group_type"] == "riddle"
            and text.lower().startswith("who am i")
        ):
            if current_item is not None:
                current_item["question"] += " " + text
            elif current["items"]:
                current["items"][-1]["question"] += " " + text
            else:
                current["prompt"] = text

            continue

        # -------------------------------
        # TRUE/FALSE PREMISE
        # -------------------------------

        if (
            current is not None
            and current["group_type"] == "true_false"
            and current_item is None
            and not current["items"]
            and current["prompt"] is None
        ):
            current["prompt"] = text
            continue

        # -------------------------------
        # TEXT INSIDE CURRENT ITEM
        # -------------------------------

        if current_item is not None:
            current_item["question"] = clean(
                current_item["question"] + " " + text
            )

            if line["images"]:
                current_item["images"].extend(line["images"])

            continue

        # -------------------------------
        # QUESTION / PROMPT
        # -------------------------------

        if looks_like_question(text):
            if current is None:
                current = make_group(context, block)

            if (
                current["group_type"] in
                ("riddle", "true_false")
                and current["items"]
            ):
                if current["items"]:
                    current["items"][-1]["question"] = clean(
                        current["items"][-1]["question"]
                        + " "
                        + text
                    )
                continue

            if current["items"] and current["prompt"] is None:
                current["prompt"] = text
                continue

            if not current["standalone"]:
                current["standalone"].append(
                    {
                        "question": text,
                        "answer": None,
                        "solution": None,
                        "source": {
                            "start_block": block,
                            "end_block": None,
                        },
                    }
                )
                continue

            previous = current["standalone"][-1]

            if previous["answer"] is not None:
                current["standalone"].append(
                    {
                        "question": text,
                        "answer": None,
                        "solution": None,
                        "source": {
                            "start_block": block,
                            "end_block": None,
                        },
                    }
                )
            else:
                previous["question"] = clean(
                    previous["question"] + " " + text
                )

            continue

        # -------------------------------
        # OTHER TEXT
        # -------------------------------

        if current is None:
            current = make_group(context, block)
            current["prompt"] = text
            continue

        if current_item is not None:
            current_item["question"] = clean(
                current_item["question"] + " " + text
            )
        elif current["standalone"]:
            current["standalone"][-1]["question"] = clean(
                current["standalone"][-1]["question"]
                + " "
                + text
            )
        elif current["prompt"] is None:
            current["prompt"] = text
        else:
            current["prompt"] = clean(
                current["prompt"] + " " + text
            )

    if lines:
        close_group(lines[-1]["block"])

    return {
        "document_id": document["document_id"],
        "source": document.get("source", {}),
        "groups": groups,
        "statistics": {
            "groups": len(groups),
            "numbered_items": sum(
                len(group["items"])
                for group in groups
            ),
            "standalone_questions": sum(
                len(group["standalone"])
                for group in groups
            ),
        },
    }


def flatten(result):
    records = []

    document_id = result["document_id"]

    for group_index, group in enumerate(
        result["groups"],
        start=1,
    ):
        metadata = group["metadata"]

        group_id = (
            f"{document_id}_g{group_index:04d}"
        )

        for item_index, item in enumerate(
            group["items"],
            start=1,
        ):
            question = item["question"]

            if group["prompt"]:
                question = clean(
                    group["prompt"]
                    + " "
                    + question
                )

            if group["group_type"] == "riddle":
                question = clean(
                    question
                )

            records.append(
                {
                    "question_id": (
                        f"{group_id}_q{item_index:03d}"
                    ),
                    "competition": "NSMQ",
                    "question_type": group["group_type"],
                    "metadata": metadata,
                    "prompt": group["prompt"],
                    "question_text": question,
                    "answer": item["answer"],
                    "solution": item["solution"],
                    "images": item["images"],
                    "source": {
                        "document_id": document_id,
                        "start_block": item["source"][
                            "start_block"
                        ],
                        "end_block": item["source"][
                            "end_block"
                        ],
                    },
                }
            )

        for standalone_index, item in enumerate(
            group["standalone"],
            start=1,
        ):
            records.append(
                {
                    "question_id": (
                        f"{group_id}_s{standalone_index:03d}"
                    ),
                    "competition": "NSMQ",
                    "question_type": group["group_type"],
                    "metadata": metadata,
                    "prompt": group["prompt"],
                    "question_text": clean(
                        item["question"]
                    ),
                    "answer": item["answer"],
                    "solution": item["solution"],
                    "images": [],
                    "source": {
                        "document_id": document_id,
                        "start_block": item["source"][
                            "start_block"
                        ],
                        "end_block": item["source"][
                            "end_block"
                        ],
                    },
                }
            )

    return records


def process_one(document_id):
    document = load_document(document_id)

    result = segment(document)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = (
        OUTPUT_DIR
        / f"{document_id}.json"
    )

    with output.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return result


def process_all():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    total_documents = 0
    total_groups = 0
    total_items = 0
    total_standalone = 0
    total_records = 0

    with FLAT_OUTPUT.open(
        "w",
        encoding="utf-8",
    ) as flat:

        for path in sorted(
            DOCUMENT_DIR.glob("*.json")
        ):
            document_id = path.stem

            try:
                result = process_one(
                    document_id
                )

                records = flatten(result)

                for record in records:
                    flat.write(
                        json.dumps(
                            record,
                            ensure_ascii=False,
                        )
                        + "\n"
                    )

                total_documents += 1
                total_groups += result[
                    "statistics"
                ]["groups"]
                total_items += result[
                    "statistics"
                ]["numbered_items"]
                total_standalone += result[
                    "statistics"
                ]["standalone_questions"]
                total_records += len(records)

            except Exception as error:
                print(
                    f"FAILED {document_id}: {type(error).__name__}: {error}"
                )

    print("=" * 70)
    print("SEGMENTATION V2 CORPUS BUILD")
    print("=" * 70)
    print(f"Documents processed: {total_documents}")
    print(f"Groups:              {total_groups}")
    print(f"Numbered items:      {total_items}")
    print(f"Standalone:          {total_standalone}")
    print(f"Flattened records:    {total_records}")
    print()
    print(f"Group JSON:           {OUTPUT_DIR}")
    print(f"Flat JSONL:           {FLAT_OUTPUT}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--document",
        help="Process one document ID",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Process every extracted document",
    )

    args = parser.parse_args()

    if args.all:
        process_all()
        return

    if args.document:
        result = process_one(
            args.document
        )

        print("=" * 70)
        print("SEGMENTATION V2")
        print("=" * 70)
        print(
            "Source:",
            result["source"].get(
                "canonical_path",
                "",
            ),
        )
        print(
            "Groups:",
            result["statistics"]["groups"],
        )
        print(
            "Numbered items:",
            result["statistics"]["numbered_items"],
        )
        print(
            "Standalone:",
            result["statistics"][
                "standalone_questions"
            ],
        )
        return

    parser.error(
        "Use --document DOCUMENT_ID or --all"
    )


if __name__ == "__main__":
    main()
