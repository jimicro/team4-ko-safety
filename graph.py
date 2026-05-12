"""LangGraph wiring for one adversarial round.

START → attacker → defender → turn_eval ──(loop or end)──→ final_eval → aggregator → END
                                              │
                                              ├─ defense_failed       → final_eval
                                              ├─ current_turn > max   → final_eval
                                              └─ else                 → attacker
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents.aggregator import aggregator_node
from agents.attacker import attacker_node
from agents.defender import defender_node
from agents.evaluator import final_evaluator_node, turn_evaluator_node
from state import State


def _route_after_turn(state: State) -> str:
    if state.get("defense_failed"):
        return "final_evaluator"
    if state.get("current_turn", 1) > state.get("max_turns", 10):
        return "final_evaluator"
    return "attacker"


def build_graph():
    g = StateGraph(State)
    g.add_node("attacker", attacker_node)
    g.add_node("defender", defender_node)
    g.add_node("turn_evaluator", turn_evaluator_node)
    g.add_node("final_evaluator", final_evaluator_node)
    g.add_node("aggregator", aggregator_node)

    g.add_edge(START, "attacker")
    g.add_edge("attacker", "defender")
    g.add_edge("defender", "turn_evaluator")
    g.add_conditional_edges(
        "turn_evaluator",
        _route_after_turn,
        {"attacker": "attacker", "final_evaluator": "final_evaluator"},
    )
    g.add_edge("final_evaluator", "aggregator")
    g.add_edge("aggregator", END)

    # The recursion limit must comfortably exceed:
    #   max_turns × (attacker + defender + turn_eval) + final + aggregator
    # For max_turns=10 that's 10*3 + 2 = 32 node hops.
    return g.compile()
