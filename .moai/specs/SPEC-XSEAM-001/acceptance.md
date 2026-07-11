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

# SPEC-XSEAM-001 — 인수 기준 (acceptance)

얇은 수직 슬라이스(C# UI → 심 → offset.process / MTF → 표시 + fidelity 단언)의 Given-When-Then. 모든 기준은 관측 가능(빌드 성공 / 슬라이스 구동 / fidelity delta 정확히 0 — P1.5 트랜스포트, ±1 LSB envelope는 P2 예약 / 골든 파일 무변경 / Python 스위트 무회귀)해야 한다. 각 시나리오는 XDET-TC-080~087에 귀속한다.

## Scenarios (Given-When-Then)

### Scenario 1 — 언어 중립 계약 어셈블리 (XDET-TC-080, REQ-XSEAM-CONTRACT)
- **Given** `apps/xdet-console/` .NET 8 솔루션과 `Xdet.Engine.Contract` 프로젝트가 있고,
- **When** `dotnet build`로 계약 어셈블리를 빌드하면,
- **Then** 빌드가 성공하고, `IXdetEngine`(모듈 처리 + 지표 산출 진입점)과 XFrame/CalibSet/Params/MetricResult DTO(배열은 `(dtype, shape, buffer)` 삼중항)가 존재하며, 계약 어셈블리의 참조 목록에 pythonnet/Python 런타임 의존이 **부재**해야 한다.

### Scenario 2 — pythonnet 어댑터 왕복 (XDET-TC-081, REQ-XSEAM-ADAPTER-1/2/3)
- **Given** `PythonNetXdetEngine : IXdetEngine`와 임베드된 CPython(저장소 `uv` 환경)이 있고, 합성 offset 입력(작은 raw 프레임 DTO + 합성 CalibSet(OFFSET) `O_map` DTO + Params `raw_saturation_threshold`)이 주어지면,
- **When** C#에서 `IXdetEngine`의 모듈 처리 진입점을 호출하면,
- **Then** 어댑터가 DTO를 Python `XFrame`/`CalibSet`/`Params`로 재구성하고 `modules.offset.process`를 unmodified 호출한 뒤, 반환 XFrame(pixel float32 + masks + history)을 언어 중립 DTO로 역직렬화하여 C# 호출자에게 반환해야 한다(왕복 완료).

### Scenario 3 — 실제 골든 디스패치 · C# DSP 미계산 (XDET-TC-082, REQ-XSEAM-ADAPTER-4/5)
- **Given** 어댑터가 offset·MTF 슬라이스를 구동하고,
- **When** 심 경유 실행 후 C# 측(어댑터·UI) 코드 경로를 검사하면,
- **Then** 모든 수치 산출이 실제 Python 골든(`modules.offset.process` / `metrics.mtf.compute_mtf`)에서 발생하고 C# 측에는 어떤 DSP 산술(offset 감산·MTF 추정)도 없어야 하며, `common/`·`modules/`·`metrics/`·`pipeline/` 하위 파일이 무변경(git diff 없음)이어야 한다.

### Scenario 4 — C# UI 슬라이스 구동 (XDET-TC-083, REQ-XSEAM-UI-1/2/3)
- **Given** `Xdet.Ui`(WPF + .NET 8 + ScottPlot) 스켈레톤이 빌드되고,
- **When** 사용자가 (a) 모듈 검증기 슬라이스와 (b) 지표 뷰를 실행하면,
- **Then** (a) UI가 `IXdetEngine`으로 offset을 구동하여 입력/출력/diff XFrame을 표시하고, (b) UI가 `IXdetEngine`으로 MTF를 산출하여 반환된 MetricResult 곡선(frequencies_lpmm·mtf)을 ScottPlot으로 플롯하며, 플롯 값이 엔진 반환 배열과 일치(UI 자체 계산 0)해야 한다.

### Scenario 5 — UI 읽기 전용 · 단방향 (XDET-TC-084, REQ-XSEAM-UI-4/5)
- **Given** UI가 심/엔진을 소비하고,
- **When** UI 동작과 의존 방향을 검사하면,
- **Then** C# UI는 심/엔진에 의존하고 골든 모델·엔진 계약은 UI를 역참조하지 않으며(단방향), 어떤 UI 동작도 골든 fixture·CalibSet·`data/`에 쓰지 않아야 한다(내보내기는 사용자 지정 디렉터리로만).

### Scenario 6 — offset fidelity: diff_frames 동일성 (XDET-TC-085, REQ-XSEAM-FIDELITY-1/2/4) — **load-bearing**
- **Given** 동일 합성 offset 입력(float32 단일 경로, `pixel_f64=None` — offset의 pixel_f64 분기 비활성이라 `diff_frames`가 완전한 비교기)이 (경로 A) 심 경유 `IXdetEngine` offset 처리와 (경로 B) Python 골든 직접 `modules.offset.process`로 각각 실행되고,
- **When** 경로 A의 결과를 Python 측에서 XFrame으로 재구성하여 경로 B 출력과 `common.equivalence.diff_frames`로 비교하면,
- **Then** `EquivalenceDiff.structurally_equal`가 True이고 `max_pixel_abs_diff`가 XDET-TC-021 허용오차 이내(정수 경로 bit-동일, float 경로 ±1 LSB; 트랜스포트이므로 기대값 정확히 0)여야 한다.

### Scenario 7 — MTF fidelity: 배열 동일성 (XDET-TC-086, REQ-XSEAM-FIDELITY-3)
- **Given** 동일 합성 edge-slab ROI 프레임이 심 경유 MTF와 Python 골든 직접 `metrics.mtf.compute_mtf`로 각각 산출되고,
- **When** 두 MetricResult의 `values["frequencies_lpmm"]`·`values["mtf"]` 배열을 요소별 수치 동일성(element-wise numeric equality)으로 비교하면(MetricResult 경로이므로 `diff_frames` 미적용),
- **Then** 두 배열이 정확히 0의 delta로 일치해야 한다 — MTF는 P1.5에서 순수 float64 트랜스포트이므로 관측 delta는 정확히 0이며, XDET-TC-021 ±1 LSB envelope는 P2 C++ 재계산 몫으로 예약된다(P1.5가 소비하지 않는다).

### Scenario 8 — 공존·격리 + P2 문서 (XDET-TC-087, REQ-XSEAM-COEXIST + REQ-XSEAM-FORWARD)
- **Given** C# 솔루션이 `apps/xdet-console/`에 추가된 상태에서,
- **When** `uv run pytest`와 `uv run lint-imports`를 실행하고 솔루션 격리·P2 문서를 검사하면,
- **Then** 기존 Python 스위트가 무회귀로 green(SPEC-VIEWER-001 headless GUI 서브셋 포함; 저작 시 보고 기준 543 통과 / GUI 89 — XSEAM은 Python 코드 0 추가이므로 카운트 불변), import-linter가 green·불변, `apps/xdet-console/`가 `pyproject.toml` `packages` 미포함·pytest 미수집, README에 P2 swap(`PythonNetXdetEngine`→`NativeXdetEngine` over C ABI, UI 불변, XDET-TC-020/021 게이트) 문서가 존재해야 한다.

## Edge Cases

- **offset 경로 fidelity 불일치는 FAIL (REQ-XSEAM-FIDELITY-4)** — 심 경유 offset XFrame이 골든 직접 출력으로부터 XDET-TC-021 허용오차를 초과 이탈하면(예: 마샬링이 float32를 float64로 승격/절단하여 delta > ±1 LSB), fidelity 시험은 반드시 FAIL 해야 한다 — 통과로 침묵되면 안 된다. (음성 신뢰성: 의도적으로 `diff_frames` 비교 대상 버퍼에 1 LSB 초과 섭동을 주입하면 시험이 실제로 FAIL함을 확인.)
- **MTF 경로 fidelity 불일치는 FAIL (REQ-XSEAM-FIDELITY-3/4)** — 심 경유 MetricResult 배열(frequencies_lpmm·mtf)이 골든 직접 출력과 요소별 수치 동일성에서 정확히 0의 delta가 아니면(P1.5 순수 float64 트랜스포트이므로 기대 delta = 0), fidelity 시험은 반드시 FAIL 해야 한다 — 통과로 침묵되면 안 된다. (음성 신뢰성: MetricResult 배열에 1 LSB 초과 섭동을 의도적으로 주입하면 시험이 실제로 FAIL함을 확인 — offset 버퍼 섭동 시험의 지표 경로 미러.)
- **골든 모델 변경 시도는 범위 밖 (REQ-XSEAM-COEXIST-3, ADAPTER-5)** — 심을 뒷받침하기 위해 `common/modules/pipeline/metrics` 편집이 필요하다는 판단이 나오면, 이는 범위 위반으로 거부되고 어댑터 측에서 해소해야 한다(골든 무변경 유지). git diff가 코어에 변경을 보이면 인수 실패.
- **심 표면 Python-ism 누출 (REQ-XSEAM-CONTRACT-4)** — `IXdetEngine`/DTO에 `PyObject`·pickle·numpy 전용 타입이 노출되면 인수 실패 — 계약 어셈블리는 pythonnet 의존 0으로 C++ 구현 가능해야 한다.
- **C# DSP 재구현 (REQ-XSEAM-ADAPTER-4, UI-1)** — C# 측이 offset 감산·MTF 추정 등을 스스로 계산하면(제2 구현) 인수 실패 — 모든 수치는 실제 골든이 산출해야 한다.
- **VIEWER-001 회귀 (REQ-XSEAM-COEXIST-1)** — SPEC-VIEWER-001 headless GUI 스위트가 하나라도 실패하거나 카운트가 감소하면 인수 실패 — C# 확장은 Python GUI에 무영향이어야 한다.

## Definition of Done (체크리스트)

- [ ] `apps/xdet-console/` .NET 8 솔루션 스캐폴드 + `Xdet.Engine.Contract`(pythonnet 의존 0) 빌드 성공 (XDET-TC-080)
- [ ] `IXdetEngine`(모듈 처리 + 지표 산출) + XFrame/CalibSet/Params/MetricResult DTO + `(dtype, shape, buffer)` 배열 삼중항 정의 (CONTRACT-1~5)
- [ ] `PythonNetXdetEngine` in-process 어댑터가 DTO↔Python 객체 왕복 + 실제 골든 unmodified 호출 (XDET-TC-081, ADAPTER-1/2/3)
- [ ] 어댑터·UI에 DSP 산술 부재 + 코어 4계층 git diff 없음 (XDET-TC-082, ADAPTER-4/5)
- [ ] `Xdet.Ui`(WPF + ScottPlot) 모듈 검증기 슬라이스(offset 입력/출력/diff) + 지표 뷰(MTF 곡선) 구동 (XDET-TC-083, UI-1/2/3)
- [ ] UI 단방향 소비 + 읽기 전용(골든/CalibSet/`data/` 쓰기 없음) (XDET-TC-084, UI-4/5)
- [ ] offset fidelity: `diff_frames`로 `structurally_equal` True + `max_pixel_abs_diff` XDET-TC-021 이내 (XDET-TC-085, FIDELITY-1/2)
- [ ] MTF fidelity: MetricResult 배열 요소별 정확히 0 delta(순수 float64 트랜스포트; ±1 LSB는 P2 예약) (XDET-TC-086, FIDELITY-3)
- [ ] fidelity 불일치 시 FAIL — offset(`diff_frames` 버퍼)·MTF(MetricResult 배열) 두 경로 음성 신뢰성 섭동 확인 (FIDELITY-3/4)
- [ ] `uv run pytest` 무회귀 green(VIEWER-001 GUI 서브셋 포함) + `uv run lint-imports` green·불변 (XDET-TC-087, COEXIST-1/4)
- [ ] `apps/xdet-console/` Python 패키지 트리 격리(`pyproject.toml` `packages` 미포함, pytest 미수집) (COEXIST-2)
- [ ] `common/modules/pipeline/metrics` + `apps/gui/` 무변경(git diff 없음) (COEXIST-1/3)
- [ ] README에 P2 swap(`PythonNetXdetEngine`→`NativeXdetEngine` over C ABI, UI 불변, XDET-TC-020/021 동일성 게이트) 문서 (XDET-TC-087, FORWARD-1~4)
- [ ] 어떤 C++/네이티브 코드도 구현하지 않음(P1.5는 인터페이스+어댑터+UI+슬라이스만) (FORWARD-4)

## 판정 원칙 (측정=판정 분리)

- fidelity 허용오차(XDET-TC-021: 정수 bit-동일 / float ±1 LSB)는 CLAUDE.md T10 동일성 프레임에서 인용하며 심 내부에 하드코딩하지 않는다(P2 수치 임계는 벤치마크 대기). P1.5 트랜스포트의 관측 delta는 0(bit-동일) 기대이고, ±1 LSB는 P2에서 C++가 실제 DSP를 재계산할 때를 위한 예비 envelope다.
- Python 스위트 카운트(543/89)는 저작 시 보고 기준의 스냅샷이며, load-bearing 기준은 **무회귀(카운트 불변)** 다 — XSEAM은 Python 코드를 0 추가하므로 카운트는 불변해야 한다. run 착수 시 baseline을 재확인한다.
