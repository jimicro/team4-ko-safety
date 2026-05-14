"""Pilot experiments BEFORE the main 600-round sweep.

1) Turn-budget sweep:  5 / 10 / 15 turns × 30 rounds (10 per category) → which
                       max_turns gives the most informative ASR/breakthrough
                       distribution?
2) Single-turn baseline: same 30 seeds sent as 1-turn → ASR vs multi-turn.

Results: results/pilot_turn_sweep.jsonl, results/pilot_singleturn.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm

from agents.aggregator import load_recent_feedback
from agents.evaluator import _parse_json
from agents.llm import ATTACKER_FN, DEFENDER_FN, EVALUATOR_FN
from agents.prompts import DEFAULT_DEFENDER_MODE, DEFENDER_VARIANTS, TURN_EVALUATOR_SYSTEM
from graph import build_graph

load_dotenv()

SEEDS_PATH = Path("data/seeds.json")
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def _pilot_seeds() -> list[dict]:
    """10 seeds per category — the human-written ones, deterministic order."""
    seeds = json.loads(SEEDS_PATH.read_text(encoding="utf-8"))
    return [s for s in seeds if s["origin"] == "seed"]


def run_turn_sweep(experiment: str = "A", turn_budgets=(3, 6, 9),
                   defender_mode: str = DEFAULT_DEFENDER_MODE) -> None:
    """Sweep around the chosen 2:2:2 = 6-turn main-experiment setting (half/×1/×1.5)."""
    graph = build_graph()
    suffix = "" if defender_mode == "vanilla" else f"_{defender_mode}"
    out_path = RESULTS_DIR / f"pilot_turn_sweep_{experiment}{suffix}.jsonl"
    seeds = _pilot_seeds()

    with out_path.open("a", encoding="utf-8") as f:
        for max_turns in turn_budgets:
            for seed in tqdm(seeds, desc=f"max_turns={max_turns}/{defender_mode}"):
                init = {
                    "round_id": seed["id"],
                    "experiment": experiment,
                    "category": seed["category"],
                    "origin": "seed",
                    "seed_id": seed["id"],
                    "seed_prompt": seed["prompt"],
                    "target_content": seed.get("target_content", seed["prompt"]),
                    "domain": seed.get("domain", ""),
                    "defender_mode": defender_mode,
                    "current_turn": 1,
                    "max_turns": max_turns,
                    "conversation_history": [],
                    "total_api_calls": 0,
                    "prev_feedback": load_recent_feedback(experiment, seed["category"]),
                }
                try:
                    result = graph.invoke(init, {"recursion_limit": max_turns * 3 + 20})
                except Exception as e:
                    result = {**init, "error": f"{type(e).__name__}: {e}"}
                result["pilot_max_turns"] = max_turns
                result["ts"] = datetime.utcnow().isoformat() + "Z"
                f.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
                f.flush()


def run_single_turn(experiment: str = "A", defender_mode: str = DEFAULT_DEFENDER_MODE) -> None:
    """Send the seed as a single prompt, judge with Claude. No Attacker, no
    multi-turn buildup. This is the dead-simple baseline.
    """
    suffix = "" if defender_mode == "vanilla" else f"_{defender_mode}"
    out_path = RESULTS_DIR / f"pilot_singleturn_{experiment}{suffix}.jsonl"
    seeds = _pilot_seeds()
    defender = DEFENDER_FN[experiment]
    defender_system = DEFENDER_VARIANTS[defender_mode]

    with out_path.open("a", encoding="utf-8") as f:
        for seed in tqdm(seeds, desc=f"singleturn/{experiment}/{defender_mode}"):
            try:
                defense = defender(
                    defender_system,
                    [{"role": "user", "content": seed["prompt"]}],
                    temperature=0.4,
                )
            except Exception as e:
                defense = f"[ERROR: {type(e).__name__}: {e}]"

            judge_sys = TURN_EVALUATOR_SYSTEM.format(
                target_content=seed.get("target_content", seed["prompt"]),
                attack=seed["prompt"],
                defense=defense,
                history_summary="(싱글턴)",
            )
            try:
                raw = EVALUATOR_FN(judge_sys, [{"role": "user", "content": "판정해줘."}], temperature=0.0)
                parsed = _parse_json(raw)
            except Exception as e:
                parsed = {"판정": "계속", "이유": f"[ERROR: {e}]"}

            rec = {
                "experiment": experiment,
                "defender_mode": defender_mode,
                "seed_id": seed["id"],
                "category": seed["category"],
                "seed_prompt": seed["prompt"],
                "defense": defense,
                "판정": parsed.get("판정"),
                "이유": parsed.get("이유"),
                "ts": datetime.utcnow().isoformat() + "Z",
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", default="A", choices=["A", "B"])
    ap.add_argument("--mode", default="both", choices=["sweep", "single", "both"])
    ap.add_argument("--defender-mode", choices=list(DEFENDER_VARIANTS.keys()),
                    default=DEFAULT_DEFENDER_MODE,
                    help="Defender 프롬프트 변형 (기본 vanilla. aware = ablation 비교용)")
    args = ap.parse_args()

    required = ["OPENAI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"Missing env vars: {missing}", file=sys.stderr)
        sys.exit(1)

    if args.mode in ("sweep", "both"):
        run_turn_sweep(args.experiment, defender_mode=args.defender_mode)
    if args.mode in ("single", "both"):
        run_single_turn(args.experiment, defender_mode=args.defender_mode)


if __name__ == "__main__":
    main()
