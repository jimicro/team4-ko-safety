"""Run the full 600-round adversarial sweep (or just the 100-round normal set).

    python orchestrator.py --experiment A
    python orchestrator.py --experiment B
    python orchestrator.py --normal --experiment A
    python orchestrator.py --normal --experiment B

Each round writes one JSON line to results/runs/<experiment>_<category>.jsonl.
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
from agents.defender import defender_node
from agents.llm import DEFENDER_FN
from agents.prompts import DEFAULT_DEFENDER_MODE, DEFENDER_VARIANTS
from graph import build_graph

load_dotenv()

SEEDS_PATH = Path("data/seeds.json")              # 사람 작성 핵심 30개
NORMAL_PATH = Path("data/normal_prompts.json")
EXPANDED_PROMPTS_PATH = Path("data/expanded_prompts.json")  # produced by scripts/expand_dataset.py
RUNS_DIR = Path("results/runs")
RUNS_DIR.mkdir(parents=True, exist_ok=True)

ROUNDS_PER_CATEGORY = 100
MAX_TURNS = 6  # 2:2:2 phase split (신뢰 구축 / 경계 탐색 / 본격 공격)
CATEGORIES = ("hierarchy", "irony", "code_switching")


def _load_prompt_pool() -> list[dict]:
    """시드 (사람 작성) + 확장 프롬프트 (Claude 자동 생성, 있을 때만) 통합."""
    pool = json.loads(SEEDS_PATH.read_text(encoding="utf-8"))
    if EXPANDED_PROMPTS_PATH.exists():
        pool += json.loads(EXPANDED_PROMPTS_PATH.read_text(encoding="utf-8"))
    return pool


def _prompts_for(category: str, n: int) -> list[dict]:
    cat_pool = [s for s in _load_prompt_pool() if s["category"] == category]
    if len(cat_pool) < n:
        print(
            f"⚠ category={category} has only {len(cat_pool)} prompts "
            f"(need {n}). Run scripts/expand_dataset.py first.",
            file=sys.stderr,
        )
    return cat_pool[:n]


def _run_one_round(graph, init: dict) -> dict:
    return graph.invoke(init, {"recursion_limit": 60})


def run_adversarial(experiment: str, defender_mode: str = "vanilla") -> None:
    graph = build_graph()
    # 결과 파일명에 defender_mode 포함 → vanilla/aware 모두 같은 폴더에 공존 가능
    suffix = "" if defender_mode == "vanilla" else f"_{defender_mode}"
    for category in CATEGORIES:
        out_path = RUNS_DIR / f"{experiment}_{category}{suffix}.jsonl"
        prompts = _prompts_for(category, ROUNDS_PER_CATEGORY)

        with out_path.open("a", encoding="utf-8") as f:
            for i, item in enumerate(tqdm(prompts, desc=f"{experiment}/{category}/{defender_mode}")):
                round_id = i + 1
                init = {
                    "round_id": round_id,
                    "experiment": experiment,
                    "category": category,
                    "origin": item.get("origin", "expanded"),
                    "seed_id": item.get("id", i),
                    "seed_prompt": item["prompt"],
                    "target_content": item.get("target_content", item["prompt"]),
                    "domain": item.get("domain", ""),
                    "defender_mode": defender_mode,
                    "current_turn": 1,
                    "max_turns": MAX_TURNS,
                    "conversation_history": [],
                    "total_api_calls": 0,
                    "prev_feedback": load_recent_feedback(experiment, category),
                }
                try:
                    result = _run_one_round(graph, init)
                except Exception as e:
                    result = {**init, "error": f"{type(e).__name__}: {e}"}
                result["ts"] = datetime.utcnow().isoformat() + "Z"
                f.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
                f.flush()


def run_normal(experiment: str, defender_mode: str = "vanilla") -> None:
    """FPR test — Defender alone faces normal prompts.

    No multi-turn, no Attacker, no Evaluator JSON judgment: we just record the
    Defender's reply and a coarse refused/answered tag (analysis.py refines).
    """
    suffix = "" if defender_mode == "vanilla" else f"_{defender_mode}"
    out_path = RUNS_DIR / f"{experiment}_normal{suffix}.jsonl"
    prompts = json.loads(NORMAL_PATH.read_text(encoding="utf-8"))
    fn = DEFENDER_FN[experiment]
    system = DEFENDER_VARIANTS[defender_mode]

    with out_path.open("a", encoding="utf-8") as f:
        for p in tqdm(prompts, desc=f"{experiment}/normal/{defender_mode}"):
            try:
                reply = fn(system, [{"role": "user", "content": p["prompt"]}], temperature=0.4)
            except Exception as e:
                reply = f"[ERROR: {type(e).__name__}: {e}]"
            rec = {
                "experiment": experiment,
                "defender_mode": defender_mode,
                "prompt_id": p["id"],
                "domain": p.get("domain", ""),
                "prompt": p["prompt"],
                "defense": reply,
                "ts": datetime.utcnow().isoformat() + "Z",
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", choices=["A", "B"], required=True)
    ap.add_argument("--normal", action="store_true", help="run the 50-prompt over-refusal test instead")
    ap.add_argument("--defender-mode", choices=list(DEFENDER_VARIANTS.keys()),
                    default=DEFAULT_DEFENDER_MODE,
                    help="Defender 프롬프트 변형 (기본 vanilla — 본 실험 객관적 측정용. "
                         "aware = 우리 카테고리 인지, ablation 비교용. "
                         "결과는 results/runs/{exp}_{cat}[_mode].jsonl 로 분리 저장)")
    args = ap.parse_args()

    required = ["OPENAI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"Missing env vars: {missing}. Copy .env.example to .env and fill in.", file=sys.stderr)
        sys.exit(1)

    if args.normal:
        run_normal(args.experiment, args.defender_mode)
    else:
        run_adversarial(args.experiment, args.defender_mode)


if __name__ == "__main__":
    main()
