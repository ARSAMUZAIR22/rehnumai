# Rehnumai — Adaptive Curriculum Engine

**Team:** Arsam,Shaheer,Shanza  
**Theme & Challenge:** Theme 2 — Education & Skill Development | Hard Tier  
**Hackathon:** AI Mustaqbil 2.0 — Multi-Agentic Systems Hackathon  
**Date:** March 27–28, 2026 | NASTP Karachi

---

## The Problem

Every student learns differently — but most educational tools treat all students the same. Same content, same language, same difficulty, regardless of whether the learner is 9 or 19, a complete beginner or already advanced.

Rehnumai fixes that. It is a multi-agent adaptive curriculum engine that diagnoses each learner, builds a personalised study plan, teaches through rotating pedagogical lenses, and continuously adjusts based on how the learner performs.

---

## What It Is

Rehnumai teaches three subjects: **Maths, Science, and Geopolitics**. Each session is personalised to the learner's age, knowledge level, and rotates through three pedagogical lenses:

| Lens | What it does |
|------|-------------|
| Lens 1 — Neutral & Factual | Who, what, when, where. Foundations first. |
| Lens 2 — Critical Thinking | Why does this happen? What are the different perspectives? |
| Lens 3 — Humanitarian | What is the human impact? Why does this matter to people? |

The same system. The same agents. Completely different experience depending on who is learning.

---

## Why Multi-Agent?

A single LLM call cannot simultaneously be an assessor, a curriculum planner, a teacher, and a progress tracker without confusing its own role. Each agent has a focused responsibility, clear inputs, and measurable outputs.

The feedback loop — where the progress agent detects a level change and re-routes back to the curriculum agent — requires stateful, conditional routing that a linear script cannot handle. That is why LangGraph exists in this system.

---

## Agent Architecture

| Agent | Role | Key decision |
|-------|------|-------------|
| **Assessment agent** | Asks 5 diagnostic questions, scores answers, sets level and age group | Determines beginner / intermediate / advanced |
| **Curriculum agent** | Pulls topic bank for subject + level, sequences topics, assigns lens rotation | Builds personalised 3-topic study plan |
| **Teaching agent** | Delivers lesson through the active lens at the right vocabulary level | Generates lesson + check question dynamically |
| **Progress agent** | Scores the learner's answer, decides level change, routes next step | Triggers adaptation loop or advances to next topic |

### The adaptation loop

```
assess → plan → teach → evaluate
                  ↑         |
                  |— plan ←—|  (level changed — rebuild curriculum)
                  |— teach ←|  (next topic, same level)
                  └── END ←——  (all 3 topics complete)
```

All agents read from and write to a single shared typed state object — `GeoMindState`. No agent passes data directly to another. LangGraph reads the `next_step` field after each agent runs and routes accordingly.

---

## Subjects & Topic Banks

### Maths
| Level | Topics |
|-------|--------|
| Beginner | Addition & subtraction · Fractions · Basic geometry |
| Intermediate | Algebra fundamentals · Ratio & proportion · Statistics |
| Advanced | Quadratic equations · Trigonometry · Probability theory |

### Science
| Level | Topics |
|-------|--------|
| Beginner | Scientific method · Cells · Forces & motion |
| Intermediate | Photosynthesis · Periodic table · Electricity & circuits |
| Advanced | Genetics & DNA · Chemical reactions · Quantum mechanics |

### Geopolitics
| Level | Topics |
|-------|--------|
| Beginner | What is a war · Russia-Ukraine overview · Gaza overview |
| Intermediate | Russia-Ukraine — causes & NATO · Israel-Gaza history · Iran-Israel-US triangle |
| Advanced | Ukraine — energy & sovereignty · Palestine — international law · Iran escalation — nuclear diplomacy |

---

## Responsible AI & Safety

Three active guardrails run on every request — enforced in code, not just in prompts.

### Guardrail 1 — Age-based content filter
- **Children under 14:** Full LLM-powered review. Graphic or inappropriate content is detected and rewritten into age-safe equivalents.
- **Teens 14–17:** Lighter pass. Strips extreme graphic content.
- **Adults 18+:** No filtering.

### Guardrail 2 — Political neutrality checker
Every geopolitics lesson passes through a neutrality audit. Loaded political terms stated as fact are rewritten as attributed perspectives. Flags are logged to the server console in real time.

### Guardrail 3 — Answer safety monitor
Every learner answer is scanned before processing. Regex catches distress patterns immediately. For children, a second LLM call checks for subtler welfare signals. If either fires, a care message is shown instead of normal feedback.

---

## Tech Stack

| Tool | Role | Why |
|------|------|-----|
| Python | Language | Native home of every AI library. |
| LangGraph | Orchestration | Stateful graph routing. The adaptation loop requires conditional re-routing a linear script cannot do. |
| Groq API (Llama 3.3 70B) | LLM | Free tier, fast inference, strong reasoning. |
| Flask + Flask-CORS | API server | Bridges the HTML frontend to the LLM pipeline. |
| python-dotenv | Secrets | API key stays out of source code. |
| Vanilla HTML/CSS/JS | Frontend | Retro terminal aesthetic. Runs in any browser without a build step. |

---

## Project Structure

```
code/
├── index.html           ← Frontend — open this in browser
├── server.py            ← Flask server with all guardrails — run this first
├── main.py              ← CLI entry point (backup)
├── graph.py             ← LangGraph pipeline wiring
├── state.py             ← Shared typed state
├── utils.py             ← Groq API client
├── agents/
│   ├── assessment.py    ← Agent 1 — diagnoses learner level and age group
│   ├── curriculum.py    ← Agent 2 — builds personalised study plan
│   ├── teaching.py      ← Agent 3 — delivers lessons through active lens
│   └── progress.py      ← Agent 4 — scores answers and routes next step
├── requirements.txt
├── .env.example
└── README.md
```

---

## How to Run

### 1. Clone the repository
```bash
git clone https://github.com/your-username/rehnumai
cd code
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up your API key
```bash
cp .env.example .env
```
Open `.env` and paste your Groq API key from [console.groq.com](https://console.groq.com).

### 4. Start the server
```bash
python server.py
```

### 5. Open the frontend
```bash
xdg-open index.html   # Linux
open index.html        # Mac
```

---

