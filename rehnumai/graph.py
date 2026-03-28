from langgraph.graph import StateGraph, END
from state import GeoMindState
from agents.assessment import assessment_agent
from agents.curriculum  import curriculum_agent
from agents.teaching    import teaching_agent
from agents.progress    import progress_agent


def route(state: GeoMindState) -> str:
    """
    Router function — reads next_step from state and tells
    LangGraph which node to run next.
    """
    return state.get("next_step", "end")


def build_graph():
    """
    Builds and compiles the GeoMind LangGraph pipeline.

    Nodes:
        assess   → assessment_agent
        plan     → curriculum_agent
        teach    → teaching_agent
        evaluate → progress_agent

    Edges:
        assess   → plan   (always)
        plan     → teach  (always)
        teach    → evaluate (always)
        evaluate → teach  (next topic, same level)
                 → plan   (level changed — re-plan)
                 → END    (all topics done)
    """
    graph = StateGraph(GeoMindState)

    # ── Register nodes ───────────────────────────────────────────────────────
    graph.add_node("assess",   assessment_agent)
    graph.add_node("plan",     curriculum_agent)
    graph.add_node("teach",    teaching_agent)
    graph.add_node("evaluate", progress_agent)

    # ── Set entry point ──────────────────────────────────────────────────────
    graph.set_entry_point("assess")

    # ── Fixed edges ──────────────────────────────────────────────────────────
    graph.add_edge("assess", "plan")
    graph.add_edge("plan",   "teach")
    graph.add_edge("teach",  "evaluate")

    # ── Conditional edge from evaluate ───────────────────────────────────────
    # This is the adaptation loop — progress agent sets next_step in state
    graph.add_conditional_edges(
        "evaluate",
        route,
        {
            "teach": "teach",   # next topic, level unchanged
            "plan":  "plan",    # level changed — rebuild curriculum
            "end":   END,       # session complete
        }
    )

    return graph.compile()
