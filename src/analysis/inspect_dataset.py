import json
from pathlib import Path


DATA_FILE = Path("data/sample_questions.json")


def load_questions():
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def main():
    questions = load_questions()

    print(f"Number of questions: {len(questions)}")
    print()

    for question in questions:
        print(f"ID: {question['id']}")
        print(f"Competition: {question['competition']}")
        print(f"Subject: {question['subject']}")
        print(f"Topic: {question['topic']}")
        print(f"Difficulty: {question['difficulty']}")
        print()


if __name__ == "__main__":
    main()