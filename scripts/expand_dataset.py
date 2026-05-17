"""Expand the human-written seed dataset into a supplementary prompt set.

시드 (seed) = 사람이 직접 작성한 핵심 30개 (data/seeds.json).
확장 프롬프트 (expanded prompts) = 시드를 few-shot 예시로 받아 Claude 가 자동 생성한
보충 데이터 (카테고리당 90개 × 3 = 270개). data/expanded_prompts.json 에 저장.

본 실험에서 두 데이터셋은 분리 보고되며, 시드만으로 라운드를 돌리는 모드도 지원된다.

    python scripts/expand_dataset.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from agents.llm import call_claude
from agents.prompts import CATEGORY_STRATEGY, EXPANSION_PROMPT_SYSTEM

load_dotenv()

SEEDS_PATH = Path("data/seeds.json")
OUT_PATH = Path("data/expanded_prompts.json")
PER_CATEGORY_TARGET = 90
OVERGEN = 110  # over-generate then dedupe


def _parse_array(text: str) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\[[\s\S]*\]", text)
        if not m:
            return []
        data = json.loads(m.group(0))
    return data if isinstance(data, list) else []


def main() -> None:
    seeds = json.loads(SEEDS_PATH.read_text(encoding="utf-8"))
    by_cat: dict[str, list[dict]] = {}
    for s in seeds:
        by_cat.setdefault(s["category"], []).append(s)

    out: list[dict] = []
    next_id = max(s["id"] for s in seeds) + 1

    for category, human in by_cat.items():
        if category not in CATEGORY_STRATEGY:
            continue
        system = EXPANSION_PROMPT_SYSTEM.format(
            n=OVERGEN,
            category=category,
            category_strategy=CATEGORY_STRATEGY[category],
            human_seeds=json.dumps(
                [{"target_content": h["target_content"], "prompt": h["prompt"], "domain": h.get("domain", "")} for h in human],
                ensure_ascii=False,
                indent=2,
            ),
        )
        print(f"→ generating ~{OVERGEN} expanded prompts for category={category} ...")
        raw = call_claude(system, [{"role": "user", "content": f"카테고리 '{category}' 확장 프롬프트 {OVERGEN}개 생성."}], temperature=1.0)
        items = _parse_array(raw)

        # Deduplicate by normalized prompt; keep diverse domains.
        seen, picked = set(), []
        for it in items:
            key = re.sub(r"\s+", "", (it.get("prompt") or ""))[:60]
            if not key or key in seen:
                continue
            seen.add(key)
            picked.append({
                "id": next_id,
                "category": category,
                "origin": "expanded",
                "target_content": it.get("target_content", ""),
                "prompt": it.get("prompt", ""),
                "domain": it.get("domain", ""),
            })
            next_id += 1
            if len(picked) >= PER_CATEGORY_TARGET:
                break
        print(f"   kept {len(picked)} / requested {PER_CATEGORY_TARGET}")
        out.extend(picked)

    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ wrote {len(out)} expanded prompts → {OUT_PATH}")


if __name__ == "__main__":
    main()
