import streamlit as st
from src.ai.quiz_ai import Corpus, generate_questions, forecast


# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------

st.set_page_config(
    page_title="Quiz Intelligence",
    page_icon="🧠",
    layout="centered",
)


# ---------------------------------------------------------
# CUSTOM STYLING
# ---------------------------------------------------------

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
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# LOAD CORPUS
# ---------------------------------------------------------

@st.cache_resource
def get_corpus():
    return Corpus()


# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------

defaults = {
    "quiz_started": False,
    "questions": [],
    "current_question": 0,
    "score": 0,
    "answered": False,
    "selected_answer": None,
    "quiz_finished": False,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

st.markdown(
    '<div class="main-title">🧠 Quiz Intelligence</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">Your AI-powered quiz preparation engine</div>',
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# START QUIZ
# ---------------------------------------------------------

if start_button:

    # Reset old quiz state
    st.session_state.questions = []
    st.session_state.current_question = 0
    st.session_state.score = 0
    st.session_state.answered = False
    st.session_state.selected_answer = None
    st.session_state.quiz_finished = False

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
    # EXTRACT QUESTIONS FROM AI RESPONSE
    # -----------------------------------------------------

    if isinstance(result, dict):

        inner_result = result.get("result", {})

        if isinstance(inner_result, dict):
            questions = inner_result.get("questions", [])
        else:
            questions = []

    elif isinstance(result, list):

        questions = result

    else:

        questions = []

    # -----------------------------------------------------
    # START QUIZ IF QUESTIONS EXIST
    # -----------------------------------------------------

    if questions:

        st.session_state.questions = questions
        st.session_state.current_question = 0
        st.session_state.score = 0
        st.session_state.answered = False
        st.session_state.selected_answer = None
        st.session_state.quiz_started = True
        st.session_state.quiz_finished = False

        st.rerun()

    else:

        st.error(
            "The AI did not return any questions. "
            "Please try again."
        )


# ---------------------------------------------------------
# ACTIVE QUIZ
# ---------------------------------------------------------

if (
    st.session_state.quiz_started
    and not st.session_state.quiz_finished
):

    questions = st.session_state.questions

    index = st.session_state.current_question

    total = len(questions)

    question = questions[index]


    # -----------------------------------------------------
    # PROGRESS
    # -----------------------------------------------------

    st.progress((index + 1) / total)

    st.markdown(
        f'<div class="question-number">'
        f'Question {index + 1} of {total}'
        f'</div>',
        unsafe_allow_html=True,
    )


    # -----------------------------------------------------
    # QUESTION TEXT
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
    # OPTIONS
    # -----------------------------------------------------

    options = question.get("options", [])


    # -----------------------------------------------------
    # MULTIPLE CHOICE QUESTION
    # -----------------------------------------------------

    if options:

        selected = st.radio(
            "Choose your answer:",
            options,
            key=f"question_{index}",
            disabled=st.session_state.answered,
        )


        # -------------------------------------------------
        # SUBMIT ANSWER
        # -------------------------------------------------

        if not st.session_state.answered:

            if st.button(
                "✅ Submit Answer",
                use_container_width=True,
            ):

                st.session_state.selected_answer = selected
                st.session_state.answered = True

                correct_answer = str(
                    question.get("answer", "")
                ).strip()


                # Check answer
                if (
                    str(selected).strip().lower()
                    == correct_answer.lower()
                ):

                    st.session_state.score += 1

                st.rerun()


        # -------------------------------------------------
        # SHOW RESULT
        # -------------------------------------------------

        else:

            correct_answer = str(
                question.get("answer", "")
            ).strip()

            selected_answer = str(
                st.session_state.selected_answer
            ).strip()


            if (
                selected_answer.lower()
                == correct_answer.lower()
            ):

                st.success("🎉 Correct!")

            else:

                st.error(
                    f"❌ Not quite. "
                    f"The correct answer is: "
                    f"**{correct_answer}**"
                )


            # Explanation
            solution = question.get("solution")

            if solution:

                st.info(
                    f"💡 **Explanation:** {solution}"
                )


            # Next question
            if index + 1 < total:

                if st.button(
                    "➡️ Next Question",
                    use_container_width=True,
                ):

                    st.session_state.current_question += 1
                    st.session_state.answered = False
                    st.session_state.selected_answer = None

                    st.rerun()

            # Finish quiz
            else:

                if st.button(
                    "🏁 Finish Quiz",
                    use_container_width=True,
                ):

                    st.session_state.quiz_finished = True

                    st.rerun()


    # -----------------------------------------------------
    # OPEN-ENDED QUESTION
    # -----------------------------------------------------

    else:

        st.warning(
            "This question does not contain multiple-choice "
            "options, so enter your answer below."
        )

        answer = st.text_input(
            "Your answer:",
            key=f"text_answer_{index}",
            disabled=st.session_state.answered,
        )


        # -------------------------------------------------
        # SUBMIT OPEN-ENDED ANSWER
        # -------------------------------------------------

        if not st.session_state.answered:

            if st.button(
                "✅ Submit Answer",
                use_container_width=True,
            ):

                st.session_state.selected_answer = answer
                st.session_state.answered = True

                correct_answer = str(
                    question.get("answer", "")
                ).strip()


                if (
                    answer.strip().lower()
                    == correct_answer.lower()
                ):

                    st.session_state.score += 1

                st.rerun()


        # -------------------------------------------------
        # SHOW OPEN-ENDED RESULT
        # -------------------------------------------------

        else:

            correct_answer = str(
                question.get("answer", "")
            ).strip()

            selected_answer = str(
                st.session_state.selected_answer
            ).strip()


            if (
                selected_answer.lower()
                == correct_answer.lower()
            ):

                st.success("🎉 Correct!")

            else:

                st.error(
                    f"❌ Correct answer: "
                    f"**{correct_answer}**"
                )


            # Explanation
            solution = question.get("solution")

            if solution:

                st.info(
                    f"💡 **Explanation:** {solution}"
                )


            # Next question
            if index + 1 < total:

                if st.button(
                    "➡️ Next Question",
                    use_container_width=True,
                ):

                    st.session_state.current_question += 1
                    st.session_state.answered = False
                    st.session_state.selected_answer = None

                    st.rerun()

            # Finish
            else:

                if st.button(
                    "🏁 Finish Quiz",
                    use_container_width=True,
                ):

                    st.session_state.quiz_finished = True

                    st.rerun()


# ---------------------------------------------------------
# QUIZ RESULTS
# ---------------------------------------------------------

elif st.session_state.quiz_finished:

    questions = st.session_state.questions

    total = len(questions)

    score = st.session_state.score


    st.success("🏆 Quiz Complete!")


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
        "Score",
        f"{percentage:.0f}%",
    )


    if percentage >= 80:

        st.balloons()

        st.success(
            "🔥 Excellent performance!"
        )

    elif percentage >= 60:

        st.info(
            "👍 Good work. Keep sharpening "
            "those weak areas."
        )

    else:

        st.warning(
            "📚 More practice will help. "
            "Let's attack the weak areas!"
        )


    # Start another quiz
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
        st.session_state.selected_answer = None

        st.rerun()


# ---------------------------------------------------------
# HOME SCREEN
# ---------------------------------------------------------

else:

    st.markdown(
        "### 🎓 Prepare smarter"
    )

    st.write(
        "Quiz Intelligence uses your question corpus "
        "and AI to generate targeted practice questions "
        "for quiz preparation."
    )


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


    st.markdown(
        "### 🚀 What you can practice"
    )


    st.write(
        """
        **📘 Standard Questions**

        Build your fundamentals.


        **⚡ Speed Race**

        Practice answering quickly.


        **🧩 Riddles**

        Train your reasoning.


        **✅ True / False**

        Test rapid conceptual recall.


        **🔥 Problem of the Day**

        Take on a tougher challenge.
        """
    )


    st.info(
        "Choose your subject and quiz settings "
        "from the sidebar, then click **Start Quiz**."
    )