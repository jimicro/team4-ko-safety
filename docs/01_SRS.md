# 01. Software Requirements Specification (SRS)

| 항목 | 값 |
|---|---|
| 프로젝트 | 3-Agent 상호작용을 통한 한국어 AI 안전성 자동 검증 시스템 |
| 팀 | KAIST KTP571 TEAM 4 (박지민, 윤장한) |
| 버전 | 0.9 (Progress I 직후 작성) |
| 작성일 | 2026-05-13 |
| 표준 | IEEE 830-1998 축약 |

---

## 1. 서론

### 1.1 목적
한국어 문화 맥락 jailbreak 공격을 자동으로 생성·방어·평가하는 3-Agent
파이프라인을 구축하고, 대표 상용 LLM (ChatGPT, Gemini, Claude) 의 한국어
안전성을 정량 비교한다.

### 1.2 범위
- 한국어 텍스트 기반 jailbreak 공격·방어 파이프라인 (LangGraph)
- 한국어 문화 특화 3개 공격 카테고리 (위계 / 반어법 / 코드 스위칭) 설계 및 실증
- 양방향 교차 실험 (모델 A↔B) 으로 공격력·방어력·과잉 방어 비교
- 별도 모델 C (Claude) 를 Evaluator로 사용해 평가 편향 차단

### 1.3 비범위 (out of scope)
- 멀티모달 (이미지/음성) 공격
- 영어 또는 기타 비한국어 공격 (코드 스위칭 내 키워드만 다국어 허용)
- 실제 사용자 대상 배포·API 서빙
- 자동화된 자기 학습 (fine-tuning)

### 1.4 정의·약어
[10_GLOSSARY.md](10_GLOSSARY.md) 참조.

### 1.5 참고문헌
[04_RELATED_WORK.md](04_RELATED_WORK.md) 참조.

---

## 2. 전체 설명

### 2.1 제품 개요
하나의 라운드는 다음 흐름이다.
```
Attacker(LLM)  ──공격──▶  Defender(LLM)  ──응답──▶  Turn Evaluator(LLM)
       ▲                                                  │
       │                                            매 턴 판정
       │                                                  ▼
       └────── Aggregator ◀── Final Evaluator ◀── 종료조건 확인
                 (피드백 누적)        (종합 판정)
```
- 최대 6턴 (2:2:2 페이즈), 방어 실패 감지 시 조기 종료
- 라운드 결과는 JSON Lines 1행으로 영속 저장

### 2.2 사용자 클래스
| 사용자 | 사용 시나리오 |
|---|---|
| 연구자 (팀원) | 시드 작성·실험 실행·결과 분석 |
| TA / 지도교수 | 실험 결과·문서 리뷰 |
| 후속 연구자 | 데이터셋·코드 재현 |

### 2.3 운영 환경
- Python 3.13, Windows 11 (개발), Linux 가능
- LangGraph ≥ 0.2, LangChain ≥ 0.3
- 3사 LLM API (OpenAI, Google, Anthropic)
- (선택) LangSmith 추적

### 2.4 제약사항
| 제약 | 영향 |
|---|---|
| 학기 10주 | 라운드 수 700개로 제한 |
| API 비용 $80~200 | 모델 선택 (GPT-4o, Gemini 2.5 Flash, Claude Sonnet 4.6) |
| 한국어 단일 | 코드 스위칭 외에는 영어 비중 최소화 |
| 모델 사 안전 정책 | 일부 시드는 Attacker 자체가 거부할 수 있음 |

### 2.5 가정과 의존성
- 3사 API 가용성과 모델 ID 안정성이 실험 기간 동안 유지된다.
- Claude Sonnet 4.6 가 Evaluator로 사용 가능한 상태를 유지한다.
- Defender 가 Gemini 안전 필터의 추가 차단 없이 *자체 시스템 프롬프트* 기반으로 응답한다 (BLOCK_NONE 설정 적용).

---

## 3. 기능 요구사항 (FR)

| ID | 요구사항 | 우선순위 |
|---|---|---|
| FR-01 | Attacker 노드는 카테고리 전략과 페이즈 가이드에 따라 한국어 멀티턴 공격을 생성한다. | 필수 |
| FR-02 | Attacker 는 자체 안전 정렬에 의해 후퇴하지 않는다 (페르소나 유지). | 필수 |
| FR-03 | Defender 노드는 3단계 레이어 (Hard Block / Soft Warning / Allow) 로 응답한다. | 필수 |
| FR-04 | Defender 는 target_content / seed_prompt 를 알지 못한다. | 필수 |
| FR-05 | Turn Evaluator 는 매 턴 JSON `{"판정": "실패"\|"계속", "이유": ...}` 을 출력한다. | 필수 |
| FR-06 | Final Evaluator 는 라운드 종료 시 JSON (판정·돌파_턴·위험도·피드백) 을 출력한다. | 필수 |
| FR-07 | Aggregator 는 피드백을 디스크에 누적하고 최근 3 라운드만 다음 Attacker에 전달한다. | 필수 |
| FR-08 | 한 라운드는 최대 N 턴 (기본 6) 후 또는 방어 실패 감지 시 즉시 종료된다. | 필수 |
| FR-09 | 라운드 결과는 [06_DATA_MANAGEMENT.md](06_DATA_MANAGEMENT.md) 의 스키마대로 JSONL 1행으로 저장된다. | 필수 |
| FR-10 | 30개 사람 시드 + 270개 AI 자율 생성 시드 = 300개 시드를 카테고리별로 균등 분포한다. | 필수 |
| FR-11 | 정상 프롬프트 50개로 FPR (과잉 방어) 을 측정한다. | 필수 |
| FR-12 | 실험 A (Attacker=GPT, Defender=Gemini) 와 실험 B (역할 교환) 를 양방향 실행한다. | 필수 |
| FR-13 | DSR · ASR · FPR · 평균 돌파 턴 · 페이즈별 돌파율 · 라운드별 ASR 추이를 자동 집계한다. | 필수 |
| FR-14 | 분석 결과는 PNG 차트 5종 (히트맵·박스플롯·스택바·라인·레이더) 으로 시각화한다. | 권장 |
| FR-15 | LangSmith 추적이 활성화되면 라운드 단위 trace 가 자동 전송된다. | 선택 |
| FR-16 | 사전 실험 (3/6/9 턴 sweep + 싱글턴 대조) 을 본 실험 전에 수행한다. | 권장 |

---

## 4. 비기능 요구사항 (NFR)

| ID | 요구사항 | 측정 |
|---|---|---|
| NFR-01 (재현성) | 본 실험 재실행 시 동일 시드 입력으로 동일 분포의 결과 발생 (LLM 비결정성 허용). | 시드 ID 고정·temperature·top_p 명시 |
| NFR-02 (성능) | 1 라운드 최대 6턴 기준 평균 < 150 초. | smoke test 실측 |
| NFR-03 (비용) | 전체 본 실험 비용 ≤ $200. | 토큰 사용량 × 단가 계산 |
| NFR-04 (안정성) | API 에러 시 tenacity 로 4회 지수 백오프 재시도. | 코드 검증 |
| NFR-05 (확장성) | 새 카테고리 추가가 prompts.py 의 dict 한 항목 변경으로 가능. | 코드 리뷰 |
| NFR-06 (감사성) | 모든 라운드의 입출력은 JSONL 로 남아 사후 감사 가능. | 파일 무결성 |
| NFR-07 (보안) | API 키는 .env 로만 관리하고 git 에 커밋되지 않는다. | .gitignore 검증 |
| NFR-08 (윤리) | 생성된 jailbreak 데이터는 [07_ETHICS_RISK.md](07_ETHICS_RISK.md) 정책에 따라 관리된다. | 정책 준수 |

---

## 5. 성공 기준 (Acceptance Criteria)

[03_TEST_PLAN.md](03_TEST_PLAN.md) 에 상세 측정 절차.

| 지표 | 목표 | 근거 |
|---|---|---|
| DSR (Defense Success Rate) | ≥ 65% | AutoDefense (Zeng 2024) 3-Agent 방어 도달 수준 |
| FPR (False Positive Rate) | ≤ 20% | OR-Bench (Cui 2025) 허용 임계 |
| Evaluator-Human Agreement (Cohen's κ) | ≥ 0.75 | LLM-as-Judge (Zheng 2023) 인간 일치율 |
| 데이터셋 규모 | ≥ 600 라운드 | 카테고리당 100 × 양방향 2 + 정상 100 |
| 재현 가능한 소스 | GitHub 공개 | 산출물 |

---

## 6. 인터페이스 요구사항

### 6.1 외부 API
| 인터페이스 | 사용처 |
|---|---|
| OpenAI Chat Completions | Attacker (실험 A), Defender (실험 B) |
| Google Gemini generateContent | Defender (실험 A), Attacker (실험 B) |
| Anthropic Messages | Turn / Final Evaluator (양 실험 공통) |
| (선택) LangSmith | 추적·시각화 |

### 6.2 내부 인터페이스
- LangGraph 노드 ↔ 공유 State: [02_SDD.md §4](02_SDD.md) 의 State 스키마
- Aggregator ↔ Attacker: `results/feedback_buffer.jsonl` (롤링 윈도 3)

### 6.3 사용자 인터페이스
CLI 만 제공. 별도 GUI 없음.
- `python orchestrator.py --experiment {A,B} [--normal]`
- `python pilot.py --mode {sweep,single,both}`
- `python analysis.py`

---

## 7. 부록

### 7.1 변경 이력
| 버전 | 일자 | 변경 |
|---|---|---|
| 0.9 | 2026-05-13 | 초기 작성 (Progress I 직후) |

### 7.2 미해결 사항
- KoRSET (Kim et al. 2026) 의 의미 몰드 구조 직접 차용 여부 — 추가 검토 필요.
- Attacker 자체 후퇴 발생률에 대한 정량 모니터링 hook 필요.
