import time
from google.genai.errors import ServerError
from pathlib import Path
from collections import Counter, defaultdict
import argparse
import json
import math
import os
import re
import sys

from google import genai
from google.genai import types


CORPUS = Path(
    "data/processed/question_records_v3.jsonl"
)

OUTPUT_DIR = Path(
    "data/processed/ai_outputs"
)

MODEL = "gemini-3.7-flash"

FALLBACK_MODELS = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
]


# ============================================================
# TOPIC VOCABULARY
# ============================================================

TOPICS = {

    "mathematics": {
        "algebra": [
            "equation", "inequality", "factor", "factorize",
            "factorise", "polynomial", "quadratic", "root",
            "expression", "simultaneous"
        ],

        "calculus": [
            "differentiate", "derivative", "integrate",
            "integration", "inflexion", "limit", "tangent",
            "normal", "gradient", "stationary"
        ],

        "trigonometry": [
            "sin", "cos", "tan", "sine", "cosine",
            "tangent", "angle"
        ],

        "logarithms": [
            "log", "logarithm", "ln", "napier"
        ],

        "indices": [
            "index", "indices", "exponent", "power",
            "exponential"
        ],

        "sequences_series": [
            "sequence", "series", "arithmetic progression",
            "geometric progression", "ap", "gp", "common difference"
        ],

        "binomial": [
            "binomial", "expansion", "coefficient"
        ],

        "geometry": [
            "triangle", "quadrilateral", "polygon",
            "circle", "angle", "symmetry", "area",
            "perimeter", "volume"
        ],

        "coordinate_geometry": [
            "coordinate", "slope", "gradient", "line",
            "cartesian", "midpoint"
        ],

        "probability_statistics": [
            "probability", "mean", "median", "mode",
            "variance", "standard deviation", "statistics"
        ],

        "number_theory": [
            "prime", "divisible", "remainder", "integer",
            "factor", "multiple", "digit"
        ],
    },

    "physics": {
        "mechanics": [
            "force", "motion", "velocity", "acceleration",
            "displacement", "momentum", "energy", "work",
            "torque", "kinematics", "dynamics"
        ],

        "fluids": [
            "fluid", "pressure", "buoyancy", "density",
            "hydrostatic", "upthrust", "viscosity"
        ],

        "waves": [
            "wave", "frequency", "wavelength", "interference",
            "diffraction", "sound", "harmonic", "resonance"
        ],

        "thermal_physics": [
            "temperature", "heat", "thermal", "thermodynamic",
            "entropy", "specific heat", "expansion"
        ],

        "electricity": [
            "current", "voltage", "resistance", "circuit",
            "ohm", "charge", "electrical"
        ],

        "electrostatics": [
            "electrostatic", "electric field", "electric potential",
            "coulomb", "charge"
        ],

        "magnetism": [
            "magnetic", "magnetism", "magnetic field",
            "flux", "induction", "faraday", "lorentz"
        ],

        "optics": [
            "lens", "mirror", "reflection", "refraction",
            "optics", "image", "focal"
        ],

        "modern_physics": [
            "photoelectric", "photon", "quantum",
            "relativity", "atomic", "spectral"
        ],

        "nuclear_physics": [
            "nuclear", "radioactive", "fission",
            "fusion", "half-life", "decay"
        ],

        "semiconductors": [
            "semiconductor", "diode", "transistor",
            "pn junction", "bipolar"
        ],
    },

    "chemistry": {
        "atomic_structure": [
            "atom", "electron", "proton", "neutron",
            "isotope", "orbital", "quantum"
        ],

        "periodicity": [
            "periodic", "periodicity", "group",
            "period", "ionization", "electronegativity"
        ],

        "chemical_bonding": [
            "bond", "ionic", "covalent", "metallic",
            "bonding", "dipole", "polarity"
        ],

        "stoichiometry": [
            "mole", "molar", "stoichiometry", "mass",
            "concentration", "limiting reagent"
        ],

        "gases": [
            "gas", "pressure", "volume", "ideal gas",
            "boyle", "charles", "partial pressure"
        ],

        "energetics": [
            "enthalpy", "heat", "energy", "exothermic",
            "endothermic", "hess"
        ],

        "equilibrium": [
            "equilibrium", "le chatelier", "equilibrium constant"
        ],

        "kinetics": [
            "rate", "reaction rate", "kinetics",
            "activation energy", "catalyst"
        ],

        "acids_bases": [
            "acid", "base", "ph", "neutralization",
            "buffer", "indicator"
        ],

        "redox_electrochemistry": [
            "oxidation", "reduction", "redox",
            "electrolysis", "electrode", "cell"
        ],

        "organic": [
            "organic", "hydrocarbon", "alkane", "alkene",
            "alkyne", "alcohol", "ester", "ketone",
            "aldehyde", "amine", "isomer"
        ],

        "qualitative_analysis": [
            "test", "precipitate", "qualitative",
            "reagent", "ion", "identify"
        ],
    },

    "biology": {
        "cell_biology": [
            "cell", "organelle", "membrane", "mitosis",
            "cytoplasm", "nucleus"
        ],

        "genetics": [
            "gene", "genetic", "chromosome", "allele",
            "inheritance", "dna", "rna", "mutation"
        ],

        "ecology": [
            "ecosystem", "ecology", "food chain",
            "population", "community", "habitat",
            "succession", "eutrophication"
        ],

        "plant_biology": [
            "plant", "photosynthesis", "xylem", "phloem",
            "root", "stem", "leaf", "flower"
        ],

        "human_physiology": [
            "human", "blood", "heart", "kidney",
            "respiration", "hormone", "nervous"
        ],

        "reproduction": [
            "reproduction", "fertilization", "gamete",
            "embryo", "ovary", "testis"
        ],

        "microbiology": [
            "bacteria", "virus", "fungi", "protozoa",
            "microorganism", "pathogen"
        ],

        "classification": [
            "phylum", "classification", "taxonomy",
            "species", "genus", "kingdom"
        ],

        "evolution": [
            "evolution", "natural selection",
            "adaptation", "darwin"
        ],

        "biochemistry": [
            "protein", "enzyme", "lipid", "carbohydrate",
            "amino acid", "metabolism"
        ],
    },
}


# ============================================================
# TEXT UTILITIES
# ============================================================

def tokenize(text):
    if not text:
        return []

    text = text.lower()

    return re.findall(
        r"[a-z0-9]+(?:['’\-][a-z0-9]+)*",
        text,
    )


def clean(text):
    if text is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(text),
    ).strip()


# ============================================================
# CORPUS
# ============================================================

class Corpus:

    def __init__(self, path=CORPUS):
        self.path = path
        self.records = []

        # term -> {record_index: term_frequency}
        self.index = defaultdict(dict)

        self.doc_lengths = []
        self.document_frequency = Counter()

        self.avgdl = 0.0

        self._load()
        self._build_index()

    def _load(self):
        with self.path.open(
            "r",
            encoding="utf-8",
        ) as file:

            for line in file:

                if not line.strip():
                    continue

                record = json.loads(line)

                question = clean(
                    record.get(
                        "question_text"
                    )
                )

                if len(question) < 10:
                    continue

                self.records.append(record)

    def _build_index(self):

        total_length = 0

        for idx, record in enumerate(
            self.records
        ):

            text = clean(
                record.get(
                    "question_text"
                )
            )

            tokens = tokenize(text)

            total_length += len(tokens)

            self.doc_lengths.append(
                len(tokens)
            )

            counts = Counter(tokens)

            for term, frequency in counts.items():

                self.index[
                    term
                ][idx] = frequency

            for term in counts:
                self.document_frequency[
                    term
                ] += 1

        if self.records:
            self.avgdl = (
                total_length
                / len(self.records)
            )

    # --------------------------------------------------------
    # METADATA
    # --------------------------------------------------------

    def subject_of(self, record):

        subject = (
            record.get(
                "metadata",
                {},
            ).get("subject")
        )

        if subject:
            return subject.lower()

        text = clean(
            record.get(
                "question_text"
            )
        ).lower()

        for subject in TOPICS:

            for topic_words in TOPICS[
                subject
            ].values():

                if any(
                    word in text
                    for word in topic_words
                ):
                    return subject

        return None

    def topic_scores(self, record):

        subject = self.subject_of(
            record
        )

        if not subject:
            return {}

        text = clean(
            record.get(
                "question_text"
            )
        ).lower()

        scores = {}

        for topic, words in TOPICS[
            subject
        ].items():

            score = 0

            for word in words:

                if word in text:
                    score += 1

            if score:
                scores[topic] = score

        return scores

    def primary_topic(self, record):

        scores = self.topic_scores(
            record
        )

        if not scores:
            return "unknown"

        return max(
            scores,
            key=scores.get,
        )

    # --------------------------------------------------------
    # BM25 RETRIEVAL
    # --------------------------------------------------------

    def retrieve(
        self,
        query,
        k=8,
        subject=None,
        question_type=None,
    ):

        query_tokens = tokenize(
            query
        )

        if not query_tokens:
            return []

        N = len(self.records)

        k1 = 1.5
        b = 0.75

        scores = defaultdict(float)

        for term in set(
            query_tokens
        ):

            postings = self.index.get(
                term
            )

            if not postings:
                continue

            df = self.document_frequency[
                term
            ]

            idf = math.log(
                1
                + (
                    N - df + 0.5
                )
                / (
                    df + 0.5
                )
            )

            for idx, tf in postings.items():

                record = self.records[
                    idx
                ]

                if subject:
                    actual_subject = (
                        self.subject_of(
                            record
                        )
                    )

                    if actual_subject != subject:
                        continue

                if question_type:
                    actual_type = (
                        record.get(
                            "question_type"
                        )
                        or "standard"
                    )

                    if actual_type != question_type:
                        continue

                dl = self.doc_lengths[
                    idx
                ]

                denominator = (
                    tf
                    + k1
                    * (
                        1
                        - b
                        + b
                        * dl
                        / max(
                            self.avgdl,
                            1,
                        )
                    )
                )

                contribution = (
                    idf
                    * (
                        tf
                        * (
                            k1 + 1
                        )
                        / denominator
                    )
                )

                scores[idx] += (
                    contribution
                )

        ranked = sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        results = []

        for idx, score in ranked[:k]:

            record = self.records[
                idx
            ].copy()

            record[
                "_retrieval_score"
            ] = round(
                score,
                4,
            )

            record[
                "_subject"
            ] = self.subject_of(
                record
            )

            record[
                "_topic"
            ] = self.primary_topic(
                record
            )

            results.append(
                record
            )

        return results

    # --------------------------------------------------------
    # PATTERN ANALYSIS
    # --------------------------------------------------------

    def pattern_profile(
        self,
        subject=None,
        question_type=None,
    ):

        topic_counts = Counter()
        topic_years = defaultdict(
            set
        )

        subject_records = []

        for record in self.records:

            actual_subject = (
                self.subject_of(
                    record
                )
            )

            if subject and (
                actual_subject != subject
            ):
                continue

            actual_type = (
                record.get(
                    "question_type"
                )
                or "standard"
            )

            if question_type and (
                actual_type
                != question_type
            ):
                continue

            subject_records.append(
                record
            )

            topic = self.primary_topic(
                record
            )

            if topic == "unknown":
                continue

            topic_counts[
                topic
            ] += 1

            year = (
                record.get(
                    "metadata",
                    {},
                ).get("year")
            )

            if year:

                topic_years[
                    topic
                ].add(
                    int(year)
                )

        if not subject_records:
            return []

        years = []

        for record in subject_records:

            year = (
                record.get(
                    "metadata",
                    {},
                ).get("year")
            )

            if year:
                years.append(
                    int(year)
                )

        latest_year = (
            max(years)
            if years
            else None
        )

        results = []

        for topic, frequency in (
            topic_counts.items()
        ):

            years_seen = sorted(
                topic_years[
                    topic
                ]
            )

            recurrence = len(
                years_seen
            )

            recent_count = 0

            if latest_year:

                recent_window = {
                    year
                    for year in years_seen
                    if year
                    >= latest_year - 3
                }

                recent_count = len(
                    recent_window
                )

            frequency_score = math.log1p(
                frequency
            )

            recurrence_score = (
                recurrence
            )

            recent_score = (
                recent_count * 1.5
            )

            total_score = (
                frequency_score
                + recurrence_score
                + recent_score
            )

            results.append(
                {
                    "topic": topic,
                    "frequency": frequency,
                    "years_seen": years_seen,
                    "recurrence": recurrence,
                    "recent_years": recent_count,
                    "forecast_score": round(
                        total_score,
                        3,
                    ),
                }
            )

        results.sort(
            key=lambda x:
            x["forecast_score"],
            reverse=True,
        )

        return results


# ============================================================
# GEMINI
# ============================================================

def get_client():

    key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set.\n"
            "Run:\n"
            '$env:GEMINI_API_KEY="YOUR_KEY"'
        )

    return genai.Client(
        api_key=key
    )


def call_gemini(prompt):
    """
    Robust Gemini caller.

    Handles temporary 429/500/502/503/504 errors with retries
    and falls back through several supported models.
    """

    client = get_client()

    retryable_codes = {
        "429",
        "500",
        "502",
        "503",
        "504",
    }

    last_error = None

    for model in FALLBACK_MODELS:

        for attempt in range(3):

            try:

                print(
                    f"Using model: {model} "
                    f"(attempt {attempt + 1}/3)"
                )

                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    ),
                )

                text = response.text

                if not text:
                    raise RuntimeError(
                        "Gemini returned an empty response."
                    )

                try:
                    return json.loads(text)

                except json.JSONDecodeError:

                    # Try extracting JSON object.
                    match = re.search(
                        r"\{.*\}",
                        text,
                        re.DOTALL,
                    )

                    if match:
                        return json.loads(
                            match.group(0)
                        )

                    # Try extracting JSON array.
                    match = re.search(
                        r"\[.*\]",
                        text,
                        re.DOTALL,
                    )

                    if match:
                        return json.loads(
                            match.group(0)
                        )

                    raise RuntimeError(
                        "Gemini returned invalid JSON."
                    )

            except Exception as error:

                last_error = error

                error_text = str(error)

                is_retryable = any(
                    code in error_text
                    for code in retryable_codes
                )

                if not is_retryable:
                    raise

                wait_seconds = 2 ** attempt

                print(
                    f"Temporary Gemini error from {model}: "
                    f"{error_text}"
                )

                if attempt < 2:

                    print(
                        f"Retrying in "
                        f"{wait_seconds} seconds..."
                    )

                    time.sleep(
                        wait_seconds
                    )

                else:

                    print(
                        f"{model} failed after "
                        f"3 attempts."
                    )

    raise RuntimeError(
        "All Gemini models failed."
        f"\nLast error: {last_error}"
    )
# ============================================================
# GENERATION
# ============================================================

def generate_questions(
    corpus,
    subject,
    question_type,
    count,
    topic=None,
):

    search_query = " ".join(
        [
            subject,
            question_type,
            topic or "",
        ]
    )

    examples = corpus.retrieve(
        search_query,
        k=10,
        subject=subject,
        question_type=question_type,
    )

    profile = corpus.pattern_profile(
        subject=subject,
        question_type=question_type,
    )[:10]

    example_text = []

    for number, example in enumerate(
        examples,
        start=1,
    ):

        example_text.append(
            f"""EXAMPLE {number}
Type: {example.get("question_type")}
Topic: {example.get("_topic")}
Question: {example.get("question_text")}
Answer: {example.get("answer")}
"""
        )

    profile_text = json.dumps(
        profile,
        ensure_ascii=False,
        indent=2,
    )

    prompt = f"""
You are the generation engine of Quiz Intelligence,
an AI system trained to understand the style of Ghanaian
National Science & Maths Quiz (NSMQ) questions.

Your task is NOT to copy historical questions.

You must create ORIGINAL questions that feel naturally
written in the same competition tradition.

TARGET SUBJECT:
{subject}

TARGET QUESTION TYPE:
{question_type}

TARGET TOPIC:
{topic or "Use the strongest recurring patterns."}

NUMBER OF QUESTIONS:
{count}

HISTORICAL PATTERN PROFILE:
{profile_text}

HISTORICAL EXAMPLES FOR STYLE REFERENCE:
{"".join(example_text)}

Rules:

1. Do not reproduce an example.
2. Do not merely change numbers in an example.
3. Create genuinely new questions.
4. Preserve the characteristic concise NSMQ wording.
5. Make answers scientifically/mathematically correct.
6. Avoid ambiguous questions.
7. Match the target question type exactly.
8. For riddles, clues should progressively narrow the answer.
9. For true/false, make statements precise and defensible.
10. For speed race questions, favor short-answer questions.
11. For standard questions, use the style suggested by the examples.
12. Include a brief solution where useful.
13. Prefer curriculum-relevant concepts.
14. Do not invent fake scientific facts.

Return ONLY valid JSON with this structure:

{{
  "questions": [
    {{
      "question": "...",
      "answer": "...",
      "solution": "...",
      "topic": "...",
      "difficulty": 1,
      "style_notes": "..."
    }}
  ]
}}
"""

    result = call_gemini(prompt)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "mode": "generation",
        "subject": subject,
        "question_type": question_type,
        "topic": topic,
        "historical_examples": [
            {
                "question": e.get(
                    "question_text"
                ),
                "answer": e.get(
                    "answer"
                ),
                "source": e.get(
                    "sources",
                    [],
                ),
            }
            for e in examples
        ],
        "result": result,
    }

    output_path = (
        OUTPUT_DIR
        / "latest_generation.json"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return output


# ============================================================
# FORECASTING
# ============================================================

def forecast(
    corpus,
    subject,
    question_type=None,
    count=10,
):

    profile = corpus.pattern_profile(
        subject=subject,
        question_type=question_type,
    )

    top_topics = profile[
        :10
    ]

    examples = []

    for topic in top_topics[:5]:

        topic_name = topic[
            "topic"
        ]

        candidates = [
            r
            for r in corpus.records
            if corpus.subject_of(r)
            == subject
            and corpus.primary_topic(r)
            == topic_name
        ]

        candidates.sort(
            key=lambda r:
            (
                r.get(
                    "metadata",
                    {},
                ).get("year")
                or 0
            ),
            reverse=True,
        )

        examples.extend(
            candidates[:2]
        )

    example_text = []

    for e in examples[:12]:

        example_text.append(
            f"""
Topic: {corpus.primary_topic(e)}
Year: {e.get("metadata", {}).get("year")}
Type: {e.get("question_type")}
Question: {e.get("question_text")}
Answer: {e.get("answer")}
"""
        )

    prompt = f"""
You are the forecasting engine of Quiz Intelligence.

Analyze historical NSMQ question patterns and produce
a FORECAST of concepts and question constructions that
are worth watching in future NSMQ contests.

Important:
This is probabilistic forecasting, NOT certainty.

Subject:
{subject}

Question type:
{question_type or "all"}

Recurring topic profile:
{json.dumps(top_topics, indent=2)}

Representative historical questions:
{"".join(example_text)}

Think about:

- topics that recur across many years
- topics that disappear and later return
- recent recurrence
- question formats
- conceptual variation
- likely follow-up concepts
- balance between familiar and less frequently tested areas

Do NOT claim that any exact question will appear.

Return JSON:

{{
  "forecast": [
    {{
      "topic": "...",
      "concept": "...",
      "likelihood": 0.0,
      "reason": "...",
      "possible_question_direction": "..."
    }}
  ]
}}

Return exactly {count} forecast candidates.
"""

    result = call_gemini(prompt)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "mode": "forecast",
        "subject": subject,
        "question_type": question_type,
        "pattern_profile": top_topics,
        "result": result,
    }

    output_path = (
        OUTPUT_DIR
        / "latest_forecast.json"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return output


# ============================================================
# SEARCH
# ============================================================

def search(
    corpus,
    query,
    k,
):

    results = corpus.retrieve(
        query,
        k=k,
    )

    return results


# ============================================================
# PRINT HELPERS
# ============================================================

def print_generation(data):

    print()
    print("=" * 70)
    print("QUIZ INTELLIGENCE — GENERATED QUESTIONS")
    print("=" * 70)

    result = data[
        "result"
    ]

    questions = (
        result.get(
            "questions",
            []
        )
        if isinstance(
            result,
            dict
        )
        else []
    )

    for i, q in enumerate(
        questions,
        start=1,
    ):

        print()
        print(
            f"{i}. {q.get('question')}"
        )

        print(
            f"   Answer: {q.get('answer')}"
        )

        if q.get("solution"):
            print(
                f"   Solution: {q.get('solution')}"
            )

        print(
            f"   Topic: {q.get('topic')}"
        )

        print(
            f"   Difficulty: {q.get('difficulty')}"
        )

        print(
            f"   Style: {q.get('style_notes')}"
        )


def print_forecast(data):

    print()
    print("=" * 70)
    print("QUIZ INTELLIGENCE — FUTURE FORECAST")
    print("=" * 70)

    result = data[
        "result"
    ]

    forecasts = (
        result.get(
            "forecast",
            []
        )
        if isinstance(
            result,
            dict
        )
        else []
    )

    for i, item in enumerate(
        forecasts,
        start=1,
    ):

        likelihood = (
            item.get(
                "likelihood",
                0,
            )
        )

        print()
        print(
            f"{i}. {item.get('topic')}"
        )

        print(
            f"   Concept: {item.get('concept')}"
        )

        print(
            f"   Likelihood: {likelihood}"
        )

        print(
            f"   Reason: {item.get('reason')}"
        )

        print(
            f"   Direction: "
            f"{item.get('possible_question_direction')}"
        )


def print_search(results):

    print()
    print("=" * 70)
    print("QUIZ INTELLIGENCE — SEARCH")
    print("=" * 70)

    for i, record in enumerate(
        results,
        start=1,
    ):

        metadata = record.get(
            "metadata",
            {},
        )

        print()
        print(
            f"{i}. "
            f"{record.get('question_text')}"
        )

        print(
            f"   Answer: "
            f"{record.get('answer')}"
        )

        print(
            f"   Subject: "
            f"{record.get('_subject')}"
        )

        print(
            f"   Topic: "
            f"{record.get('_topic')}"
        )

        print(
            f"   Type: "
            f"{record.get('question_type')}"
        )

        print(
            f"   Year: "
            f"{metadata.get('year')}"
        )

        print(
            f"   Score: "
            f"{record.get('_retrieval_score')}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Quiz Intelligence AI Engine"
        )
    )

    subparsers = (
        parser.add_subparsers(
            dest="command",
            required=True,
        )
    )

    generate_parser = (
        subparsers.add_parser(
            "generate"
        )
    )

    generate_parser.add_argument(
        "--subject",
        required=True,
        choices=[
            "mathematics",
            "physics",
            "chemistry",
            "biology",
        ],
    )

    generate_parser.add_argument(
        "--type",
        default="standard",
        choices=[
            "standard",
            "riddle",
            "true_false",
            "speed_race",
            "problem_of_day",
        ],
    )

    generate_parser.add_argument(
        "--topic",
        default=None,
    )

    generate_parser.add_argument(
        "--count",
        type=int,
        default=5,
    )

    forecast_parser = (
        subparsers.add_parser(
            "forecast"
        )
    )

    forecast_parser.add_argument(
        "--subject",
        required=True,
        choices=[
            "mathematics",
            "physics",
            "chemistry",
            "biology",
        ],
    )

    forecast_parser.add_argument(
        "--type",
        default=None,
    )

    forecast_parser.add_argument(
        "--count",
        type=int,
        default=10,
    )

    search_parser = (
        subparsers.add_parser(
            "search"
        )
    )

    search_parser.add_argument(
        "query"
    )

    search_parser.add_argument(
        "--count",
        type=int,
        default=10,
    )

    args = parser.parse_args()

    print(
        "Loading Quiz Intelligence corpus..."
    )

    corpus = Corpus()

    print(
        f"Loaded {len(corpus.records)} usable questions."
    )

    if args.command == "generate":

        data = generate_questions(
            corpus,
            subject=args.subject,
            question_type=args.type,
            count=args.count,
            topic=args.topic,
        )

        print_generation(
            data
        )

        return

    if args.command == "forecast":

        data = forecast(
            corpus,
            subject=args.subject,
            question_type=args.type,
            count=args.count,
        )

        print_forecast(
            data
        )

        return

    if args.command == "search":

        results = search(
            corpus,
            args.query,
            args.count,
        )

        print_search(
            results
        )

        return


if __name__ == "__main__":
    main()