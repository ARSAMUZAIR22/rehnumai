import json
from state import GeoMindState, LENS_ROTATION, LENS_LABELS
from utils import call_llm, print_divider


def progress_agent(state: GeoMindState) -> GeoMindState:
    """
    Agent 4 — Progress Agent

    Responsibilities:
    - Score the learner's answer using LLM (0, 1, or 2)
    - Apply deterministic level promotion/demotion logic
    - Rotate lens and advance topic index
    - Decide next_step: "teach" (continue), "plan" (adapt), or "end"
    - Write all updates back to shared state
    """

    learner        = state["learner"]
    level          = learner["level"]
    name           = learner["name"]
    age_group      = learner.get("age_group", "teen")
    topic_index    = learner["topic_index"]
    lens_index     = learner["lens_index"]
    current_score  = learner["score"]
    questions_asked = learner["questions_asked"]
    study_plan     = state["study_plan"]
    current_topic  = learner["current_topic"]
    current_lens   = learner["current_lens"]
    check_question = state["current_question"]
    learner_answer = state["learner_answer"]
    subject        = state.get("subject", "maths")

    # Track consecutive wrong answers for demotion logic
    consecutive_wrong = learner.get("consecutive_wrong", 0)
    consecutive_right = learner.get("consecutive_right", 0)

    # ── Step 1: Score the answer via LLM ─────────────────────────────────────
    scoring_prompt = f"""You are an educational assessor evaluating a {level} {age_group} learner.

Question asked: {check_question}
Learner's answer: {learner_answer}
Subject: {subject}
Topic: {current_topic}

Score the answer:
- 2 = correct and shows clear understanding
- 1 = partially correct or shows basic understanding
- 0 = incorrect, blank, or completely off-topic

Also write one line of encouraging feedback appropriate for a {age_group}.

Return ONLY valid JSON in this exact format:
{{"score": 1, "feedback": "Good effort! You got the main idea."}}"""

    raw = call_llm(scoring_prompt, f"Score this answer for topic: {current_topic}")

    try:
        clean = raw.strip().strip("```json").strip("```").strip()
        result   = json.loads(clean)
        answer_score = int(result.get("score", 0))
        feedback = result.get("feedback", "Keep going!")
        if answer_score not in [0, 1, 2]:
            answer_score = 0
    except Exception:
        answer_score = 0
        feedback     = "Keep going — every attempt helps you learn!"

    # ── Step 2: Update running score and counters ─────────────────────────────
    new_score        = current_score + answer_score
    questions_asked += 1

    if answer_score == 2:
        consecutive_right += 1
        consecutive_wrong  = 0
    elif answer_score == 0:
        consecutive_wrong += 1
        consecutive_right  = 0
    else:
        # partial answer resets both streaks
        consecutive_wrong = 0
        consecutive_right = 0

    # ── Step 3: Deterministic level change logic ──────────────────────────────
    # LLM told us the score — Python decides the routing
    level_changed = False
    new_level     = level

    if consecutive_right >= 2 and level == "beginner":
        new_level     = "intermediate"
        level_changed = True
        print_divider("Level Up!")
        print(f"Excellent work {name}! You're moving to INTERMEDIATE level.\n")

    elif consecutive_right >= 2 and level == "intermediate":
        new_level     = "advanced"
        level_changed = True
        print_divider("Level Up!")
        print(f"Outstanding {name}! You're moving to ADVANCED level.\n")

    elif consecutive_wrong >= 2 and level == "advanced":
        new_level     = "intermediate"
        level_changed = True
        print_divider("Adjusting Difficulty")
        print(f"Let's slow down a bit {name}. Moving to INTERMEDIATE level.\n")

    elif consecutive_wrong >= 2 and level == "intermediate":
        new_level     = "beginner"
        level_changed = True
        print_divider("Adjusting Difficulty")
        print(f"Let's build a stronger foundation {name}. Moving to BEGINNER level.\n")

    # ── Step 4: Show feedback to learner ─────────────────────────────────────
    score_label = ["Needs work", "Good effort", "Excellent!"][answer_score]
    print_divider("Feedback")
    print(f"Score: {answer_score}/2 — {score_label}")
    print(f"{feedback}\n")
    print(f"Running total: {new_score} points across {questions_asked} questions\n")

    # ── Step 5: Decide next step ──────────────────────────────────────────────
    next_topic_index = topic_index + 1
    next_lens_index  = (lens_index + 1) % len(LENS_ROTATION)

    if level_changed:
        # Re-run curriculum agent with new level — this is the adaptation loop
        next_step = "plan"

    elif next_topic_index >= len(study_plan):
        # All topics done — session complete
        next_step = "end"

    else:
        # Continue to next topic with next lens
        next_step = "teach"

    # ── Step 6: Advance topic and lens in state ───────────────────────────────
    updated_learner = dict(learner)
    updated_learner["score"]            = new_score
    updated_learner["questions_asked"]  = questions_asked
    updated_learner["level"]            = new_level
    updated_learner["consecutive_wrong"] = consecutive_wrong
    updated_learner["consecutive_right"] = consecutive_right

    if next_step == "teach":
        # Advance to next topic and rotate lens
        updated_learner["topic_index"]   = next_topic_index
        updated_learner["current_topic"] = study_plan[next_topic_index]
        updated_learner["lens_index"]    = next_lens_index
        updated_learner["current_lens"]  = LENS_ROTATION[next_lens_index]

        next_lens_label = LENS_LABELS[LENS_ROTATION[next_lens_index]]
        print(f"Next up: {study_plan[next_topic_index]}")
        print(f"Lens: {next_lens_label}\n")

    elif next_step == "plan":
        # Reset index — curriculum agent will rebuild plan for new level
        updated_learner["topic_index"]    = 0
        updated_learner["consecutive_wrong"] = 0
        updated_learner["consecutive_right"] = 0

    elif next_step == "end":
        # Print final summary
        print_divider("Session Complete")
        print(f"Well done {name}!")
        print(f"Final score   : {new_score} points")
        print(f"Questions done: {questions_asked}")
        print(f"Final level   : {new_level.upper()}")
        print(f"Subject       : {subject.capitalize()}\n")
        print("You have completed your adaptive learning session. Keep exploring!\n")

    messages = list(state["messages"])
    messages.append(
        f"[Progress] Topic: {current_topic} | Answer score: {answer_score}/2 | "
        f"Level: {new_level} | Next: {next_step}"
    )

    return {
        **state,
        "learner":       updated_learner,
        "feedback":      feedback,
        "messages":      messages,
        "next_step":     next_step
    }
