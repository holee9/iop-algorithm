# XDET Test Spec — TC Table v1.0

기준: V&V Plan 골격 v1.0, 측정 프로토콜 v1.0, EVAL v1.1. VV별 TC 발번. 판정은 EV min 기준(자동), 데이터는 골든 데이터셋(GDS) 참조.

| TC ID | 상위 VV | 시험 내용 | 데이터 | 자동 판정 |
|---|---|---|---|---|
| XDET-TC-000 | VV-000 | 모듈 단위 CI: 각 모듈 fixture 입출력 일치 + 시그니처·의존 방향 정적 검사 (직접 호출 검출 시 실패) | 합성 fixture (모듈 동봉) | 계약 위반 0건 |
| XDET-TC-001 | VV-001 | 보정 전/후 DQE 3선량(XN/2, XN, 2XN) 측정, 열화율 산출 | GDS-RQA5 균일+edge 세트 | EV-101 min |
| XDET-TC-002 | VV-001 | 보정 전/후 MTF@3.57 lp/mm 유지율 | GDS-edge (W 2mm, 1.5~3°) | EV-102 min |
| XDET-TC-003 | VV-001 | Defect 보정: 검증 세트 전수 — 잔존 cluster 0건, 검출 누락률 | GDS-defect (주입 결함 포함 합성+실측) | EV-103 min |
| XDET-TC-004 | VV-002 | First-frame lag % (포화 근접 노출 시퀀스) | GDS-lag 시퀀스 | EV-104 min |
| XDET-TC-005 | VV-002 | Ghost 잔상 CNR (고대비 패턴 후 균일 조사) | GDS-ghost | EV-104 min |
| XDET-TC-006 | VV-003 | Line artifact 잔존 (균일 조사, 3단 window 자동 검사) | GDS-균일 선량 계단 | EV-105 min |
| XDET-TC-007 | VV-003 | 구조물 오염 오보정률 (금속 임플란트 모사 세트) | GDS-구조물 세트 | EV-105 min |
| XDET-TC-008 | VV-004 | 포화 경계 아티팩트 자동 검출 | GDS-포화 시나리오 | EV-106 min |
| XDET-TC-009 | VV-004 | 기하 잔차 (격자 팬텀) | GDS-격자 | EV-106 min |
| XDET-TC-010 | VV-005 | SNR 개선율 + SRb 열화 동시 판정 (선량 계단) | GDS-임상 모사 저선량 | EV-201, EV-102 min |
| XDET-TC-011 | VV-005 | VST 왕복 무편향성 (denoiser 우회 시 원신호 복원) | 합성 Poisson-Gaussian 세트 | 편차 임계 내 |
| XDET-TC-012 | VV-006 | 대비강화/DRC 자동 IQA 회귀 (기준 버전 대비 비열화) | GDS-임상 모사 | IQA 스코어 기준선 |
| XDET-TC-013 | VV-007 | 자동 윈도우 수용률 집계 | GDS-부위별 세트 | EV-205 min |
| XDET-TC-014 | VV-007 | GSDF LUT 적합성 자가검사 | LUT 산출물 | PS3.14 적합 |
| XDET-TC-015 | VV-008 | Grid 성분 검출 정확도 + 잔존 grid line — grid 밀도 3부류(f_grid < Nyquist / ≈ / > Nyquist, aliased 포함) 필수 | GDS-grid 세트 (SWR-1006 요건) | EV-203 min |
| XDET-TC-016 | VV-008 | Moiré/aliasing 발생 검사 + GLS 실패 시 무처리 통과 확인 | GDS-grid 경계 사례 | EV-203, FR-M007 |
| XDET-TC-017 | VV-009 | 무그리드+커널 보정 CNR 개선 (팬텀) | GDS-scatter 팬텀 | EV-202 min |
| XDET-TC-018 | VV-011 | SNRn/SRb 자동 산출 + IQI 자동 판독 정확도 | GDS-NDT 시편 (BAM5류 용접 시편 권장) | EV-301 min |
| XDET-TC-019 | VV-011 | 두께보정 후 CSa/SMTR + SRb 보호 | GDS-step wedge | EV-303, EV-102 min |
| XDET-TC-020 | VV-012 | Tier별 파이프라인 처리시간 (100회 중앙값, cold/warm) | GDS-표준 프레임 | EV-401 min |
| XDET-TC-021 | VV-012 | 티어 간 출력 diff (결정론 bit / 부동소수점 허용오차) | GDS-표준 프레임 | EV-402 min |
| XDET-TC-022 | VV-010 | 관찰자 연구 (인허가용 — 프로토콜 별도) | 임상/모사 세트 | EV-204 (인력) |
| XDET-TC-023~025 | VV-013/014/015 | (Gen 2 예약 — PCCP 동기 상세화) | — | — |

## 운용

1. TC-001~021은 CI 회귀 스위트 등록 — 커밋 트리거 자동 실행, min 미달 시 머지 차단 (P1 계획서 §3).
2. GDS 세트 ID는 골든 데이터셋 레포 태그와 1:1 — 데이터 변경 = 재베이스라인 절차.
3. TC-022는 인허가 단계 실행 (개발 게이트 아님).
