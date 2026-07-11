# XDET RTM v1.2 (완성판) — MR ↔ PR ↔ FR ↔ EV ↔ VV ↔ TC

v1.1 대비 (issue #34): NDT 응용 빔질 특성화·dSNRn@1mGy 추적 행 추가 (측정 프로토콜 §1b, EV-301 확장). **RTM이 요구 변경의 관리 경로(governed path)임을 명시.** 파일명 유지(문서 맵 참조 보존).
v1.0 대비: FR 열 추가, VV/TC 열 충전. Gen 2 행은 예약 유지.

| MR | PR | FR | EV | VV | TC |
|---|---|---|---|---|---|
| MR-003 | (공통 기반) | FR-C015 | — | VV-000 | TC-000 |
| MR-003 | PR-CORE-001 | FR-C001~C004 | EV-101/102/103 | VV-001 | TC-001~003 |
| MR-003 | PR-CORE-002 | FR-C005~C006 | EV-104 | VV-002 | TC-004~005 |
| MR-003 | PR-CORE-003 | FR-C007 | EV-105 | VV-003 | TC-006~007 |
| MR-003 | PR-CORE-005 | FR-C008~C009 | EV-106 | VV-004 | TC-008~009 |
| MR-004 | PR-CORE-004 | FR-C010~C011 | EV-201, EV-102 | VV-005 | TC-010~011 |
| MR-004, MR-008 | PR-CORE-006 | FR-C014 (예약) | EV-201 | VV-013 | TC-023 (예약) |
| MR-007 | PR-CORE-007 | FR-C012 | EV-401 | VV-012 | TC-020 |
| MR-010 | PR-CORE-008 | FR-C013 | EV-402 | VV-012 | TC-021 |
| MR-001 | PR-MED-001 | FR-M001~M002 | EV-204 | VV-006/010 | TC-012, TC-022 |
| MR-001 | PR-MED-002 | FR-M003 | EV-204 | VV-006/010 | TC-012, TC-022 |
| MR-001 | PR-MED-003 | FR-M004~M005 | EV-204, EV-205 | VV-007 | TC-013~014 |
| MR-006 | PR-MED-004 | FR-M006~M007 | EV-203, EV-102 | VV-008 | TC-015~016 |
| MR-005 | PR-MED-005 | FR-M008 | EV-202 | VV-009 | TC-017 |
| MR-005, MR-008 | PR-MED-006 | FR-M009 (예약) | EV-202 | VV-014 | TC-024 (예약) |
| MR-002 | PR-NDT-001 | FR-N001, FR-N003 | EV-301 | VV-011 | TC-018 |
| MR-002 | PR-NDT-002 | FR-N002 | EV-303, EV-102 | VV-011 | TC-019 |
| MR-002 | PR-NDT-001 (확장) | FR-N001 (dSNRn 확장, issue #34) | EV-301 · dSNRn@1mGy (측정 프로토콜 §1b) | VV-011 | TC-018 |
| MR-009 | PR-NDT-003 | FR-N004 (예약) | EV-302 | VV-015 | TC-025 (예약) |

## 무결성 점검 (v1.1)

- 고아 없음: MR 10 / PR 17 / FR 28 / EV 16 / VV 16 / TC 26 전 계층 연결 (프레임워크 FR-C015/VV-000/TC-000 포함).
- Gen 1 범위(P1 대상): 예약 3행 제외 14행 — 전부 TC까지 충전 완료.
- 검증 계획 동결(E3) 게이트 충족 조건: 본 RTM + V&V Plan + Test Spec 승인.
- **v1.2 추가 (issue #34)**: NDT dSNRn@1mGy 확장 행은 기존 EV-301 ↔ VV-011 ↔ TC-018 체인의 **정련(refinement)** 이며 신규 고아를 만들지 않는다 (측정 근거: 측정 프로토콜 §1b). 요구(빔질·효율 지표) 변경은 본 RTM을 경유하는 것이 **관리 경로(governed path)** 이다 — 개정 이력 필수(§운용 2).

## 운용

1. SWR v1.0 발행 완료 — RTM v1.2에서 SWR 열 추가 예정 (FR별 SWR 범위: FRD·SWR 문서 상호 참조로 임시 추적).
2. 변경 영향 분석: 임의 ID 기준 상·하류 전파 확인 후 개정 — 개정 이력 필수.
3. Gen 2 예약 행은 PCCP 전략 승인 시 충전.
