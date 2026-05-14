# 08. Operations Runbook

| 항목 | 값 |
|---|---|
| 버전 | 0.9 |
| 작성일 | 2026-05-13 |

본 문서는 실험 실행·장애 대응·비용 관리의 표준 절차를 제공한다.

---

## 1. 사전 준비 (1회)

### 1.1 환경 구성
```powershell
# 1. Python 의존성
pip install -r requirements.txt

# 2. 환경변수
copy .env.example .env
notepad .env
# 다음 4개를 채운다:
#   OPENAI_API_KEY=...
#   GOOGLE_API_KEY=...
#   ANTHROPIC_API_KEY=...
#   LANGSMITH_API_KEY=...   (선택)
```

### 1.2 키 발급
| 키 | 발급 URL | 결제 등록 필요 |
|---|---|---|
| OpenAI | https://platform.openai.com/api-keys | ✓ ($5 충전) |
| Google | https://aistudio.google.com/apikey | ✓ (카드 등록) |
| Anthropic | https://console.anthropic.com/settings/keys | ✓ ($5 충전) |
| LangSmith | https://smith.langchain.com → API Keys | × (무료 5000 traces) |

### 1.3 비용 한도 설정 (필수)
각 콘솔에서 monthly spending limit 를 다음 값으로 설정:
- OpenAI: $100
- Google: $50
- Anthropic: $100

---

## 2. 정상 실행 흐름

### 2.1 단계별 절차
```powershell
# Step 0: 키 검증
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('OK' if all(os.getenv(k) for k in ['OPENAI_API_KEY','GOOGLE_API_KEY','ANTHROPIC_API_KEY']) else 'MISSING KEYS')"

# Step 1: 단건 스모크 (1 라운드, ~$0.05, ~110초)
#  → 코드 변경 직후 항상 실행
python scripts/smoke_test.py                          # 기본 (id=1, 실험 A, 6턴)
python scripts/smoke_test.py --max-turns 2            # 더 빠른 검증 (~30초)
python scripts/smoke_test.py --seed-id 1 --experiment B   # 양방향 둘 다 점검

# Step 2: AI 시드 생성 (1회, ~$5, ~5분)
python scripts\generate_seeds_ai.py

# Step 3: 사전 실험 (~$15, ~40분)
python pilot.py --mode both --experiment A
python analysis.py    # 사전 실험 결과 검토

# Step 4: 본 실험 (~$80~150, 2~3시간)
python orchestrator.py --experiment A
python orchestrator.py --experiment B
python orchestrator.py --experiment A --normal
python orchestrator.py --experiment B --normal

# Step 5: 분석 (matplotlib 차트 5종 + summary.json)
python analysis.py

# Step 5-b: Streamlit Trace Viewer (인터랙티브 라운드 탐색)
streamlit run scripts/viewer.py

# Step 6: 인간 어노테이션 (60 라운드 샘플링, 별도 작업)
# Step 7: 결과 보고서 작성 (별도)
```

### 2.2 예상 소요 시간 / 비용

| 단계 | 시간 | 비용 |
|---|---|---|
| 스모크 | 1 분 | $0.05 |
| AI 시드 생성 | 5 분 | $3~7 |
| 사전 실험 | 30~45 분 | $10~20 |
| 본 실험 A | 1~1.5 시간 | $30~60 |
| 본 실험 B | 1~1.5 시간 | $30~60 |
| Normal A/B | 10 분 | $2~5 |
| 분석 | 1 분 | $0 |
| **총** | **3~4 시간** | **$75~150** |

---

## 3. 모니터링

### 3.1 진행 상황 확인
```powershell
# 현재 라운드 진행 상황
Get-Content "results/runs/A_hierarchy.jsonl" | Measure-Object -Line
# 또는
(Get-Content "results/runs/A_hierarchy.jsonl").Count
```

### 3.2 Streamlit Trace Viewer (로컬, LangSmith 대체)
```powershell
streamlit run scripts/viewer.py
```
- 자동으로 브라우저 열림 (http://localhost:8501)
- `results/runs/`, `results/smoke/`, `results/pilot_*` 모두 자동 로딩
- 필터: 카테고리·실험·Defender 모드·판정·도메인
- 라운드 행 클릭 → 대화 전문 + 무기 매트릭스 + Final Evaluator 판정 펼침
- 한국어 렌더링 안정, 외부 서비스 의존 없음

### 3.3 LangSmith 실시간 추적 (선택)
- https://smith.langchain.com → Tracing → `team4-ko-safety`
- 라운드별 trace 자동 적재 (`.env` 의 `LANGSMITH_API_KEY` 있어야 함)
- 에러 발생 시 빨강 표시
- 단점: 한국어 렌더링 불안정, 외부 서비스 의존 → 평소엔 Streamlit 권장

### 3.4 비용 모니터링
- OpenAI: https://platform.openai.com/usage
- Google: https://aistudio.google.com (Billing)
- Anthropic: https://console.anthropic.com/settings/billing

각 실험 단계 전후 잔액 확인. 한도 80% 도달 시 자동 정지 설정 권장.

---

## 4. 장애 대응

### 4.1 API 에러 패턴별 대응

| 증상 | 원인 | 대응 |
|---|---|---|
| `RateLimitError: billing_not_active` | 결제 미등록 | 콘솔에서 결제 등록 또는 충전 |
| `ResourceExhausted: prepayment depleted` | Google 잔액 0 | Google Cloud Billing 에 잔액 충전 |
| `NotFound: model ... no longer available` | 모델 ID 변경/회수 | `agents/llm.py` 의 `GEMINI_MODEL` 등 업데이트 |
| `401 Unauthorized` | 키 만료/오타 | 키 재발급 후 `.env` 갱신 |
| `429 quota exceeded` | rate limit | tenacity 가 자동 재시도. 지속 시 라운드 일시 정지 (Ctrl+C) 후 5~10분 대기 |
| `503 Service Unavailable` | 모델 사 일시 장애 | 자동 재시도. 30분 이상 지속 시 다음 카테고리로 우회 |

### 4.2 라운드 중단 시 복구

`orchestrator.py` 는 결과를 JSONL append-only 로 저장하므로 **재실행 시 자동으로 이어진다.**

```powershell
# 중단된 카테고리 확인
(Get-Content "results/runs/A_hierarchy.jsonl").Count
# 100 이 아니면 재실행:
python orchestrator.py --experiment A
```

⚠ 단, 같은 round_id 가 중복 기록될 수 있음. 분석 시 중복 제거 (analysis.py 가 자동으로 round_id+experiment 기준 unique 처리하도록 추후 보강 — TODO).

### 4.3 결과 파일 손상
```powershell
# 1. 백업 확인
Copy-Item "results/" -Destination "results_bak_$(Get-Date -f yyyyMMdd)/" -Recurse

# 2. JSONL 라인 단위 무결성 점검
Get-Content "results/runs/A_hierarchy.jsonl" | ForEach-Object { try { $_ | ConvertFrom-Json | Out-Null } catch { Write-Host "BAD LINE: $_" } }
```

손상 라인을 제거한 후 재실행.

### 4.4 Attacker 자체 후퇴 (self-collapse)

증상: Attacker 출력에 "죄송하지만…", "AI 어시스턴트로서…" 등.

대응 우선순위:
1. `agents/prompts.py` 의 ATTACKER_SYSTEM 강화 (역할 명시 더 강하게)
2. `agents/attacker.py` 의 메시지 구조 점검 (transcript packing 유지)
3. 그래도 지속 시 해당 시드를 `data/seeds_blacklist.json` 으로 격리 (본 실험에서 제외)

---

## 5. 결과 검증 체크리스트

본 실험 종료 후 다음을 모두 통과해야 분석/보고로 진행:

- [ ] `results/runs/A_hierarchy.jsonl` 100 행
- [ ] `results/runs/A_irony.jsonl` 100 행
- [ ] `results/runs/A_code_switching.jsonl` 100 행
- [ ] `results/runs/B_*.jsonl` 각 100 행
- [ ] `results/runs/A_normal.jsonl` 50 행, `B_normal.jsonl` 50 행
- [ ] 모든 JSONL 라인에 `final_result.판정` 존재
- [ ] error 필드 비율 < 5%
- [ ] `python analysis.py` 에러 없이 완료
- [ ] `results/summary.json` 의 DSR/FPR 값이 합리적 범위 (0~1)
- [ ] `results/figures/` 5개 PNG 생성

---

## 6. 유지보수

### 6.1 의존성 업데이트
- `requirements.txt` 의 패키지는 본 실험 종료 전 까지 lock.
- 새 모델 (예: Claude 4.7) 등장 시 별도 실험으로 분리.

### 6.2 코드 변경 후 회귀 절차
1. AST 점검 (`python -c "import ast; ..."`)
2. 스모크 1 라운드
3. (대규모 변경) 사전 실험 카테고리 1개만 (10 라운드)
4. 본 실험 재실행 결정

### 6.3 모델 ID 변경 대응
모델 ID 가 변경되면 다음 4 곳을 모두 업데이트:
- `agents/llm.py` 의 `GPT_MODEL`, `GEMINI_MODEL`, `CLAUDE_MODEL`
- `.env` 에 환경변수로 명시 (선택)
- `docs/01_SRS.md §2.3`, `docs/10_GLOSSARY.md` 의 모델 식별자
- 결과 파일 메타데이터 (run_metadata.json)

---

## 7. 백업·아카이브

| 시점 | 작업 |
|---|---|
| 매일 (실험 기간) | `git add results/ && git commit -m "round logs $(date -I)"` (사적 repo) |
| 본 실험 종료 | `Compress-Archive results/ -DestinationPath "team4_results_$(Get-Date -f yyyyMMdd).zip"` |
| 발표 직전 | 외장 SSD + 클라우드 백업 |
| 발표 직후 | GitHub 공개 (Redaction 적용본) |
| 1년 후 | Zenodo DOI 등록 (선택) |

---

## 8. 비상 연락

- 코드 문제: 팀 내 슬랙/메신저
- API 결제 문제: 각 모델 사 콘솔의 Support
- 윤리 / 데이터 문제: 멘토 TA → 지도교수
