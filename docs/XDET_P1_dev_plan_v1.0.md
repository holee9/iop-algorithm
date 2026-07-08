# XDET P1 개발 계획서 (SW 레퍼런스 / 골든 모델) v1.0

기준: PRD v1.0 (Gen 1 범위), EVAL v1.1, RTM v1.0. 목적: 전 Gen 1 알고리즘의 float 정밀도 레퍼런스 구현과 자동 검증 체계 확립. 본 계획서의 산출물이 P2 최적화·P4 FPGA 등가성 검증의 기준(골든 모델)이 된다.

## 1. 범위 (PR 매핑)

| WP | 내용 | 대응 PR | 완료 기준 (EV) |
|---|---|---|---|
| WP1 | 보정 코어: offset/gain/defect | PR-CORE-001 | EV-101/102/103 min |
| WP2 | Lag/ghost 보정 | PR-CORE-002 | EV-104 min |
| WP3 | Line noise 보정 | PR-CORE-003 | EV-105 min |
| WP4 | 포화·기하 보정 | PR-CORE-005 | EV-106 min |
| WP5 | VST+BM3D/NLM 노이즈 저감 | PR-CORE-004 | EV-201/102 min |
| WP6 | 다중스케일 대비강화 + DRC | PR-MED-001/002 | EV-204 min (자동 IQA 대체) |
| WP7 | 자동 윈도잉 + GSDF | PR-MED-003 | EV-204 GSDF, EV-205 min |
| WP8 | Grid line suppression | PR-MED-004 | EV-203/102 min |
| WP9 | 커널 virtual grid | PR-MED-005 | EV-202 min |
| WP10 | NDT: integration + SNRn 리포팅 + 두께보정 | PR-NDT-001/002 | EV-301/303 min |
| WP11 | 자동 검증 파이프라인 (골든 데이터셋 + 지표 산출 + 회귀) + XFrame/CalibSet 공통 컨테이너·모듈 harness 구현 (SWR-000-6~11) | 전 PR 공통 | §3 참조 + 모듈 단위 CI |
| WP12 | 티어 gating + 결과 동일성 프레임 | PR-CORE-007/008 | EV-401/402 (구조만, 수치는 P2) |

제외: Gen 2/3 항목 (DL denoising, DL scatter, ADR), FPGA (P3 이후).

## 2. 일정 골격 (상대 주차)

| 구간 | 내용 |
|---|---|
| W1–W4 | WP11 선행 (검증 인프라 없이는 어떤 WP도 완료 판정 불가) + WP1 착수 |
| W3–W12 | WP1–WP4 (Common Core) 순차 완료 |
| W8–W20 | WP5–WP9 (Medical) 병행 |
| W14–W22 | WP10 (NDT) |
| W20–W26 | 통합 회귀, 골든 모델 형상 동결 (P1 게이트) |
| 병행 | 자사 패널 베이스라인 실측 → EVAL v1.2 [B] 치환 (게이트 아님) |

## 3. 자동 검증 아키텍처 (WP11 — 최소 인력 원칙)

- 골든 데이터셋 v1: 대표 조건 raw 라이브러리 (균일 조사 선량 계단, edge 팬텀, 임상 모사, NDT 시편). 버전 관리 (Gitea LFS).
- 지표 산출 엔진: IEC 62220-1 DQE/MTF/NPS, ASTM E2597 (iSRb/CSa/lag/bad pixel), ISO 17636-2 SNRn/SRb — 전부 스크립트화, 사람 판독 배제.
- 자동 판독: CDRAD contrast-detail 자동 스코어링, duplex wire 자동 판독 채택.
- 회귀 게이트: 커밋 트리거 → 전 EV 자동 산출 → min 미달 시 머지 차단. P1 게이트 = 전 WP의 EV min 자동 통과 + 형상 동결.
- 인력 개입 잔여: 인허가용 관찰자 연구(EV-204)만 — P1 범위 외, 인허가 단계로 이관.

## 4. 형상·추적 규칙

- 레포: 알고리즘 라이브러리 / 검증 파이프라인 / 골든 데이터셋 3분리 (Gitea canonical).
- 각 WP 산출 코드에 PR ID 태그 → RTM VV/TC 열 충전은 V&V Plan에서 발번.
- 골든 모델 동결 이후 변경은 회귀 전체 통과 + 변경 기록 필수 (IEC 62304 형상관리 연결).

## 5. 리스크

| 리스크 | 대응 |
|---|---|
| 베이스라인 실측 지연 | 문헌 수치로 진행 (승인된 절충안), [B]만 후치환 |
| BM3D full 해상도 처리시간 (9.4MP) | P1은 정확도만 판정 — 속도는 P2 과제로 명시적 분리 |
| MUSICA류 특허 회피 설계 확인 | 릴리스 게이트로 이연 (사용자 결정) — SWR ⚠P 절에 대안 설계 예비 정의로 리스크 완충 |
