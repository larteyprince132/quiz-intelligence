from pathlib import Path
import json
import re


DOCUMENT_DIR = Path("data/processed/documents")

OUTPUT_DIR = Path("data/processed/question_segments")

OUTPUT_FILE = Path(
    "data/processed/question_segments.jsonl"
)


ROUND_RE = re.compile(
    r"^\s*round\s*([1-5])(?:\s*[:\-]?\s*(.*))?$",
    re.IGNORECASE,
)

CONTEST_RE = re.compile(
    r"^\s*contest\s+(\d+)\s*([a-z])?\s*$",
    re.IGNORECASE,
)

SUBJECT_RE = re.compile(
    r"^\s*(biology|chemistry|mathematics|maths|physics)"
    r"\s*(\d+)?\s*$",
    re.IGNORECASE,
)

ANSWER_RE = re.compile(
    r"^\s*(answer|ans|a)\s*[:\.\-]?\s*(.*)$",
    re.IGNORECASE,
)

QUESTION_RE = re.compile(
    r"^\s*(q\.|question\s*[:.]|\d+[\).\:]?)\s+",
    re.IGNORECASE,
)

PREAMBLE_RE = re.compile(
    r"^\s*preamble\s*[:=\-]?\s*(.*)$",
    re.IGNORECASE,
)

SOLUTION_RE = re.compile(
    r"^\s*solution\s*[:=\-]?\s*(.*)$",
    re.IGNORECASE,
)

SPECIAL_SECTION_RE = re.compile(
    r"^\s*(speed\s*race|true\s+or\s+false|"
    r"riddles?|problem\s+of\s+the\s+day)\b",
    re.IGNORECASE,
)


def clean_text(text):
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def looks_like_question(text):
    text = clean_text(text)

    if not text:
        return False

    if QUESTION_RE.match(text):
        return True

    if text.endswith("?"):
        return True

    question_starters = (
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
    )

    lower = text.lower()

    return lower.startswith(question_starters)


def strip_question_marker(text):
    text = clean_text(text)

    text = re.sub(
        r"^\s*q\.\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^\s*question\s*[:.]?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return text.strip()


def extract_answer(text):
    match = ANSWER_RE.match(text)

    if not match:
        return None

    answer = match.group(2).strip()

    return {
        "raw": text,
        "answer": answer,
    }


def classify_section(text):
    match = SPECIAL_SECTION_RE.match(text)

    if not match:
        return None

    label = match.group(1).lower()

    if "speed" in label:
        return "speed_race"

    if "true" in label:
        return "true_false"

    if "riddle" in label:
        return "riddle"

    if "problem" in label:
        return "problem_of_day"

    return None


def read_document(path):
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def blocks_to_lines(document):
    lines = []

    for index, block in enumerate(
        document.get("blocks", []),
        start=1,
    ):

        if block.get("type") != "paragraph":
            continue

        text = clean_text(
            block.get("text", "")
        )

        if not text:
            continue

        lines.append({
            "block_index": index,
            "text": text,
            "images": block.get(
                "images",
                [],
            ),
        })

    return lines


def make_question(
    competition="NSMQ",
    year=None,
    contest=None,
    contest_label=None,
    round_number=None,
    round_label=None,
    subject=None,
    section_type=None,
    preamble=None,
    start_block=None,
):
    return {
        "question_id": None,

        "competition": competition,

        "metadata": {
            "year": year,
            "contest": contest,
            "contest_label": contest_label,
            "round": round_number,
            "round_label": round_label,
            "subject": subject,
            "section_type": section_type,
        },

        "preamble": preamble,

        "question_text": "",

        "answer": None,

        "solution": None,

        "images": [],

        "source": {
            "document_id": None,
            "start_block": start_block,
            "end_block": None,
        },

        "parser_status": "candidate",
    }


def append_text(question, text):
    text = clean_text(text)

    if not text:
        return

    if question["question_text"]:
        question["question_text"] += " " + text
    else:
        question["question_text"] = text


def finalize_question(question):
    if question is None:
        return None

    question["question_text"] = clean_text(
        question["question_text"]
    )

    if question["preamble"]:
        question["preamble"] = clean_text(
            question["preamble"]
        )

    return question


def segment_document(document):
    lines = blocks_to_lines(document)

    results = []

    current_question = None

    current_round = None
    current_round_label = None

    current_contest = None
    current_contest_label = None

    current_subject = None
    current_section_type = None

    current_preamble = None

    in_solution = False

    for line in lines:

        text = line["text"]
        lower = text.lower()

        # --------------------------------------------------
        # ROUND
        # --------------------------------------------------

        round_match = ROUND_RE.match(text)

        if round_match:

            if current_question:
                current_question[
                    "source"
                ]["end_block"] = (
                    line["block_index"] - 1
                )

                results.append(
                    finalize_question(
                        current_question
                    )
                )

                current_question = None

            current_round = int(
                round_match.group(1)
            )

            current_round_label = (
                round_match.group(2)
            )

            current_section_type = (
                classify_section(text)
            )

            current_preamble = None
            in_solution = False

            continue

        # --------------------------------------------------
        # CONTEST
        # --------------------------------------------------

        contest_match = CONTEST_RE.match(text)

        if contest_match:

            if current_question:

                current_question[
                    "source"
                ]["end_block"] = (
                    line["block_index"] - 1
                )

                results.append(
                    finalize_question(
                        current_question
                    )
                )

                current_question = None

            current_contest = int(
                contest_match.group(1)
            )

            suffix = contest_match.group(2)

            current_contest_label = (
                text
            )

            current_section_type = (
                classify_section(text)
                or current_section_type
            )

            current_preamble = None
            in_solution = False

            continue

        # --------------------------------------------------
        # SPECIAL SECTION
        # --------------------------------------------------

        special = classify_section(text)

        if special:

            current_section_type = special

            if current_question:
                current_question[
                    "source"
                ]["end_block"] = (
                    line["block_index"] - 1
                )

                results.append(
                    finalize_question(
                        current_question
                    )
                )

                current_question = None

            continue

        # --------------------------------------------------
        # SUBJECT
        # --------------------------------------------------

        subject_match = SUBJECT_RE.match(text)

        if subject_match:

            current_subject = (
                subject_match.group(1)
                .lower()
            )

            if current_subject == "maths":
                current_subject = "mathematics"

            continue

        # --------------------------------------------------
        # PREAMBLE
        # --------------------------------------------------

        preamble_match = PREAMBLE_RE.match(text)

        if preamble_match:

            current_preamble = (
                preamble_match.group(1)
                .strip()
                or None
            )

            continue

        # --------------------------------------------------
        # SOLUTION
        # --------------------------------------------------

        solution_match = SOLUTION_RE.match(text)

        if solution_match:

            in_solution = True

            if current_question:

                value = (
                    solution_match.group(1)
                    .strip()
                )

                if value:
                    current_question[
                        "solution"
                    ] = value

            continue

        # --------------------------------------------------
        # ANSWER
        # --------------------------------------------------

        answer = extract_answer(text)

        if answer:

            if current_question:

                current_question[
                    "answer"
                ] = answer["answer"]

                in_solution = False

            continue

        # --------------------------------------------------
        # QUESTION DETECTION
        # --------------------------------------------------

        if looks_like_question(text):

            if current_question:

                current_question[
                    "source"
                ]["end_block"] = (
                    line["block_index"] - 1
                )

                results.append(
                    finalize_question(
                        current_question
                    )
                )

            current_question = make_question(
                contest=current_contest,
                contest_label=current_contest_label,
                round_number=current_round,
                round_label=current_round_label,
                subject=current_subject,
                section_type=current_section_type,
                preamble=current_preamble,
                start_block=line[
                    "block_index"
                ],
            )

            current_question[
                "question_text"
            ] = strip_question_marker(
                text
            )

            current_question[
                "images"
            ].extend(
                line["images"]
            )

            in_solution = False

            continue

        # --------------------------------------------------
        # CONTINUE CURRENT QUESTION
        # --------------------------------------------------

        if current_question:

            if in_solution:

                if current_question[
                    "solution"
                ]:

                    current_question[
                        "solution"
                    ] += " " + text

                else:

                    current_question[
                        "solution"
                    ] = text

            else:

                append_text(
                    current_question,
                    text,
                )

            current_question[
                "images"
            ].extend(
                line["images"]
            )

    # ------------------------------------------------------
    # FINAL QUESTION
    # ------------------------------------------------------

    if current_question:

        current_question[
            "source"
        ]["end_block"] = (
            lines[-1]["block_index"]
            if lines
            else None
        )

        results.append(
            finalize_question(
                current_question
            )
        )

    # Attach document provenance and IDs.
    document_id = document.get(
        "document_id"
    )

    for index, question in enumerate(
        results,
        start=1,
    ):

        question[
            "question_id"
        ] = (
            f"{document_id}_q{index:04d}"
        )

        question[
            "source"
        ]["document_id"] = document_id

    return results


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    document_files = sorted(
        DOCUMENT_DIR.glob("*.json")
    )

    print("=" * 70)
    print("QUESTION SEGMENTATION")
    print("=" * 70)

    print(
        f"\nDocuments found: "
        f"{len(document_files)}"
    )

    all_questions = []

    successful = 0
    failed = 0

    for index, path in enumerate(
        document_files,
        start=1,
    ):

        try:

            document = read_document(
                path
            )

            questions = segment_document(
                document
            )

            all_questions.extend(
                questions
            )

            successful += 1

        except Exception as error:

            failed += 1

            print(
                f"\nERROR: {path.name}"
            )

            print(
                f"{type(error).__name__}: "
                f"{error}"
            )

        if (
            index == 1
            or index % 100 == 0
            or index == len(document_files)
        ):

            print(
                f"[{index}/{len(document_files)}] "
                f"Documents={successful} "
                f"Errors={failed} "
                f"Candidates={len(all_questions)}"
            )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        for question in all_questions:

            file.write(
                json.dumps(
                    question,
                    ensure_ascii=False,
                )
                + "\n"
            )

    print()
    print("=" * 70)
    print("SEGMENTATION COMPLETE")
    print("=" * 70)

    print(
        f"\nDocuments processed: "
        f"{successful}"
    )

    print(
        f"Document errors: "
        f"{failed}"
    )

    print(
        f"Question candidates: "
        f"{len(all_questions)}"
    )

    print(
        f"\nOutput: "
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()