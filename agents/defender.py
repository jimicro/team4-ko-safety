"""Defender node — responds to the user as a safe assistant."""
from __future__ import annotations

from state import State
from .llm import DEFENDER_FN
from .prompts import DEFENDER_SYSTEM


def _history_as_messages(state: State) -> list[dict]:
    """Defender sees a normal chat: user = Attacker's messages, assistant = its
    own past replies. It is *not* told about seed/target_content.
    """
    msgs: list[dict] = []
    for t in state.get("conversation_history", []):
        if t.get("attack"):
            msgs.append({"role": "user", "content": t["attack"]})
        if t.get("defense"):
            msgs.append({"role": "assistant", "content": t["defense"]})

    # This turn's attack hasn't been written to history yet.
    pending = state.get("pending_attack", "")
    if pending:
        msgs.append({"role": "user", "content": pending})
    return msgs


def defender_node(state: State) -> dict:
    fn = DEFENDER_FN[state["experiment"]]
    defense = fn(DEFENDER_SYSTEM, _history_as_messages(state), temperature=0.4).strip()
    return {
        "pending_defense": defense,
        "total_api_calls": state.get("total_api_calls", 0) + 1,
    }
