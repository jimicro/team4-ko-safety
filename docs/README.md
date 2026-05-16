# 문서 인덱스

KAIST KTP571 · TEAM 4 · 3-Agent 한국어 AI 안전성 자동 검증 시스템

소프트웨어 공학 표준 문서 세트. IEEE 830 (SRS), IEEE 1016 (SDD), IEEE 829
(테스트), IEEE 26515 (운영) 가이드라인을 단일 학기 프로젝트 규모에 맞게 축약.

## 문서 목록

| # | 문서 | 대응 표준 / 목적 |
|---|---|---|
| [01](01_SRS.md) | Software Requirements Specification | 무엇을 만드는가 — 기능·비기능 요구사항 |
| [02](02_SDD.md) | Software Design Document | 어떻게 만드는가 — 아키텍처·데이터·인터페이스 |
| [03](03_TEST_PLAN.md) | Test Plan | 어떻게 검증하는가 — 파일럿·본 실험·평가 절차 |
| [04](04_RELATED_WORK.md) | Related Work Survey | 선행 연구 정리 (Crescendo·CSRT·KoRSET 등) |
| [05](05_ATTACK_TAXONOMY.md) | Attack Taxonomy & Seed Catalog | 카테고리 정의 + 30개 시드 명세 |
| [06](06_DATA_MANAGEMENT.md) | Data Management Plan | 데이터 스키마·저장·공개 정책 |
| [07](07_ETHICS_RISK.md) | Ethics & Risk Assessment | 윤리적 사용·dual-use 위험 관리 |
| [08](08_OPERATIONS.md) | Operations Runbook | 실행 절차·장애 대응·비용 관리 |
| [09](09_TRACEABILITY.md) | Traceability Matrix | 요구사항 ↔ 설계 ↔ 코드 ↔ 테스트 |
| [10](10_GLOSSARY.md) | Glossary | 용어·약어·모델 식별자 |

## 읽는 순서 권장

- **신규 팀원/리뷰어**: 01 → 04 → 05 → 02 → 03 → 07
- **개발자**: 02 → 05 → 08 → 09
- **평가자**: 01 → 09 → 03 → 결과 (results/summary.json)
- **IRB / 윤리 검토**: 07 → 06 → 05

## 문서 버전 관리

- 본 문서들은 코드와 같은 저장소 (`docs/`) 에서 git으로 관리.
- 메이저 변경 시 각 문서 헤더의 "버전" 라인 업데이트.
- 본 실험 진입 (orchestrator 첫 실행) 시점에 docs를 **v1.0** 으로 태깅.
