---
id: SPEC-LAG-001
version: 0.1.1
status: draft
created: 2026-07-09
updated: 2026-07-09
author: drake.lee
priority: high
issue_number: 5
---

# SPEC-LAG-001 — T4 WP2 lag 보정 처리 모듈 (지수합 상태변수 재귀 + IRF 피팅 도구)

XDET 영상처리 SW P1의 다섯 번째 작업 T4(WP2). lag(잔상) 보정 처리 모듈 `modules/lag.py`를 T0 프레임워크의 단일 계약 `process(XFrame, CalibSet, Params) -> XFrame`으로 구현하되, **SWR-000-7이 명시 허용한 내부 상태 보유 모듈**로서 지수합 IRF 기반 상태변수 재귀(SWR-401~402)를 수행한다. lag 단계는 고정 파이프라인 순서 offset → gain → defect → **lag** → line noise → 포화 → 기하 → post 중 오케스트레이터 `CANONICAL_ORDER`의 `lag` 위치(defect 이후·line_noise 이전)에서만 실행된다. 본 SPEC은 T0에서 구조적으로만 확인하고 이연했던 **상태 직렬화 인터페이스(REQ-INFRA-CONTRACT-2 — `serialize_state`/`load_state` ↔ XFrame)의 첫 런타임 검증**을 담당한다. IRF 계수(aᵢ, bᵢ, M)는 실측 대기([B]) 파라미터이므로 Gen 1은 **기지 지수합 IRF를 주입한 합성 데이터로 보정 엔진·피팅 도구를 선검증**한다.

- 근거: SWR-401~404(lag 보정, FR-C005/C006) · SWR-000-1~12(아키텍처) — `docs/XDET_SWR_spec_v1.2.md`; EVAL v1.1 XDET-EV-104(Lag/Ghost, [B]); TestSpec XDET-TC-004~005; 측정프로토콜 §1.5(Lag/Ghost)
- 완료 정의(DoD): **합성 주입 IRF 보정 효과를 검증** — 실측 step-response 도착 전, 기지 지수합 IRF(aᵢ, bᵢ, M=3~4)를 주입한 합성 연속 시퀀스에 lag 보정을 적용하고 (a) first-frame lag % 개선은 T1 지표 엔진 `metrics/lag.compute_first_frame_lag`로, (b) ghost 잔상 CNR 감소는 `metrics/lag.compute_ghost_cnr`로 `tests/`에서 판정하며, (c) **상태 직렬화 왕복(serialize_state → load_state) 후 이어 처리한 출력이 무중단 처리와 바이트 동일**함을 확인한다(REQ-INFRA-CONTRACT-2 T4 런타임 검증). XDET-TC-004는 EV-104 min 게이트로, XDET-TC-005는 부분 게이트(ghost CNR 감소; ghost 종단 비가시는 FB/실 패널 통합 후)로 pytest skeleton(skip)에서 실동작 케이스로 전환
- 선행 계약: [SPEC-INFRA-001](../SPEC-INFRA-001/spec.md) — `process` 계약·XFrame 불변·마스크 스택·이력 체인(`HistoryEntry.extra`)·오케스트레이터 진입 게이트(종류-단계 배선 `lag→LAG`·해상도·패널 ID·유효기간)·import-linter 레이어링(`module → common` 단방향)·`CANONICAL_ORDER`·**REQ-INFRA-CONTRACT-2**(상태 보유 모듈의 XFrame 직렬화 인터페이스 — T0 구조 확인, T4 런타임 검증 이연)·`common/contract.py` `StatefulModule` 프로토콜(`serialize_state`/`load_state`); [SPEC-METRICS-001](../SPEC-METRICS-001/spec.md) — first-frame lag·ghost CNR 판정 엔진 `metrics/lag`(REQ-METRICS-LAG-1/2/5); [SPEC-CORR-001](../SPEC-CORR-001/spec.md) — 선행 처리 모듈(offset/gain/defect)·offset 단계 raw 포화 검출(REQ-CORR-OFFSET-4, `raw_saturation_threshold` [B] 필수 Params 선례)·`modules/` 처리 패턴·마스크 스택 SATURATION 계약; [SPEC-LNSG-001](../SPEC-LNSG-001/spec.md) — `modules/` 처리 모듈 패턴(경로 결정론·부분 게이트·부록 A 등재 선례)
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.1.1 (2026-07-09)** — plan-audit 반복 1 반영(PASS 0.89; BLOCK #1 해소 + D1~D7 minor). 「결정 필요/확인 사항」 1·2·4·6 확정(3·5 확인 유지):
  1. **[BLOCK #1 해소] 시퀀스 구동 = 신규 `pipeline/sequence.py` 러너**: 프레임 시퀀스 상태 threading은 신규 additive 시퀀스 러너 `pipeline/sequence.py`가 담당한다 — 프레임별 `run_pipeline`을 래핑하고, lag 상태 보유 인스턴스 수명 = 시퀀스 수명(시퀀스 개시 시 인스턴스 신규화 = 리셋; 별도 리셋 프로토콜 메서드 없음), FB 트리거는 러너가 호출한다. `run_pipeline`·`CANONICAL_ORDER`·진입 게이트·REQ-LAG-CONTRACT-1 표면은 불변(additive — T0 표면 변경 없음)이고, 구동 경로는 `pipeline/`(프로덕션)에 두며 `tests/`가 아니다.
  2. **[확정] 상태 패킹 = (M,ny,nx) float32**: {sᵢ} M개 상태면을 (M, ny, nx) float32 pixel + zeros 마스크로 XFrame 패킹한다(XFrame `__post_init__`는 ndim 제약이 없어 3차원 pixel 허용). 상태 dtype을 float32로 고정해 serialize/load 왕복이 바이트 동일하다(D5 흡수).
  4. **[확정] FB 트리거 = 시퀀스 러너 소유**: FB 트리거 스텁(요청/완료 핸드셰이크)은 시퀀스 러너(`pipeline/sequence.py`)가 소유·호출하고 mock으로 시험한다.
  6. **[확정] SATURATION 화소 값 보존 + 재귀는 계산값**: SATURATION 화소의 출력 값은 보존(`modules/line_noise.py` 선례·SWR-602 취지)하되, 재귀는 보존된 출력이 아니라 계산된 감산 값 Î[k−1]로 진행하여 상태 진화가 물리적이도록 한다(D7 축 정의). 이 규칙을 REQ-LAG-CORR-5(Unwanted)로 승급했다(D1).
  - **D1~D7 minor 반영**: D1 REQ-LAG-CORR-5 신설(EC-6·DoD 추적); D2 Scenario 1 Then 비포화 화소 한정(fixture 포화 부재); D3 SWR-402 재귀 [C] 주장 완화 — 부록 A-2 [C] 행에 402 미등재(대표 열거)이므로 확정 [C]가 아닌 [C] 추론으로 표기; D4 Scenario 3 헤더에 STATE-1 매핑; D5 결정 2에 흡수(float32); D6 DoD 분리(XDET-TC-004=EV-104 min 게이트, XDET-TC-005=부분 게이트); D7 결정 6에 흡수.
  - status: draft (run 착수 전까지 유지).
- **v0.1.0 (2026-07-09)** — 초안 생성. GitHub 이슈 #5. 5개 요구 그룹(CORR/STATE/IRF/CONTRACT/VALIDATE) EARS 구조 확정. 핵심 범위 결정:
  1. **Gen 1 = LTI 지수합 보정**: IRF h[n] = Σᵢ₌₁..M aᵢ·bᵢⁿ(M = 3~4, [L] 문헌 표준 N=4 Starman) 상태변수 재귀(SWR-401~402)만 구현한다. 비선형 NLCSC 승급은 LTI 잔존 초과 시 예약 경로로 두되 Gen 1 범위 밖(SWR-401, Exclusions).
  2. **IRF 계수 = [B] → CalibSet(LAG) 외부화, 무단 기본값 금지**: aᵢ·bᵢ·M은 2-1 실측 step-response 대기 [B](SWR 부록 A-1)이므로 CalibSet(kind=LAG)로 주입한다. lag 단계는 종류-단계 배선(`lag→LAG`)이 강제되고 게이트가 CalibSet 부재/불일치를 거부한다(SWR-000-5; offset `raw_saturation_threshold` 선례 계승). lag 모듈에는 [T]/[P] 튜닝 Param이 없다(재귀는 IRF로 완전 결정).
  3. **상태 보유 모듈(SWR-000-7 명시 예외)·CONTRACT-2 첫 런타임 검증**: lag은 프레임당 지수항 상태 {sᵢ}를 연속 촬영 순서로 유지하며, 그 상태는 XFrame으로 직렬화 가능해야 한다(REQ-INFRA-CONTRACT-2). T0가 구조적으로만 확인한 `serialize_state`/`load_state` ↔ XFrame 인터페이스를 T4가 실제 상태 보유 모듈로 런타임 왕복 검증한다.
  4. **Ghost = FB 트리거 인터페이스만·전용 감쇠 없음**: forward-bias(FB) 시퀀스 실행은 패널 FW 소관이고 SW는 트리거 인터페이스(촬영 전 FB 요청/완료 확인)만 정의한다(SWR-404). 전용 잔존 ghost SW 감쇠는 Gen 1 범위 밖(실측 후 판정). 단, SWR-402 재귀가 연속 시퀀스에서 공간 구조 잔상을 **부산물로 감소**시키는 것은 전용 감쇠와 구분되며 XDET-TC-005 ghost CNR 판정으로 관측한다.
  5. **노출 구간별 IRF 세트 전환(SWR-403) 이연**: 노출 의존 비선형 확인·전환 판정은 2-1 실측 후 [B]. Gen 1은 단일 LTI IRF 세트만 사용한다(구현 안 함, Exclusions).
  6. **판정 = T1 엔진 tests/ 소비, EV 외부 주입**: first-frame lag %는 `metrics/lag.compute_first_frame_lag`(REQ-METRICS-LAG-1/2), ghost CNR은 `compute_ghost_cnr`(REQ-METRICS-LAG-5)로 판정하되, 모듈은 `metrics`를 import하지 않으므로(CONTRACT-3) 판정은 `tests/`에서 모듈+엔진을 함께 소비한다. EV-104 min/typ/max는 EVAL v1.1/Params에서 외부 주입(측정=판정 분리, SPEC-METRICS/CORR/LNSG 계승).
  - **헤드라인 미해소 항목(BLOCK 후보)**: 단일 프레임 `process` 계약 + 단일 프레임 `run_pipeline`(현 orchestrator에 시퀀스 처리 루프 없음)만으로는 연속 촬영 **프레임 시퀀스 상태 threading·구동 위치**가 정의되지 않는다 — 「결정 필요/확인 사항」 1(run 착수 전 확정 필요, orchestrator 확장 여부에 따라 T0 표면 변경 가능).
  - 파라미터 등급 확정(SWR 부록 A 대조): IRF 계수 aᵢ·bᵢ·차수 M(SWR-401) = [B](2-1 실측); M = 3~4 구조는 [L] 문헌 근거; SWR-402 재귀 방법 = [C] 관행. lag 모듈 [T]/[P] 튜닝 상수 없음.
  - status: draft (run 단계 착수 전까지 유지).

## Environment / Assumptions

- Python 3.11+, numpy/scipy 기반 float 골든 모델 (tech.md). **속도 최적화 금지 — 정확도 단일 목표**(P2에서 최적화). SWR-402 "프레임당 O(M·N_pixels)"는 계산 복잡도 서술이며 최적화 요구가 아니다.
- 대상 프레임: 3072×3072 / 3072×2560, 16-bit unsigned raw, pitch 140µm (EVAL v1.1 §0). lag은 시간 축(연속 촬영 프레임 시퀀스)을 다루는 유일한 처리 모듈이다.
- **실측 step-response 도착 전 — 합성 데이터로 검증한다.** 기지 지수합 IRF(aᵢ, bᵢ, M)를 주입한 합성 연속 시퀀스(포화 근접 노출 후 잔상 감쇠; 고대비 패턴 후 균일 조사)를 생성하고, 보정 후 first-frame lag % 개선·ghost CNR 감소·상태 직렬화 왕복 재현을 확인한다(CLAUDE.md T4 주의: IRF 파라미터는 2단계 실측 대기 — 합성 IRF로 선검증).
- **용어 정의 — 합성 검증 컨텍스트(synthetic-validation context)**: 합성 시퀀스 fixture 시험 실행(기지 IRF 주입 → 보정 후 판정)을 가리키는 단일 용어이다. 이는 T0(SPEC-INFRA-001)의 **검증 모드(validation_mode — float64 병행 버퍼·단계별 중간 XFrame 보존 활성 상태)**와는 별개 개념이다. SPEC-CORR-001/LNSG-001의 동명 용어 정의를 계승한다.
- T0 계약 소비: lag 모듈은 XFrame(불변)을 입력받아 새 XFrame을 반환하는 처리 모듈이며 `process(XFrame, CalibSet, Params) -> XFrame` 계약을 따른다. 마스크 스택 비트플래그(DEFECT/SATURATION/INTERPOLATION), 이력 체인(`HistoryEntry.extra` 스칼라 진단 채널), 오케스트레이터 진입 게이트, `CANONICAL_ORDER`(offset→gain→defect→**lag**→line_noise→saturation→geometry→post)를 그대로 소비한다. 의존 방향은 `modules → common` 단방향(import-linter).
- **상태 보유 모듈(SWR-000-7 명시 예외)**: SWR-000-7은 순수함수형 계약의 예외로 "내부 상태는 lag 등 명시 선언 모듈만 허용, 상태도 컨테이너로 직렬화 가능해야 함"을 규정한다. lag 모듈은 이 예외에 해당하며, 프레임당 지수항 상태 {sᵢ}(각 프레임 화소 형상의 M개 상태면)를 유지한다. 이 내부 상태는 SWR-000-6이 금지하는 "사이드채널"이 아니라 SWR-000-7이 허용한 명시 상태이며, `serialize_state`로 XFrame 직렬화 가능하다.
- **CONTRACT-2 런타임 검증**: T0(SPEC-INFRA-001)는 `common/contract.py`의 `StatefulModule` 프로토콜(`serialize_state() -> XFrame` / `load_state(XFrame) -> None`)이 계약 계층에 존재함을 **구조적으로만** 확인하고, 상태 보유 모듈을 통한 런타임 왕복 검증을 T4로 이연했다(REQ-INFRA-CONTRACT-2). 본 SPEC이 그 첫 런타임 검증을 수행한다.
- **종류-단계 배선**: 오케스트레이터 `_KIND_BY_STAGE`는 `lag → lag`을 등재하므로 lag 단계 CalibSet은 `kind=LAG`가 강제된다(`common.calibset.CalibKind.LAG`). IRF 계수(aᵢ, bᵢ, M)는 CalibSet(LAG)의 data 페이로드에 소재한다.
- before/after 판정 중 first-frame lag %·ghost CNR은 T1 지표 엔진 `metrics/lag`(REQ-METRICS-LAG-1/2/5)를 소비한다. 단, 모듈은 `metrics`를 import할 수 없으므로(CONTRACT-3) 판정 로직은 **시험 코드(`tests/`)에서** 모듈과 엔진을 함께 소비한다.
- IRF 계수([B]), 합성 IRF 파라미터, 재현 허용오차는 전부 CalibSet/Params/외부 주입으로 외부화한다(하드코딩 금지). 등급은 SWR 부록 A를 따른다.
- EV 판정 수치(EVAL v1.1 XDET-EV-104 min/typ/max)는 **엔진·모듈 외부에서 주입**된다(측정=판정 분리, SPEC-METRICS/CORR/LNSG 계승). 참조값: first-frame lag 보정 후 ≤5%(min)/≤2%(typ, LTI 문헌 잔존 ≤1.4%)/≤0.5%(max, 비선형 NLCSC 문헌 ≤0.29%); ghost 비가시.
- **파이프라인 위치·시퀀스 구동**: lag은 defect 이후·line_noise 이전(`CANONICAL_ORDER`)에서 실행된다. `run_pipeline`은 단일 프레임을 처리하므로, 연속 촬영 시퀀스의 프레임 시퀀스 상태 threading은 신규 additive 시퀀스 러너 `pipeline/sequence.py`가 담당한다 — 프레임별 `run_pipeline`을 래핑하고 lag 인스턴스를 시퀀스 수명 동안 재사용한다. `run_pipeline`·`CANONICAL_ORDER`·진입 게이트 표면은 불변이다(「결정 필요/확인 사항」 1 확정; BLOCK #1 해소).

## Requirements (EARS)

### REQ-LAG-CORR — Lag 보정 알고리즘 + Ghost 트리거 인터페이스 (SWR-401~404, FR-C005/C006)

- **REQ-LAG-CORR-1 (Ubiquitous)** — lag 모듈은 IRF를 지수합 모델 h[n] = Σᵢ₌₁..M aᵢ·bᵢⁿ(M = 3~4, [L] 문헌 표준)로 표현하고 Gen 1은 LTI 보정 경로만 구현해야 한다(SWR-401). IRF 계수 aᵢ·bᵢ·차수 M은 실측 대기 [B]이므로 하드코딩하지 않고 CalibSet(kind=LAG)로 외부화한다(SWR-000-5 무단 기본값 대체 금지; offset `raw_saturation_threshold` 필수 Params 선례). 비선형 NLCSC 승급 경로는 LTI 잔존 초과 시 예약이며 Gen 1 범위 밖이다(Exclusions).
- **REQ-LAG-CORR-2 (Event-Driven)** — WHEN 연속 촬영 시퀀스의 프레임 k가 lag 단계에 입력되면, THEN 시스템은 각 지수항 상태를 sᵢ[k] = bᵢ·(sᵢ[k−1] + aᵢ·Î[k−1])로 갱신하고 보정 출력을 Î[k] = I[k] − Σᵢ sᵢ[k]로 산출해야 한다(SWR-402 상태변수 재귀; Î[k−1]은 직전 프레임의 **계산된** 보정 값 — SATURATION 화소에서는 보존된 출력이 아니라 계산값을 사용한다, REQ-LAG-CORR-5·「결정 필요/확인 사항」 6). 결정론적 단일 경로 — 조건부 분기 없음.
- **REQ-LAG-CORR-3 (Event-Driven)** — WHEN 연속 촬영 시퀀스가 개시되면, THEN 시스템은 촬영 전 forward-bias(FB) 실행 요청과 완료 확인을 수행하는 트리거 인터페이스를 제공해야 한다(SWR-404; FB 시퀀스 실행 자체는 패널 FW 소관 — SW는 인터페이스만 정의). P1 골든 모델에는 실 취득 계층이 없으므로 인터페이스는 요청/완료 핸드셰이크 계약(스텁)으로 실현되고 mock으로 시험된다. 이 FB 트리거 스텁은 시퀀스 러너(`pipeline/sequence.py`)가 소유·호출한다(「결정 필요/확인 사항」 4 확정).
- **REQ-LAG-CORR-4 (Unwanted)** — IF FB 이후 잔존 ghost가 남으면, THEN 시스템(SW)은 이를 추가로 감쇠(전용 ghost 모델링·외삽)하려 시도하지 않아야 한다(SWR-404 — 잔존 ghost SW 감쇠는 Gen 1 범위 외, 필요성은 실측 후 판정). SWR-402 LTI 보정이 연속 시퀀스에서 공간 구조 잔상(ghost)을 부산물로 감소시키는 것은 본 금지의 대상이 아니며 전용 감쇠와 구분된다.
- **REQ-LAG-CORR-5 (Unwanted)** — IF 화소에 SATURATION 마스크가 설정되어 있으면, THEN lag 모듈은 그 화소의 출력 값을 변경해서는 안 된다(포화점 아래 값 미생성; `modules/line_noise.py` SATURATION 보존·SWR-602 복원 금지 취지 일관). 단, 내부 상태 재귀는 그 화소에서도 보존된 출력이 아니라 계산된 감산 값 Î[k−1]로 진행하여 상태 진화가 물리적으로 유지되어야 한다(「결정 필요/확인 사항」 6 확정; D7 축). 결정론적 — 조건부 분기 없음. EC-6·DoD가 본 요구를 추적한다.

### REQ-LAG-STATE — 상태 관리 (SWR-000-7, REQ-INFRA-CONTRACT-2 런타임 검증)

- **REQ-LAG-STATE-1 (Ubiquitous)** — lag 모듈은 SWR-000-7이 명시 허용한 내부 상태 보유 모듈로서, 프레임당 지수항 상태 {sᵢ}(각 프레임 화소 형상의 M개 상태면)를 연속 촬영 순서로 유지해야 한다(순수함수형 예외 — SWR-000-7 "내부 상태는 lag 등 명시 선언 모듈만 허용").
- **REQ-LAG-STATE-2 (Event-Driven)** — WHEN 상태 직렬화가 요청되면, THEN 시스템은 내부 상태 {sᵢ}를 XFrame 컨테이너로 직렬화(`serialize_state() -> XFrame`)하고 그 XFrame으로부터 상태를 복원(`load_state(XFrame) -> None`)할 수 있어야 하며, 직렬화→복원 왕복은 상태를 정확히 보존해야 한다(REQ-INFRA-CONTRACT-2, `StatefulModule` 프로토콜). 상태는 컨테이너 외 사이드채널로 유지되지 않아야 한다(SWR-000-6). M개 상태면은 (M, ny, nx) float32 pixel + zeros 마스크로 XFrame 패킹되며 dtype을 float32로 고정해 왕복이 바이트 동일하다(「결정 필요/확인 사항」 2 확정).
- **REQ-LAG-STATE-3 (Ubiquitous)** — 상태 재귀는 결정론적이어야 한다: 동일 IRF·동일 입력 시퀀스·동일 초기 상태(sᵢ[−1] = 0)에 대해 보정 출력과 최종 상태가 바이트 재현되어야 한다(SWR-000-1 float 골든 모델, IEC 62304 재현).
- **REQ-LAG-STATE-4 (Event-Driven)** — WHEN 새로운 연속 촬영 시퀀스가 개시되면, THEN 시스템은 상태를 초기값(sᵢ[−1] = 0)으로 재설정하여 이전 시퀀스 상태가 누출되지 않도록 해야 한다(시퀀스 간 리셋 시맨틱 — 시퀀스 러너 `pipeline/sequence.py`가 시퀀스 개시 시 lag 인스턴스를 신규화하여 리셋; 별도 리셋 프로토콜 메서드 없음, 「결정 필요/확인 사항」 1 확정; 결정론적, 무단 잔존 없음).
- **REQ-LAG-STATE-5 (Event-Driven)** — WHEN 연속 촬영 시퀀스의 프레임들이 순차 처리되면, THEN 시스템은 프레임 k의 최종 상태를 프레임 k+1의 초기 상태로 이어받아 재귀를 지속해야 한다. 단일 프레임 `process` 계약(SWR-000-7)·단일 프레임 `run_pipeline`은 시퀀스 threading을 정의하지 않으므로, 구동은 신규 additive 시퀀스 러너 `pipeline/sequence.py`가 담당한다 — 프레임별 `run_pipeline`을 래핑하고 lag 인스턴스를 시퀀스 수명 동안 재사용하여 프레임 간 상태를 이어받는다(「결정 필요/확인 사항」 1 확정; `run_pipeline`·`CANONICAL_ORDER` 표면 불변).

### REQ-LAG-IRF — IRF 피팅 도구 (오프라인 캘리브레이션, SWR-401)

- **REQ-LAG-IRF-1 (Event-Driven)** — WHEN 복수 노출(포화의 2~90% 범위 다점) rising/falling step-response 시퀀스가 IRF 피팅 도구에 입력되면, THEN 도구는 지수합 IRF 계수(aᵢ, bᵢ, M = 3~4)를 피팅하여 CalibSet(kind=LAG)로 산출해야 한다(SWR-401). 피팅 도구는 오프라인 캘리브레이션 도구이며 파이프라인 처리 모듈이 아니다(배치는 「결정 필요/확인 사항」 5 — `metrics/` 빌더 선례).
- **REQ-LAG-IRF-2 (Unwanted)** — IF 단일 노출만으로 IRF 캘리브레이션을 시도하면, THEN 도구는 이를 거부해야 한다(SWR-401 "단일 노출 캘리브레이션 금지" — IRF는 측정 기법·노출 수준에 민감 [L]). 결정론적 거부(명시 오류).
- **REQ-LAG-IRF-3 (State-Driven)** — WHILE 실측 step-response 미도착(2-1 실측 대기, [B])인 동안, 시스템은 기지 지수합 IRF(합성 aᵢ, bᵢ, M 주입)로 피팅 도구·보정 엔진을 선검증해야 한다(CLAUDE.md T4 합성 IRF 선검증). 합성 IRF로 생성한 계단 응답을 피팅 도구에 입력하면 주입 계수를 허용오차 내로 복원해야 한다. 실측 [B] 계수 확정은 범위 밖이다(Exclusions).

### REQ-LAG-CONTRACT — 공통 모듈 계약 준수 (SWR-000-2~12, REQ-INFRA-* 소비)

- **REQ-LAG-CONTRACT-1 (Ubiquitous)** — lag 모듈은 단일 시그니처 `process(XFrame, CalibSet, Params) -> XFrame`를 노출해야 하며(SWR-000-7, REQ-INFRA-CONTRACT-1), 입력 XFrame을 불변으로 취급(원본 미변경)하고 새 XFrame을 반환해야 한다(SWR-000-3, REQ-INFRA-DATA-6). 내부 상태 보유는 SWR-000-7이 lag에 명시 허용한 예외이며, 그 상태는 REQ-LAG-STATE-2에 따라 XFrame으로 직렬화 가능해야 한다.
- **REQ-LAG-CONTRACT-2 (Event-Driven)** — WHEN lag 모듈이 출력 XFrame을 생성하면, THEN 시스템은 처리 메타(모듈 버전·파라미터 해시·소비 CalibSet ID)를 이력 체인에 결정론적으로 추가해야 한다(SWR-000-4, REQ-INFRA-DATA-4, IEC 62304 추적).
- **REQ-LAG-CONTRACT-3 (Ubiquitous)** — 의존 방향은 `modules → common` 단방향이어야 하며, lag 모듈은 다른 처리 모듈·`pipeline`·`metrics`를 import해서는 안 된다(SWR-000-8, REQ-INFRA-STATIC import-linter 계약). first-frame lag·ghost CNR 판정 엔진(`metrics/lag`) 소비는 `tests/`에서만 이뤄진다. 실행 순서·조합은 오케스트레이터 단독 소관이며 모듈 간 직접 호출은 금지된다(REQ-INFRA-ORCH-1/2).
- **REQ-LAG-CONTRACT-4 (Unwanted)** — IF 등록된 lag 단계의 CalibSet이 부재하거나 불일치(해상도·패널 ID·유효기간, 그리고 종류-단계 배선 `lag→LAG`)하면, THEN 오케스트레이터 진입 게이트가 처리를 거부하고 위반 단계·필드를 명시한 오류를 발생시켜야 한다(무단 기본값 대체 금지, SWR-000-5, REQ-INFRA-ORCH-4).
- **REQ-LAG-CONTRACT-5 (Unwanted)** — IF lag 모듈이 XFrame 컨테이너 외 채널(전역 상태·부가 반환값·파일 우회)로 데이터를 전달하려 하면, THEN 시스템은 이를 계약 위반으로 취급해야 한다(SWR-000-6 사이드채널 금지). 자동 검출 가능 범위는 시그니처·부가 반환값 위반(계약 검사)과 의존 방향 위반(import-linter 정적 검사)이며(acceptance.md EC-4의 검증 범위와 동일), 전역 상태·파일 우회는 테스트 가능 AC가 아닌 설계 규칙으로서 코드 리뷰 게이트로 다룬다(SPEC-INFRA-001 REQ-INFRA-DATA-2 방식 계승). 단, lag의 내부 상태(REQ-LAG-STATE-1)는 SWR-000-7 명시 허용 예외이며 `serialize_state`로 XFrame 직렬화 가능하므로 금지된 사이드채널이 아니다.
- **REQ-LAG-CONTRACT-6 (Ubiquitous)** — lag 모듈은 고정 파이프라인 순서 `CANONICAL_ORDER`의 lag 위치(offset→gain→defect→lag→line_noise→…)에서만 실행되어야 하며(SWR-000-2, REQ-INFRA-ORCH-3; 등록 stages는 `CANONICAL_ORDER`의 부분수열), 합성 입력 + 기대 출력 fixture로 harness 단독 시험이 가능해야 한다(SWR-000-11, XDET-TC-000). 단, 상태 보유 모듈이므로 harness는 사전 상태(`load_state`) 주입·사후 상태(`serialize_state`) 대조를 포함하도록 확장되어야 한다(단일 호출 순수함수 가정의 확장; 「결정 필요/확인 사항」 3).

### REQ-LAG-VALIDATE — 합성 검증 + 보정 효과 판정 (XDET-TC-004~005, EV-104)

- **REQ-LAG-VALIDATE-1 (State-Driven)** — WHILE 실측 step-response·GDS 미도착 합성 검증 컨텍스트인 동안, 시스템은 기지 지수합 IRF를 주입한 합성 연속 시퀀스에 대해 lag 보정이 잔상을 억제함을 보여야 한다(DoD 전제, CLAUDE.md T4).
- **REQ-LAG-VALIDATE-2 (Event-Driven)** — WHEN 포화 근접 노출 후 잔상 시퀀스(기지 IRF 주입)에 lag 보정을 적용하면, THEN 시스템은 `tests/`에서 T1 엔진 `metrics/lag.compute_first_frame_lag`로 보정 전/후 first-frame lag %를 산출하여 보정 후가 EV-104 min(≤5%) 이내이고 보정 전 대비 개선됨을 판정 가능해야 한다(XDET-TC-004, 측정프로토콜 §1.5; REQ-METRICS-LAG-1/2 소비). 기지 IRF의 해석적 잔존 lag가 ground truth이다.
- **REQ-LAG-VALIDATE-3 (Event-Driven)** — WHEN 고대비 패턴 프레임 후 균일 조사 프레임으로 구성된 합성 연속 시퀀스(기지 IRF 주입)에 lag 보정을 적용하면, THEN 시스템은 `tests/`에서 `metrics/lag.compute_ghost_cnr`로 균일 프레임의 잔상 CNR을 산출하여 보정 후가 보정 전 대비 감소함을 판정 가능해야 한다(XDET-TC-005, 측정프로토콜 §1.5; REQ-METRICS-LAG-5 소비). ghost 감소는 SWR-402 재귀가 공간 구조 잔상을 부산물로 감산한 결과이다(전용 ghost 감쇠 아님 — REQ-LAG-CORR-4). EV-104 ghost "비가시"의 최종 운영 판정은 FB(패널 FW) 의존이므로 T4는 부분 게이트이다(「결정 필요/확인 사항」 6).
- **REQ-LAG-VALIDATE-4 (Event-Driven)** — WHEN lag 모듈의 내부 상태를 시퀀스 중간에 직렬화(`serialize_state`)한 뒤 새 인스턴스에 복원(`load_state`)하고 시퀀스를 이어 처리하면, THEN 시스템은 중단 없이 처리한 경우와 바이트 동일한 보정 출력·최종 상태를 산출해야 한다(상태는 (M, ny, nx) float32로 XFrame 패킹되고 dtype 고정으로 직렬화 왕복이 바이트 동일 — 「결정 필요/확인 사항」 2 확정; REQ-INFRA-CONTRACT-2 T4 런타임 검증; 상태 직렬화 왕복·결정론). 이 시나리오가 T0에서 이연된 상태 직렬화 인터페이스의 첫 런타임 검증이다.
- **REQ-LAG-VALIDATE-5 (Ubiquitous)** — XDET-EV-104 min/typ/max 판정 수치는 EVAL v1.1/Params에서 외부 주입되어야 하며, 검증은 산출값과 외부 임계의 비교로만 이뤄져야 한다(측정=판정 분리). 모듈·판정 코드는 게이트 임계를 내장하지 않는다.
- **REQ-LAG-VALIDATE-6 (Ubiquitous)** — 시험 케이스 XDET-TC-004 · XDET-TC-005는 현재 pytest skeleton(skip)에서 합성 입력·판정 연동의 실동작 케이스로 전환되어야 한다(REQ-INFRA-CI-1 계승). lag 모듈은 `metrics`를 import하지 않으므로 판정은 `tests/`에서 모듈 + `metrics/lag`를 함께 소비한다.

## Exclusions (What NOT to Build)

- **비선형(NLCSC) 승급 없음** — SWR-401의 비선형 lag 보정(NLCSC, 문헌 잔존 ≤0.29%)은 Gen 1 범위 밖. LTI 지수합 보정만 구현하며, LTI 잔존이 EV-104 초과 시의 NLCSC 승급은 예약 경로로만 문서화한다.
- **노출 구간별 IRF 세트 전환 없음** — SWR-403의 노출 의존 비선형(강노출 후 IRF 변화) 확인·노출 구간별 파라미터 세트 전환은 2-1 실측 후 판정([B])이므로 Gen 1은 단일 LTI IRF 세트만 사용한다. CalibSet(LAG) 스키마가 다중 세트 확장을 원천 배제하지는 않으나 전환 로직은 구현하지 않는다.
- **FB 시퀀스 실행 없음** — SWR-404의 forward-bias 시퀀스 실행은 패널 FW 소관. SW는 트리거 인터페이스(FB 요청/완료 확인)만 정의한다(REQ-LAG-CORR-3).
- **전용 잔존 ghost SW 감쇠 없음** — SWR-404 — 잔존 ghost의 전용 SW 감쇠(ghost 전용 모델링·외삽)는 Gen 1 범위 밖(실측 후 필요성 판정). SWR-402 재귀의 부산물 ghost 감소만 관측한다(REQ-LAG-CORR-4).
- **실측 IRF [B] 계수 확정 없음** — aᵢ·bᵢ·M의 실측 확정은 2-1 step-response 취득 후. 합성 IRF만으로 엔진·도구를 선검증한다(REQ-LAG-IRF-3).
- **실 GDS 판정 없음** — GDS-lag/GDS-ghost 실영상 판정은 2단계 실측 도착 후. 합성 시퀀스(기지 IRF 주입)만으로 검증한다.
- **first-frame lag/ghost CNR 측정 엔진 구현 없음** — `metrics/lag`(first-frame lag %·ghost CNR 산출)는 SPEC-METRICS-001(T1) 소관. T4는 `tests/`에서 소비만 하며 재구현하지 않는다.
- **EV 게이트 임계 내장 없음** — XDET-EV-104 min/typ/max(EVAL v1.1)는 외부 주입. 처리 모듈·판정 코드는 합격/불합격 임계를 내장하지 않는다.
- **후속·타 WP 처리 모듈 없음** — 선행 offset/gain/defect(SWR-101~304/T2)·line noise·포화·기하(SWR-501~603/T3)와 후속 VST+BM3D(SWR-701~706/T5)·MSE/DRC·GSDF(SWR-801~903/T6)·grid 억제(T7)·virtual grid(T8)·NDT(T9)·티어/동일성(T10)은 T4 범위 밖.
- **성능·처리시간·티어 게이트 없음** — EV-401/402, XDET-TC-020/021은 P2. SWR-402의 O(M·N_pixels)는 복잡도 서술이며 속도 최적화 요구가 아니다.
- **Gen 2 항목 없음** — DL 기반 처리·ADR은 P1 범위 밖.

## 결정 필요/확인 사항

SWR 조항이 T0/T1 구현과 모호하거나 상충하는 지점. plan-audit 반복 1에서 orchestrator가 「1·2·4·6」을 **확정(RESOLVED)**했고 「3·5」는 확인 대상으로 남는다(임의 해소하지 않음). 확정 항목은 각 항목 앞에 `[확정 — RESOLVED]` + 결정 + rationale로 표기하며, 항목 번호는 불변(Environment/Exclusions/HISTORY/plan 교차 참조 유지)이다.

1. **[확정 — RESOLVED] 프레임 시퀀스 상태 threading·구동 위치** — lag 보정(SWR-402)은 본질적으로 시퀀스 연산(sᵢ[k]가 sᵢ[k−1]·Î[k−1]에 의존)이나, `process` 계약은 단일 프레임을 처리하고 `pipeline/orchestrator.run_pipeline`은 단일 프레임을 스테이지 순서대로 실행할 뿐 연속 촬영 시퀀스를 순회하는 루프가 없다. **결정**: 신규 additive 시퀀스 러너 `pipeline/sequence.py`가 시퀀스 구동을 담당한다 — 프레임별 `run_pipeline`을 래핑하고, lag 상태 보유 인스턴스 수명 = 시퀀스 수명(시퀀스 개시 시 인스턴스 신규화 = 리셋; 별도 리셋 프로토콜 메서드 없음, REQ-LAG-STATE-4/5), FB 트리거는 러너가 호출한다(결정 4). `run_pipeline`·`CANONICAL_ORDER`·진입 게이트·REQ-LAG-CONTRACT-1 표면은 불변(additive — T0 표면 변경 없음)이고, 구동 경로는 `pipeline/`(프로덕션)에 두며 `tests/`가 아니다. **rationale**: 시퀀스 러너를 별도 파일로 추가하면 시퀀스 threading을 프로덕션 경로에 두면서도 T0 단일 프레임 계약을 건드리지 않아 BLOCK 후보를 해소한다; 인스턴스 수명=시퀀스 수명으로 리셋을 표현하면 프로토콜 표면 확장이 불필요하다.
2. **[확정 — RESOLVED] 상태 {sᵢ}의 XFrame 패킹** — `serialize_state`는 XFrame을 반환하나 lag 상태는 M개 per-pixel 상태면이다. **결정**: M개 상태면을 (M, ny, nx) float32 pixel + zeros 마스크로 단일 XFrame에 패킹한다(XFrame `__post_init__`는 ndim 제약이 없어 3차원 pixel 허용). 상태 dtype은 float32로 고정한다. **rationale**: (M,ny,nx) 스태킹은 T0 XFrame 확장 없이 M개 상태면을 컨테이너로 직렬화 가능하게 하고(CONTRACT-2), dtype float32 고정은 serialize→load 왕복을 바이트 동일하게 만들어(D5) REQ-LAG-VALIDATE-4의 바이트 재현을 성립시킨다.
3. **harness 확장(상태 보유 모듈)** — `common/contract.run_harness`·`check_process_contract`는 단일 호출 순수함수 의미(입력→출력 XFrame 전체 비교)를 가정한다. 상태 보유 모듈은 사전 상태·사후 상태가 결과의 일부다. **가정 default**: harness fixture를 확장하여 `load_state`로 사전 상태를 주입하고 `serialize_state`로 사후 상태를 대조한다(단일 호출 비교 + 상태 왕복 비교). **확인**: harness API 확장 범위(T0 계약 계층 수정 필요 여부).
4. **[확정 — RESOLVED] Ghost 트리거 인터페이스 배치·형상** — P1 골든 모델에는 실 취득 계층이 없다. **결정**: FB 트리거 스텁(요청/완료 핸드셰이크)은 시퀀스 러너(`pipeline/sequence.py`)가 소유·호출하고 mock으로 시험한다(SWR-404 "인터페이스만 정의"). **rationale**: FB는 시퀀스 개시 시점(러너 소관, REQ-LAG-CORR-3)에 촬영 전 요청/완료로 발생하므로 시퀀스 구동을 담당하는 러너가 트리거의 자연스러운 소유자이며, P1에는 실 취득 계층이 없으므로 스텁+mock 이상은 불필요하다.
5. **IRF 피팅 도구 배치** — 오프라인 캘리브레이션 빌더로서 CalibSet(LAG)를 산출한다. **가정 default**: `metrics/lag_irf.py`(캘리브레이션 빌더, `metrics/defect_map.py` 선례) — `metrics → common` 단방향, CalibSet(LAG) emit. 처리 모듈의 `metrics` import 금지는 `modules/`만 관장하므로 빌더가 `metrics/`에 있어도 계약 위반이 아니다(SPEC-CORR-001 defect_map 선례). **확인**: `metrics/` vs 별도 `calibration/` 패키지 배치.
6. **[확정 — RESOLVED] 마스크 상호작용(포화 화소 값 보존)·XDET-TC-005 게이트 범위** — lag은 offset의 raw 포화 검출(REQ-CORR-OFFSET-4, SATURATION 플래그) 이후에 실행된다. 포화(클램프) 화소에서 상태 Σsᵢ를 감산하면 포화점 아래 값을 생성해 SWR-602 복원 금지 취지를 위반할 수 있다. **결정**: SATURATION 화소의 출력 값은 보존한다(포화점 아래 값 미생성; `modules/line_noise.py` SATURATION 보존·SWR-602 취지 일관). 단, 내부 상태 재귀는 그 화소에서도 보존된 출력이 아니라 계산된 감산 값 Î[k−1]로 진행하여 상태 진화가 물리적으로 유지된다(D7 축). 이 규칙은 REQ-LAG-CORR-5(Unwanted)로 승급했다(D1). XDET-TC-005는 부분 게이트(ghost CNR 감소만 T4 합성 검증; ghost 종단 비가시 운영 판정은 FB/실 패널 통합 후, LNSG EV-106 부분 게이트 선례)로 등록한다(D6). **rationale**: 포화점 아래 값 생성은 SWR-602 복원 금지에 저촉되므로 출력 보존이 필수이나, 상태 재귀까지 동결하면 후속 프레임 상태가 비물리적으로 얼어붙는다 — 출력 보존과 상태 진화(계산값 사용)를 분리하면 두 제약을 모두 만족한다.
