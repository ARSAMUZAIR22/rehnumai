import json
from state import GeoMindState, CONFLICT_TOPICS, LENS_ROTATION, LENS_LABELS
from utils import call_llm, print_divider


def curriculum_agent(state: GeoMindState) -> GeoMindState:
    """
    Agent 2 — Curriculum Agent

    Responsibilities:
    - Pull the right topic bank based on learner level + subject
    - Ask LLM to sequence the 3 topics pedagogically
    - Assign lens rotation across the 3 topics (hardcoded — deterministic)
    - Write study_plan, current_topic, current_lens to state
    
    This agent re-runs whenever the progress agent detects a level change.
    That re-run is the entire adaptation mechanic.
    """

    learner = state["learner"]
    level   = learner["level"]
    subject = state.get("subject", "maths")
    name    = learner["name"]

    print_divider("Building Your Study Plan")
    print(f"Designing a personalised {level} curriculum for {name}...\n")

    # ── Step 1: Pull topic bank — no LLM needed here ────────────────────────
    # CONFLICT_TOPICS in state.py has topics per level per subject
    # If subject key doesn't exist fall back to maths
    topic_bank = CONFLICT_TOPICS.get(subject, {}).get(level, [])

    # Safety fallback if topic bank is somehow empty
    if not topic_bank:
        topic_bank = [
            f"Introduction to {subject} — core concepts",
            f"Intermediate {subject} — building deeper understanding",
            f"Advanced {subject} — analysis and application"
        ]

    # ── Step 2: Ask LLM to sequence topics pedagogically ────────────────────
    sequencing_prompt = f"""You are a curriculum design agent for a {level} learner studying {subject}.

Given these 3 topics, sequence them from most foundational to most complex:
{json.dumps(topic_bank, indent=2)}

Rules:
- Return ONLY a valid JSON array of the 3 topics in your chosen order
- Do not add new topics or modify the topic text
- Do not include explanation, just the JSON array

Example format:
["Topic A", "Topic B", "Topic C"]"""

    sequencing_message = f"Sequence these 3 topics for a {level} {subject} learner."

    raw = call_llm(sequencing_prompt, sequencing_message)

    try:
        clean = raw.strip().strip("```json").strip("```").strip()
        study_plan = json.loads(clean)
        if not isinstance(study_plan, list) or len(study_plan) != 3:
            raise ValueError("Not a list of 3")
        # Ensure every item is actually from the original bank
        study_plan = [t for t in study_plan if t in topic_bank]
        # If LLM hallucinated topics, fall back to original order
        if len(study_plan) != 3:
            study_plan = topic_bank[:3]
    except Exception:
        study_plan = topic_bank[:3]

    # ── Step 3: Assign lens rotation — hardcoded, deterministic ─────────────
    # Topic 1 → factual | Topic 2 → critical_thinking | Topic 3 → humanitarian
    # This guarantees rotation happens regardless of LLM behaviour
    lens_assignment = {
        study_plan[0]: LENS_ROTATION[0],  # factual
        study_plan[1]: LENS_ROTATION[1],  # critical_thinking
        study_plan[2]: LENS_ROTATION[2],  # humanitarian
    }

    # ── Step 4: Print study plan to CLI ─────────────────────────────────────
    print(f"Your {level.upper()} study plan for {subject.capitalize()}:\n")
    for i, topic in enumerate(study_plan, 1):
        lens  = lens_assignment[topic]
        label = LENS_LABELS[lens]
        print(f"  Topic {i}: {topic}")
        print(f"           {label}\n")

    # ── Step 5: Write everything to shared state ─────────────────────────────
    # Reset topic index to 0 — important when re-running after level change
    updated_learner = dict(learner)
    updated_learner["topic_index"]   = 0
    updated_learner["current_topic"] = study_plan[0]
    updated_learner["current_lens"]  = lens_assignment[study_plan[0]]
    updated_learner["lens_index"]    = 0

    messages = list(state["messages"])
    messages.append(
        f"[Curriculum] Plan set for {level} {subject}: "
        + " → ".join(study_plan)
    )

    return {
        **state,
        "learner":        updated_learner,
        "study_plan":     study_plan,
        "lens_assignment": lens_assignment,
        "current_lesson": "",
        "current_question": "",
        "learner_answer": "",
        "messages":       messages,
        "next_step":      "teach"   # always goes to teaching agent next
    }
