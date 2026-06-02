"""Expand the human-written seed dataset by varying each seed individually.

시드 (seed) = 사람이 직접 작성한 핵심 30개 (data/seeds.json).
확장 프롬프트 (expanded prompts) = 시드를 *하나씩* 던지고 같은 의도의 변형을
N개 만들어 모은 보충 데이터.

[방식] 시드 10개를 한꺼번에 주면 모델이 비슷한 것만 내놓아 다양성이 고갈된다.
대신 시드 1개에 집중시켜 그 시드의 수법·도메인을 깊게 변주한다.
  카테고리당 시드 10개 × {PER_SEED} 변형 = 150개 과생성 (raw)
  → 나중에 선별/중복제거해서 expanded_prompts.json 으로 합친다.

[출력] 카테고리별 raw 파일:
  data/expanded_prompts_raw_hierarchy.json
  data/expanded_prompts_raw_irony.json
  data/expanded_prompts_raw_code_switching.json

    python scripts/expand_dataset.py                      # 세 카테고리 모두
    python scripts/expand_dataset.py --category irony     # 한 카테고리만
    python scripts/expand_dataset.py --category irony --per-seed 15
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from agents.llm import call_claude
from agents.prompts import CATEGORY_STRATEGY, SEED_VARIATION_SYSTEM

load_dotenv()

SEEDS_PATH = Path("data/seeds.json")
OUT_PATH = Path("data/expanded_prompts.json")
DATA_DIR = Path("data")
PER_SEED_DEFAULT = 15  # 시드 1개당 만들 변형 수 (과생성 → 나중에 선별)
CATEGORIES = ("hierarchy", "irony", "code_switching")

# CLI 에서 --category 1/2/3 또는 이름으로 지정 가능.
CATEGORY_BY_NUM = {"1": "hierarchy", "2": "irony", "3": "code_switching"}


def _resolve_category(value: str) -> str:
    """'1' / '2' / '3' 또는 카테고리 이름을 정식 이름으로 변환."""
    if value in CATEGORY_BY_NUM:
        return CATEGORY_BY_NUM[value]
    if value in CATEGORIES:
        return value
    raise SystemExit(f"--category 는 1/2/3 또는 {CATEGORIES} 중 하나. 받은 값: {value}")


def _parse_array(text: str) -> list[dict]:
    """JSON 배열 파싱. 잘린 응답이면 완전한 객체만 복구한다."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE)
    # 1) 정상 배열
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    # 2) 배열 슬라이스 재시도
    m = re.search(r"\[[\s\S]*\]", text)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
    # 3) 잘린 JSON — 완전한 객체 {...} 만 개별 파싱
    objs: list[dict] = []
    for om in re.finditer(r"\{[^{}]*\}", text):
        try:
            obj = json.loads(om.group(0))
            if isinstance(obj, dict):
                objs.append(obj)
        except json.JSONDecodeError:
            continue
    return objs


def _vary_one_seed(seed: dict, per_seed: int, next_id: int) -> list[dict]:
    """시드 1개를 받아 변형 per_seed 개를 생성."""
    category = seed["category"]
    system = SEED_VARIATION_SYSTEM.format(
        n=per_seed,
        category=category,
        category_strategy=CATEGORY_STRATEGY[category],
        target_content=seed.get("target_content", ""),
        seed_prompt=seed.get("prompt", ""),
        domain=seed.get("domain", ""),
    )
    raw = call_claude(
        system,
        [{"role": "user", "content": f"원본 시드 기준 변형 {per_seed}개 생성."}],
        temperature=1.0,
        max_tokens=4096,
    )
    items = _parse_array(raw)

    picked: list[dict] = []
    seen: set[str] = set()
    for it in items:
        prompt = (it.get("prompt") or "").strip()
        key = re.sub(r"\s+", "", prompt)[:60]
        if not key or key in seen:
            continue
        seen.add(key)
        picked.append({
            "id": next_id + len(picked),
            "category": category,
            "origin": "expanded",
            "parent_seed_id": seed.get("id"),
            "target_content": it.get("target_content", ""),
            "prompt": prompt,
            "domain": it.get("domain", seed.get("domain", "")),
        })
    return picked


def expand_category(category: str, seeds: list[dict], per_seed: int, next_id: int) -> int:
    """한 카테고리의 시드들을 변형해 raw 파일로 저장. 다음 id 반환."""
    human = [s for s in seeds if s["category"] == category]
    out: list[dict] = []
    for seed in human:
        print(f"[gen] category={category} seed_id={seed.get('id')} domain={seed.get('domain')}")
        variations = _vary_one_seed(seed, per_seed, next_id)
        next_id += len(variations)
        out.extend(variations)
        print(f"      -> {len(variations)} variations")

    out_path = DATA_DIR / f"expanded_prompts_raw_{category}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] category={category}: wrote {len(out)} raw prompts -> {out_path}")
    return next_id


def _word_set(text: str) -> set[str]:
    return set(re.findall(r"[가-힣A-Za-z]+", text))


def _select_from_seed(variations: list[dict], k: int) -> list[dict]:
    """한 시드의 변형들 중 서로 가장 안 겹치는 k개를 greedy 로 고른다.

    첫 항목은 가장 긴 발화(보통 정보량↑)를, 이후는 이미 고른 것들과 단어
    중복(Jaccard)이 가장 낮은 것을 차례로 추가한다 → 다양성 우선 선별.
    """
    if len(variations) <= k:
        return variations
    pool = sorted(variations, key=lambda v: -len(v.get("prompt", "")))
    chosen = [pool.pop(0)]
    chosen_sets = [_word_set(chosen[0].get("prompt", ""))]
    while pool and len(chosen) < k:
        best_i, best_score = 0, 2.0
        for i, cand in enumerate(pool):
            cs = _word_set(cand.get("prompt", ""))
            # 이미 고른 것들과의 최대 유사도 (낮을수록 다양)
            sim = max(
                (len(cs & s) / len(cs | s) if (cs | s) else 0.0)
                for s in chosen_sets
            )
            if sim < best_score:
                best_score, best_i = sim, i
        pick = pool.pop(best_i)
        chosen.append(pick)
        chosen_sets.append(_word_set(pick.get("prompt", "")))
    return chosen


def merge_and_select(per_seed: int) -> None:
    """raw 파일들을 읽어 시드별 per_seed 개씩 선별 → expanded_prompts.json."""
    merged: list[dict] = []
    next_id = 1000  # 사람 시드 id 와 절대 안 겹치게 1000번대 부여
    for cat in CATEGORIES:
        raw_path = DATA_DIR / f"expanded_prompts_raw_{cat}.json"
        if not raw_path.exists():
            print(f"[skip] {raw_path} 없음 — {cat} 건너뜀")
            continue
        rows = json.loads(raw_path.read_text(encoding="utf-8"))
        by_seed: dict[int, list[dict]] = {}
        for r in rows:
            by_seed.setdefault(r.get("parent_seed_id"), []).append(r)
        cat_count = 0
        for seed_id in sorted(by_seed):
            picked = _select_from_seed(by_seed[seed_id], per_seed)
            for p in picked:
                p["id"] = next_id
                next_id += 1
                merged.append(p)
                cat_count += 1
        print(f"[select] {cat}: {cat_count} prompts ({len(by_seed)} seeds x ~{per_seed})")

    OUT_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] merged {len(merged)} prompts -> {OUT_PATH}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--category",
                    help="한 카테고리만 생성. 1/2/3 또는 "
                         "hierarchy/irony/code_switching (생략 시 세 카테고리 모두). "
                         "다시 돌리면 해당 raw 파일을 덮어쓴다.")
    ap.add_argument("--per-seed", type=int, default=PER_SEED_DEFAULT,
                    help=f"생성 시 시드 1개당 변형 수 (기본 {PER_SEED_DEFAULT}, 과생성).")
    ap.add_argument("--merge", action="store_true",
                    help="생성하지 않고, 기존 raw 파일 3개를 선별·합쳐 "
                         "expanded_prompts.json 만 만든다 (비용 0).")
    ap.add_argument("--select-per-seed", type=int, default=9,
                    help="합칠 때 시드 1개당 채택 수 (기본 9 → 카테고리당 90).")
    args = ap.parse_args()

    # --merge 단독: 선별·합치기만 (API 호출 없음)
    if args.merge:
        merge_and_select(args.select_per_seed)
        return

    seeds = json.loads(SEEDS_PATH.read_text(encoding="utf-8"))
    next_id = max(s["id"] for s in seeds) + 1
    if args.category:
        targets = [_resolve_category(args.category)]
    else:
        targets = list(CATEGORIES)
    for cat in targets:
        next_id = expand_category(cat, seeds, args.per_seed, next_id)

    # 카테고리 지정 없이 전체 생성한 경우, 이어서 자동 선별·합치기
    if not args.category:
        merge_and_select(args.select_per_seed)


if __name__ == "__main__":
    main()
