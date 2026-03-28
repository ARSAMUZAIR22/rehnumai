import json
from state import GeoMindState, CONFLICT_TOPICS
from utils import call_llm, print_divider


def assessment_agent(state: GeoMindState) -> GeoMindState:
    """
    Agent 1 — Assessment Agent
    
    Responsibilities:
    - Greet the learner and collect name, age, subject
    - Ask 5 diagnostic questions based on subject
    - Score answers and set beginner/intermediate/advanced level
    - Set age_group flag used by all downstream agents
    - Write results to shared state
    """

    print_divider("GeoMind — Adaptive Learning Engine")
    print("Welcome! I am your personal AI tutor.\n")

    # ── Step 1: Collect basic info ──────────────────────────────────────────
    name = input("What is your name? ").strip()
    
    while True:
        try:
            age = int(input("How old are you? ").strip())
            if 8 <= age <= 25:
                break
            print("Please enter an age between 8 and 25.")
        except ValueError:
            print("Please enter a valid number.")

    print("\nWhich subject would you like to study today?")
    print("  1. Maths")
    print("  2. Science")
    print("  3. Geopolitics")

    subject_map = {"1": "maths", "2": "science", "3": "geopolitics"}
    while True:
        choice = input("\nEnter 1, 2, or 3: ").strip()
        if choice in subject_map:
            subject = subject_map[choice]
            break
        print("Please enter 1, 2, or 3.")

    # ── Step 2: Determine age group ─────────────────────────────────────────
    if age < 14:
        age_group = "child"
    elif age < 18:
        age_group = "teen"
    else:
        age_group = "adult"

    # ── Step 3: Generate diagnostic questions via LLM ───────────────────────
    print_divider("Diagnostic Quiz")
    print(f"Hi {name}! I will ask you 5 quick questions about {subject.capitalize()}.")
    print("Answer as best you can — there are no wrong answers here.\n")

    system_prompt = f"""You are an educational assessment agent for a {age_group} learner aged {age}.
Your job is to generate exactly 5 diagnostic questions for the subject: {subject}.

Rules:
- Questions must be appropriate for a {age_group} (age {age})
- Start simple and gradually increase difficulty
- Questions must be short and clear
- Return ONLY a valid JSON array of 5 strings, nothing else
- No numbering, no explanation, just the JSON array

Example format:
["Question 1?", "Question 2?", "Question 3?", "Question 4?", "Question 5?"]"""

    user_message = f"Generate 5 diagnostic questions for {subject} for a {age_group} aged {age}."

    # Get questions from LLM
    raw = call_llm(system_prompt, user_message)

    # Parse the JSON array of questions
    try:
        # Strip any markdown code fences if model adds them
        clean = raw.strip().strip("```json").strip("```").strip()
        questions = json.loads(clean)
        if not isinstance(questions, list) or len(questions) != 5:
            raise ValueError("Not a list of 5")
    except Exception:
        # Fallback questions if parsing fails
        questions = [
            f"What is the most basic concept in {subject} you know?",
            f"Can you give an example from {subject}?",
            f"What have you studied in {subject} recently?",
            f"What is something you find difficult in {subject}?",
            f"What is something you find easy in {subject}?"
        ]

    # ── Step 4: Ask questions and collect answers ───────────────────────────
    answers = []
    for i, question in enumerate(questions, 1):
        print(f"Q{i}: {question}")
        answer = input("Your answer: ").strip()
        answers.append(answer)
        print()

    # ── Step 5: Score answers via LLM ───────────────────────────────────────
    qa_pairs = "\n".join([
        f"Q{i+1}: {questions[i]}\nA{i+1}: {answers[i]}"
        for i in range(5)
    ])

    scoring_prompt = f"""You are an educational assessor evaluating a {age_group} learner aged {age} on {subject}.

Score each answer 0, 1, or 2:
- 0 = incorrect or blank
- 1 = partially correct or shows basic understanding  
- 2 = correct and shows clear understanding

Then determine overall level:
- Total 0-4  → beginner
- Total 5-7  → intermediate
- Total 8-10 → advanced

Return ONLY valid JSON in this exact format, nothing else:
{{"scores": [0,1,2,1,2], "total": 6, "level": "intermediate", "feedback": "One encouraging sentence."}}"""

    scoring_message = f"Score these question-answer pairs:\n\n{qa_pairs}"

    raw_score = call_llm(scoring_prompt, scoring_message)

    try:
        clean_score = raw_score.strip().strip("```json").strip("```").strip()
        result = json.loads(clean_score)
        level   = result.get("level", "beginner")
        total   = result.get("total", 0)
        feedback = result.get("feedback", "Good effort!")
        if level not in ["beginner", "intermediate", "advanced"]:
            level = "beginner"
    except Exception:
        level    = "beginner"
        total    = 0
        feedback = "Good effort! Let's start from the basics."

    # ── Step 6: Show result and write to state ──────────────────────────────
    print_divider("Assessment Complete")
    print(f"Score: {total}/10")
    print(f"Level: {level.upper()}")
    print(f"\n{feedback}\n")

    # Update shared state — everything downstream reads from here
    updated_learner = dict(state["learner"])
    updated_learner["name"]        = name
    updated_learner["age"]         = age
    updated_learner["level"]       = level
    updated_learner["age_group"]   = age_group

    messages = list(state["messages"])
    messages.append(f"[Assessment] {name} | Age {age} | {subject.capitalize()} | Level: {level}")

    return {
        **state,
        "learner":   updated_learner,
        "subject":   subject,
        "messages":  messages,
        "next_step": "plan"   # tells LangGraph to run curriculum agent next
    }
