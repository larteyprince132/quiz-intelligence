import streamlit as st
from src.ai.quiz_ai import Corpus, generate_questions


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Quiz Intelligence",
    page_icon="🧠",
    layout="centered",
)


# =========================================================
# STYLING
# =========================================================

st.markdown(
    """
    <style>

        .main-title {
            font-size: 3rem;
            font-weight: 800;
            text-align: center;
            margin-bottom: 0.2rem;
        }

        .subtitle {
            text-align: center;
            color: #777;
            font-size: 1.1rem;
            margin-bottom: 2rem;
        }

        .question-number {
            font-size: 1rem;
            color: #777;
            margin-bottom: 0.5rem;
        }

        .score {
            font-size: 4rem;
            font-weight: 800;
            text-align: center;
            margin: 1rem 0;
        }

        .topic-card {
            padding: 1rem;
            border-radius: 12px;
            border: 1px solid #ddd;
            margin-bottom: 0.8rem;
        }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# CORPUS
# =========================================================

@st.cache_resource
def get_corpus():
    return Corpus()


# =========================================================
# SESSION STATE
# =========================================================

defaults = {
    "quiz_started": False,
    "quiz_finished": False,
    "questions": [],
    "current_question": 0,
    "score": 0,
    "answered": False,
    "selected_answer": "",
    "results": [],
}

for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="main-title">🧠 Quiz Intelligence</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    'Your AI-powered quiz preparation engine'
    '</div>',
    unsafe_allow_html=True,
)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.header("⚙️ Quiz Settings")

    subject = st.selectbox(
        "Subject",
        [
            "mathematics",
            "physics",
            "chemistry",
            "biology",
        ],
    )

    topic = st.text_input(
        "Topic (optional)",
        placeholder="e.g. calculus",
    )

    quiz_type = st.selectbox(
        "Quiz Type",
        [
            "standard",
            "speed_race",
            "problem_of_the_day",
            "riddle",
            "true_false",
        ],
    )

    question_count = st.slider(
        "Number of Questions",
        min_value=5,
        max_value=20,
        value=5,
    )

    start_button = st.button(
        "🚀 Start Quiz",
        use_container_width=True,
    )


# =========================================================
# START QUIZ
# =========================================================

if start_button:

    # Reset quiz
    st.session_state.quiz_started = False
    st.session_state.quiz_finished = False
    st.session_state.questions = []
    st.session_state.current_question = 0
    st.session_state.score = 0
    st.session_state.answered = False
    st.session_state.selected_answer = ""
    st.session_state.results = []

    with st.spinner("🧠 Generating your quiz..."):

        corpus = get_corpus()

        result = generate_questions(
            corpus,
            subject=subject,
            question_type=quiz_type,
            count=question_count,
            topic=topic if topic.strip() else None,
        )

    # -----------------------------------------------------
    # Extract questions
    # -----------------------------------------------------

    if isinstance(result, dict):

        inner_result = result.get("result", {})

        if isinstance(inner_result, dict):

            questions = inner_result.get(
                "questions",
                [],
            )

        else:

            questions = []

    elif isinstance(result, list):

        questions = result

    else:

        questions = []


    # -----------------------------------------------------
    # Start quiz
    # -----------------------------------------------------

    if questions:

        st.session_state.questions = questions
        st.session_state.quiz_started = True
        st.session_state.current_question = 0
        st.session_state.score = 0
        st.session_state.answered = False
        st.session_state.selected_answer = ""
        st.session_state.results = []

        st.rerun()

    else:

        st.error(
            "The AI did not return any questions. "
            "Please try again."
        )


# =========================================================
# ACTIVE QUIZ
# =========================================================

if (
    st.session_state.quiz_started
    and not st.session_state.quiz_finished
):

    questions = st.session_state.questions

    index = st.session_state.current_question

    total = len(questions)

    question = questions[index]


    # -----------------------------------------------------
    # Progress
    # -----------------------------------------------------

    st.progress(
        (index + 1) / total
    )

    st.markdown(
        f'<div class="question-number">'
        f'Question {index + 1} of {total}'
        f'</div>',
        unsafe_allow_html=True,
    )


    # -----------------------------------------------------
    # Question
    # -----------------------------------------------------

    question_text = question.get(
        "question_text",
        question.get(
            "question",
            "Question unavailable",
        ),
    )

    st.subheader(question_text)


    # -----------------------------------------------------
    # Metadata
    # -----------------------------------------------------

    q_topic = question.get(
        "topic",
        topic if topic else "General",
    )

    difficulty = question.get(
        "difficulty",
        None,
    )

    if difficulty is not None:

        st.caption(
            f"📚 Topic: {q_topic}   |   "
            f"🎯 Difficulty: {difficulty}/5"
        )

    else:

        st.caption(
            f"📚 Topic: {q_topic}"
        )


    # -----------------------------------------------------
    # Answer box
    # -----------------------------------------------------

    answer = st.text_area(
        "Your answer:",
        value=(
            st.session_state.selected_answer
            if st.session_state.answered
            else ""
        ),
        height=120,
        key=f"answer_box_{index}",
        disabled=st.session_state.answered,
        placeholder="Type your answer here...",
    )


    # -----------------------------------------------------
    # Submit
    # -----------------------------------------------------

    if not st.session_state.answered:

        if st.button(
            "✅ Submit Answer",
            use_container_width=True,
        ):

            st.session_state.selected_answer = answer.strip()

            correct_answer = str(
                question.get(
                    "answer",
                    "",
                )
            ).strip()


            student_answer = (
                answer.strip().lower()
            )

            expected_answer = (
                correct_answer.lower()
            )


            # -------------------------------------------------
            # Basic answer evaluation
            # -------------------------------------------------

            is_correct = (
                student_answer != ""
                and student_answer == expected_answer
            )


            if is_correct:

                st.session_state.score += 1


            # Store result
            st.session_state.results.append(
                {
                    "question": question_text,
                    "topic": q_topic,
                    "difficulty": difficulty,
                    "student_answer": answer.strip(),
                    "correct_answer": correct_answer,
                    "correct": is_correct,
                }
            )


            st.session_state.answered = True

            st.rerun()


    # -----------------------------------------------------
    # Feedback
    # -----------------------------------------------------

    else:

        correct_answer = str(
            question.get(
                "answer",
                "",
            )
        ).strip()

        student_answer = str(
            st.session_state.selected_answer
        ).strip()


        if (
            student_answer.lower()
            == correct_answer.lower()
            and student_answer != ""
        ):

            st.success(
                "🎉 Correct! Excellent work."
            )

        else:

            st.error(
                "❌ Not quite."
            )

            st.markdown(
                f"### Correct answer"
            )

            st.write(correct_answer)


        # -------------------------------------------------
        # Explanation
        # -------------------------------------------------

        solution = question.get(
            "solution"
        )

        if solution:

            st.info(
                f"💡 **Explanation**\n\n{solution}"
            )


        # -------------------------------------------------
        # Next question
        # -------------------------------------------------

        if index + 1 < total:

            if st.button(
                "➡️ Next Question",
                use_container_width=True,
            ):

                st.session_state.current_question += 1
                st.session_state.answered = False
                st.session_state.selected_answer = ""

                st.rerun()

        else:

            if st.button(
                "🏁 Finish Quiz",
                use_container_width=True,
            ):

                st.session_state.quiz_started = False
                st.session_state.quiz_finished = True

                st.rerun()


# =========================================================
# RESULTS
# =========================================================

elif st.session_state.quiz_finished:

    results = st.session_state.results

    total = len(results)

    score = st.session_state.score


    # -----------------------------------------------------
    # Header
    # -----------------------------------------------------

    st.success(
        "🏆 Quiz Complete!"
    )

    st.markdown(
        f'<div class="score">'
        f'{score} / {total}'
        f'</div>',
        unsafe_allow_html=True,
    )


    percentage = (
        score / total * 100
        if total
        else 0
    )


    st.metric(
        "Overall Score",
        f"{percentage:.0f}%",
    )


    # -----------------------------------------------------
    # Performance message
    # -----------------------------------------------------

    if percentage >= 80:

        st.balloons()

        st.success(
            "🔥 Excellent performance! "
            "You're getting into serious quiz territory."
        )

    elif percentage >= 60:

        st.info(
            "👍 Solid performance. "
            "A little more targeted practice can push this higher."
        )

    else:

        st.warning(
            "📚 More practice is needed. "
            "Let's identify where the gaps are."
        )


    # =====================================================
    # TOPIC PERFORMANCE
    # =====================================================

    st.markdown("---")

    st.header(
        "🧠 Topic Performance"
    )


    topic_stats = {}


    for result in results:

        current_topic = result.get(
            "topic",
            "General",
        )

        if current_topic not in topic_stats:

            topic_stats[current_topic] = {
                "correct": 0,
                "total": 0,
            }

        topic_stats[current_topic]["total"] += 1

        if result["correct"]:

            topic_stats[current_topic]["correct"] += 1


    for current_topic, stats in topic_stats.items():

        topic_total = stats["total"]

        topic_correct = stats["correct"]

        topic_percentage = (
            topic_correct
            / topic_total
            * 100
        )


        if topic_percentage >= 80:

            indicator = "🟢"

        elif topic_percentage >= 60:

            indicator = "🟡"

        else:

            indicator = "🔴"


        st.markdown(
            f"""
            <div class="topic-card">
                <strong>
                    {indicator} {current_topic}
                </strong>
                <br>
                {topic_correct} / {topic_total}
                correct
                <br>
                {topic_percentage:.0f}%
            </div>
            """,
            unsafe_allow_html=True,
        )


    # =====================================================
    # WEAK AREAS
    # =====================================================

    weak_topics = []

    for current_topic, stats in topic_stats.items():

        topic_percentage = (
            stats["correct"]
            / stats["total"]
            * 100
        )

        if topic_percentage < 60:

            weak_topics.append(
                current_topic
            )


    if weak_topics:

        st.markdown("---")

        st.header(
            "🎯 Recommended Practice"
        )

        st.warning(
            "These areas need more attention:"
        )

        for weak_topic in weak_topics:

            st.write(
                f"🔴 **{weak_topic}**"
            )

        st.write(
            "The next version will be able to "
            "automatically generate targeted questions "
            "for these weak areas."
        )


    # =====================================================
    # QUESTION REVIEW
    # =====================================================

    st.markdown("---")

    st.header(
        "📝 Question Review"
    )


    for number, result in enumerate(
        results,
        start=1,
    ):

        if result["correct"]:

            icon = "✅"

        else:

            icon = "❌"


        with st.expander(
            f"{icon} Question {number}"
        ):

            st.write(
                result["question"]
            )

            st.write(
                f"**Your answer:** "
                f"{result['student_answer']}"
            )

            st.write(
                f"**Correct answer:** "
                f"{result['correct_answer']}"
            )


    # =====================================================
    # NEW QUIZ
    # =====================================================

    st.markdown("---")

    if st.button(
        "🔄 Start Another Quiz",
        use_container_width=True,
    ):

        st.session_state.quiz_started = False
        st.session_state.quiz_finished = False
        st.session_state.questions = []
        st.session_state.current_question = 0
        st.session_state.score = 0
        st.session_state.answered = False
        st.session_state.selected_answer = ""
        st.session_state.results = []

        st.rerun()


# =========================================================
# HOME SCREEN
# =========================================================

else:

    st.markdown(
        "### 🎓 Prepare smarter"
    )

    st.write(
        "Quiz Intelligence uses your question corpus "
        "and AI to generate targeted practice questions "
        "for quiz preparation."
    )


    # -----------------------------------------------------
    # Stats
    # -----------------------------------------------------

    col1, col2, col3 = st.columns(3)


    with col1:

        st.metric(
            "Question Bank",
            "18,394+",
        )


    with col2:

        st.metric(
            "Subjects",
            "4",
        )


    with col3:

        st.metric(
            "AI Powered",
            "✓",
        )


    st.markdown("---")


    # -----------------------------------------------------
    # Modes
    # -----------------------------------------------------

    st.markdown(
        "### 🚀 Practice Modes"
    )

    st.write(
        """
        **📘 Standard Questions**

        Build your fundamentals with focused questions.


        **⚡ Speed Race**

        Train yourself to think and answer quickly.


        **🧩 Riddles**

        Develop reasoning and lateral thinking.


        **✅ True / False**

        Test rapid conceptual recall.


        **🔥 Problem of the Day**

        Take on a tougher challenge.
        """
    )


    st.info(
        "Choose your subject and quiz settings "
        "from the sidebar, then click "
        "**Start Quiz**."
    )