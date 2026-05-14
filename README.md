# 3-Agent 상호작용을 통한 한국어 AI 안전성 자동 검증 시스템

[![License: MIT (code)](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)
[![Data: CC BY-NC 4.0](https://img.shields.io/badge/data-CC--BY--NC%204.0-lightgrey.svg)](docs/06_DATA_MANAGEMENT.md)
[![Python 3.13](https://img.shields.io/badge/python-3.13-green.svg)](https://www.python.org)

> ⚠️ **연구 산출물 안내** — 본 저장소는 KAIST KTP571 수업의 학술 연구 결과물입니다.
> 한국어 LLM 안전성 평가를 위한 적대적 평가(adversarial evaluation) 파이프라인이며,
> *실제 공격·악용 목적이 아닙니다*. 사용 시 [docs/07_ETHICS_RISK.md](docs/07_ETHICS_RISK.md) 의
> Responsible Disclosure 정책을 준수해 주세요.

KAIST KTP571 · TEAM 4 (박지민 · 윤장한) · 멘토 TA 임채균 · 담당교수 최호진

한국어 문화 맥락에 특화된 멀티턴 jailbreak 공격을 자동으로 생성·방어·평가하는
3-Agent LangGraph 파이프라인. ChatGPT와 Gemini의 한국어 안전성 특성을
양방향 교차 실험으로 정량 비교한다.

선행 연구 (Crescendo, AutoRedTeamer, CSRT, KoRSET 등 14편) 의 검증된 기법을
한국 문화 맥락 3카테고리 — **위계 관계 · 반어법 · 코드 스위칭** — 으로 정밀
매핑했습니다. 자세한 분석은 [docs/04_RELATED_WORK.md](docs/04_RELATED_WORK.md) 참조.

## 구조

```
TEAM4/
├── agents/                # Attacker / Defender / Evaluator / Aggregator 노드
│   ├── prompts.py         # 시스템 프롬프트
│   ├── attacker.py
│   ├── defender.py
│   ├── evaluator.py       # Turn Evaluator + Final Evaluator
│   └── aggregator.py      # 피드백 생성·압축
├── data/
│   ├── seeds.json         # 30개 수동 시드 (카테고리별 10개)
│   └── normal_prompts.json # 50개 정상 프롬프트 (FPR 측정용)
├── results/
│   ├── runs/              # JSONL 라운드 로그
│   └── figures/           # 분석 차트
├── scripts/
│   └── generate_seeds_ai.py  # 카테고리당 90개 AI 자율 생성
├── state.py               # 공유 State TypedDict
├── graph.py               # LangGraph 그래프 빌더
├── orchestrator.py        # 전체 실험 (실험 A/B × 700라운드) 실행
├── pilot.py               # 5/10/15턴 사전 실험 + 싱글턴 대조군
├── analysis.py            # DSR/ASR/FPR 계산 + 시각화
├── requirements.txt
└── .env.example
```

## 실험 모델 배정

| 역할 | 실험 A | 실험 B |
|---|---|---|
| Attacker | GPT-4o | Gemini 2.0 Flash |
| Defender | Gemini 2.0 Flash | GPT-4o |
| Evaluator | Claude Sonnet 4.6 (고정) | Claude Sonnet 4.6 (고정) |

## 데이터 규모

- 시드 30개 (카테고리별 10) + AI 자율 생성 270개 + 정상 50개
- 카테고리 3개 × 100라운드 × 양방향 2회 + 정상 50건 × 2 = **총 700라운드**

## 목표 지표

| 지표 | 목표 |
|---|---|
| DSR (방어 성공률) | ≥ 65% |
| FPR (정상 오차단율) | ≤ 20% |
| Agreement (Evaluator vs 인간) | ≥ 75% |
| 데이터셋 | ≥ 600건 |

## 시작하기

```powershell
pip install -r requirements.txt
copy .env.example .env  # 그 다음 API 키 채우기

# 0. 단건 스모크 테스트 (코드 변경 시 가장 먼저)
python scripts/smoke_test.py                                # 기본 (id=1, A, 6턴, Defender=vanilla)
python scripts/smoke_test.py --defender-mode aware          # Ablation 비교
python scripts/smoke_test.py --help                         # 옵션 전체

# 1. 사전 실험 (3/6/9턴 + 싱글턴 대조)
python pilot.py --mode both

# 2. 본 실험 (700 라운드 양방향, Defender=vanilla)
python orchestrator.py --experiment A
python orchestrator.py --experiment B
python orchestrator.py --experiment A --normal
python orchestrator.py --experiment B --normal

# 2-Ablation. Defender 프롬프트 엔지니어링 효과 비교 (멘토 권고)
python orchestrator.py --experiment A --defender-mode aware
python orchestrator.py --experiment B --defender-mode aware

# 3. 분석 + 차트
python analysis.py
```

자세한 절차는 [docs/08_OPERATIONS.md](docs/08_OPERATIONS.md), 검증 절차는 [docs/03_TEST_PLAN.md](docs/03_TEST_PLAN.md) 참조.
