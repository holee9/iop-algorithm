# XDET V&V Plan 골격 v1.0 (자동화 검증 우선)

기준: PRD v1.0, EVAL v1.1, RTM v1.0, P1 계획서 v1.0. 원칙: 최대 자동화·최소 인력 개입 (사용자 결정 ③). TC 발번은 Test Spec 단계.

## 1. VV 발번 및 방법 분류

| VV ID | 검증 대상 (PR) | 판정 지표 (EV) | 방법 | 자동화 |
|---|---|---|---|---|
| XDET-VV-000 | FR-C015 (프레임워크) | — (구조 검증) | 모듈 단위 harness: 전 모듈 XFrame 입출력 fixture 시험, 인터페이스 계약(SWR-000-7) 준수·직접 호출 부재 정적 검사 | 완전 자동 (모듈 CI) |
| XDET-VV-001 | PR-CORE-001 | EV-101/102/103 | IEC 62220-1 측정 스크립트 + defect 검증 세트 | 완전 자동 |
| XDET-VV-002 | PR-CORE-002 | EV-104 | 노출 시퀀스 lag 자동 측정 (ASTM E2597 §lag) | 완전 자동 |
| XDET-VV-003 | PR-CORE-003 | EV-105 | 균일 조사 세트 artifact 자동 검출 + 오보정 세트 | 완전 자동 |
| XDET-VV-004 | PR-CORE-005 | EV-106 | 포화 시나리오·격자 팬텀 잔차 자동 산출 | 완전 자동 |
| XDET-VV-005 | PR-CORE-004 | EV-201/102 | SNR/SRb 자동 산출 + hallucination 검사 세트 | 완전 자동 |
| XDET-VV-006 | PR-MED-001/002 | EV-204(대체) | 자동 IQA 회귀 (개발 루프) | 자동 (개발) |
| XDET-VV-007 | PR-MED-003 | EV-204 GSDF, EV-205 | GSDF LUT 적합 검사 + 수용률 자동 집계 | 완전 자동 |
| XDET-VV-008 | PR-MED-004 | EV-203/102 | grid 주파수 잔존 자동 분석 (FFT) + moiré 검사 | 완전 자동 |
| XDET-VV-009 | PR-MED-005 | EV-202 | CNR 자동 산출 (팬텀), MC 기준 편차 | 완전 자동 |
| XDET-VV-010 | PR-MED-001~005 (인허가) | EV-204 | 관찰자 연구 (최소 규모) | **인력 — 유일** |
| XDET-VV-011 | PR-NDT-001/002 | EV-301/303 | SNRn/duplex wire/CSa 자동 판독 | 완전 자동 |
| XDET-VV-012 | PR-CORE-007/008 | EV-401/402 | 티어 벤치마크 + 결과 diff 자동 비교 | 완전 자동 |
| XDET-VV-013 | PR-CORE-006 (Gen 2) | EV-201 | (예약 — PCCP 검증 프로토콜과 통합) | 자동+감사 |
| XDET-VV-014 | PR-MED-006 (Gen 2) | EV-202 | (예약) | 자동+감사 |
| XDET-VV-015 | PR-NDT-003 (Gen 2) | EV-302 | POD 자동 산출 + 검증 세트 (예약) | 자동 |

## 2. 자동화 커버리지

- 15개 VV 중 인력 필수 1건 (VV-010, 인허가용 관찰자 연구) — 개발 루프에서는 VV-006 자동 IQA가 대행.
- 자동화율: 개발 단계 100%, 인허가 단계 1건 예외.

## 3. 운용

1. RTM VV 열은 본 표로 충전 — 개정 시 RTM 동기화.
2. Test Spec 단계에서 VV별 TC 발번 (조건·데이터·합격판정 상세).
3. Gen 2 VV(013~015)는 PCCP 전략 문서와 함께 상세화.
4. 검증 계획 동결(E3) 게이트 = 본 문서 v1.x 승인 + TC 충전 완료.
