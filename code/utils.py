import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# One shared Groq client — all agents import this
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Llama 3.3 70B — best free model on Groq for reasoning tasks
MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 1024


def call_llm(system_prompt: str, user_message: str) -> str:
    """
    Makes a single call to the Groq API.
    Every agent uses this — keeps all API logic in one place.

    Args:
        system_prompt: Defines the agent's role and behaviour
        user_message:  The specific instruction for this call

    Returns:
        The model's response as a plain string
    """
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message}
        ]
    )
    return response.choices[0].message.content.strip()


def print_divider(label: str = ""):
    """Prints a clean CLI divider with an optional label."""
    width = 60
    if label:
        pad = (width - len(label) - 2) // 2
        print(f"\n{'─' * pad} {label} {'─' * pad}\n")
    else:
        print(f"\n{'─' * width}\n")
