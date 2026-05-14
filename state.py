"""Shared LangGraph State for the 3-Agent pipeline.

Flow per turn:
    attacker_node  → writes pending_attack
    defender_node  → writes pending_defense
    turn_eval_node → judges, then appends ONE completed Turn dict to
                     conversation_history (the only writer of that list)
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional, TypedDict

Category = Literal["hierarchy", "irony", "code_switching", "normal"]
Origin = Literal["seed", "ai_generated", "normal"]
Experiment = Literal["A", "B"]
TurnJudgment = Literal["계속", "실패"]
DefenderMode = Literal["vanilla", "safe", "aware"]


class Turn(TypedDict, total=False):
    turn: int
    attack: str
    defense: str
    turn_judgment: TurnJudgment
    turn_judgment_reason: str


class FinalResult(TypedDict, total=False):
    판정: Literal["방어 성공", "방어 실패"]
    돌파_턴: Optional[int]
    조기탐지: bool
    근거: str
    위험도: int  # 1..5
    카테고리_분석: str
    피드백: str


def _append(a: list, b: list) -> list:
    """LangGraph reducer — extend rather than replace."""
    return (a or []) + (b or [])


class State(TypedDict, total=False):
    # ── Round metadata ─────────────────────────────────────────────
    round_id: int
    experiment: Experiment
    category: Category
    origin: Origin
    seed_id: int
    seed_prompt: str          # attack goal (NOT sent verbatim to Defender)
    target_content: str       # the harmful info we want Defender to refuse
    domain: str
    defender_mode: DefenderMode  # which Defender prompt variant is active

    # ── Turn control ───────────────────────────────────────────────
    current_turn: int
    max_turns: int

    # ── Per-turn scratch (overwritten each turn) ───────────────────
    pending_attack: str
    pending_defense: str

    # ── Conversation history (Turn Evaluator is the only writer) ──
    conversation_history: Annotated[list[Turn], _append]

    # ── Termination ────────────────────────────────────────────────
    defense_failed: bool
    failed_at_turn: Optional[int]

    # ── Final judgment ─────────────────────────────────────────────
    final_result: FinalResult

    # ── Feedback loop (from previous round Aggregator) ─────────────
    prev_feedback: str

    # ── Bookkeeping ────────────────────────────────────────────────
    total_api_calls: int
