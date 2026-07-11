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

# SPEC-XSEAM-001 — 구현 계획 (plan)

언어 중립 엔진 심 + C# UI 스켈레톤(P1.5 얇은 수직 슬라이스)의 구현 계획. 시간 추정 없음 — Priority(High/Medium/Low)와 단계 순서로만 기술한다. Python 골든 모델은 동결 오라클로 무변경, 작업은 전부 신규 `apps/xdet-console/` C# 솔루션에 additive.

## 1. 기술 접근 (Technical Approach)

### 1.1 durable 심과 교체 가능 어댑터의 분리

- **`IXdetEngine`(durable 심)**: 최소 두 진입점 — 모듈 처리(`process(XFrame,CalibSet,Params)->XFrame` 미러)와 지표 산출(`compute_*(...)->MetricResult` 미러). Python-ism 없음, C ABI 표현 가능. → `Xdet.Engine.Contract` 어셈블리(pythonnet 의존 0).
- **DTO 계약**: XFrame/CalibSet/Params/MetricResult를 언어 중립 표현. 배열은 `(dtype, shape, 연속 raw 버퍼)` 삼중항. `common/xframe.py`(pixel float32 + mask 스택 + noise (alpha,sigma) + history), `common/calibset.py`(panel_id/resolution/valid_from/valid_until/kind/data/domain/beam_quality), `common/contract.py::Params`(key→value), `metrics/result.py::MetricResult`(name/values/condition/warnings)의 필드를 1:1 미러. P1.5 대상은 float32 단일 경로 XFrame(`pixel_f64=None`); 검증 모드 병렬 float64 버퍼(`pixel_f64`, `xframe.py` L160, `offset.process`가 존재 시 소비)의 DTO 전송은 P2 전방 범위로 이연.
- **`PythonNetXdetEngine`(P1.5 어댑터)**: `IXdetEngine` 구현. pythonnet으로 CPython 임베드 → DTO를 Python `XFrame`/`CalibSet`/`Params`로 재구성 → 실제 골든(`modules.offset.process`, `metrics.mtf.compute_mtf`) unmodified 호출 → 결과를 DTO로 역직렬화. **DSP 재계산 없음(트랜스포트)**.
- **P2(문서만)**: `NativeXdetEngine`(C++/C ABI)가 동일 `IXdetEngine` 구현 → UI 무변경. XDET-TC-020/021 동일성 게이트 통과 필수.

### 1.2 얇은 수직 슬라이스 (모듈 1 + 지표 1)

- **모듈 = offset**: `modules/offset.py::process`. 합성 raw 프레임(float32 단일 경로 `pixel_f64=None` — offset의 pixel_f64 분기 비활성) + 합성 CalibSet(OFFSET) `O_map` + Params `raw_saturation_threshold`(SWR-601 [B], 외부 주입). 심 경유 실행 → 출력 XFrame(pixel/masks/history) 표시.
- **지표 = MTF**: `metrics/mtf.py::compute_mtf(frame, params)->MetricResult`. 합성 edge-slab ROI 프레임 + MTF Params(pitch/oversample/angle range·margin). 심 경유 산출 → MetricResult(frequencies_lpmm·mtf) → ScottPlot 곡선. (DQE는 사전계산 MTF+NNPS 필요 → 대안, 결정 3.)

### 1.3 UI 원칙(VIEWER-001 상속)

- C-09 지표 자체 계산 0: UI/어댑터는 DSP 미계산, 엔진 결과만 표시.
- C-11 단방향 소비: UI→심→엔진, 역참조 없음.
- C-20 읽기-실행 전용: 골든 fixture/CalibSet/`data/` 쓰기 금지, 내보내기는 사용자 지정 디렉터리.

### 1.4 fidelity 동일성 프레임(load-bearing)

- **offset(XFrame) 경로**: 심 경유 결과를 Python 측에서 재구성 → 골든 직접 출력과 `common.equivalence.diff_frames`(pixel/masks/noise 동일성 + `max_pixel_abs_diff` + `structurally_equal`)로 비교 → XDET-TC-021 허용오차(정수 bit-동일 / float ±1 LSB). 트랜스포트라 기대 delta = 0(값-동일); 초과 이탈 = FAIL. 합성 입력은 float32 단일 경로(`pixel_f64=None`)라 `diff_frames`가 완전한 비교기.
- **MTF(MetricResult) 경로**: `diff_frames`는 XFrame만 받으므로 미적용. MetricResult 배열(frequencies_lpmm·mtf)을 요소별 수치 동일성(element-wise numeric equality)으로 비교 → 순수 float64 트랜스포트라 정확히 0 delta 기대; XDET-TC-021 ±1 LSB envelope는 P2 C++ 재계산 예약분(P1.5 미소비). 초과 이탈(음성 신뢰성 섭동) = FAIL.
- 이는 P2 C++ 포트를 게이트할 바로 그 훅의 "visual XDET-TC-021 seed"다.

## 2. 마일스톤 (우선순위 기반, 시간 추정 없음)

### M1 — 계약 어셈블리 (Priority High) — REQ-XSEAM-CONTRACT
- `apps/xdet-console/` .NET 8 솔루션 스캐폴드 + `Xdet.Engine.Contract` 프로젝트.
- `IXdetEngine` 인터페이스 + XFrame/CalibSet/Params/MetricResult DTO + `(dtype, shape, buffer)` 배열 삼중항. pythonnet 의존 0 검증.
- DoD: XDET-TC-080(계약 빌드 + 인터페이스/DTO 존재 + 계약 어셈블리에 pythonnet 참조 부재).

### M2 — pythonnet 어댑터 (Priority High) — REQ-XSEAM-ADAPTER
- `Xdet.Engine.PythonNet` 프로젝트 + `PythonNetXdetEngine : IXdetEngine`.
- DTO↔Python 객체 재구성/역직렬화, 실제 골든 unmodified 호출, DSP 미계산.
- DoD: XDET-TC-081(왕복), XDET-TC-082(실제 골든 디스패치 + C# DSP 부재 + 골든 파일 무변경).

### M3 — C# UI 스켈레톤 (Priority Medium) — REQ-XSEAM-UI
- `Xdet.Ui`(WPF + .NET 8 + ScottPlot): 모듈 검증기 슬라이스(offset 입력/출력/diff) + 지표 뷰(MTF ScottPlot 곡선). 엔진 심만 소비.
- DoD: XDET-TC-083(UI 빌드 + 두 슬라이스 구동), XDET-TC-084(읽기 전용 + 단방향).

### M4 — fidelity 동일성 슬라이스 (Priority High, load-bearing) — REQ-XSEAM-FIDELITY
- offset 슬라이스(XFrame 경로): 심 결과 XFrame vs 골든 직접 출력을 `diff_frames`로 비교 — 트랜스포트라 정확히 0/bit-동일 기대, XDET-TC-021 허용오차 게이트.
- MTF 슬라이스(MetricResult 경로): 배열(frequencies_lpmm·mtf)을 요소별 수치 동일성으로 비교 — 순수 float64 트랜스포트라 정확히 0 delta 기대(±1 LSB는 P2 예약); `diff_frames`는 XFrame 전용이라 미적용.
- DoD: XDET-TC-085(offset diff_frames 동일), XDET-TC-086(MTF 배열 정확히 0 동일), offset·MTF 두 경로 음성 신뢰성 섭동(>1 LSB) 시 FAIL.

### M5 — 공존·격리 + 전방 호환 문서 (Priority Medium) — REQ-XSEAM-COEXIST / REQ-XSEAM-FORWARD
- Python 골든·VIEWER-001·import-linter 무변경 검증(`uv run pytest`, `uv run lint-imports`), C# 솔루션 pyproject/pytest 격리.
- P2 swap(`PythonNetXdetEngine`→`NativeXdetEngine` over C ABI, UI 불변, XDET-TC-020/021 게이트) 문서화.
- DoD: XDET-TC-087(Python 회귀 무변경 + import-linter green + 골든 파일 무변경 + P2 문서 존재).

## 3. 대상 파일 (신규, 전부 `apps/xdet-console/` 하위)

| 경로(제안) | 역할 | 요구 그룹 |
|---|---|---|
| `apps/xdet-console/XdetConsole.sln` | .NET 8 솔루션 루트(격리) | COEXIST |
| `apps/xdet-console/Xdet.Engine.Contract/` | `IXdetEngine` + DTO(durable 심, pythonnet 의존 0) | CONTRACT |
| `apps/xdet-console/Xdet.Engine.PythonNet/` | `PythonNetXdetEngine`(pythonnet in-process 어댑터) | ADAPTER |
| `apps/xdet-console/Xdet.Ui/` | WPF + .NET 8 + ScottPlot UI 스켈레톤 | UI |
| `apps/xdet-console/Xdet.Engine.Tests/` | xUnit fidelity 슬라이스(`diff_frames` 재사용) | FIDELITY |
| `apps/xdet-console/README.md` | 로컬 `dotnet build`/`dotnet test` 단계 + P2 swap 문서 | FORWARD, COEXIST |

무변경(소비만): `common/xframe.py`·`common/contract.py`·`common/calibset.py`·`modules/offset.py`·`metrics/mtf.py`·`metrics/result.py`·`common/equivalence.py`. Python 코어·`apps/gui/`·import-linter 계약·`pyproject.toml` 불변.

## 4. 시험 케이스 매핑 (XDET-TC-080~087)

| TC | 대상 | 요구 |
|---|---|---|
| XDET-TC-080 | 계약 어셈블리 빌드 + `IXdetEngine`/DTO 존재 + pythonnet 의존 0 | CONTRACT-1/2/3/4/5 |
| XDET-TC-081 | 어댑터 XFrame/CalibSet/Params/MetricResult 왕복 | ADAPTER-1/2/3 |
| XDET-TC-082 | 실제 골든 디스패치 + C# DSP 미계산 + 골든 무변경 | ADAPTER-4/5 |
| XDET-TC-083 | UI 빌드 + 모듈 검증기·지표 뷰 구동(headless/smoke) | UI-1/2/3 |
| XDET-TC-084 | UI 읽기 전용 + 단방향 소비 | UI-4/5 |
| XDET-TC-085 | offset 슬라이스 `diff_frames` XDET-TC-021 동일 | FIDELITY-1/2/4 |
| XDET-TC-086 | MTF 슬라이스 MetricResult 배열 ±1 LSB 동일 | FIDELITY-3 |
| XDET-TC-087 | Python 회귀·import-linter·골든 무변경 + P2 문서 | COEXIST-1~4, FORWARD-1~4 |

TC 블록 근거: Gen 1(000~021)·VIEWER(030~037)·REALDATA(040~049)·ERGO(050~055)·CALDOM(060~067)·DQEDOC(070~073) 범위 밖 신규 080~087. C# 테스트는 `dotnet test`(xUnit)로 실행되며 Python 캡스톤 스캔(`tests/**/*.py`)과 무간섭.

## 5. 리스크 및 완화

| 리스크 | 완화 |
|---|---|
| pythonnet 대용량 float32 배열 마샬링 비용 | P1.5 슬라이스는 소형 배열; `(dtype,shape,buffer)` DTO로 IPC/RPC 폴백 교체 가능(결정 1) |
| Python 전용 CI가 C# 빌드를 게이트하지 못함 | 문서화된 로컬 `dotnet test` + fidelity 인라인 `diff_frames`; 별도 .NET 잡은 결정 2 |
| 심 표면에 Python-ism 누출 → C++ 구현 불가 | REQ-XSEAM-CONTRACT-4 Unwanted 가드 + 계약 어셈블리 pythonnet 의존 0(XDET-TC-080) |
| C#에서 DSP 재구현 유혹 → 제2 구현 표류 | REQ-XSEAM-ADAPTER-4/UI-1 Unwanted 가드 + fidelity가 트랜스포트 정확성만 허용 |
| 골든/ VIEWER-001 우발적 변경 | REQ-XSEAM-COEXIST Unwanted 가드 + `uv run pytest`/`lint-imports` 무변경 검증(XDET-TC-087) |
| C++ 포트가 골든과 미묘히 다른 수치 산출(P2) | XDET-TC-020/021 동일성 프레임이 사전 설계된 적합성 게이트(REQ-XSEAM-FORWARD-3); 슬라이스가 그 훅을 seed |

## 6. 의존성 및 순서

- M1(계약) → M2(어댑터) → M3(UI) 순차(각각 앞 산출물 소비). M4(fidelity)는 M2 후 착수 가능(UI 없이 어댑터만으로 동일성 단언 가능), M3와 병행 가능. M5(공존·문서)는 M1~M4 완료 후 검증·문서화.
- 외부: .NET 8 SDK, pythonnet(호스트 CPython = 저장소 `uv` 환경), ScottPlot, xUnit. Python 측 신규 의존 0.
