# 04. Related Work Survey

| 항목 | 값 |
|---|---|
| 버전 | 0.9 |
| 작성일 | 2026-05-13 |
| 조사 범위 | LLM jailbreak, 멀티턴 공격, 한국어/다국어 안전성, 평가 방법론 |

본 문서는 본 프로젝트 카테고리(위계·반어법·코드 스위칭) 에 직접 매핑되는
선행 연구를 정리한다. 각 항목은 (1) 핵심 기법, (2) 정량 근거, (3) 우리 매핑,
(4) 인용을 포함한다.

---

## 1. Multi-turn Jailbreak

### 1.1 Crescendo (Russinovich et al. 2024)
- **기법**: 무해 질문으로 시작 → 모델 *자신의 이전 답변을 인용*하며 점진적 escalation.
- **정량 근거**: Sentence A 뒤에 Sentence B가 올 때 compliance **99.99%**, 단독 36.2% (논문 §3).
- **데이터**: GPT-4 대비 +29~61pp, Gemini Pro +49~71pp (모델별 평균).
- **우리 매핑**: ② 반어법 카테고리의 골든 카드. Aggregator 가 Defender 의 무해 답변을 자기 인용 재료로 다음 라운드 Attacker 에 전달하면 자연 구현.
- **인용**: arXiv:2404.01833

### 1.2 Echo Chamber (Alobaid et al. 2025)
- **기법**: 5단계 (poisonous seeds → steering → invoke → path select → persuasion) 자기 강화 loop.
- **정량 근거**: 폭력/혐오 도메인 > 90%, 전체 평균 **45%** (Crescendo 28.6% 능가).
- **우리 매핑**: ② 반어법. 가치 역전 ("막으려면 알아야") 구조의 이론적 근거.
- **인용**: arXiv:2601.05742

### 1.3 X-Teaming (Rahman et al. 2025)
- **기법**: Planner / Attacker / Verifier 3-agent. 평균 4~5턴.
- **정량 근거**: Claude 3.7 96.2%, Deepseek V3 98.1%, Qwen2.5 99.4% ASR.
- **우리 매핑**: 우리 3-Agent 파이프라인의 직접 ancestor. 차별점은 (a) 한국어 문화 맥락 특화, (b) Aggregator 분리, (c) 양방향 교차 실험.
- **인용**: arXiv:2504.13203

### 1.4 AutoRedTeamer (Zhou et al. 2025)
- **기법**: 메모리 기반 공격 조합 자동 탐색. "Authority Manipulation" 전략 보유.
- **정량 근거**: Llama-3.1-70B 0.82 ASR.
- **우리 매핑**: ① 위계 — "Authority Manipulation" 이 직접 대응. 우리는 한국 PDI 60 맥락으로 구체화.
- **인용**: arXiv:2503.15754

### 1.5 AutoAdv (Reddy et al. 2025)
- **기법**: 2단계 (disguise → adaptive refine) 패턴/온도 매니저, 6턴 적응.
- **정량 근거**: Llama-3.1-8B 95% ASR (6턴).
- **우리 매핑**: 본 실험 6턴 (2:2:2) 의 정량 근거. AutoAdv 6턴 95% 와 X-Teaming 7턴 (평균 4턴 소요) 사이.
- **인용**: arXiv:2511.02376

### 1.6 M2S (Ha et al. 2025)
- **기법**: 멀티턴 공격을 Hyphenize/Numberize/Pythonize 로 단일 턴 압축.
- **정량 근거**: GPT-4o 89%, Mistral-7B 95.9%.
- **우리 매핑**: 직접 사용은 X. 본 실험 결과를 단일 턴 baseline 비교용으로 활용 가능.
- **인용**: arXiv:2503.04856

### 1.7 GPTFuzzer (Yu et al. 2023)
- **기법**: 인간 작성 jailbreak 템플릿을 AFL 식 mutation.
- **정량 근거**: ChatGPT/Llama-2 90%+.
- **우리 매핑**: AI 시드 자율 생성 (`scripts/generate_seeds_ai.py`) 의 ancestor.
- **인용**: arXiv:2309.10253

---

## 2. 한국어 · 다국어 · 문화 맥락

### 2.1 Multilingual Jailbreak (Deng et al. ICLR 2024)
- **기법**: 저자원 언어 번역으로 안전 필터 우회. MultiJail 9개 언어.
- **정량 근거**: **Korean ChatGPT unsafe rate 9.84%, GPT-4 3.81%** (영어 대비 약 3배).
- **우리 매핑**: 한국어 단독으로도 영어 대비 위험 — 본 프로젝트의 동기 직접 근거.
- **인용**: arXiv:2310.06474

### 2.2 CSRT — Code-Switching Red-Teaming (Yoo et al. ACL 2025)
- **기법**: 10개 언어 (En + Zh, It, Vi, **Ar, Ko, Th**, Bn, Sw, Jv) 혼합 단일 질의.
- **정량 근거**: 영어 단일 대비 **+46.7%** 공격 성공 증가.
- **우리 매핑**: ③ 코드 스위칭 카테고리의 직접 근거. 우리는 한국어 base 에 다국어 키워드 삽입 형태로 변형.
- **인용**: arXiv:2406.15481

### 2.3 CAGE / KoRSET (Kim et al. ICLR 2026)
- **기법**: Semantic Mold 로 적대적 구조와 문화 콘텐츠 분리, 한국 맥락 주입. 존댓말/반말, 연령 권위, 한국법(국가보안법), 시사 이슈, 코드 스위칭 5요소 명시.
- **정량 근거**: Llama-3.1-8B **43.8%** (직역 28.2%, +15.6pp). Qwen2.5-7B 25.3% vs 14.6%.
- **우리 매핑**: 가장 가까운 직접 비교 대상. **본 실험은 KoRSET 단일 턴 43.8% 를 멀티턴으로 능가하는지가 핵심 contribution.**
- **인용**: arXiv:2602.20170

### 2.4 Suh & Kim (JKIISC 2024)
- **기법**: 한국어 무해 발화 + `/` 구분자 + 악성 트리거. 존댓말 / 문법 변형.
- **정량 근거**: ChatGPT 완전 성공 4.3%, 부분 1.0% (단일 턴 기준).
- **우리 매핑**: ① 위계 + 한국어 교착어 특성. 우리는 멀티턴으로 단일 턴 성공률 한계를 돌파하려 시도.
- **인용**: JKIISC 2024 (KoreaScience)

### 2.5 AssurAI (TTA 2025)
- **데이터**: 35개 한국 사회문화 위험 분류, 11,480 인스턴스 멀티모달.
- **우리 매핑**: 위험 분류 체계는 우리 시드 도메인 매핑에 참조 가능. 정량 ASR 은 미공개.
- **인용**: arXiv:2511.20686 / HuggingFace TTA01/AssurAI

---

## 3. 방어 · 평가 방법론

### 3.1 AutoDefense (Zeng et al. 2024)
- **기법**: 다중 에이전트 방어 (의도 추론 → 응답 검증 → 최종 판단).
- **정량 근거**: 3-Agent 방어 후 DSR 65% 도달.
- **우리 매핑**: Defender 의 3단계 레이어 (Hard/Soft/Allow) 설계 근거. 본 실험 DSR ≥ 65% 목표의 정량 기준.
- **인용**: arXiv:2403.04783

### 3.2 OR-Bench (Cui et al. 2025)
- **기법**: 정상 요청 거부율(과잉 방어) 벤치마크.
- **정량 근거**: 허용 임계 FPR ≤ 20%.
- **우리 매핑**: 정상 프롬프트 50건 × 양방향 2회 = 100건 테스트셋 설계.
- **인용**: arXiv:2405.20947

### 3.3 LLM-as-a-Judge (Zheng et al. NeurIPS 2023)
- **기법**: LLM 으로 LLM 출력 자동 평가.
- **정량 근거**: 인간 평가자 일치율 약 80% (Cohen's κ).
- **우리 매핑**: Final Evaluator 신뢰성 검증 (Q-Agree 지표, 목표 κ ≥ 0.75).
- **인용**: arXiv:2306.05685

---

## 4. 본 프로젝트 차별성 (vs 가장 가까운 선행 연구)

| 항목 | AutoRedTeamer (2025) | CAGE / KoRSET (2026) | **본 프로젝트** |
|---|---|---|---|
| 에이전트 수 | 2 | (벤치마크 생성) | **3 (분리된 Evaluator)** |
| Defender | 외부 모델 | 외부 모델 | **독립 에이전트 + 3단계 레이어** |
| Evaluator | 공격 성공만 판정 | (해당 없음) | **독립 에이전트 + 인간 검증** |
| 언어 | 영어 중심 | 한국어 | **한국어 (코드 스위칭 다국어 포함)** |
| 멀티턴 | 메모리 기반 | 단일 턴 | **2:2:2 페이즈, 6턴, 피드백 루프** |
| 실험 구조 | 단방향 | (벤치마크) | **양방향 교차 (A↔B)** |
| 평가 모델 | 동일 계열 | (벤치마크) | **3사 완전 독립 분리** |
| 한국 문화 맥락 | 없음 | 5요소 | **3 카테고리 정밀 분리 + 페이즈별 무기 매핑** |

---

## 5. 본 프로젝트가 차용한 검증된 기법

| 기법 | 출처 | 우리 적용 |
|---|---|---|
| 점진적 escalation | Crescendo | 페이즈 가이드 1~2 / 3~4 / 5~6 |
| Authority manipulation | AutoRedTeamer | ① 위계 카테고리 전략 |
| 자기 인용 강화 | Crescendo, Echo Chamber | (계획) Aggregator 피드백에 Defender 무해 응답 인용 |
| 다국어 키워드 위장 | CSRT, MultiJail | ③ 코드 스위칭 카테고리 |
| Hypothetical wrapping | AutoAdv, Echo Chamber | 5턴 무기 |
| Salami (부분 요청) | M2S 변형, X-Teaming | 6턴 무기 |
| 시드 → AI 자율 확장 | GPTFuzzer | `scripts/generate_seeds_ai.py` |
| LLM-as-Judge | Zheng 2023 | Turn / Final Evaluator |
| Over-refusal 측정 | OR-Bench | 정상 테스트셋 50건 |
| 한국 문화 5요소 | CAGE / KoRSET | 시드 카탈로그 (05) 매핑 |

---

## 6. 출처 (URL)

- Crescendo: https://arxiv.org/abs/2404.01833
- AutoRedTeamer: https://arxiv.org/abs/2503.15754
- AutoAdv: https://arxiv.org/abs/2511.02376
- GPTFuzzer: https://arxiv.org/abs/2309.10253
- Multilingual Jailbreak: https://arxiv.org/abs/2310.06474
- CSRT: https://arxiv.org/abs/2406.15481 · https://aclanthology.org/2025.acl-long.657.pdf
- Echo Chamber: https://arxiv.org/abs/2601.05742
- M2S: https://arxiv.org/abs/2503.04856 · https://aclanthology.org/2025.acl-long.805.pdf
- X-Teaming: https://arxiv.org/abs/2504.13203 · https://x-teaming.github.io/
- Suh & Kim: https://koreascience.kr/article/JAKO202419057619210.page
- CAGE / KoRSET: https://arxiv.org/abs/2602.20170
- AssurAI: https://arxiv.org/abs/2511.20686 · https://huggingface.co/datasets/TTA01/AssurAI
- AutoDefense: https://arxiv.org/abs/2403.04783
- OR-Bench: https://arxiv.org/abs/2405.20947
- LLM-as-Judge: https://arxiv.org/abs/2306.05685

---

## 7. 조사 한계

- Crescendo·CSRT·CAGE 의 verbatim 한국어 공격 프롬프트는 안전 윤리상 일부 출처가 비공개. 우리 시드는 패턴만 차용하고 원문은 자체 작성.
- CSRT 의 언어쌍별 ASR breakdown 은 본문 표 파싱 실패로 확인 불가 — 전체 평균 +46.7% 만 확정.
- AssurAI 정량 ASR 은 파일럿 단계라 미공개.
