# TRM v2.0 / PRM v1.0 / EVAL v1.0 교차검증·보정 리포트 (v1.0)

방법: 순방향(TRM→PRM→EVAL, 누락 검출) + 역방향(EVAL→PRM/TRM, 과도 검출) 전수 대조.

## 1. 순방향 점검 결과 (누락)

| # | 발견 사항 | 판정 | 보정 |
|---|---|---|---|
| F1 | TRM §1.7 saturation/geometric distortion → EVAL 지표 부재 | 누락 | EV-106 신설 (포화 복원 가시성·기하 잔차) |
| F2 | TRM 두께보정(NDT) → EVAL에 SMTR/CSa(ASTM E2597) 지표 부재 | 누락 | EV-303 신설 |
| F3 | TRM auto windowing → EVAL에 GSDF 적합성만 있고 자동 윈도우 수용률 지표 부재 | 누락 | EV-205 신설 (자동 윈도우 무수정 수용률) |
| F4 | TRM §1.7 → PRM 매핑 테이블에 non-uniformity/distortion/saturation 행 부재 | 누락 | PRM 매핑에 Core Gen 1 행 추가 |
| F5 | 그 외 TRM 14개 항목 | 정합 | — |

## 2. 역방향 점검 결과 (과도)

| # | 발견 사항 | 판정 | 보정 |
|---|---|---|---|
| R1 | EVAL §1.3 defect 검출 누락률 max "0%" — 통계적으로 입증 불가능한 절대치 | 과도 | "정의된 검증 세트 내 0건"으로 측정 가능 정의로 수정 |
| R2 | EVAL §2.1 선량 절감 max 50% — 벤더 팬텀 주장 기반, 임상 근거 희소 | 경계 | 유지하되 [B] 표기 추가 (자체 검증 전 대외 사용 금지) |
| R3 | EVAL §3.2 ADR max recall 98% — 자체 데이터 부재 상태 | 경계 | 유지 (이미 잠정치 명시됨), 파일럿 후 재보정 |
| R4 | EVAL §4 처리시간 → TRM에 대응 기술 항목 불명확 | 비대칭 | TRM P2에 "파이프라인 실시간화(SIMD/GPU)" 작업 항목 명시 |
| R5 | 그 외 EVAL 지표 | 근거 정합 | — |

## 3. 문서 개정 지시 (delta 방식)

- TRM v2.0 → **v2.1**: R4 반영 (P2 내용에 실시간화 명시).
- PRM v1.0 → **v1.1**: F4 반영 (매핑 1행 추가: Non-uniformity/distortion/saturation | Core | Gen 1 | 전 Tier).
- EVAL v1.0 → **v1.1**: F1/F2/F3 지표 신설, R1 재정의, R2 [B] 표기, 전 지표 EV ID 부여 (EV ID 표는 MR/PR table 문서 참조).

본 리포트가 상기 3개 문서의 공식 변경 기록(change notice)이며, 차기 전면 개정 시 본문에 병합한다.

## 4. 결론

구조적 모순 없음. 누락 3건(지표 신설), 매핑 1건, 과도/경계 3건(정의 수정 1, 표기 강화 2) — 모두 경미하며 MRD/PRD 착수 가능 상태로 판정.
