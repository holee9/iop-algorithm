# 진입점 카탈로그

전체 아키텍처는 [overview.md](./overview.md), 데이터 흐름은 [data-flow.md](./data-flow.md) 참조.

## 실행 애플리케이션 / CLI

| 파일 | 유형 | 책임 |
|---|---|---|
| `apps/gui/app.py` | GUI 앱 | `qtpy → PySide6 + pyqtgraph` 기반 `MainWindow`(+`CompareDisplay`). **유일한 실행 애플리케이션.** module/pipeline/metrics 3탭 비교 뷰어. 무거운 연산은 `apps/gui/worker.py`의 `CallableWorker`로 백그라운드 스레드에서 실행해 GUI 스레드를 막지 않음 |
| `scripts/ingest_edrogi.py` | CLI (argparse) | 에드로지16BIT 실측 raw 샘플 세트 인제스트. `images/에드로지16BIT/` → `data/edrogi` 사이드카+manifest+ROI fixture+샘플 CalibSet 생성. **[HARD] QUARANTINE**: 배관(plumbing) 검증 전용, 알고리즘 파라미터([B]/[T]/[P]) 유도 근거로 사용 금지 |
| `scripts/spike_gui_probe.py` | CLI (헤드리스 스파이크) | Phase-0 napari 프로토타입 검증(SG-1~SG-3 기준). 골든모델 패키지(`common/modules/pipeline/metrics`) 외부이며 import-linter 대상 아님 |

## 파이프라인 호출 경로

세 가지 호출 진입점이 있으며, 상위로 갈수록 더 많은 관심사(연속성, 티어 게이팅)를 감싼다.

### 1. 단일 프레임 — `pipeline.orchestrator.run_pipeline`

가장 기본적인 진입점. 호출자는 다음을 조립해서 전달한다:

- `frame: XFrame` — `common.io.load_raw_frame` 등으로 생성된 입력 프레임
- `definition: PipelineDefinition` — `CANONICAL_ORDER`의 subsequence(스테이지 목록), 보통 `PipelineDefinition.full()` 또는 부분 집합
- `registry: Mapping[str, ProcessCallable]` — 보통 `modules.registry.default_registry()`
- `calib_map: Mapping[str, CalibSet]` — 스테이지별 CalibSet (`_calibration_gate`가 kind/panel/유효기간 검사)
- `params_map: Mapping[str, Params] | None` — 스테이지별 Params(생략 시 모듈 기본값)

각 스테이지는 `_calibration_gate` 진입 게이트를 통과해야 실행되며, 실행 순서는 `definition.stages`(CANONICAL_ORDER의 부분수열)를 따른다.

### 2. 연속 캡처 — `pipeline.sequence.run_sequence`

프레임 시퀀스(예: fluoroscopy)를 처리. 프레임마다 `run_pipeline`을 반복 호출하되:

- lag(WP2) 상태변수를 프레임 간 스레딩(이전 프레임의 `LagCorrector` 상태를 다음 호출에 전달)
- 시퀀스 시작 시 `RegistryFactory`로 fresh registry를 생성해 상태를 격리
- forward-bias(FB) 트리거 핸드셰이크(SWR-404) 처리

### 3. 티어 게이팅 — `pipeline.tier.run_tier`

하드웨어 연산능력에 따라 파이프라인 구성을 강제 다운그레이드. `decide_tier`로 티어 결정 → `select_pipeline`로 해당 티어의 `PipelineDefinition` 선택 → `run_tier`가 내부적으로 `run_pipeline`/`run_sequence`를 호출. `registry`/`calib_map`은 호출자가 주입하며 `pipeline.tier`는 `modules`/`metrics`를 import하지 않는다(계약 6, [dependencies.md](./dependencies.md) 참조). `time_tier`는 실행 시간 측정 헬퍼(현재는 구조 통과만 검증, 절대 시간 임계는 P2).

## 테스트 하네스 진입점

| 파일/함수 | 책임 |
|---|---|
| `common.contract.run_harness` | 단일 `ProcessModule` 계약 검증(TC-000): `process(XFrame, CalibSet, Params) -> XFrame` 시그니처 준수, 순수성, 마스크/노이즈/이력 필드 무결성 확인 |
| `common.contract.run_stateful_harness` | `StatefulModule`(lag 등) 계약 검증. 상태 스레딩·XFrame 직렬화 확인 |

이 하네스들은 `tests/` 내 TC-000~021 pytest 케이스에서 각 모듈/파이프라인 fixture와 함께 사용된다(SWR 부록 대응, CI 등록 대상).

## GUI에서 파이프라인으로의 호출 흐름 (요약)

```mermaid
flowchart LR
    User(["사용자"]) --> MainWindow["apps/gui/app.py<br/>MainWindow"]
    MainWindow --> ModulePanel["module_panel.run_module<br/>(단일 모듈)"]
    MainWindow --> PipelinePanel["pipeline_panel.run_partial_pipeline<br/>(부분/전체 스테이지)"]
    ModulePanel -->|process 직접 호출| Modules["modules/*.py"]
    PipelinePanel --> RunPipeline["pipeline.orchestrator.run_pipeline"]
    RunPipeline -->|registry.get(stage)| Modules
    MainWindow --> MetricsPanel["metrics_panel.plot_mtf 등"]
    MetricsPanel --> Metrics["metrics/*.py"]
```

`module_panel`은 단일 모듈을 직접 호출해 입출력 XFrame 쌍을 비교하며(오케스트레이터 우회, 단일 스테이지 디버깅 목적), `pipeline_panel`은 반드시 `run_pipeline`을 통해 실행한다.
