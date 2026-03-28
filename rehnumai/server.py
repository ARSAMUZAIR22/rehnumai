from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from groq import Groq
import os, json, re

load_dotenv()
app = Flask(__name__)
CORS(app)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

def llm(system, user, tokens=1024):
    r = client.chat.completions.create(
        model=MODEL, max_tokens=tokens,
        messages=[{"role":"system","content":system},{"role":"user","content":user}]
    )
    return r.choices[0].message.content.strip()


# ── GUARDRAIL 1: Age-based content filter ─────────────────────────────────────
def age_filter(text, age_group):
    """
    Runs lesson content through a safety check.
    Children under 14: full filter — rewrites graphic or inappropriate content.
    Teens 14-17: lighter check — strips only extreme graphic content.
    Adults: no filtering.
    """
    if age_group == "child":
        sys_p = """You are a child safety filter for educational content aimed at children under 14.

Review this lesson text and check for:
- Any graphic descriptions of violence, injury, death, or suffering
- Inflammatory political language that assigns clear blame to a group
- Content that would be disturbing or inappropriate for a child under 14
- Any language that could frighten or traumatise a young child

If the text passes: return {"safe": true, "text": "<original text unchanged>", "reason": "clean"}
If the text fails: return {"safe": false, "text": "<rewritten child-safe version that still teaches the topic>", "reason": "<brief explanation>"}

Rules for rewriting:
- Keep the same topic and educational value
- Replace graphic details with abstract descriptions
- Remove specific casualty numbers
- Keep the friendly conversational tone
- Do not sanitise so much that the lesson loses meaning

Return ONLY valid JSON. No other text."""

        raw = llm(sys_p, f"Check this lesson:\n\n{text}", tokens=1200)
        try:
            result = json.loads(raw.strip().strip("```json").strip("```").strip())
            if not result.get("safe", True):
                print(f"  [GUARDRAIL-1] Child filter triggered: {result.get('reason','')}")
            return result.get("text", text)
        except Exception:
            return text

    elif age_group == "teen":
        sys_p = """You are a content moderator for educational material for teenagers aged 14-17.

Check this lesson for:
- Extremely graphic descriptions of violence or suffering
- Content that glorifies military action or terrorism
- Inflammatory rhetoric presenting one side as purely evil

If clean: return {"safe": true, "text": "<original text unchanged>"}
If needs adjustment: return {"safe": false, "text": "<adjusted version>"}

Return ONLY valid JSON."""

        raw = llm(sys_p, f"Check this lesson:\n\n{text}", tokens=1200)
        try:
            result = json.loads(raw.strip().strip("```json").strip("```").strip())
            return result.get("text", text)
        except Exception:
            return text

    return text


# ── GUARDRAIL 2: Political neutrality checker ──────────────────────────────────
def neutrality_check(text, subject):
    """
    Checks geopolitics lessons for political bias before sending to browser.
    Rewrites one-sided assertions as attributed perspectives.
    Only runs for the geopolitics subject.
    """
    if subject != "geopolitics":
        return text

    sys_p = """You are a political neutrality auditor for an educational platform.

Review this geopolitics lesson for:
- Language that attributes clear moral guilt to a specific nation, group, or leader
- One-sided framing that presents only one perspective as valid
- Loaded political terms stated as fact rather than as contested claims
- Any content that reads as propaganda for any side

If neutral: return {"neutral": true, "text": "<original text unchanged>", "flags": []}
If biased: return {"neutral": false, "text": "<rewritten neutral version>", "flags": ["list of issues"]}

Rules for rewriting:
- Replace assertions with attributed perspectives: "Israel says X" / "Palestinians argue Y"
- Replace loaded terms with neutral descriptions or attribute them: "what critics call X"
- Keep all factual information — only reframe one-sided assertions
- Keep the lesson educational and engaging

Return ONLY valid JSON. No other text."""

    raw = llm(sys_p, f"Audit this geopolitics lesson:\n\n{text}", tokens=1400)
    try:
        result = json.loads(raw.strip().strip("```json").strip("```").strip())
        flags  = result.get("flags", [])
        if not result.get("neutral", True) and flags:
            print(f"  [GUARDRAIL-2] Neutrality flags: {', '.join(flags)}")
        return result.get("text", text)
    except Exception:
        return text


# ── GUARDRAIL 3: Answer safety monitor ────────────────────────────────────────
def answer_safety(answer, age_group):
    """
    Scans the learner's typed answer for distress signals or hate speech.
    Returns (is_safe, override_message).
    If not safe, override_message replaces normal feedback.
    """
    DISTRESS_PATTERNS = [
        r"\b(kill myself|suicide|want to die|end my life|hurt myself|self harm)\b",
        r"\b(i hate \w+s|all \w+s should die|death to)\b",
        r"\b(nobody cares|no one cares|i am worthless|i am nothing)\b",
    ]
    text_lower = answer.lower()
    for pattern in DISTRESS_PATTERNS:
        if re.search(pattern, text_lower):
            print(f"  [GUARDRAIL-3] Distress pattern detected.")
            return False, "It looks like you might be going through something difficult. That matters more than any lesson. Please talk to someone you trust — a parent, teacher, or counsellor."

    if age_group == "child" and len(answer) > 10:
        sys_p = """You are a child welfare monitor for an educational platform.

A child typed an answer to a quiz question. Check for:
- Signs of distress, fear, or being in danger
- Mentions of being hurt, abused, or threatened
- Self-harm ideation

Return ONLY valid JSON: {"safe": true} or {"safe": false, "reason": "brief reason"}"""

        raw = llm(sys_p, f"Check this child's answer: {answer}", tokens=120)
        try:
            result = json.loads(raw.strip().strip("```json").strip("```").strip())
            if not result.get("safe", True):
                print(f"  [GUARDRAIL-3] Child welfare flag: {result.get('reason','')}")
                return False, "It sounds like something might be wrong. Please talk to a trusted adult — a parent, teacher, or counsellor. You do not have to go through anything alone."
        except Exception:
            pass

    return True, None


# ── ROUTES ─────────────────────────────────────────────────────────────────────

@app.route("/quiz", methods=["POST"])
def quiz():
    """Generate 5 diagnostic questions for a subject + age group."""
    d = request.json
    subject   = d.get("subject", "maths")
    age       = d.get("age", 15)
    age_group = d.get("age_group", "teen")

    sys_p = f"""You are generating a diagnostic quiz for a {age_group} aged {age} studying {subject}.

Generate exactly 5 questions. Rules:
- Start dead simple — something they definitely know if they have ever thought about {subject}
- Gradually increase to questions that require actual reasoning, not just recall
- Questions should feel like a curious friend asking, not an exam paper
- For geopolitics: ask about real current events they have probably heard of
- Never ask "Define the term..." — ask "What do you think..." or "Why do you think..." or "What happens when..."
- Keep each question under 15 words

Return ONLY a valid JSON array of 5 strings. Nothing else.
Example: ["Q1?","Q2?","Q3?","Q4?","Q5?"]"""

    raw = llm(sys_p, f"Generate 5 {subject} questions for age {age}.")
    try:
        qs = json.loads(raw.strip().strip("```json").strip("```").strip())
        if not isinstance(qs, list) or len(qs) != 5:
            raise ValueError
    except Exception:
        qs = [
            f"What do you already know about {subject}?",
            f"Can you name one real example from {subject}?",
            f"What topic in {subject} do you find hardest?",
            f"What have you studied in {subject} recently?",
            f"What excites you most about {subject}?",
        ]
    return jsonify({"questions": qs})


@app.route("/score_quiz", methods=["POST"])
def score_quiz():
    """Score 5 quiz answers and return level."""
    d = request.json
    subject   = d.get("subject", "maths")
    age_group = d.get("age_group", "teen")
    qa_pairs  = d.get("qa_pairs", "")

    sys_p = f"""You are scoring a {age_group} on {subject}.
Score each answer 0-2. Total 0-4=beginner, 5-7=intermediate, 8-10=advanced.
Return ONLY valid JSON with per-answer scores:
{{"scores":[1,2,0,1,2],"total":6,"level":"intermediate","feedback":"One sentence."}}"""

    raw = llm(sys_p, f"Score these:\n{qa_pairs}")
    try:
        result   = json.loads(raw.strip().strip("```json").strip("```").strip())
        level    = result.get("level", "beginner")
        total    = result.get("total", 0)
        feedback = result.get("feedback", "Let's get started.")
        scores   = result.get("scores", [])
        if level not in ["beginner", "intermediate", "advanced"]:
            level = "beginner"
        # Validate scores list
        if not isinstance(scores, list) or len(scores) != 5:
            scores = []
    except Exception:
        level, total, feedback, scores = "beginner", 0, "Let's build from the ground up.", []
    return jsonify({"level": level, "total": total, "feedback": feedback, "scores": scores})


@app.route("/lesson", methods=["POST"])
def lesson():
    """Generate a lesson for a topic through a lens, then run the full guardrail pipeline."""
    d = request.json
    name      = d.get("name", "Learner")
    age       = d.get("age", 15)
    age_group = d.get("age_group", "teen")
    level     = d.get("level", "beginner")
    subject   = d.get("subject", "maths")
    topic     = d.get("topic", "")
    lens      = d.get("lens", "factual")

    lens_instructions = {
        "factual":
            "Present only verified facts. Who, what, when, where. No opinions. Neutral language throughout. If something is disputed say so explicitly.",
        "critical_thinking":
            "Encourage questioning. Who benefits from each narrative? How do different outlets frame this differently? What information might be missing? Guide thinking — do not give verdicts.",
        "humanitarian":
            "Centre the human cost. Civilians affected, displacement, international humanitarian law. Empathy first. Never glorify military action. Behind every statistic is a person.",
    }
    level_instructions = {
        "beginner":
            "Simple everyday language. Short sentences. Relatable analogies from daily life. Define every technical term the moment you use it.",
        "intermediate":
            "Clear language. Some jargon is fine if briefly explained. Assume they have heard of the topic but do not know the detail.",
        "advanced":
            "Full technical and analytical language. Assume solid prior knowledge. Challenge them to think beyond the surface.",
    }

    sys_p = f"""You are GeoMind — not a textbook, not a Wikipedia article. You are a sharp, curious older friend who genuinely loves explaining how the world works.

You are talking to {name}, a {age_group} aged {age}. Their level is {level}.
Topic: "{topic}" — teach it through the {lens} lens.

YOUR VOICE — non-negotiable:
- Start with something that hooks immediately. "Okay so here's the thing about this..." or "Right so this is actually wild —" or "Most people get this completely wrong."
- Use everyday analogies. Connect it to something a {age_group} actually experiences — school, money, social media, family, sports.
- Short punchy sentences. Mix them with longer ones. Never write more than 3 lines without a line break.
- Never say: "it is important to note", "it is worth mentioning", "in conclusion", "furthermore", "this topic encompasses"
- If something is genuinely surprising or messed up — react to it. Have a point of view on how to THINK about it, not what to BELIEVE.
- Stay strictly neutral on who is right or wrong politically. Present perspectives, not verdicts.

LENS — this shapes what you focus on:
{lens_instructions[lens]}

LEVEL — this shapes how you explain:
{level_instructions[level]}

FORMAT — follow exactly, no deviation:
LESSON:
[3-4 paragraphs. Friend voice. Real analogies. Reactions where appropriate.]

QUESTION:
[One question that requires actual thinking — not "what is X" but "why do you think X happens" or "what would change if Y"]"""

    raw = llm(sys_p, f"Teach '{topic}' through the {lens} lens.")

    if "LESSON:" in raw and "QUESTION:" in raw:
        parts    = raw.split("QUESTION:")
        lesson_t = parts[0].replace("LESSON:", "").strip()
        question = parts[1].strip()
    else:
        lesson_t = raw.strip()
        question = f"What is the most important thing you learned about {topic}?"

    # ── Guardrail pipeline ────────────────────────────────────────────────────
    print(f"  [LESSON] {name} | {age_group} | {subject} | {lens} lens | {level}")

    # Guardrail 1 — Age filter
    lesson_t = age_filter(lesson_t, age_group)
    print(f"  [GUARDRAIL-1] Age filter done ({age_group})")

    # Guardrail 2 — Neutrality check (geopolitics only)
    lesson_t = neutrality_check(lesson_t, subject)
    if subject == "geopolitics":
        print(f"  [GUARDRAIL-2] Neutrality check done")

    return jsonify({
        "lesson": lesson_t,
        "question": question,
        "guardrail_applied": True,
        "age_group": age_group,
        "lens": lens,
    })


@app.route("/feedback", methods=["POST"])
def feedback():
    """Score a learner answer — with answer safety check before processing."""
    d = request.json
    level     = d.get("level", "beginner")
    age_group = d.get("age_group", "teen")
    subject   = d.get("subject", "maths")
    topic     = d.get("topic", "")
    question  = d.get("question", "")
    answer    = d.get("answer", "")

    # Guardrail 3 — Answer safety
    is_safe, override = answer_safety(answer, age_group)
    if not is_safe:
        print(f"  [GUARDRAIL-3] Unsafe answer intercepted — returning welfare message")
        return jsonify({"score": 0, "feedback": override, "safety_flag": True})

    sys_p = f"""You are GeoMind — a sharp, honest older friend giving real feedback. Not a teacher. Not a chatbot.

Question asked: {question}
Their answer: {answer}
Topic: {topic} | Level: {level} | Subject: {subject}

Score it:
- 2 = they got it, genuinely
- 1 = right direction but incomplete
- 0 = off the mark

Write ONE line of feedback. Rules:
- Never say "Great effort!", "Good job!", "Don't worry", "That's a great start", "Well done"
- Score 2: be specific about exactly what they got right — "Yes — and the key part you nailed is..."
- Score 1: acknowledge what they got, then push — "You got the what but not the why. Think about..."
- Score 0: be honest but not harsh — "Not quite. Here's the thing most people miss about this..."
- Sound like a person, not an evaluation rubric

Return ONLY valid JSON: {{"score": 1, "feedback": "your one line here"}}"""

    raw = llm(sys_p, f"Score this answer for: {topic}", tokens=256)
    try:
        result       = json.loads(raw.strip().strip("```json").strip("```").strip())
        score        = int(result.get("score", 0))
        feedback_txt = result.get("feedback", "Keep going.")
        if score not in [0, 1, 2]:
            score = 0
    except Exception:
        score, feedback_txt = 0, "Not quite — but every attempt builds understanding."
    return jsonify({"score": score, "feedback": feedback_txt})


if __name__ == "__main__":
    print("\n  GeoMind — Adaptive Learning Engine")
    print("  ─────────────────────────────────────")
    print("  Guardrails active:")
    print("    [1] Age-based content filter    (child / teen / adult)")
    print("    [2] Political neutrality checker (geopolitics only)")
    print("    [3] Answer safety monitor        (distress + hate speech)")
    print("  ─────────────────────────────────────")
    print("  Open index.html in your browser.\n")
    app.run(port=5000, debug=False)
