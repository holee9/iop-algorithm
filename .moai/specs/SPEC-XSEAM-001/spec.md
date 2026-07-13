---
id: SPEC-XSEAM-001
version: 0.1.1
status: draft
created: 2026-07-11
updated: 2026-07-11
author: drake.lee
priority: medium
issue_number: 50
labels: [xseam, productization, csharp-ui, engine-contract, pythonnet]
---

# SPEC-XSEAM-001 — 언어 중립 엔진 심(seam) + C# UI 스켈레톤 (P1.5 제품화 확장 얇은 수직 슬라이스)

> **역사적 기준:** 이 SPEC은 현재 `apps/xdet-console/`에 구현된 P1.5 얇은 수직 슬라이스의 원 설계 기록이다. 초기 `.NET 8` 가정은 실제 소스의 `.NET 9`로 대체됐으며, 전체 알고리즘 GUI 확장의 현재 규범은 `SPEC-XGUI-MASTER` v0.5.1 후보와 `SPEC-XSEAM-002`다. 본 문서의 전체 범위·버전 가정을 신규 구현 기준으로 사용하지 않는다.

XDET 영상처리 SW의 **제품화(productization) 확장 P1.5** 계획이다. 최종 제품은 C++/C# 구조로 이행해야 하므로, 본 SPEC은 (1) 구현 언어에 독립적인 **엔진 심(engine seam)** — C# 인터페이스 `IXdetEngine` + XFrame/CalibSet/Params/MetricResult 직렬화 데이터 계약 — 과 (2) 그 심을 소비하는 **C# UI 스켈레톤**을, 기존 Python 골든 모델은 **동결된 레퍼런스 오라클(frozen oracle)** 로 그대로 둔 채 정의한다. P1.5는 아키텍처를 end-to-end로 증명하는 **얇은 수직 슬라이스**만 만든다: 모듈 1개(`offset`) + 지표 1개(MTF)를 C# UI에서 심을 거쳐 Python 골든으로 구동하고 결과를 표시하며, 그 결과가 Python 골든 직접 출력과 **동일함(fidelity)** 을 단언한다. 본 SPEC은 계획 + 상세 사양 + 인수 기준이며 **구현은 포함하지 않는다**(C++ 미구현).

**심(seam)은 durable(내구) 계약이고 어댑터는 교체 가능하다.** P1.5에서 `IXdetEngine`은 **pythonnet in-process 어댑터**(`PythonNetXdetEngine`)로 실현되어 **실제 Python 골든 엔진**(`modules.offset.process`, `metrics.mtf.compute_mtf`)을 호출한다 — DSP를 C#에서 재구현하지 않는다. 이후 P2에서 **C++ ABI 위의 `NativeXdetEngine`** 가 동일한 `IXdetEngine`을 구현하므로 UI는 바뀌지 않으며, C++ 포트는 T10/XDET-TC-020~021 동일성 프레임(정수 경로 bit-동일 / 부동소수점 경로 ±1 LSB)을 적합성 게이트로 통과해야 한다.

- 근거(변경 없음): `CLAUDE.md` 아키텍처 강제 규칙(SWR-000-6~12: XFrame 단일 I/O 컨테이너, `process(XFrame,CalibSet,Params)->XFrame` 단일 시그니처, 사이드채널 금지, CalibSet 공통 스키마) · `CLAUDE.md` T10 / XDET-TC-020~021(티어/동일성 프레임 + diff 검증 훅, 정수 bit-동일 / float ±1 LSB — 포팅·최적화 구현을 골든에 대해 검증하는 사전 설계 메커니즘) · `common/equivalence.py::diff_frames(a,b)->EquivalenceDiff`(T10 동일성 비교 훅) · `common/xframe.py`(XFrame: pixel float32 + mask 스택 + noise model + history 체인) · `common/contract.py`(Params) · `common/calibset.py`(CalibSet 스키마) · `modules/offset.py::process`(얇은 슬라이스 모듈) · `metrics/mtf.py::compute_mtf`(얇은 슬라이스 지표)
- 선례/상속 원칙: [SPEC-VIEWER-001](../SPEC-VIEWER-001/spec.md) — Python 검증 GUI(status: implemented)의 [HARD] 원칙을 C#으로 상속한다. **읽기-실행 전용**(C-20: 골든 fixture/CalibSet에 절대 쓰지 않음), **지표 자체 계산 0**(C-09: UI는 DSP를 스스로 계산하지 않고 실제 엔진 호출 결과만 표시), **단방향 소비**(C-11: UI는 코어를 import만 하고 코어는 UI를 역참조하지 않음). C# UI는 같은 아이디어의 다른 언어 구현이다.
- 완료 정의(DoD): P1.5 얇은 수직 슬라이스가 다음을 성립 — (1) `Xdet.Engine.Contract` 계약 어셈블리 빌드(언어 중립 `IXdetEngine` + DTO, pythonnet 의존 0, XDET-TC-080) → (2) `PythonNetXdetEngine` in-process 어댑터가 실제 골든을 호출·왕복(XDET-TC-081/082) → (3) C# WPF + ScottPlot UI 스켈레톤이 모듈 검증기 슬라이스(offset)·지표 뷰(MTF)를 심 경유로 구동(XDET-TC-083/084) → (4) **fidelity 단언**: 심 경유 결과가 Python 골든 직접 출력과 `diff_frames`로 XDET-TC-021 허용오차 내 일치(XDET-TC-085/086) → (5) Python 골든·VIEWER-001·import-linter 무변경 + C# 솔루션 격리 + C++ P2 swap 문서화(XDET-TC-087). 절대 시간·전체 모듈/지표 커버리지·C++ 구현은 범위 밖.
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.1.1 (2026-07-11)** — plan-auditor 결함 교정(판정 ACCEPT-WITH-NITS 0.86 반영, D1–D7). **D1** [major]: REQ-XSEAM-FIDELITY-2를 **XFrame(offset) 경로로 한정** — `common.equivalence.diff_frames`는 XFrame만 받으므로 offset fidelity에만 적용하고, MTF(MetricResult) 경로는 요소별 수치 동일성(element-wise numeric equality) 비교로 REQ-XSEAM-FIDELITY-3에 분리(모순 해소, Scenario 7과 정합). **D2** [soundness]: MTF는 P1.5에서 순수 float64 트랜스포트이므로 관측 delta를 **정확히 0**으로 고정(FIDELITY-3) — ±1 LSB는 P2 C++ 재계산 몫으로 예약된 envelope이며 P1.5 트랜스포트가 소비하지 않는다; 지표 경로 **음성 신뢰성 섭동 시험**(>1 LSB 섭동 → FAIL)을 acceptance Edge cases에 추가(offset 섭동 시험 미러). **D3** [latent]: DTO가 `XFrame.pixel_f64`(검증 모드 float64 병렬 버퍼)를 누락 → P1.5 얇은 슬라이스를 **float32 단일 경로(`pixel_f64=None`) 합성 프레임으로 한정**하고 `pixel_f64` 전송을 P2 전방 범위로 명시(CONTRACT-2 + plan §1.2 + Exclusions). **D4** [convention]: plan/acceptance의 맨 `TC-NNN`을 전부 `XDET-TC-NNN`으로 접두(GUI_CRITERIA §5). **D5** [style]: Unwanted REQ(CONTRACT-4·ADAPTER-4/5·UI-5·COEXIST-3·FORWARD-4)의 후행 비양태 문장 제거 — 각 단일 양태 결과로 종료. **D6** [imprecision]: Environment "byte-동일"→"값-동일(`equal_nan` 포함)"(diff_frames 값 동일성 정확화). **D7** [convention]: 정규 REQ 본문의 발명 구현명(`PythonNetXdetEngine` 어댑터 클래스, `NativeXdetEngine`, `Xdet.Engine.Contract` 어셈블리명)을 plan.md으로 이관 — 골든 시그니처 미러(`offset.process`·`compute_mtf`·`diff_frames`)와 durable 심 `IXdetEngine`은 계약의 WHAT이므로 유지. 확정 아키텍처(seam/adapter/UI/scope/coexistence) 무변경, EARS 총계 **27개 불변**.
- **v0.1.0 (2026-07-11)** — 초안 생성. GitHub 이슈 #50. 6개 요구 그룹(CONTRACT/ADAPTER/UI/FIDELITY/COEXIST/FORWARD) EARS 구조 확정, 총 27개 EARS 요구. 시험케이스 블록 **XDET-TC-080~087**(Gen 1 000~021 / VIEWER 030~037 / REALDATA 040~049 / ERGO 050~055 / CALDOM 060~067 / DQEDOC 070~073 범위 밖 신규 블록). 확정 설계 결정을 인코딩: (a) **엔진 심 = C# 인터페이스 `IXdetEngine` + 언어 중립 직렬화 계약** — durable 심; P1.5는 pythonnet in-process 어댑터로 실현하되 DSP 재구현 없음, 배열은 (dtype, shape, buffer) 삼중항으로 표현하여 미래 C++ 어댑터가 Python 런타임 없이 구현 가능. (b) **UI = WPF + .NET 8 + ScottPlot**(성숙한 엔지니어링급; WinUI 3는 문서화된 대안). (c) **범위(P1.5) = 얇은 수직 슬라이스** — `offset` 모듈 1개 + `MTF` 지표 1개를 C# → 심 → Python 골든으로 구동 + fidelity 단언. (d) **공존 = Python 골든(common/modules/pipeline/metrics)·SPEC-VIEWER-001 GUI 무변경**, C# 솔루션은 `apps/xdet-console/`(신규·분리). 저작 시 검증한 사실: `modules/offset.py::process`는 `raw_saturation_threshold` Params + CalibSet(OFFSET) `O_map`를 요구; `metrics/mtf.py::compute_mtf(frame, params)->MetricResult`는 단일 프레임 입력→플롯 가능한 곡선 산출(지표 슬라이스에 적합, DQE는 사전계산 MTF+NNPS 필요하므로 대안); `common/equivalence.py::diff_frames`는 pixel_equal/masks_equal/noise_equal/max_pixel_abs_diff/structurally_equal를 산출하는 기존 T10 훅(재사용, 재구현 없음). 3건의 열린 결정(심 트랜스포트 세부·C# 빌드/게이팅·apps 경로/버전)은 가정 기본값과 함께 「결정 필요/확인 사항」에 기재 — 어느 것도 run 착수를 차단하지 않는다.

## Environment / Assumptions

- **본 SPEC은 T-스테이지가 아니다.** `CANONICAL_ORDER` 스테이지 추가·`process(...)->XFrame` 시그니처 변경·신규 `CalibKind`·`_KIND_BY_STAGE` 변경이 전혀 없다. Python 코어 4계층(`common/ modules/ pipeline/ metrics/`)과 오케스트레이터 표면은 불변이며, 본 SPEC은 그 위에 **새로운 C# 소비자**를 additive로 얹는 제품화 확장이다(VIEWER-001 검증 도구 계열의 확장 — 다른 언어).
- **골든 모델 = 동결된 레퍼런스 오라클.** Python 골든 모델(`common/modules/pipeline/metrics`)은 P1 형상 동결의 정답지이며 본 SPEC이 편집하지 않는다. C# 심은 이를 **읽기 전용으로 소비**한다(어댑터는 골든 함수를 unmodified 호출). 이는 SWR-000-6~12 아키텍처 계약의 언어 경계 넘어선 보존이다.
- **엔진 심(durable 계약).** C# 인터페이스 `IXdetEngine`이 durable 심이다. 최소 두 진입점 — 모듈 처리(`process(XFrame,CalibSet,Params)->XFrame` 미러)와 지표 산출(`compute_*(...)->MetricResult` 미러) — 을 노출한다. `IXdetEngine`과 DTO는 독립 계약 어셈블리 `Xdet.Engine.Contract`에 있으며 **pythonnet/Python 런타임 의존이 0**이다. 배열은 언어 중립 `(dtype, shape, 연속 버퍼)` 삼중항으로 직렬화하여 Python-ism이 심 표면으로 새지 않고, 미래 C++ 백엔드가 C ABI로 구현 가능하다.
- **P1.5 어댑터 = pythonnet in-process(트랜스포트, 재계산 아님).** `PythonNetXdetEngine`이 `IXdetEngine`을 구현하며 pythonnet으로 CPython을 .NET 프로세스에 임베드하여 **실제 골든**을 호출한다 — 모듈 처리는 `modules.offset.process`로, 지표 산출은 `metrics.mtf.compute_mtf`로 디스패치. C# 측은 어떤 DSP도 계산하지 않으므로(VIEWER-001 C-09 상속), 심은 순수 트랜스포트이고 왕복 버퍼는 Python 골든 출력과 **값-동일(`equal_nan` 포함 — `diff_frames`는 바이트가 아니라 값 동일성을 검증)**해야 한다(±1 LSB 예산은 P2에서 C++가 실제 DSP를 재계산할 때를 위한 예비 envelope). 대용량 3072² float32 배열 마샬링 비용이 문제될 경우 로컬 IPC/RPC 폴백을 예비로 두되 P1.5 슬라이스는 소형 배열이라 in-process로 충분하다(「결정 필요/확인 사항」 1).
- **UI = WPF + .NET 8 + ScottPlot.** C# UI는 `IXdetEngine`과 DTO만 소비하고 DSP를 스스로 계산하지 않는다(C-09). 모듈 검증기 슬라이스(입력/출력/diff 표시)와 지표 뷰(ScottPlot 곡선 플롯)를 제공한다. 코어·엔진 계약은 UI를 역참조하지 않는다(C-11 단방향). UI는 골든 fixture/CalibSet/`data/`에 쓰지 않고 내보내기는 사용자 지정 디렉터리로만(C-20 읽기-실행 전용). WinUI 3는 문서화된 대안이다.
- **얇은 수직 슬라이스(P1.5 범위).** 모듈 1개 = `offset`(`process(XFrame,CalibSet,Params)->XFrame`, 요구 Params `raw_saturation_threshold`, CalibSet(OFFSET) `O_map` 소비), 지표 1개 = `MTF`(`compute_mtf(frame, params)->MetricResult`, 단일 프레임→MTF(f) 곡선). 합성 입력(작은 offset raw 프레임 + 합성 CalibSet(OFFSET) + 합성 edge-slab ROI 프레임)으로 구동한다. 전체 12개 모듈·7개 지표 커버리지는 범위 밖.
- **Fidelity 동일성 프레임(load-bearing).** 심 경유 결과가 Python 골든 직접 출력과 XDET-TC-021 허용오차 내 일치함을 단언한다. 비교는 사전 설계된 T10 훅 `common.equivalence.diff_frames`(pixel/masks/noise 동일성 + `max_pixel_abs_diff` + `structurally_equal`)를 재사용한다 — C++ P2 포트를 게이트할 바로 그 메커니즘. P1.5 어댑터는 트랜스포트라 관측 delta는 정확히 0(bit-동일) 기대이며, ±1 LSB 초과 이탈은 마샬링 손상으로 FAIL 처리한다.
- **공존·격리(HARD).** Python 골든·SPEC-VIEWER-001 GUI(`apps/gui/`)는 본 SPEC으로 변경되지 않는다. C# 솔루션은 `apps/xdet-console/`(신규 분리 디렉터리)에 위치하며 `pyproject.toml` `packages`에 포함되지 않고 pytest가 수집하지 않는다. Python import-linter 계약은 green·불변(C# 측은 Python 의존 그래프에 비가시). 캡스톤 스캔(`tests/**/*.py` rglob, `_GEN1_TC_RANGE = range(0,22)`)은 Python 파일만 대상이라 C# 소스와 무간섭.
- **CI 경계.** 저장소 CI는 Python 전용이다. C# 빌드/테스트는 별도 툴체인(`dotnet build`/`dotnet test`)이며 P1.5에서는 문서화된 로컬 빌드 단계로 두고 Python 전용 CI에 강제하지 않는다(「결정 필요/확인 사항」 2). fidelity 골든 레퍼런스는 임베드된 Python 인터프리터 내부에서 `diff_frames`로 산출하여 별도 fixture 파일 의존을 최소화한다.
- **환경.** Python은 `uv run`으로만 실행(회귀 `uv run pytest`, 정적검사 `uv run lint-imports`). .NET은 .NET 8 LTS 툴체인(`dotnet`). 정확성·재현성이 목적이며 성능/배포 최적화는 목적이 아니다(P1 속도 최적화 금지 원칙 승계).

## Requirements (EARS)

### REQ-XSEAM-CONTRACT — 언어 중립 엔진 심: `IXdetEngine` 인터페이스 + 직렬화 계약 (SWR-000-6/7/10, C++ 구현가능성, XDET-TC-080)

- **REQ-XSEAM-CONTRACT-1 (Ubiquitous)** — C# 엔진 심은 언어 중립 인터페이스 `IXdetEngine`을 정의해야 하며, 골든의 `process(XFrame,CalibSet,Params)->XFrame`와 `compute_*(...)->MetricResult` 계약을 미러하는 모듈 처리 진입점과 지표 산출 진입점을 최소한 노출하여, 백엔드 구현과 무관하게 단일 인터페이스가 DSP 엔진을 추상화해야 한다.
- **REQ-XSEAM-CONTRACT-2 (Ubiquitous)** — 심은 언어 경계를 넘어 XFrame(pixel float32 버퍼 + mask 스택 + noise model (alpha,sigma) + history 체인), CalibSet(panel_id/resolution/유효기간/kind/data 페이로드/domain/beam_quality), Params(key→value 맵), MetricResult(name + named values + condition 메타데이터 + warnings)를 직렬화하는 데이터 계약을 정의해야 하며, P1.5 얇은 슬라이스는 float32 단일 경로 XFrame(`pixel_f64=None`)만 대상으로 하고 검증 모드 float64 병렬 버퍼(`pixel_f64`)의 직렬화 전송은 P2 전방 범위로 이연해야 한다.
- **REQ-XSEAM-CONTRACT-3 (Ubiquitous)** — 데이터 계약은 모든 수치 배열을 Python 객체가 아니라 명시적 `(dtype, shape, 연속 raw 버퍼)` 삼중항으로 언어 중립 표현해야 하며, 그 버퍼는 Python 런타임 없이 어떤 구현자도 재구성 가능해야 한다.
- **REQ-XSEAM-CONTRACT-4 (Unwanted)** — IF 심 계약이 `IXdetEngine` 표면이나 그 DTO에 Python 고유 타입(예: `PyObject`, pickle blob, numpy 전용 구성물)을 노출하면, THEN 이는 계약 위반으로 취급되어야 한다.
- **REQ-XSEAM-CONTRACT-5 (Ubiquitous)** — `IXdetEngine` 인터페이스와 DTO는 pythonnet 및 Python 런타임에 의존하지 않는 독립 계약 어셈블리에 있어야 하며, durable 심이 P1.5 어댑터로부터 분리되어야 한다.

### REQ-XSEAM-ADAPTER — pythonnet in-process 어댑터: 실제 골든 호출 (확정 결정, DSP 재구현 금지, XDET-TC-081/082)

- **REQ-XSEAM-ADAPTER-1 (Ubiquitous)** — P1.5 pythonnet in-process 어댑터는 pythonnet으로 실제 Python 골든 엔진을 in-process 호출하여 `IXdetEngine`을 구현해야 하며, 모듈 처리는 `modules.offset.process`로, 지표 산출은 `metrics.mtf.compute_mtf`(얇은 슬라이스 대상)로 디스패치해야 한다.
- **REQ-XSEAM-ADAPTER-2 (Event-Driven)** — WHEN 어댑터가 C#으로부터 직렬화된 XFrame/CalibSet/Params를 수신하면, THEN 대응하는 Python `common.xframe.XFrame`/`common.calibset.CalibSet`/`common.contract.Params` 객체를 재구성하여 골든 함수를 unmodified 호출해야 한다.
- **REQ-XSEAM-ADAPTER-3 (Event-Driven)** — WHEN 골든 함수가 XFrame 또는 MetricResult를 반환하면, THEN 어댑터는 그것을 C# 호출자를 위한 언어 중립 DTO로 다시 직렬화해야 한다.
- **REQ-XSEAM-ADAPTER-4 (Unwanted)** — IF 어댑터가 마샬링을 넘어 어떤 DSP 계산(offset 감산, MTF 추정, 배열 산술)을 스스로 수행하면, THEN 이는 계약 위반으로 취급되어야 한다(DSP 재구현 금지).
- **REQ-XSEAM-ADAPTER-5 (Unwanted)** — IF 심을 뒷받침하기 위해 `common/`·`modules/`·`metrics/`·`pipeline/` 하위 어떤 파일이라도 편집해야 하면, THEN 이는 거부되어야 한다(골든 모델 읽기 전용 소비).

### REQ-XSEAM-UI — C# WPF + ScottPlot 스켈레톤: VIEWER-001 원칙 상속 (C-09/C-11/C-20, XDET-TC-083/084)

- **REQ-XSEAM-UI-1 (Ubiquitous)** — C# UI(WPF, .NET 8, ScottPlot)는 엔진 심에만 의존해야 하며 — `IXdetEngine`과 DTO를 소비 — 어떤 DSP 계산도 스스로 수행하지 않아야 한다(VIEWER-001 C-09 "지표 자체 계산 0" 상속; UI는 실제 엔진을 호출하고 지표/보정을 인라인 계산하지 않는다).
- **REQ-XSEAM-UI-2 (Event-Driven)** — WHEN 사용자가 모듈 검증기 슬라이스를 실행하면, THEN UI는 공급된 입력(합성 offset 입력)에 대해 `IXdetEngine`을 호출하고 결과 XFrame의 입력/출력/diff를 표시해야 한다(심 경유 `offset.process`).
- **REQ-XSEAM-UI-3 (Event-Driven)** — WHEN 사용자가 지표 뷰를 실행하면, THEN UI는 `IXdetEngine`을 호출해 지표(MTF)를 산출하고 반환된 MetricResult 곡선을 ScottPlot으로 플롯해야 한다 — 엔진이 반환한 값만 플롯 값으로 사용(VIEWER-001 C-09 위임; 플롯 값 = 엔진 출력).
- **REQ-XSEAM-UI-4 (Ubiquitous)** — UI는 코어를 단방향 소비해야 한다 — C# UI는 심/엔진에 의존하고, 골든 모델도 엔진 계약도 UI를 역참조하지 않는다(VIEWER-001 C-11 단방향 소비 상속).
- **REQ-XSEAM-UI-5 (Unwanted)** — IF 어떤 UI 동작이 골든 fixture·CalibSet 파일·`data/` 골든 산출물에 쓰기를 시도하면, THEN 이는 거부되어야 한다(VIEWER-001 C-20 읽기 전용 상속; 내보내기는 사용자 지정 디렉터리로만).

### REQ-XSEAM-FIDELITY — 골든 동일성: 심 결과 = Python 골든 직접 출력 (T10/XDET-TC-020~021, diff_frames, XDET-TC-085/086) — **load-bearing**

- **REQ-XSEAM-FIDELITY-1 (Event-Driven)** — WHEN 모듈 검증기 슬라이스가 심 경유로 `offset.process`를 실행하면, THEN Python 측에서 재구성한 결과 XFrame은 Python 골든의 직접 `modules.offset.process` 출력과 XDET-TC-021 허용오차 내로 일치해야 한다 — 정수 경로 bit-동일, 부동소수점 경로 ±1 LSB 이내.
- **REQ-XSEAM-FIDELITY-2 (Ubiquitous)** — XFrame(offset) 경로의 fidelity 단언은 사전 설계된 T10 동일성 훅 `common.equivalence.diff_frames(a,b)->EquivalenceDiff`(pixel_equal/masks_equal/noise_equal/max_pixel_abs_diff/structurally_equal)로 계산되어야 하며(C++ P2 포트를 게이트할 바로 그 메커니즘 재사용), XFrame 경로용 별도 비교기를 만들지 않아야 한다. `diff_frames`는 XFrame만 받으므로 MetricResult(MTF) 경로에는 적용되지 않는다 — 그 경로 비교는 REQ-XSEAM-FIDELITY-3이 정의한다.
- **REQ-XSEAM-FIDELITY-3 (Event-Driven)** — WHEN 지표 뷰가 심 경유로 MTF를 산출하면, THEN 반환된 MetricResult 배열 값(frequencies_lpmm·mtf)은 Python 골든의 직접 `metrics.mtf.compute_mtf` 출력과 요소별 수치 동일성(element-wise numeric equality)으로 비교되어 정확히 0의 delta로 일치해야 한다 — MTF는 P1.5에서 순수 float64 트랜스포트이므로 관측 delta는 정확히 0이고, XDET-TC-021 ±1 LSB envelope는 P2에서 C++가 실제 DSP를 재계산할 때를 위한 예약분이라 P1.5 트랜스포트가 소비하지 않는다.
- **REQ-XSEAM-FIDELITY-4 (Unwanted)** — IF 심 결과가 Python 골든 직접 출력으로부터 XDET-TC-021 허용오차를 초과하여 이탈하면, THEN 얇은 슬라이스 fidelity 시험은 FAIL 해야 한다(동일성 게이트는 load-bearing — 불일치는 슬라이스를 차단한다; P1.5 어댑터는 재계산이 아닌 트랜스포트이므로 기대 delta는 정확히 0/bit-동일이고, 어떤 이탈도 마샬링 손상 신호다).

### REQ-XSEAM-COEXIST — Python 골든 + VIEWER-001 무변경 · C# 격리 (공존 불변식, import-linter, XDET-TC-087)

- **REQ-XSEAM-COEXIST-1 (Ubiquitous)** — Python 골든 모델(`common/`·`modules/`·`pipeline/`·`metrics/`)과 SPEC-VIEWER-001 Python GUI(`apps/gui/`)는 본 SPEC으로 변경되지 않아야 한다 — 골든은 동결 레퍼런스 오라클, VIEWER-001은 P1 검증 도구다.
- **REQ-XSEAM-COEXIST-2 (Ubiquitous)** — C# 솔루션은 신규 분리 디렉터리 `apps/xdet-console/`에 위치하여 Python 패키지 트리로부터 격리되어야 한다(`pyproject.toml` `packages` 미포함, pytest 미수집).
- **REQ-XSEAM-COEXIST-3 (Unwanted)** — IF 본 SPEC이 골든 모델·Python import-linter 계층 계약·SPEC-VIEWER-001 GUI를 수정하면, THEN 이는 범위 위반으로 거부되어야 한다(확장은 순수 additive).
- **REQ-XSEAM-COEXIST-4 (Ubiquitous)** — Python import-linter 계약은 green·불변으로 유지되어야 한다 — C# 솔루션은 Python 의존 그래프에 비가시다(어떤 Python 파일도 C# 측을 import하지 않고, C# 측은 Python 패키지가 아니다).

### REQ-XSEAM-FORWARD — 전방 호환: C++ 구현가능성 · P2 swap · XDET-TC-021 게이트 (확정 결정, XDET-TC-020~021, XDET-TC-087)

- **REQ-XSEAM-FORWARD-1 (Ubiquitous)** — `IXdetEngine` 인터페이스와 DTO 계약은 C++로 구현 가능해야 한다 — 심 위의 모든 요소가 C ABI로 표현 가능(원시 스칼라·문자열·`(dtype, shape, buffer)` 배열 삼중항)하여 미래 C++ 네이티브 엔진이 동일 인터페이스를 구현할 수 있어야 한다.
- **REQ-XSEAM-FORWARD-2 (Ubiquitous)** — 본 SPEC은 P2 swap 경로를 문서화해야 한다 — 불변의 `IXdetEngine` 뒤에서 P1.5 pythonnet 어댑터를 P2 C++ 네이티브 엔진(C ABI 위)으로 교체하며, C# UI는 백엔드 변경에 영향받지 않아야 한다.
- **REQ-XSEAM-FORWARD-3 (Ubiquitous)** — 문서화된 P2 C++ 포트는 XDET-TC-020/021 동일성 프레임으로 게이트되어야 한다 — 네이티브 구현은 그 출력이 Python 골든과 XDET-TC-021 허용오차(정수 bit-동일 / float ±1 LSB) 내로 일치할 때만 수용되며, 얇은 슬라이스가 성립시킨 `common.equivalence.diff_frames` 메커니즘을 재사용한다.
- **REQ-XSEAM-FORWARD-4 (Unwanted)** — IF 본 SPEC이 어떤 C++/네이티브 코드나 실제 P2 네이티브 엔진을 구현하면, THEN 이는 거부되어야 한다(C++ 포트는 P2 범위 밖).

## Exclusions (What NOT to Build)

- **C++ 구현 없음** — P1.5는 `IXdetEngine` 인터페이스·`PythonNetXdetEngine` 어댑터·C# UI 스켈레톤·fidelity 슬라이스만 만든다. 실제 `NativeXdetEngine`(C++/C ABI)나 네이티브 DSP 커널은 P2로 범위 밖(REQ-XSEAM-FORWARD-4). 본 SPEC은 P2 swap을 **문서화**만 한다.
- **전체 모듈/지표 커버리지 없음(얇은 슬라이스만)** — 모듈 1개(`offset`) + 지표 1개(`MTF`)만 심 경유로 구동한다. 나머지 11개 처리 모듈·6개 지표, 전체 파이프라인 실행, 스테이지별 비교는 P1.5 범위 밖(아키텍처 end-to-end 증명이 목적).
- **검증 모드 float64 버퍼(`pixel_f64`) 전송 없음** — P1.5 얇은 슬라이스는 float32 단일 경로 XFrame(`pixel_f64=None`, 합성 f32-only 프레임)만 심 경유로 구동한다. `common/xframe.py`의 검증 모드 병렬 float64 버퍼(`pixel_f64`, `modules/offset.py`가 존재 시 소비)와 그 DTO 직렬화 전송은 P2 전방 범위다. 합성 입력이 `pixel_f64=None`이면 offset의 pixel_f64 분기가 비활성이고 `diff_frames`도 `pixel_f64`를 비교하지 않으므로, `diff_frames`가 f32-only 프레임의 완전한 비교기가 된다(REQ-XSEAM-CONTRACT-2, REQ-XSEAM-FIDELITY-2).
- **골든 모델 변경 없음** — `common/modules/pipeline/metrics` Python 골든은 동결 오라클로 편집하지 않는다. 어댑터는 골든 함수를 unmodified 호출하며 심을 위해 코어 표면을 바꾸지 않는다(REQ-XSEAM-ADAPTER-5, COEXIST-1/3).
- **C#에서의 DSP 재구현 없음** — C# 측(어댑터·UI)은 어떤 DSP도 계산하지 않는다. offset 감산·MTF 추정 등 모든 수치는 실제 Python 골든이 산출하고 C#은 트랜스포트·표시만 한다(REQ-XSEAM-ADAPTER-4, UI-1; VIEWER-001 C-09 상속).
- **Python VIEWER-001 GUI 교체·제거 없음** — `apps/gui/`(pyqtgraph 검증 GUI)는 P1 검증 도구로 그대로 유지된다. C# UI는 대체물이 아니라 제품화 경로의 **병렬 신규 소비자**다(COEXIST-1).
- **C# 빌드의 저장소 CI 강제 없음(문서화된 로컬 빌드 단계 초과 금지)** — 저장소 CI는 Python 전용이다. C# `dotnet build`/`dotnet test`는 문서화된 로컬 단계로 두고 Python CI에 게이트로 추가하지 않는다. 별도 .NET CI 잡 추가 여부는 결정 항목으로 플래그한다(「결정 필요/확인 사항」 2).
- **배포·서버·다중 사용자 없음** — 로컬 데스크톱 UI 스켈레톤만. 웹 서버·REST·컨테이너 배포·세션/인증은 범위 밖(VIEWER-001 Exclusions 승계).
- **Gen 2 항목 없음** — DL·ADR 등은 구현하지 않는다. C# 심/UI는 Gen 1 골든 파이프라인만 대상으로 한다.
- **성능/마샬링 미세 최적화 없음** — P1.5 목적은 아키텍처 정합성·fidelity 증명이며 대용량 배열 마샬링 성능 최적화는 범위 밖(트랜스포트 정확성 외; 대용량 배열 비용은 「결정 필요/확인 사항」 1의 트랜스포트 결정으로 이연).

## 결정 필요/확인 사항

저작 시 확정 설계 결정을 EARS로 인코딩했으며, run 착수 전 사용자 확인이 유용한 항목 3건은 아래와 같다. **어느 것도 실측[B] 대기가 아니며 run 단계를 차단하지 않는다**(각 항목에 가정 기본값 제시).

1. **[확인 필요] 심 트랜스포트 세부 — pythonnet in-process vs 로컬 IPC/RPC 폴백.** **가정 기본값**: pythonnet(Python.NET 3.0.x)으로 CPython을 .NET 프로세스에 임베드하는 in-process 트랜스포트. P1.5 얇은 슬라이스는 소형 배열이라 in-process로 충분하다. **예비**: 대용량 3072² float32 배열 마샬링 비용/안정성이 문제되면 로컬 IPC/RPC(예: stdin/stdout JSON 또는 로컬 소켓)로 폴백 — `(dtype, shape, buffer)` DTO(REQ-XSEAM-CONTRACT-3)가 `IXdetEngine`을 바꾸지 않고 트랜스포트를 교체 가능하게 한다. **확인 대상**: P1.5에서 in-process 확정 vs 폴백 경로도 스켈레톤에 예비할지.
2. **[확인 필요] Python 전용 CI 하의 C# 빌드/테스트 게이팅.** **가정 기본값**: C# 솔루션 README에 `dotnet build` + `dotnet test`(fidelity 슬라이스 포함) 로컬 단계를 문서화하고, 저장소의 Python 전용 CI에는 추가하지 않는다(CI는 Python 전용 유지). fidelity 골든 레퍼런스는 임베드된 Python 내부에서 `diff_frames`로 산출(별도 fixture 파일 최소화). **확인 대상**: 별도 GitHub Actions .NET 잡을 신설할지(후속 별건 가능), fidelity 레퍼런스를 커밋 fixture로 둘지 인라인 비교로 둘지.
3. **[확인 필요] 정확한 apps/ 경로 + .NET/ScottPlot/pythonnet 버전.** **가정 기본값**: 디렉터리 `apps/xdet-console/`(운영 콘솔 명명), .NET 8 LTS, WPF(`Microsoft.WindowsDesktop.App`; WinUI 3는 문서화된 대안), ScottPlot 5.x, Python.NET(pythonnet) 3.0.x, 테스트 xUnit. 지표 슬라이스 기본값 = MTF(단일 프레임→곡선 자기완결); DQE는 사전계산 MTF+NNPS 필요하므로 대안. **확인 대상**: 디렉터리명·프레임워크(WPF vs WinUI 3)·버전 핀·지표(MTF vs DQE) 사용자 선호.
