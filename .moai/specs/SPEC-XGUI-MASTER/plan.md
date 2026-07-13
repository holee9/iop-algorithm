---
id: SPEC-XGUI-MASTER
version: 0.5.1
status: planned
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-12
updated: 2026-07-13
author: drake.lee
priority: high
issue_number: 58
labels: [xgui, csharp-ui, gui-redesign, master-plan, golden-frozen]
---

# SPEC-XGUI-MASTER — 구현 계획

## 1. 기술 방향

목표 구현은 `apps/xdet-console/` C# WPF 앱이다. `apps/gui/`는 상호작용·가드·시험의 참조 선례이며 변경 대상이 아니다.

```text
WPF App
  ├─ Shared shell: input-set browser / compare / parameter editor / tier / export
  ├─ 8 algorithm-group feature tabs
  └─ Xdet.Engine.Contract (DTO + IXdetEngine)
           ↓
     Xdet.Engine.PythonNet
           ↓
     frozen Python golden
```

UI는 입력 수집·상태 표시·렌더링만 담당한다. 알고리즘 실행, 지표 계산, 조합 순서, 캘리브레이션 게이트와 동일성 판정은 seam 뒤 엔진이 담당한다.

## 2. 선행 게이트

### M0 — 문서·계약 기준선

- 본 마스터와 8개 하위 SPEC의 `spec.md`, `plan.md`, `acceptance.md`, `research.md`를 일치시킨다.
- `algorithm-catalog.md`의 전체 FeatureId/EntryPoint/노출/DTO/GUI/TC 매핑을 구현 범위로 채택한다.
- `SPEC-XSEAM-002` v0.5.1의 9개 실행 family, typed value/error, DQE/tier/session 계약을 구현 기준으로 채택한다.
- 중앙 TC 레지스트리 096~167의 `PLANNED` 할당을 `docs/XDET_TestSpec_v1.0.md`에 고정한다. 구현 PR은 실제 test name·증거 경로를 등록하고 해당 TC만 `AUTOMATED`/`UI-AUTOMATED`로 변경한다.

### M0.5 — 문서 검토·승인·동결

M0 작성 완료만으로 M1에 진입하지 않는다. [baseline-control.md](baseline-control.md)의 G0를 다음 순서로 닫는다.

1. 소스 target operation 67개(공개 대상 64 + SAMPLE helper 3), common infrastructure 6개, catalog callable 합계 73개와 9-family seam, 8개 그룹, 중앙 TC 72개의 집합 차이를 검사한다.
2. [traceability-matrix.md](traceability-matrix.md)에서 모든 EARS ID가 인수기준·TC·증거로 전개되는지 검사한다.
3. GUI 평가의 미정 임계·미완료 표지, 깨진 링크, 상충하는 Qt/Python 제품 결정을 0건으로 만든다. Params provenance 등급 `[T]`는 외부 Params/config 권위 여부를 검사한다.
4. 입력·Params·CalibSet·출력·typed error·provenance·evidence·artifact 계약을 family별로 교차검토한다.
5. 내부 감사 보고서를 `.moai/reports/`에 기록하고 현재 worktree/commit과 검사 명령을 명시한다.
6. 사용자에게 기준선 후보 v0.5.1과 미결정 사항 0건을 제시하고 명시적 승인을 받는다.
7. 승인된 버전·일시·범위를 기록하고 `approval_state=approved`, `implementation_authorized=true`로 동기화한 뒤 기준선을 동결한다.

**M0.5 종료 조건:** G0 12/12, 사용자 승인 기록 존재, 규범 문서 버전 일치, 기준선 동결. 하나라도 없으면 M1 이후 작업을 시작하지 않는다.

### M1 — 공통 C# 셸

- `Features/Shared/FolderBrowser`: 폴더 트리, 가상화 썸네일, 필름스트립, 이전/다음
- `Features/Shared/InputSet`: `xdet.input-set/1.0` single-frame/stack/sequence/profile/calibration-series/metric-series 검증과 ordered hash
- `Features/Shared/CompareWorkspace`: before/after/diff, W/L, probe, blink, mask overlay, history
- `Features/Shared/ParameterEditor`: `AlgorithmCatalogManifest` 기반 입력/Params/CalibSet 폼. required key는 골든 introspection, type/unit/constraint는 SWR·config metadata, numeric default는 Params/config만 권위 소스로 사용
- `Features/Shared/RunCoordinator`: `run_id`, phase, UI-thread 외 직렬 실행, soft cancel, 늦은 결과 억제
- `Features/Shared/Export`: result raw/sidecar/mask, `xdet.run-manifest/1.0`, hash·재현성 결과, C-20 가드 표시
- `Features/Shared/Tier`: capability·injected tier policy·forced downgrade·variant·timing record
- 모든 기능은 ViewModel과 렌더러를 분리하고 UI 스레드에서 골든 호출을 실행하지 않는다.
- M1 종료 전 `dotnet build apps/xdet-console/Xdet.sln --no-restore`와 실제 UI smoke를 실행한다. 현재 관찰된 `NU1701`(`ScottPlot.WPF` 전이 `SkiaSharp.Views.WPF`)을 포함한 TFM/패키지 호환성 경고는 호환 패키지 조합으로 해소해야 하며, 경고를 무시한 채 M2로 진입하지 않는다.

### M2 — 전체 알고리즘 seam

- 현재 offset→gain 고정 `IXdetEngine.RunPipeline`을 `PipelineRunRequest → PipelineRunResult` generic 계약으로 확장하고 기존 overload는 호환용으로만 둔다.
- PythonNet 어댑터는 실제 `pipeline.orchestrator.run_pipeline`을 unmodified 호출한다.
- `validation_mode`의 `intermediates`, frame history/domain/evidence-grade/warnings를 DTO로 운반한다.
- 비-부분수열과 CalibSet 결여·불일치를 typed `EngineError`로 반환하고 Python GUI helper에 의존하지 않는다.
- Lag에는 `RunSequence/FitLagIrf/ComputeLagMetrics`, NDT에는 SNRn/IQI/thickness, Metrics에는 MTF/NPS/defect 전용 request/result를 추가한다. 이들은 `run_pipeline`을 사용하지 않지만 모두 `IXdetEngine`을 경유한다.
- calibration builder에는 defect map, lag IRF, noise model, parametric/sample-fit scatter request/result를 추가한다.
- Metrics에는 `DqeComposeRequest/Result`를 추가하고 NPS support bin마다 골든 `mtf_value_at`을 호출한 뒤 `compute_dqe`를 호출한다. 범위 밖 bin을 외삽하지 않는다.
- 공통 실행에는 `decide_tier/select_pipeline/run_tier/time_tier` DTO를 추가한다. P1 timing은 구조 기록만 하며 절대 성능 합격 기준을 만들지 않는다.
- lag state snapshot/restore와 NDT accumulator shot log/target state를 session DTO로 운반한다.

### M3 — 그룹 탭 순차 구현

1. Calibration — 후속 그룹이 소비할 OC/GC/BPM과 비교 셸 기준 확립
2. Lag — 상태형 시퀀스와 fresh registry 경계 확립
3. Line/Sat/Geo — 마스크·다중 스테이지 표시 확립
4. Denoise — 동적 Params와 NOISE CalibSet 조달
5. Enhancement — 표시 도메인과 GSDF
6. Grid/Virtual-Grid — 주파수/공간 진단 분리
7. NDT — 스트리밍·리포트형 화면
8. Metrics — MTF/NPS/DQE/line-noise/defect; DQE는 engine-owned 고정 축 정책으로 활성

각 탭은 개별 인수 기준을 통과한 뒤 다음 탭과의 조합을 활성화한다.

### M4 — 저장·재열기

- raw-DN, display-normalized, report-only 산출물을 구분한다.
- 프레임 결과는 `_result.raw`+`.json`, mask가 있으면 XFrame과 동일한 `uint8` `_result_mask.raw`, 지표·NDT는 JSON/CSV 리포트를 사용한다.
- 모든 sidecar/report는 별도 `xdet.run-manifest/1.0`에서 input/Params/CalibSet/artifact SHA-256, adapter/golden version, `AlgorithmAvailability`와 실행별 `EvidenceGrade`를 연결한다.
- 저장은 엔진 어댑터의 C-20 가드를 통과한 사용자 폴더에서만 수행한다.
- 결과 raw가 완전한 XFrame snapshot이 아님을 사이드카와 UI에 표시한다.
- 저장 재열기 양자화 대조(`artifact round-trip`)와 동일 실행 재구동(`run reproducibility`)을 별도 결과로 제공한다.

### M5 — 검증·평가

- Contract unit → PythonNet integration → WPF ViewModel → headless UI → interactive UIA 순으로 시험한다.
- child TC 096~167, 기존 골든 TC, `uv run pytest`, `uv run lint-imports`, `dotnet test`를 실행한다.
- 전체 WPF solution build는 오류 0·TFM/패키지 호환성 경고 0이어야 하며, UIA smoke는 실제 `Xdet.Console.App` 프로세스에서 모든 등록 action의 도달 가능성과 렌더 생존을 증명해야 한다.
- `AlgorithmCatalogCoverageTests`로 Python 공개 façade, catalog, `AlgorithmCatalogManifest`, Contract, GUI action, TC가 전수 일치하는지 검사한다.
- `eval-methodology.md` must-pass를 모두 통과해야 구현 완료로 판정한다.

## 3. 대상 구조

| 위치 | 역할 |
|---|---|
| `apps/xdet-console/src/Xdet.Engine.Contract/` | 언어 중립 DTO, 기능별 요청/결과, 오류·등급·domain |
| `apps/xdet-console/src/Xdet.Engine.PythonNet/` | 골든 호출, DTO 변환, C-20 가드, fidelity 비교 |
| `apps/xdet-console/src/Xdet.Console.App/Features/Shared/` | 폴더 브라우저, 비교, Params, export, 상태 |
| `apps/xdet-console/src/Xdet.Console.App/Features/Shared/RunCoordinator/` | 단일 엔진 큐, run state, 취소·늦은 결과 억제 |
| `apps/xdet-console/src/Xdet.Console.App/Features/<Group>/` | 8개 그룹 View/ViewModel |
| `apps/xdet-console/tests/Xdet.Engine.Tests/` | 계약·어댑터·fidelity·거부 시험 |
| `apps/xdet-console/tools/Xdet.UiSmoke/` | 실제 WPF UIA 시나리오 |

대형 단일 `PythonNetXdetEngine.cs`에는 새 기능을 계속 누적하지 않는다. 공개 `IXdetEngine`은 유지하되 내부 구현을 기능별 adapter/service 또는 partial로 분리한다.

## 4. 의존 순서와 병렬성

- M0 → M0.5(사용자 승인·동결) → M1 → M2 → 그룹별 M3 → M4 → M5 순서를 지킨다.
- `implementation_authorized=false`인 동안 M1 이후의 소스·XAML·테스트·패키지·빌드 설정을 변경하지 않는다.
- Calibration은 Denoise/Enhancement보다 먼저, Denoise는 Enhancement보다 먼저 진행한다.
- NDT와 Metrics는 처리 파이프라인 탭과 독립적이지만 공통 셸·export 이후 진행한다.
- DQE engine composition과 tier family는 Metrics/그룹 탭보다 먼저 구현한다.

## 5. 리스크와 완화

| 리스크 | 완화 |
|---|---|
| C#에서 DSP가 중복됨 | 엔진 반환 DTO만 렌더, 정적 부재·음성 대조 시험 |
| 그룹별 TC 충돌·누락 | 마스터 096~167 레지스트리와 catalog coverage test 단일 관리 |
| Python GUI와 C# 타깃 혼재 | 모든 plan 대상 경로를 `apps/xdet-console/`로 고정 |
| 거대한 어댑터 클래스 | 기능별 내부 서비스 분리, Contract는 언어 중립 유지 |
| SAMPLE 과대해석 | 데이터 등급 배지와 QUARANTINE must-pass |
| normalized raw 오해 | domain 태그와 “운영 산출물, XFrame snapshot 아님” 표시 |
| DQE 임의 보간·외삽 | NPS support 고정 정책 + 골든 `mtf_value_at` 호출 + UI 수치 코드 정적 부재 시험 |
| 공개 연산이 catalog에서 누락 | AST/manifest/Contract/GUI/TC 전수 coverage test |
| 등록 실측 부재가 기능 비활성으로 오해됨 | AlgorithmAvailability와 EvidenceGrade 분리, user-supplied strict input 지원 |
| 취소된 Python 호출이 늦게 반환해 상태 오염 | `run_id` commit guard, canceled result 폐기, 엔진 큐는 호출 반환 전 다음 실행 진입 금지 |
| 결과 파일만으로 실행 재현 불가 | 공통 run manifest와 canonical Params/CalibSet/artifact hash 의무화 |
| Python GUI helper가 실행 경계로 유입 | adapter import 정적 검사, `run_pipeline`/`run_sequence`/`metrics.*` 공개 골든만 호출 |
| net9.0-windows에서 WPF 그래프 패키지가 .NET Framework asset으로 복원됨 | M1에서 `NU1701` 0을 build gate로 강제하고 실제 WPF UI smoke로 로드·렌더를 확인; 해소 전 M2 진입 금지 |
