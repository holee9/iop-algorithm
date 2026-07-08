# XDET PRD — Product Requirements Document + PR Table (v1.0)

기준: MRD v1.0, TRM v2.1, EVAL v1.1. Acceptance criteria는 EV ID 참조형 — 수치는 EVAL이 단일 출처.

## EV ID 등록표 (EVAL v1.1 지표에 부여)

| EV ID | 지표 | EVAL 절 |
|---|---|---|
| XDET-EV-101 | DQE 무열화 (@RQA5) | §1.1 |
| XDET-EV-102 | MTF/SRb 유지율 | §1.2 |
| XDET-EV-103 | Defect 보정 품질 (검증 세트 기준) | §1.3 (R1 수정) |
| XDET-EV-104 | Lag/Ghost 잔류 | §1.4 |
| XDET-EV-105 | Line noise 잔존·오보정률 | §1.5 |
| XDET-EV-106 | 포화 복원·기하 잔차 (신설) | §1.6(신) |
| XDET-EV-201 | 노이즈 저감·선량 절감 | §2.1 |
| XDET-EV-202 | Scatter 보정 화질·정확도 | §2.2 |
| XDET-EV-203 | Grid line 억제 품질 | §2.3 |
| XDET-EV-204 | 관찰자 평가·GSDF 적합 | §2.4 |
| XDET-EV-205 | 자동 윈도우 수용률 (신설) | §2.4(신) |
| XDET-EV-301 | SNRn/IQI 등급 | §3.1 |
| XDET-EV-302 | ADR recall/false call/POD | §3.2 |
| XDET-EV-303 | SMTR/CSa (신설) | §3.3(신) |
| XDET-EV-401 | 파이프라인 처리시간 (Tier별) | §4 |
| XDET-EV-402 | 티어 간 결과 동일성 | §4 |

## PR Table

### Core (공용)

| ID | 제품 요구 | 세대 | Acceptance | 상위 MR |
|---|---|---|---|---|
| XDET-PR-CORE-001 | Offset/gain/defect 보정 파이프라인 | Gen 1 | EV-101, EV-102, EV-103 각 min 이상 | MR-003 |
| XDET-PR-CORE-002 | Lag/ghost 보정 | Gen 1 | EV-104 min 이상 | MR-003 |
| XDET-PR-CORE-003 | Line noise 보정 | Gen 1 | EV-105 min 이상 | MR-003 |
| XDET-PR-CORE-004 | 고전 노이즈 저감 (VST+BM3D/NLM) | Gen 1 | EV-201 min, EV-102 min 동시 충족 | MR-004 |
| XDET-PR-CORE-005 | 포화·기하 보정 | Gen 1 | EV-106 min 이상 | MR-003 |
| XDET-PR-CORE-006 | DL 노이즈 저감 (결정론적 fallback 동봉) | Gen 2 | EV-201 typ, hallucination 0 (EV-201 내) | MR-004, MR-008 |
| XDET-PR-CORE-007 | Tier 자동 감지·기능 gating | Gen 1 | EV-401 min (티어별) | MR-007 |
| XDET-PR-CORE-008 | 티어 간 결과 동일성 보장 | Gen 1 | EV-402 min 이상 | MR-010 |

### Medical

| ID | 제품 요구 | 세대 | Acceptance | 상위 MR |
|---|---|---|---|---|
| XDET-PR-MED-001 | 다중스케일 대비 강화 (자체 설계) | Gen 1 | EV-204 min 이상 | MR-001 |
| XDET-PR-MED-002 | DRC/tissue equalization | Gen 1 | EV-204 min 이상 | MR-001 |
| XDET-PR-MED-003 | 자동 윈도잉 + GSDF 출력 | Gen 1 | EV-204 GSDF 적합, EV-205 min | MR-001 |
| XDET-PR-MED-004 | Grid line suppression | Gen 1 | EV-203 min, EV-102 min | MR-006 |
| XDET-PR-MED-005 | 커널 기반 virtual grid | Gen 1 후반 | EV-202 min 이상 | MR-005 |
| XDET-PR-MED-006 | DL scatter correction (PCCP) | Gen 2 | EV-202 typ 이상 | MR-005, MR-008 |

### NDT

| ID | 제품 요구 | 세대 | Acceptance | 상위 MR |
|---|---|---|---|---|
| XDET-PR-NDT-001 | Frame integration + SNRn 리포팅 | Gen 1 | EV-301 min 이상 | MR-002 |
| XDET-PR-NDT-002 | 두께보정·weld 강조 | Gen 1 | EV-303 min, EV-102 min | MR-002 |
| XDET-PR-NDT-003 | ADR (파일럿→상용) | Gen 2→3 | EV-302 min (파일럿), typ (상용) | MR-009 |

## 운용 규칙

1. acceptance criteria 없는 PR 등록 금지 (EVAL §5 규칙 계승).
2. PR 변경 시 RTM 통해 하위 FR/SWR·VV·TC 영향 분석 필수.
3. Gen 2 PR은 결정론적 fallback PR과 쌍으로 관리 (MR-008).
