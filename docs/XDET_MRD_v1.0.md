# XDET MRD — Market Requirements Document + MR Table (v1.0)

기준: PRM v1.1, 교차검증 리포트 v1.0. 시장 요구는 제품 관점(무엇이 필요한가)만 기술하며 구현 방식을 지정하지 않는다.

## MR Table

| ID | 시장 요구 | 출처/근거 | 대응 PR 그룹 |
|---|---|---|---|
| XDET-MR-001 | 의료용 DR 시스템에 탑재 가능한 진단 화질 post-processing SW (MFDS/FDA/CE MDR 인허가 가능) | PRM §2, §6 | PR-MED-* |
| XDET-MR-002 | 산업용 NDT 시스템에 탑재 가능한 ISO 17636-2/ASTM 적합 post-processing SW | PRM §2 | PR-NDT-* |
| XDET-MR-003 | 검출기 raw 영상 입력 기반 공용 보정 코어 (신틸레이터·패널 물리 결함의 완전 보정) | PRM §2, TRM 1계층 | PR-CORE-* |
| XDET-MR-004 | 저선량 촬영에서 표준 선량 동등 화질 (환자 선량 절감 가치) | TRM §1.6, EVAL EV-201 | PR-CORE-004, PR-MED-* |
| XDET-MR-005 | 물리 grid 없이 grid 동등 화질 (무그리드 워크플로) | TRM §2.6 | PR-MED-005/006 |
| XDET-MR-006 | 물리 grid 사용 시 grid line 완전 억제 | TRM §2.5 | PR-MED-004 |
| XDET-MR-007 | 설치 PC 사양별 SKU (CPU only / 보급형 GPU / 고성능) | PRM §2 SKU | PR-CORE-007, 전 PR |
| XDET-MR-008 | Gen 1 결정론적 구성으로 3개국 동시 인허가, Gen 2 딥러닝은 PCCP 경로 | PRM §3, §6 | 전 PR (세대 속성) |
| XDET-MR-009 | NDT 결함 자동인식(ADR) 제공 (검사 생산성) | PRM §4 | PR-NDT-003 |
| XDET-MR-010 | SKU/티어 간 진단 결과 일관성 (동일 입력 → 동일 결과) | PRM §2 주, EVAL EV-402 | PR-CORE-008 |

## 운용 규칙

- MR은 수치 목표를 갖지 않는다 (수치는 PR의 acceptance criteria = EV 참조).
- MR 추가/변경은 본 문서 개정으로만 가능하며 RTM에 즉시 반영.
