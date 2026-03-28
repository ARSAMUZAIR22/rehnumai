from typing import TypedDict, List, Optional, Dict

# This is the single source of truth passed between all agents.
# Every agent reads from this state and returns an updated version of it.

class LearnerProfile(TypedDict):
    name: str
    age: int
    level: str           # "beginner", "intermediate", "advanced"
    current_lens: str    # "factual", "critical_thinking", "humanitarian"
    lens_index: int      # 0, 1, 2 — tracks rotation position
    current_topic: str   # e.g. "The Russia-Ukraine War"
    topic_index: int     # which topic in the plan we're on
    score: int           # running score out of 100
    questions_asked: int

class GeoMindState(TypedDict):
    # Learner profile — set by assessment agent, updated by progress agent
    learner: LearnerProfile

    # The 3-topic study plan — set by curriculum agent
    study_plan: List[str]

    # The current lesson content — set by teaching agent
    current_lesson: str

    # The check question posed to the learner — set by teaching agent
    current_question: str

    # The learner's answer to the check question
    learner_answer: str

    # Feedback from the progress agent after evaluating the answer
    feedback: str

    # Full conversation history shown in the CLI
    messages: List[str]

    # Controls flow — which node runs next
    next_step: str  # "assess" | "plan" | "teach" | "evaluate" | "end"


def initial_state() -> GeoMindState:
    """Returns a blank starting state before any agent has run."""
    return GeoMindState(
        learner=LearnerProfile(
            name="",
            age=0,
            level="beginner",
            current_lens="factual",
            lens_index=0,
            current_topic="",
            topic_index=0,
            score=0,
            questions_asked=0,
        ),
        study_plan=[],
        current_lesson="",
        current_question="",
        learner_answer="",
        feedback="",
        messages=[],
        next_step="assess",
    )


# The 3 lenses in rotation order
LENS_ROTATION = ["factual", "critical_thinking", "humanitarian"]

# Labels printed to the CLI for each lens
LENS_LABELS = {
    "factual":           "🌍 Lens 1 — Neutral & Factual",
    "critical_thinking": "🧠 Lens 2 — Critical Thinking",
    "humanitarian":      "❤️  Lens 3 — Humanitarian",
}

# Conflict topics available — curriculum agent picks 3 based on learner level
CONFLICT_TOPICS = {
    "beginner": [
        "What is a war and why do countries fight?",
        "The Russia-Ukraine War — what happened and why",
        "The conflict in Gaza — a simple overview",
    ],
    "intermediate": [
        "The Russia-Ukraine War — causes, NATO, and global impact",
        "The Israel-Gaza conflict — history and current situation",
        "The Kashmir dispute — India, Pakistan, and the unresolved border",
    ],
    "advanced": [
        "Geopolitics of the Russia-Ukraine War — energy, alliances, and sovereignty",
        "The Israel-Palestine conflict — international law and humanitarian crisis",
        "The South China Sea — territorial claims and US-China rivalry",
    ],
}
