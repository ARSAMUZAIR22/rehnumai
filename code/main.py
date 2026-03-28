from graph import build_graph
from state import initial_state


def main():
    # Build the LangGraph pipeline
    app = build_graph()

    # Start with a blank state
    state = initial_state()

    # Run the full pipeline — LangGraph handles all routing automatically
    final_state = app.invoke(state)

    # Optional: print full message log at the end
    print("\n── Session Log ──────────────────────────────────────────")
    for msg in final_state.get("messages", []):
        print(f"  {msg}")
    print("─────────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    main()
