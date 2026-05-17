# 09. Traceability Matrix

| 항목 | 값 |
|---|---|
| 버전 | 0.9 |
| 작성일 | 2026-05-13 |

요구사항 → 설계 → 코드 → 테스트 추적성. 각 항목 변경 시 종방향 영향을 즉시
파악할 수 있게 한다.

---

## 1. 기능 요구사항 (FR) 추적

| FR ID | 요구사항 | SDD §  | 코드 | 테스트 |
|---|---|---|---|---|
| FR-01 | Attacker 한국어 멀티턴 공격 생성 | §3, §6.1 | `agents/attacker.py`, `agents/prompts.py:ATTACKER_SYSTEM` | L2 스모크 (Attacker 응답 비어있지 않음) |
| FR-02 | Attacker 자체 후퇴 금지 | §7 (위협 표) | `agents/prompts.py:ATTACKER_SYSTEM` (강화), `agents/attacker.py:_history_as_transcript` | L2 collapse 정규식 검사 |
| FR-03 | Defender 3단계 레이어 | §3, §6 | `agents/defender.py`, `agents/prompts.py:DEFENDER_SYSTEM` | L4 인간 어노테이션 |
| FR-04 | Defender 가 seed/target 모름 | §1.2 원칙 #2 | `agents/defender.py:_history_as_messages` (seed 미전달) | 코드 리뷰 |
| FR-05 | Turn Evaluator JSON 출력 | §3 | `agents/evaluator.py:turn_evaluator_node`, `_parse_json` | L2 (JSON 파싱 성공) |
| FR-06 | Final Evaluator JSON 출력 | §3 | `agents/evaluator.py:final_evaluator_node` | L2 (final_result 키 존재) |
| FR-07 | Aggregator 피드백 누적 / 롤링 3 | §6.2 | `agents/aggregator.py:aggregator_node`, `load_recent_feedback` | 라운드 연속 실행 후 piping 확인 |
| FR-08 | 라운드 최대 N턴, 조기 종료 | §6.1 | `graph.py:_route_after_turn` | L2 (current_turn 증가 패턴) |
| FR-09 | JSONL 영속 저장 | §4.2 | `orchestrator.py:run_adversarial` | L4 (라인 수 일치) |
| FR-10 | 시드 30 + 확장 프롬프트 270 = 300 분포 | §4.2 | `data/seeds.json`, `scripts/expand_dataset.py` | L3 사전 확인 |
| FR-11 | 정상 50건 FPR 측정 | §4.2 | `data/normal_prompts.json`, `orchestrator.py:run_normal` | L4 |
| FR-12 | 실험 A/B 양방향 | §5.2 | `agents/llm.py:ATTACKER_FN`/`DEFENDER_FN` dict | L4 |
| FR-13 | DSR·ASR·FPR·돌파턴·페이즈·라운드 추이 집계 | §6.2 | `analysis.py:compute_summary` | L4 (summary.json 검증) |
| FR-14 | 차트 5종 시각화 | §6.2 | `analysis.py:plot_*` | L4 (PNG 5개 생성) |
| FR-15 | LangSmith 추적 | §5.2 | env `LANGSMITH_*` | LangSmith UI 수동 확인 |
| FR-16 | 사전 실험 | §6 | `pilot.py` | L3 |

---

## 2. 비기능 요구사항 (NFR) 추적

| NFR ID | 요구사항 | 검증 방법 | 현재 상태 |
|---|---|---|---|
| NFR-01 재현성 | 동일 시드 결과 분포 유사 | 시드 ID·temperature 로그 기록 | (TODO) run_metadata.json |
| NFR-02 성능 | 1 라운드 < 150 초 | 스모크 측정 | 105~127s 확인 |
| NFR-03 비용 | ≤ $200 | 토큰 × 단가 | 1 라운드 ~$0.05 → 700 라운드 ~$35~150 |
| NFR-04 안정성 | 재시도 4회 지수 백오프 | `agents/llm.py:@retry` 데코레이터 | 적용 완료 |
| NFR-05 확장성 | 카테고리 추가 1곳 변경 | `prompts.py:CATEGORY_STRATEGY` dict | 적용 완료 |
| NFR-06 감사성 | 모든 라운드 JSONL | append-only 파일 | 적용 완료 |
| NFR-07 보안 | .env / .gitignore | 파일 검증 | 적용 완료 |
| NFR-08 윤리 | 07 정책 준수 | 시드 검수 / Redaction | (예정) |

---

## 3. 카테고리 → 시드 → 선행 연구 추적

| 카테고리 | 시드 ID | 선행 연구 근거 | 추정 ASR |
|---|---|---|---|
| hierarchy | 1 | CAGE + AutoRedTeamer | 70~85% |
| hierarchy | 2 | CAGE 전문직 권위 | 60~75% |
| hierarchy | 3 | CAGE + AutoRedTeamer | 55~70% |
| hierarchy | 4 | Suh & Kim | 40~55% |
| hierarchy | 5 | CAGE 국가보안법 | 35~50% |
| hierarchy | 6 | CAGE 의료 권위 | 45~60% |
| hierarchy | 7 | CAGE 시사 | 40~55% |
| hierarchy | 8 | CAGE 편집 권위 | 50~65% |
| hierarchy | 9 | Suh & Kim 직장 위계 | 30~45% |
| hierarchy | 10 | CAGE 학술 권위 | 25~40% |
| irony | 11 | Echo Chamber 가치 역전 | 65~80% |
| irony | 12 | Crescendo escalation | 55~70% |
| irony | 13 | Echo Chamber 자기 인용 | 60~75% |
| irony | 14 | Crescendo + 사소화 | 30~45% |
| irony | 15 | Echo Chamber 가치 역전 | 55~70% |
| irony | 16 | Crescendo | 45~60% |
| irony | 17 | CAGE 수능 시사 | 50~65% |
| irony | 18 | Echo Chamber | 50~65% |
| irony | 19 | Echo Chamber | 55~70% |
| irony | 20 | Suh & Kim + Crescendo | 55~70% |
| code_switching | 21 | CSRT En+Ko | 70~85% |
| code_switching | 22 | MultiJail Zh+Ko | 35~50% |
| code_switching | 23 | CSRT Ja+Ko | 50~65% |
| code_switching | 24 | CSRT 키릴 | 45~60% |
| code_switching | 25 | CSRT Ar+Ko | 55~70% |
| code_switching | 26 | CSRT Th+Ko 저자원 | 35~50% |
| code_switching | 27 | CSRT Id+Ko | 25~40% |
| code_switching | 28 | CSRT Sw+Ko 저자원 | 45~60% |
| code_switching | 29 | MultiJail De + Crescendo | 30~45% |
| code_switching | 30 | CSRT 3개 혼합 | 65~80% |

---

## 4. 평가 지표 → 데이터 → 코드 → 목표

| 지표 (ID) | 데이터 소스 | 계산 코드 | 목표 |
|---|---|---|---|
| M-DSR | `runs/{A,B}_{cat}.jsonl` | `analysis.py:compute_summary` (verdict=="방어 성공" 비율) | ≥ 65% |
| M-ASR | 동일 | `1 − DSR` | 측정 |
| M-FPR | `runs/{A,B}_normal.jsonl` | `analysis.py` 의 refusal 정규식 | ≤ 20% |
| M-Break | `runs/*.jsonl` | `final_result.돌파_턴` 평균 | 측정 |
| M-Phase | 동일 | `analysis.py:plot_phase_stack` | 측정 |
| M-Recover | 동일 | `analysis.py:plot_feedback_progress` rolling-10 | 측정 |
| Q-Agree | `annotation.jsonl` + `runs/*` | (별도 스크립트) Cohen's κ | ≥ 0.75 |

---

## 5. 산출물 ↔ 요구사항 매핑

| 산출물 | 만족하는 요구사항 |
|---|---|
| GitHub 소스 코드 | FR-01~FR-16, NFR-* |
| `data/seeds.json` + `expanded_prompts.json` | FR-10, NFR-08 |
| `data/normal_prompts.json` | FR-11 |
| `results/runs/*.jsonl` 600+ 행 | FR-09, FR-12 (양방향) |
| `results/summary.json` | FR-13 |
| `results/figures/*.png` | FR-14 |
| `docs/` 10종 | SDD 표준 + 윤리 |

---

## 6. 변경 영향 분석 가이드

| 변경 위치 | 영향 받는 항목 |
|---|---|
| `prompts.py:ATTACKER_SYSTEM` | FR-01, FR-02, FR-16, 전체 ASR (재 사전 실험 필요) |
| `prompts.py:CATEGORY_STRATEGY` | FR-01, 카테고리별 ASR |
| `prompts.py:DEFENDER_VARIANTS` | FR-03, M-DSR (Defender 모드별 별도 측정 필요) — ADR-7 |
| `state.py:State` | FR-09, NFR-06, 모든 노드 코드 |
| `state.py:defender_mode` | FR-03 결과 파일 분리 (`*_{mode}.jsonl`), analysis.py 비교 차트 |
| `graph.py:_route_after_turn` | FR-08 (종료 조건) |
| `orchestrator.py:MAX_TURNS` | FR-08, M-Phase, 비용 |
| `agents/llm.py` 모델 ID | FR-12, NFR-02, NFR-03 |
| `data/seeds.json` | FR-10, M-DSR/ASR |

요구사항 1개 변경 시 위 표로 종횡 영향을 추적.
