from state import GeoMindState, LENS_LABELS
from utils import call_llm, print_divider


def teaching_agent(state: GeoMindState) -> GeoMindState:
    """
    Agent 3 — Teaching Agent

    Responsibilities:
    - Build a dynamic system prompt using level + age_group + topic + lens
    - Call LLM to generate lesson content through the active lens
    - Parse lesson body and check question from response
    - Print lesson to CLI and wait for learner answer
    - Write lesson, question, and answer to state
    """

    learner       = state["learner"]
    level         = learner["level"]
    age_group     = learner.get("age_group", "teen")
    name          = learner["name"]
    current_topic = learner["current_topic"]
    current_lens  = learner["current_lens"]
    topic_index   = learner["topic_index"]
    study_plan    = state["study_plan"]
    subject       = state.get("subject", "maths")

    lens_label = LENS_LABELS[current_lens]

    print_divider(f"Topic {topic_index + 1} of {len(study_plan)}")
    print(f"Subject : {subject.capitalize()}")
    print(f"Topic   : {current_topic}")
    print(f"Lens    : {lens_label}")
    print(f"Level   : {level.upper()}\n")

    # ── Step 1: Build dynamic system prompt ──────────────────────────────────
    # This is the core of the teaching agent — every variable shapes the output
    lens_instructions = {
        "factual": (
            "Present only verified facts. Explain who the key actors are, "
            "what happened, when, and why. No opinions. No blame. "
            "Use neutral language throughout."
        ),
        "critical_thinking": (
            "Encourage the learner to question narratives. Explore: who benefits "
            "from each version of events? How do different media outlets frame this "
            "differently? What information might be missing? Guide thinking, don't give answers."
        ),
        "humanitarian": (
            "Centre the human cost. Focus on civilians affected, displacement, "
            "international humanitarian law, and real human stories. "
            "Avoid glorifying any military action. Emphasise empathy and shared humanity."
        )
    }

    age_instructions = {
        "child":  "Use very simple words. Short sentences. Relatable analogies. Avoid graphic content entirely.",
        "teen":   "Use clear language. Some technical terms are fine if explained. Keep it engaging.",
        "adult":  "Use full academic language. Technical terms welcome. Assume prior knowledge."
    }

    system_prompt = f"""You are an expert {subject} tutor for a {age_group} learner aged around {learner['age']}.
The learner's name is {name} and their level is {level}.

Your task: Teach the topic "{current_topic}" using the {current_lens.upper()} lens.

Lens instruction:
{lens_instructions[current_lens]}

Language instruction:
{age_instructions[age_group]}

Structure your response in EXACTLY this format — no deviation:

LESSON:
[Write 3-5 paragraphs teaching the topic through the lens above]

QUESTION:
[Write exactly ONE comprehension check question relevant to this lesson]

Rules:
- Do not add any text before LESSON: or after the question
- The question must be answerable from the lesson content
- Do not number the question
- Do not add "Answer:" or any hint"""

    user_message = (
        f"Teach '{current_topic}' through the {current_lens} lens "
        f"for a {level} {age_group} learner studying {subject}."
    )

    # ── Step 2: Call LLM ─────────────────────────────────────────────────────
    print("Generating your lesson...\n")
    raw_response = call_llm(system_prompt, user_message)

    # ── Step 3: Parse lesson and question ────────────────────────────────────
    lesson_text   = ""
    check_question = ""

    if "LESSON:" in raw_response and "QUESTION:" in raw_response:
        parts = raw_response.split("QUESTION:")
        lesson_part = parts[0].replace("LESSON:", "").strip()
        question_part = parts[1].strip() if len(parts) > 1 else ""
        lesson_text    = lesson_part
        check_question = question_part
    else:
        # Fallback — treat whole response as lesson, add generic question
        lesson_text    = raw_response.strip()
        check_question = f"What is the most important thing you learned about {current_topic}?"

    # ── Step 4: Display lesson to learner ────────────────────────────────────
    print(lesson_text)
    print()
    print_divider("Check Your Understanding")
    print(f"{check_question}\n")

    # ── Step 5: Collect learner's answer ─────────────────────────────────────
    learner_answer = input(f"{name}: ").strip()
    if not learner_answer:
        learner_answer = "(no answer provided)"

    # ── Step 6: Write to state ───────────────────────────────────────────────
    messages = list(state["messages"])
    messages.append(
        f"[Teaching] Topic: {current_topic} | Lens: {current_lens} | Level: {level}"
    )

    return {
        **state,
        "learner":          learner,
        "current_lesson":   lesson_text,
        "current_question": check_question,
        "learner_answer":   learner_answer,
        "messages":         messages,
        "next_step":        "evaluate"   # always goes to progress agent next
    }
