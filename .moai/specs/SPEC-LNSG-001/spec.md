---
id: SPEC-LNSG-001
version: 0.2.0
status: implemented
created: 2026-07-09
updated: 2026-07-09
author: drake.lee
priority: high
issue_number: 4
---

# SPEC-LNSG-001 — T3 WP3 line noise 보정 + WP4 포화·기하 처리 모듈 (modules/)

XDET 영상처리 SW P1의 네 번째 작업 T3(WP3+WP4). line noise 보정·포화 처리·기하 보정 처리 모듈 3종(`modules/line_noise.py` · `modules/saturation.py` · `modules/geometry.py`)을 T0 프레임워크의 단일 계약 `process(XFrame, CalibSet, Params) -> XFrame` 순수함수형으로 구현한다. 세 모듈은 고정 파이프라인 순서 offset → gain → defect → lag → **line noise → 포화 → 기하** → post 중 해당 위치(오케스트레이터 `CANONICAL_ORDER`의 `line_noise` → `saturation` → `geometry`)에서만 실행된다. line noise 보정은 **레퍼런스 영역 부재를 전제로 한 SWR-503 대안 경로를 우선 구현**하고, 레퍼런스 기반 SWR-501/502 경로는 조건부(Optional)로 둔다.

- 근거: SWR-501~504(line noise, FR-C007) · SWR-601~602(포화, FR-C008) · SWR-603(기하, FR-C009) · SWR-000-2~12(아키텍처) — `docs/XDET_SWR_spec_v1.2.md`; EVAL v1.1 EV-105(line noise)/EV-106(포화 복원·기하 잔차); TestSpec XDET-TC-006~009
- 완료 정의(DoD): **합성 주입 왜곡 억제·처리를 검증** — 실측 영상 도착 전, 기지 line noise/포화/기하 왜곡을 주입한 합성 팬텀에 각 처리를 적용하고 (a) line noise 제거는 T1 지표 엔진 `metrics/nps.detect_line_noise`로 보정 전/후 1D NPS 저주파 이상 피크 제거를 판정(SWR-504 + REQ-METRICS-NPS-8 확장(행/열)), (b) 구조물 오염 오보정률·(c) 포화 마스크 통합·경계 밴드·복원 금지 사후조건·(d) 기하 잔차는 `tests/`에서 ground truth 대조 직접 측정으로 판정한다. XDET-TC-006~009를 pytest skeleton(skip)에서 실동작 케이스로 전환하여 EV-105/106 min 대비 통과
- 선행 계약: [SPEC-INFRA-001](../SPEC-INFRA-001/spec.md) — `process` 계약·XFrame 불변·마스크 스택(DEFECT/SATURATION/INTERPOLATION)·이력 체인·오케스트레이터 진입 게이트(종류-단계 배선·해상도·패널 ID·유효기간)·import-linter 레이어링(`module → common` 단방향)·`CANONICAL_ORDER`; [SPEC-METRICS-001](../SPEC-METRICS-001/spec.md) — line noise 정량화 판정 엔진 `metrics/nps.detect_line_noise`(REQ-METRICS-NPS-8, 행/열 1D NPS 저주파 이상 피크); [SPEC-CORR-001](../SPEC-CORR-001/spec.md) — 선행 처리 모듈(offset/gain/defect), offset 단계의 raw 포화 검출(REQ-CORR-OFFSET-4, S_th `raw_saturation_threshold`) 및 gain 클램프의 SATURATION 플래그 설정 계약
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.2.0 (2026-07-09)** — 구현 완료(status: implemented). 커밋 7ab0338(모듈 3종+OFFSET-4) + 리뷰 결함 10건 수정. 156 passed / 14 skipped(2회 동일), 레이어링 계약 5건 KEPT. 구현 중 확정:
  - geometry 활성 보정은 마스크 스택을 비트플레인별 nearest-neighbor 역워프로 수송하고, 경계 충전 픽셀은 DEFECT로 무효화.
  - MaskFlag.SATURATION_BAND(=8) 신설 — 2px 경계 밴드는 core SATURATION과 분리(멱등성). T5 소비자는 두 플래그를 함께 제외해야 함.
  - line_noise는 SATURATION 픽셀 값을 변경하지 않음(클램프 보존). 고역 제한은 FFT 저역 컷 방식(비주기 wrap-seam은 [T] 경계 내 문서화).
  - raw_saturation_threshold는 offset 필수 Params([B], 무단 기본값 대체 금지).

- **v0.1.1 (2026-07-09)** — plan-audit iteration 1 (PASS 0.89; D1 mandatory + ambiguity-2 BLOCK) 결함 반영 + orchestrator 결정 2 확정:
  - **결정 2 확정(raw 포화 검출 = offset 단계)**: raw 포화 검출(I_raw ≥ S_th)은 I_raw를 입력 프레임으로 받는 유일한 단계인 첫 파이프라인 단계 **offset**이 감산 전에 수행하며(SPEC-CORR-001 REQ-CORR-OFFSET-4로 이관, v0.2.1), S_th는 offset 단계 Params 키 `raw_saturation_threshold`([B])에 단일 소재한다. T3 포화 모듈은 offset(raw) ∪ gain 클램프로 누적된 SATURATION 마스크를 소비하여 경계 밴드 2px 팽창·복원 금지 사후조건·통계 메타데이터만 담당한다. **rationale**: 처리 모듈 계약(`process(XFrame,CalibSet,Params)->XFrame`)은 보존된 중간 XFrame에 접근할 수 없어 후반 단계가 raw를 재검출할 수 없다. REQ-LNSG-SAT-1·Environment·「결정 필요/확인 사항」 2 정정.
  - **D1(major, mandatory)**: REQ-LNSG-SAT-3·EC-2 복원 금지 사후조건 (3)을 "포화 처리가 INTERPOLATION 플래그를 새로 설정하지 않는다(입력에 이미 존재하던 플래그는 보존)"로 재서술 — 상류 defect 단계 INTERPOLATION과 SATURATION의 적법 공존 반영.
  - **D2**: REQ-LNSG-LINE-1의 창 length·고역 컷오프는 Params([T])로 확정 유지, 「결정 필요/확인 사항」 1의 하위 확인 (ii)(Params vs CalibSet)를 삭제(중복 이접 제거 — L49와 일관).
  - **D3**: S_th 단일 소재를 offset 단계 Params `raw_saturation_threshold`로 고정(spec·plan의 "S_th 또는 Params 위임" 이접 서술 제거) — 결정 2로 해소.
  - **D4**: REQ-LNSG-LINE-1을 WHERE-form Optional("WHERE CalibSet(LINE_NOISE)가 reference 영역을 제공하지 않으면 …")로 재구조화 — REQ-LNSG-LINE-2(reference 제공)와 상호배타 보완쌍.
  - **D5**: REQ-LNSG-VALIDATE-1(합성 검증 컨텍스트 전제)의 커버리지 노트를 acceptance DoD 헤더에 추가(Scenario 6~9로 충족).
  - **D6**: line noise 판정 엔진 인용을 "SWR-504 + REQ-METRICS-NPS-8 확장(행/열)"로 정정(REQ-LNSG-VALIDATE-2·DoD·선행 계약).
  - status: draft 유지(run 단계 착수 전까지).

- **v0.1.0 (2026-07-09)** — 초안 생성. GitHub 이슈 #4. 5개 요구 그룹(LINE/SAT/GEOM/CONTRACT/VALIDATE) EARS 구조 확정. 핵심 범위 결정:
  1. **line noise 우선 경로 = SWR-503(레퍼런스 부재)**: 패널 비조사/차폐 reference 영역 좌표는 [B](ROIC/패널 사양 대기, SWR-501)이므로, 열 방향 저주파 프로파일 감산 + 고역 제한(SWR-503)을 우선(mandatory) 경로로 구현한다. 레퍼런스 기반 행 단위 보정(SWR-501/502, 6·MAD 오염 배제)은 CalibSet(LINE_NOISE)가 reference 영역을 제공할 때의 조건부(Optional) 경로로 둔다. 경로 선택은 CalibSet 내용(reference 영역 유무)으로 결정론적으로 이뤄진다 — 「결정 필요/확인 사항」 1.
  2. **line noise 판정 엔진 재사용**: 보정 효과(1D NPS 저주파 이상 피크 제거, SWR-504)는 T1 엔진 `metrics/nps.detect_line_noise`로 `tests/`에서 판정한다. 처리 모듈은 `metrics`를 import하지 않으므로(CONTRACT-3) 판정은 시험 코드에서 모듈+엔진을 함께 소비한다.
  3. **포화 = 검출·마스킹·복원 금지, 복원 없음**: 포화 화소(원취득값 ≥ S_th, [B])는 SATURATION 마스크로 표시·하류 전달(제외 가중 대상)하고, 경계 밴드(2px)를 완충 가중 대상으로 표시하며, 포화 영역 "복원"은 절대 금지한다(SWR-602 [HARD]). gain 클램프가 설정한 SATURATION 플래그(SPEC-CORR-001 v0.2.0)와 합집합으로 통합 — 「결정 필요/확인 사항」 2·3.
  4. **기하 = 조건부 활성**: 격자 팬텀 캘리브레이션 저차 다항 왜곡 모델(차수 [B], 2-6)이 CalibSet(OTHER)로 제공되고 캘리브레이션 잔차가 EV-106 min 이상일 때만 보정을 적용하고, 잔차가 EV-106 min 미만이면(FPD 직접 촬상 왜곡 미미) 모듈을 비활성(무처리 통과)한다(SWR-603).
  5. **노이즈 모델 미갱신**: line noise 감산은 XFrame 노이즈 모델(α, σ)을 재추정·변경하지 않는다(노이즈 추정은 SWR-701/T5 소관, SPEC-CORR-001 결정 2 계승).
  - 파라미터 등급 확정(SWR 부록 A 대조): reference 영역 좌표(SWR-501)=[B], SWR-503 창 length·고역 컷오프=[T], SWR-503 방법=[C] 관행, 포화 임계 S_th(SWR-601)=[B], 기하 다항 차수(SWR-603)=[B]. SWR-502 오염 배제 계수(6·MAD)·SWR-602 경계 밴드 폭(2px)은 SWR 본문 명시 상수이나 부록 A 미등재 — Params 외부화하되 등급 미부여(부록 A 등재 필요, 「결정 필요/확인 사항」 6).
  - status: draft (run 단계 착수 전까지 유지).

## Environment / Assumptions

- Python 3.11+, numpy/scipy 기반 float 골든 모델 (tech.md). **속도 최적화 금지 — 정확도 단일 목표**(P2에서 최적화).
- 대상 프레임: 3072×3072 / 3072×2560, 16-bit unsigned raw, pitch 140µm, Nyquist f_N = 3.57 lp/mm(EVAL v1.1 §0).
- **실측 영상 도착 전 — 합성 데이터로 처리 모듈을 검증한다.** 기지 line noise(행/열 저주파 오프셋)·포화 영역(좌표·강도)·기하 왜곡(격자 팬텀 변위)을 주입한 합성 프레임을 생성하고, 처리 후 왜곡 억제·포화 마스킹·기하 잔차 감소를 확인한다(CLAUDE.md T3 주의: reference 부재 시 SWR-503 대안 경로 우선; 합성 데이터로 엔진·모듈 선검증).
- **용어 정의 — 합성 검증 컨텍스트(synthetic-validation context)**: 합성 팬텀 fixture 시험 실행(기지 왜곡 주입 → 처리 후 억제·판정)을 가리키는 단일 용어이다. 이는 T0(SPEC-INFRA-001)의 **검증 모드(validation_mode — float64 병행 버퍼·단계별 중간 XFrame 보존이 활성인 상태)**와는 별개 개념이다. SPEC-CORR-001의 동명 용어 정의를 계승한다.
- T0 계약 소비: 세 모듈은 XFrame(불변)을 입력받아 새 XFrame을 반환하는 처리 모듈이며 `process(XFrame, CalibSet, Params) -> XFrame` 계약을 따른다. 마스크 스택 비트플래그(DEFECT/SATURATION/INTERPOLATION), 이력 체인, 오케스트레이터 진입 게이트, `CANONICAL_ORDER`(…lag → line_noise → saturation → geometry → post)를 그대로 소비한다. 의존 방향은 `modules → common` 단방향(import-linter).
- **종류-단계 배선**: 오케스트레이터 `_KIND_BY_STAGE`는 `line_noise → LINE_NOISE`를 등재하므로 line noise 단계 CalibSet은 `kind=LINE_NOISE`가 강제된다. `saturation`·`geometry` 단계는 `_KIND_BY_STAGE`에 없으므로 종류-단계 배선이 강제되지 않으며, 두 단계의 CalibSet은 `CalibKind.OTHER`로 등록한다(존재·해상도·패널 ID·유효기간 게이트는 여전히 적용).
- **SATURATION 마스크 통합**: 포화 단계 입력의 SATURATION 마스크는 상류 offset 단계의 raw 포화 검출(I_raw ≥ S_th, SPEC-CORR-001 REQ-CORR-OFFSET-4)과 gain 단계 65535 클램프(SPEC-CORR-001 REQ-CORR-GAIN-2)가 각각 설정한 플래그가 마스크 스택에 누적된 **합집합**이다. raw 포화 검출은 I_raw를 입력 프레임으로 받는 유일한 단계인 offset이 수행하며(「결정 필요/확인 사항」 2 확정), T3 포화 모듈은 이 누적 마스크를 소비하여 경계 밴드·복원 금지 사후조건·통계 기록만 담당한다(raw 재검출 없음).
- before/after 판정 중 line noise 제거는 T1 지표 엔진 `metrics/nps.detect_line_noise`(1D NPS 저주파 이상 피크·MAD 유의성 검정)를 소비한다. 단, 모듈은 `metrics`를 import할 수 없으므로(CONTRACT-3) 판정 로직은 **시험 코드(`tests/`)에서** 모듈과 엔진을 함께 소비한다. 구조물 오염 오보정률·포화 사후조건·기하 잔차는 T1 엔진에 대응 함수가 없으므로 `tests/`에서 ground truth 대조 직접 측정으로 판정한다.
- 물리·튜닝·[B] 상수(SWR-503 창 length·고역 컷오프, 포화 임계 S_th[offset 단계 `raw_saturation_threshold`, SPEC-CORR-001 소재], 기하 다항 차수, reference 영역 좌표, 오염 배제 계수, 경계 밴드 폭)는 전부 Params/CalibSet로 외부화한다(하드코딩 금지). 등급은 SWR 부록 A를 따른다.
- EV 판정 수치(EVAL v1.1 EV-105/106 min/typ/max)는 **엔진·모듈 외부에서 주입**된다(측정=판정 분리, SPEC-METRICS-001·CORR-001 계승).

## Requirements (EARS)

### REQ-LNSG-LINE — Line noise 보정 (SWR-501~504, FR-C007)

- **REQ-LNSG-LINE-1 (Optional)** — WHERE CalibSet(LINE_NOISE)가 reference 영역을 제공하지 않으면(P1 우선 경로), line noise 모듈은 열 방향 저주파 프로파일(행별 강건 평균 → 1D median, 창 length [T])을 추정하여 감산하되, 해부학 저주파 보호를 위해 감산 성분에 고역 제한(컷오프 [T])을 적용해야 한다(SWR-503, 방법 등급 [C] 관행). 창 length·고역 컷오프는 TBD-[T](부록 A)로 Params에 외부화한다. 이 경로(reference 부재)와 REQ-LNSG-LINE-2(reference 제공)는 CalibSet(LINE_NOISE)의 reference 영역 유무로 상호배타적·결정론적으로 선택되는 보완쌍이다(「결정 필요/확인 사항」 1).
- **REQ-LNSG-LINE-2 (Optional)** — WHERE CalibSet(LINE_NOISE)가 패널의 비조사/차폐 reference 영역 좌표(TBD-[B], SWR-501)를 제공하면, 시스템은 레퍼런스 기반 행 단위 보정을 적용해야 한다: 행 r의 reference 픽셀 집합에서 중앙값 m(r)을 산출하여 행 전체에서 감산하고(SWR-502), |m(r) − median(m)| > k·MAD(k = 오염 배제 계수, SWR-502 명시값 6, Params 외부화)인 행은 인접 행 보간값을 사용해 금속 구조물·직접선 오염을 배제해야 한다. reference 영역이 제공되지 않으면 본 요구는 적용되지 않으며 REQ-LNSG-LINE-1(SWR-503) 경로를 사용한다.
- **REQ-LNSG-LINE-3 (Ubiquitous)** — line noise 모듈은 프로파일·행 중앙값 등 강건 통계를 산출할 때 XFrame 마스크의 DEFECT·INTERPOLATION·SATURATION 화소를 통계에서 제외 가중해야 하며(오염 방지, SWR-000-9 강건통계·마스크연산 공용 컴포넌트 소비), XFrame 노이즈 모델(α, σ)을 재추정·변경하지 않아야 한다(노이즈 추정은 SWR-701/T5 소관 — SPEC-CORR-001 결정 2 계승).

### REQ-LNSG-SAT — 포화 처리 (SWR-601~602, FR-C008)

- **REQ-LNSG-SAT-1 (Event-Driven)** — WHEN 포화 모듈이 입력 XFrame을 처리하면, THEN 시스템은 상류 단계에서 누적된 SATURATION 마스크(offset 단계의 raw 포화 검출 I_raw ≥ S_th — SPEC-CORR-001 REQ-CORR-OFFSET-4 ∪ gain 클램프 65535 — SPEC-CORR-001 REQ-CORR-GAIN-2)를 그대로 소비·하류 전달해야 한다(하류 denoiser·대비강화의 제외 가중 대상, SWR-601). raw 포화 검출 임계 S_th는 offset 단계 Params 키 `raw_saturation_threshold`(TBD-[B], 부록 A; 선량 계단에서 응답 포화점 실측, 통상 full-scale의 ~98%)에 단일 소재하며, 포화 모듈은 raw 신호를 재검출하지 않는다(모듈 계약은 보존된 중간 XFrame에 접근 불가이며 offset이 I_raw를 소비하는 유일 단계 — 「결정 필요/확인 사항」 2 확정).
- **REQ-LNSG-SAT-2 (Event-Driven)** — WHEN 포화 단계가 누적 SATURATION 마스크를 소비하면, THEN 시스템은 포화 영역 경계 밴드(폭 W_band, SWR-602 명시값 2px, Params 외부화)를 완충 가중 대상으로 표시하여 하류 링잉을 억제해야 한다(SWR-602). 경계 밴드의 XFrame 표현 방식은 「결정 필요/확인 사항」 3.
- **REQ-LNSG-SAT-3 (Unwanted)** — IF 포화 화소에 대해 신호 "복원"(외삽·재구성으로 포화점 아래 값 생성)을 시도하는 처리가 존재하면, THEN 시스템은 이를 금지하고 다음 사후조건을 정확히 만족해야 한다: (1) 포화 화소값이 입력과 동일하게 보존되고, (2) SATURATION 플래그가 유지되며, (3) 포화 처리가 INTERPOLATION 플래그를 새로 설정하지 않는다(입력에 이미 존재하던 플래그는 보존 — 상류 defect 단계 INTERPOLATION과 SATURATION의 적법 공존)(허위 신호 생성 위험, SWR-602 [HARD] 복원 금지). 결정론적 단일 경로 — 조건부 복원 분기 없음.
- **REQ-LNSG-SAT-4 (Event-Driven)** — WHEN 포화 모듈이 출력 XFrame을 생성하면, THEN 시스템은 포화 통계(포화 화소 비율 등 스칼라)를 해당 처리 단계의 이력 체인 엔트리 메타데이터에 기록해야 한다(SWR-601 하류 전달·기록 요구의 P1 실현; DICOM 태그 실제 emission은 출력 포맷 소관으로 Exclusions). 컨테이너 외 사이드채널·부가 반환값 금지(SWR-000-6).

### REQ-LNSG-GEOM — 기하 보정 (SWR-603, FR-C009)

- **REQ-LNSG-GEOM-1 (Optional)** — WHERE 격자 팬텀 캘리브레이션 기반 저차 다항 왜곡 모델(차수 TBD-[B], 2-6; SWR-603)이 CalibSet(OTHER, geometry 단계)로 제공되고 그 캘리브레이션 잔차가 EV-106 min(기하 왜곡 잔차 ≤1 px) 이상이면, 시스템은 해당 왜곡 모델로 기하 보정을 적용하여 보정 후 잔차를 EV-106 min 이내로 낮춰야 한다. 다항 차수는 TBD-[B](2-6 실측 잔차로 결정)로 Params/CalibSet에 외부화한다.
- **REQ-LNSG-GEOM-2 (State-Driven)** — WHILE 제공된 기하 캘리브레이션 잔차가 EV-106 min 미만인 동안(FPD 직접 촬상 왜곡 미미), 시스템은 기하 모듈을 비활성 상태(무처리 통과 — 입력 XFrame을 왜곡 보정 없이 반환)로 유지해야 한다(SWR-603 조건부 비활성). 활성/비활성 판정은 잔차 대 EV-106 min 비교로 결정론적으로 이뤄진다(무단 기본값·추정 없음).

### REQ-LNSG-CONTRACT — 공통 모듈 계약 준수 (SWR-000-2~12, REQ-INFRA-* 소비)

- **REQ-LNSG-CONTRACT-1 (Ubiquitous)** — line_noise/saturation/geometry 세 모듈은 각각 단일 시그니처 `process(XFrame, CalibSet, Params) -> XFrame` 순수함수형이어야 하며(SWR-000-7, REQ-INFRA-CONTRACT-1), 입력 XFrame을 불변으로 취급(원본 미변경)하고 새 XFrame을 반환해야 한다(SWR-000-3, REQ-INFRA-DATA-6).
- **REQ-LNSG-CONTRACT-2 (Event-Driven)** — WHEN 각 모듈이 출력 XFrame을 생성하면, THEN 시스템은 처리 메타(모듈 버전 · 파라미터 해시 · 소비 CalibSet ID)를 이력 체인에 결정론적으로 추가해야 한다(SWR-000-4, REQ-INFRA-DATA-4, IEC 62304 추적).
- **REQ-LNSG-CONTRACT-3 (Ubiquitous)** — 의존 방향은 `modules → common` 단방향이어야 하며, 모듈은 다른 처리 모듈 · `pipeline` · `metrics`를 import해서는 안 된다(SWR-000-8, REQ-INFRA-STATIC import-linter 계약). 실행 순서·조합은 오케스트레이터 단독 소관이며 모듈 간 직접 호출은 금지된다(REQ-INFRA-ORCH-1/2). line noise 정량화 엔진(`metrics/nps.detect_line_noise`) 소비는 `tests/`에서만 이뤄진다.
- **REQ-LNSG-CONTRACT-4 (Unwanted)** — IF 처리 모듈이 XFrame 컨테이너 외 채널(전역 상태 · 부가 반환값 · 파일 우회)로 데이터를 전달하려 하면, THEN 시스템은 이를 계약 위반으로 취급해야 한다(SWR-000-6 사이드채널 금지). 자동 검출 가능 범위는 시그니처·부가 반환값 위반(계약 검사)과 의존 방향 위반(import-linter 정적 검사)이며(acceptance.md EC-4의 검증 범위와 동일), 전역 상태·파일 우회는 테스트 가능 AC가 아닌 설계 규칙으로서 코드 리뷰 게이트로 다룬다(SPEC-INFRA-001 REQ-INFRA-DATA-2 방식 계승).
- **REQ-LNSG-CONTRACT-5 (Unwanted)** — IF 등록된 line_noise/saturation/geometry 단계의 CalibSet이 부재하거나 불일치(해상도 · 패널 ID · 유효기간, 그리고 line_noise 단계는 종류-단계 배선 line_noise→LINE_NOISE)하면, THEN 오케스트레이터 진입 게이트가 처리를 거부하고 명시 오류를 발생시켜야 한다(무단 기본값 대체 금지, SWR-000-5, REQ-INFRA-ORCH-4). saturation/geometry 단계는 `_KIND_BY_STAGE` 미등재로 종류 강제는 없으나 CalibSet(OTHER)의 존재·해상도·패널 ID·유효기간은 게이트 대상이다.
- **REQ-LNSG-CONTRACT-6 (Ubiquitous)** — 세 모듈은 고정 파이프라인 순서 `CANONICAL_ORDER`의 line_noise → saturation → geometry 위치에서만 실행되어야 하며(SWR-000-2, REQ-INFRA-ORCH-3; 등록 stages는 `CANONICAL_ORDER`의 부분수열), 각 모듈은 합성 입력 + 기대 출력 fixture로 harness 단독 시험이 가능해야 한다(SWR-000-11, XDET-TC-000).

### REQ-LNSG-VALIDATE — 합성 검증 + 왜곡 억제 판정 (XDET-TC-006~009, EV-105/106)

- **REQ-LNSG-VALIDATE-1 (State-Driven)** — WHILE 실측 영상 도착 전 합성 검증 컨텍스트인 동안, 시스템은 기지 line noise/포화/기하 왜곡을 주입한 합성 프레임에 대해 각 모듈이 왜곡을 억제·처리함을 보여야 한다(DoD 전제, CLAUDE.md T3).
- **REQ-LNSG-VALIDATE-2 (Event-Driven)** — WHEN 균일 조사 합성 프레임에 기지 행/열 line noise를 주입하고 line noise 보정을 적용하면, THEN 시스템은 T1 엔진 `metrics/nps.detect_line_noise`로 보정 전 행/열 방향 1D NPS의 저주파 이상 피크가 검출되고 보정 후 유의성 임계(median + sig_factor·MAD) 이하로 미검출됨을 판정 가능해야 한다(SWR-504 + REQ-METRICS-NPS-8 확장(행/열), XDET-TC-006 EV-105 min "잔존 line artifact 비가시" — 표준 window의 관측 가능 대리 지표 = 1D NPS 이상 피크 미검출).
- **REQ-LNSG-VALIDATE-3 (Event-Driven)** — WHEN 금속 구조물 오염을 모사한(기지 ground truth 동반) 합성 프레임에 line noise 보정을 적용하면, THEN 시스템은 구조물 영역 오보정률(ground truth 대비 허위 변경 화소 비율)을 `tests/`에서 산출하여 EV-105 min(구조물 오염 오보정률 ≤1%) 이내임을 판정 가능해야 한다(XDET-TC-007). 오보정 억제는 활성 경로에 따른다 — 레퍼런스 경로(REQ-LNSG-LINE-2)는 오염 행 k·MAD 배제(SWR-502), 우선 경로(REQ-LNSG-LINE-1)는 고역 제한 + 마스크 제외에 의한다(「결정 필요/확인 사항」 5).
- **REQ-LNSG-VALIDATE-4 (Event-Driven)** — WHEN 기지 포화 영역을 주입한 합성 프레임에 포화 처리를 적용하면, THEN 시스템은 `tests/`에서 (a) offset 단계 검출(raw ≥ S_th, SPEC-CORR-001 REQ-CORR-OFFSET-4)로 설정된 SATURATION 플래그가 포화 단계 출력에 전수 보존됨, (b) 경계 밴드(W_band)가 완충 가중 대상으로 표시됨, (c) 복원 금지 사후조건(포화 화소값 불변 · SATURATION 유지 · INTERPOLATION 신규 미설정[기존 보존])을 판정 가능해야 한다(XDET-TC-008 EV-106 min "포화 영역 경계 아티팩트 비가시"의 T3 게이트 범위 = 마스크 통합·경계 밴드·복원 금지 메커니즘). 최종 경계 아티팩트 비가시(denoiser·대비강화 후 종단 판정)는 T5/T6 의존으로 T3 범위 밖이다(「결정 필요/확인 사항」 4).
- **REQ-LNSG-VALIDATE-5 (Event-Driven)** — WHEN 기지 기하 왜곡을 주입한 격자 팬텀 합성 프레임에 기하 보정을 적용하면, THEN 시스템은 `tests/`에서 보정 후 격자선 잔차(격자선 위치 대 이상 격자 위치의 변위)를 산출하여 EV-106 min(기하 왜곡 잔차 ≤1 px) 이내임을 판정 가능해야 한다(XDET-TC-009). 잔차가 애초 EV-106 min 미만이면 모듈 비활성(REQ-LNSG-GEOM-2)이 관측됨을 함께 확인한다.
- **REQ-LNSG-VALIDATE-6 (Ubiquitous)** — EV-105/106 min/typ/max 판정 수치는 EVAL v1.1/Params에서 외부 주입되어야 하며, 검증은 산출값과 외부 임계의 비교로만 이뤄져야 한다(측정=판정 분리 계승). 처리 모듈·판정 코드는 게이트 임계를 내장하지 않는다.
- **REQ-LNSG-VALIDATE-7 (Ubiquitous)** — 시험 케이스 XDET-TC-006 · XDET-TC-007 · XDET-TC-008 · XDET-TC-009는 현재 pytest skeleton(skip)에서 합성 입력·판정 연동의 실동작 케이스로 전환되어야 한다(REQ-INFRA-CI-1 계승). 모듈은 `metrics`를 import하지 않으므로 line noise 판정은 `tests/`에서 모듈 + `metrics/nps.detect_line_noise`를 함께 소비하고, 오보정률·포화 사후조건·기하 잔차는 `tests/` ground truth 대조 직접 측정으로 판정한다.

## Exclusions (What NOT to Build)

- **후속·타 WP 처리 모듈 없음** — VST+BM3D 노이즈 저감(SWR-701~706/T5), MSE/DRC·자동 윈도잉·GSDF(SWR-801~805·901~903/T6), grid 억제(SWR-1001~1006/T7), 커널 virtual grid(SWR-1101~1103/T8), NDT(SWR-1201~1204/T9), 티어·동일성(SWR-1301~1303/T10)은 T3 범위 밖. 선행 offset/gain/defect(SWR-101~304/T2)·lag(SWR-401~404/T4)도 본 SPEC 범위 밖(T4 lag은 파이프라인상 line noise 앞이나 별개 SPEC).
- **하류 가중 적용 없음** — 포화 마스크·경계 밴드는 T3가 substrate(마스크·표시)만 생성한다. 실제 denoiser 블록 매칭 제외 가중(SWR-706)·대비강화 제외 가중의 **적용**은 T5/T6 소관이다. 따라서 EV-106 "포화 경계 아티팩트 비가시"의 종단 판정도 T5/T6에서 재실행된다(T3는 부분 게이트, 「결정 필요/확인 사항」 4).
- **노이즈 모델 재추정 없음** — 노이즈 모델(α, σ) 추정·갱신은 SWR-701(T5) 소관. line noise 감산·포화·기하 모듈은 노이즈 모델을 재추정하지 않는다(결정 5).
- **DICOM 태그 실제 emission 없음** — SWR-601의 포화 마스크 DICOM 태그 기록은 출력 포맷/DICOM 직렬화 소관으로 P1 골든 모델 범위 밖. T3는 포화 통계를 이력 체인 메타데이터에 기록한다(REQ-LNSG-SAT-4).
- **레퍼런스 영역 좌표 [B] 확정 없음** — SWR-501의 패널 비조사/차폐 reference 영역 좌표(ROIC/패널 사양 대기, [B])는 확정하지 않는다. 레퍼런스 경로(REQ-LNSG-LINE-2)는 Optional로만 두고, P1 우선 경로는 SWR-503(레퍼런스 부재)이다.
- **[B] 값 확정 없음** — 포화 임계 S_th(SWR-601, 선량 계단 실측), 기하 다항 차수(SWR-603, 2-6 실측 잔차)의 실측 [B] 값 확정은 범위 밖. Optional/조건부 경로 + 외부 주입만 둔다.
- **⚠P·특허 대조 없음** — SWR-501의 ⚠P(reference 영역) 특허 대조는 릴리스 게이트로 이연(사양 §부록 B). 본 SPEC은 대안 설계(SWR-503) 우선 구현으로 회피.
- **실 캘리브레이션 데이터·GDS 채우기 없음** — 합성 팬텀(기지 왜곡 주입)만으로 모듈을 검증한다. 실 line noise·포화·격자 팬텀 실영상(GDS) 판정은 2단계 실측 도착 후.
- **EV 게이트 임계 내장 없음** — EV-105/106 min/typ/max 판정 수치(EVAL v1.1)는 외부 주입. 처리 모듈·판정 코드는 합격/불합격 임계를 내장하지 않는다.
- **성능·처리시간·티어 게이트 없음** — EV-401/402, XDET-TC-020/021은 P2.
- **Gen 2 항목 없음** — DL 기반 처리·ADR은 P1 범위 밖.

## 결정 필요/확인 사항

SWR 조항이 T0/T1 구현과 모호하거나 상충하는 지점. 「2」는 orchestrator 결정으로 확정(RESOLVED, HISTORY v0.1.1 반영)하고, 「1·3·4·5·6」은 run 착수 전 확인 대상으로 남긴다(임의 해소하지 않음). 각 확인 항목은 가정 default를 명시하되 최종 확정은 orchestrator 결정을 따른다.

1. **line noise 경로 선택과 오케스트레이터 게이트** — SWR-503(레퍼런스 부재) 우선 경로는 reference 좌표가 필요 없으나, 오케스트레이터 진입 게이트(`_calibration_gate`)는 등록된 모든 단계에 CalibSet 존재를 요구하고 `_KIND_BY_STAGE`는 line_noise→LINE_NOISE를 강제한다. **가정 default**: line_noise 단계는 CalibSet(LINE_NOISE)를 항상 요구(SWR-000-5 무단 대체 금지)하며, 그 CalibSet이 reference 영역 좌표를 담으면 REQ-LNSG-LINE-2(SWR-501/502), 담지 않으면(reference-availability 필드가 없음/빈 값) REQ-LNSG-LINE-1(SWR-503)을 **결정론적으로** 선택한다(런타임 휴리스틱·"A 또는 B" 없음). 확인: reference-free 모드를 CalibSet(LINE_NOISE)로 표현할지 아니면 line_noise 단계를 게이트 예외로 둘지(SWR-503 튜닝 파라미터 창 length·컷오프는 Params([T])로 확정 — REQ-LNSG-LINE-1과 일관, v0.1.1 D2로 하위 확인 삭제).
2. **[확정 — RESOLVED] SWR-601 원취득값(I_raw) 검출 단계** — 포화 단계는 `CANONICAL_ORDER`상 후반(offset/gain/defect/lag/line_noise 이후)이라 raw 원취득값이 이미 변형된다. **확정**: raw 포화 검출(I_raw ≥ S_th)은 I_raw를 입력 프레임으로 받는 유일한 단계인 첫 파이프라인 단계 **offset**이 수행한다 — offset이 감산 전에 I_raw ≥ S_th 화소에 SATURATION 플래그를 설정한다(SPEC-CORR-001 REQ-CORR-OFFSET-4로 이관, v0.2.1). S_th는 offset 단계 Params 키 `raw_saturation_threshold`([B], 통상 full-scale ~98%)에 단일 소재한다(D3 함께 확정 — S_th 이접 소재 제거). T3 포화 모듈은 offset(raw) ∪ gain 클램프로 누적된 SATURATION 마스크를 소비하여 경계 밴드 2px 팽창·복원 금지 사후조건·통계 메타데이터만 담당한다(REQ-LNSG-SAT-1~4). **rationale**: 처리 모듈 계약(`process(XFrame,CalibSet,Params)->XFrame`)은 보존된 중간 XFrame(검증 모드 산물)에 접근할 수 없으므로 후반 단계가 raw를 재검출할 수 없다. offset이 raw를 소비하는 유일 단계이므로 검출 소재를 offset으로 고정하면 검증 모드 의존·경로 분기가 제거된다.
3. **SWR-602 경계 밴드(2px) 표현** — XFrame 마스크 스택은 비트플래그(DEFECT/SATURATION/INTERPOLATION)로 "완충 가중"용 가중 채널이 없다. **가정 default**: 경계 밴드를 SATURATION 마스크의 W_band(2px) 팽창으로 표시(전면 제외의 보수적 근사)하고, 실제 graded 완충 가중은 가중을 소유하는 denoiser(T5)가 적용한다. 확인: 신규 마스크 플래그/가중 채널 도입(T0 XFrame 확장) vs SATURATION 팽창 근사 중 선택.
4. **EV-106 "포화 경계 아티팩트 비가시" 게이트 범위** — 최종 비가시는 denoiser·대비강화(T5/T6) 후에야 관측 가능하다. **가정 default**: T3는 XDET-TC-008을 검출·마스킹·복원 금지 메커니즘까지 **부분 게이트**하고(REQ-LNSG-VALIDATE-4), 종단 비가시 판정은 T5/T6에서 재실행한다. 확인: XDET-TC-008을 T3 부분 게이트 + T5/T6 종단 게이트로 분할 등록할지.
5. **XDET-TC-007 오보정률 게이트 경로** — 6·MAD 오염 배제(SWR-502)는 Optional 레퍼런스 경로(REQ-LNSG-LINE-2) 소관이고, P1 우선 경로(SWR-503)의 구조물 보호는 고역 제한 + 마스크 제외이다. **가정 default**: 오보정률을 활성 경로 기준으로 EV-105 min과 비교한다(우선 경로는 SWR-503 고역 제한, 레퍼런스 fixture 제공 시 SWR-502 6·MAD도 검증). 확인: P1 합성 검증에서 레퍼런스 경로 fixture(reference 영역 포함 CalibSet)를 포함할지.
6. **SWR-502 오염 배제 계수(6·MAD)·SWR-602 경계 밴드 폭(2px)의 부록 A 등재** — 두 상수는 SWR 본문 명시이나 부록 A(TBD 레지스터·등급 총괄) 미등재이다. **가정 default**: Params로 외부화하되(SWR 본문 값 6·2px 기본값) 등급은 미부여로 두고 부록 A 등재를 요청한다(SPEC-CORR-001의 `line_max_width` 부록 A 등재 선례). 확인: [T]/[P] 중 어느 등급으로 등재할지.
