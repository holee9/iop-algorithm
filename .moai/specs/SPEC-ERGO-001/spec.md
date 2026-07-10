---
id: SPEC-ERGO-001
title: "소비자 인체공학: 패키지 재노출 · 모듈 REQUIRED_PARAMS 매니페스트 · Params 조회/검증 · metric 반환형 통일"
version: 0.1.0
status: implemented
created: 2026-07-11
updated: 2026-07-11
author: drake.lee
priority: medium
issue_number: 19
labels: [ergonomics, developer-surface, re-exports, params-introspection, metric-return-type, additive]
---

# SPEC-ERGO-001 — 소비자 인체공학 갭 번들: 패키지 재노출 · 모듈 필요-파라미터 매니페스트 · Params 조회/검증 표면 · metric 반환형 통일

GUI 검토(이슈 #14, SPEC-VIEWER-001)에서 드러난 **소비자 인체공학(consumer-ergonomics) 갭 번들**을 해소한다(이슈 #19). GUI의 파라미터 폼·모듈 선택 UI를 구성하려면 지금은 각 모듈의 소스를 직접 읽어야 한다 — 공개 표면이 introspection 불가하고, "스테이지 X가 어떤 Params를 요구하는가"가 코드에서 열거되지 않으며, `Params`는 조회/검증 표면이 없고, metric 반환형이 이질적이기 때문이다. 본 SPEC은 이 네 갭을 **additive·거동 보존(behavior-preserving)** 방식으로 최소 해소한다.

**본 SPEC은 골든 모델 처리 모듈이 아니라 개발자 소비 표면(developer-surface) 개선이다**(SPEC-VIEWER-001/REALDATA-001 계열). SWR ID에 대응하는 파이프라인 스테이지를 신설하지 않으며(`process(XFrame,CalibSet,Params)->XFrame` 시그니처 없음, `CANONICAL_ORDER`·`_KIND_BY_STAGE` 무변경, 신규 `CalibKind` 없음), 기존 심층경로 import·`process` 시그니처·파이프라인 순서·전 기존 테스트를 **불변(KEPT)**으로 유지한다. **단, SPEC-REALDATA-001과 달리 본 SPEC은 `common/contract.py`를 additive로 수정할 수 있다** — Params 조회/검증 표면 추가가 본 SPEC의 실제 목적이기 때문이며, 수정은 최소·backward-compatible로 한정한다.

네 갭(전부 현재 코드 대조 확인):
1. **패키지 재노출 부재** — `pipeline/__init__.py`만 `__all__` + 재노출을 정의한다. `common`/`modules`/`metrics`의 `__init__.py`는 docstring 전용 → 심층경로 import 강제, 공개 표면 introspection 불가. `metrics/__init__.py` docstring은 이미 의도한 export 목록을 열거하고 있다.
2. **모듈별 필요-파라미터 매니페스트 부재** — 필요 키가 모듈-private 헬퍼에 숨어있다(`modules/denoise.py::_required_keys(method)`; `gain_min`/`gain_max`는 `modules/gain.py::P_GAIN_MIN`/`P_GAIN_MAX` 상수 + 팬텀 기본값). "스테이지 X가 필요로 하는 Params"가 코드에서 열거되지 않는다.
3. **Params introspection 부재** — `common/contract.py::Params`는 `.get()`/`.hash()`/`.values`(불변 MappingProxy)만 노출한다. 키-검증 편의 표면이 없다.
4. **metric 반환형 이질성** — 대부분 `MetricResult`이나 `metrics/ndt.py::correct_thickness`는 `ThicknessResult`를 반환한다 → 제네릭 디스패치(name→run→render `.values`)에 특수 케이스가 필요하다.

- 근거: `docs/XDET_SWR_spec_v1.2.md`(SWR-000-6 fixture 동봉 단위시험 · SWR-000-8 레이어링/의존방향 · SWR-000-9 공용 컴포넌트 중복 금지) · GUI 검토 이슈 #14/#19 · `docs/XDET_TestSpec_v1.0.md`(신규 XDET-TC-050~055).
- 선행/소비 계약: [SPEC-INFRA-001](../SPEC-INFRA-001/spec.md)(`common/contract.py::Params`/`ProcessModule`·import-linter 레이어링 계약·`pipeline/__init__.py` `__all__` 선례) · [SPEC-VIEWER-001](../SPEC-VIEWER-001/spec.md)(`apps/gui/` 소비 표면 — `metrics_panel.plot_mtf`·`module_panel`·`modules/registry.py::default_registry`) · [SPEC-REALDATA-001](../SPEC-REALDATA-001/spec.md)(표본 세트 격리 — REQUIRED_PARAMS는 키 이름만, 표본 유도 수치 금지).
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.1.0 (2026-07-11)** — 초안 생성. GitHub 이슈 #19. GUI 검토(#14)에서 발견된 소비자 인체공학 갭 4종을 additive·거동 보존으로 해소. 6개 요구 그룹(EXPORTS/PARAMS/INTROSPECT/METRIC/CONTRACT/VALIDATE) EARS 구조 확정. 핵심 범위 결정:
  1. **metric 반환형 = 어댑터(치환/wrap 아님)** — `metrics/ndt.py::correct_thickness`는 `ThicknessResult`를 계속 반환하고, `metrics/result.py`에 additive 정규화 어댑터 `metric_view(obj) -> MetricResult`를 추가한다(MetricResult=항등, ThicknessResult=요약 스칼라 투영). 근거: `res.flattened`/`res.changed`/`res.low_freq`를 직접 접근하는 테스트 4파일(`test_ndt_thickness`·`test_ndt_contract`·`test_review_fixes_ndt`·`test_tc_ndt`)이 반환형 치환 시 전부 깨진다(거동 보존 HARD 위반). ThicknessResult는 EV 스칼라 지표가 아니라 (SRb/CSa 측정에 소비되는) flatten 변환 산출물이므로 MetricResult로의 강제 wrap은 개념을 혼동시킨다(「결정 필요/확인」 1).
  2. **개발자 소비 표면 개선 — 처리 모듈/스테이지 아님** — `CANONICAL_ORDER`·`process` 시그니처·`_KIND_BY_STAGE`·신규 `CalibKind` 없음. `common/contract.py`만 additive 수정 허용(Params 조회/검증이 목적).
  3. **격리 존중(SPEC-REALDATA-001)** — REQUIRED_PARAMS는 **키 이름 문자열만** 담고 표본/팬텀 수치값(예 `gain_min=0.5`)을 절대 포함하지 않는다.
  4. **TC 블록 = XDET-TC-050~055**(056~059 예약-미사용) — Gen1=000~021·022~029 예약·VIEWER=030~037·038~039 갭·REALDATA=040~049 뒤 신규 블록, 캡스톤 스캔(`tests/test_tc_skeletons.py` `_GEN1_TC_RANGE = range(0,22)`) 무간섭.

## Environment / Assumptions

- Python 3.11+, numpy/scipy 기반 float 골든 모델(CLAUDE.md, tech.md). 본 작업은 정확성·재현성·개발자 소비성이 목적이며 성능/배포 목적이 아니다.
- **실행 환경(HARD, lesson L#4)**: 본 저장소에는 PATH에 `python`이 없다 — 모든 명령은 `uv run ...`으로 실행하며, 한글 출력이 필요한 스크립트/테스트는 `PYTHONIOENCODING=utf-8`을 설정한다. SPEC/plan의 모든 명령 예시는 `uv run` 접두를 쓴다.
- **검증된 코드 사실(현재 상태 대조 확인, 재확인 불요)**:
  - `pipeline/__init__.py`만 `__all__`(CANONICAL_ORDER/PipelineDefinition/CalibrationError/run_pipeline)을 정의. `common/__init__.py`·`modules/__init__.py`·`metrics/__init__.py`는 docstring 전용(재노출 없음).
  - `metrics/__init__.py` docstring 열거 목록 = result.{MetricResult, MetricCondition, MetricReadError, require_param} · mtf.compute_mtf · nps.{compute_nps, detect_line_noise} · dqe.compute_dqe · lag.{compute_first_frame_lag, compute_ghost_cnr} · defect_stats.classify_defects · ndt.{read_duplex_srb, compute_snrn} — 이 목록이 metrics `__all__`의 기준이다(신규 `metric_view` 추가).
  - `common/contract.py::Params`(frozen dataclass) 표면 = `values`(불변 MappingProxy) · `get(key, default)` · `hash()`. 키-검증 표면 없음.
  - `modules/gain.py`: `P_GAIN_MIN="gain_min"`/`P_GAIN_MAX="gain_max"` 모듈 상수 + `_require`(단건-우선 실패). `modules/denoise.py`: `_required_keys(method)`(method별 키 집합; bm3d/nlm 분기) + `_require_present`(누락 전건 수집). 팬텀 수치값 `gain_min=0.5`/`gain_max=2.0`은 `tests/modules/phantoms/corrections.py`에만 상주(모듈 코드 아님).
  - `modules/` 처리 모듈 12종: offset, gain, defect, lag, line_noise, saturation, geometry, grid, virtual_grid, denoise, mse, window(import-linter `independence` 계약 대상). `modules/registry.py::default_registry`가 이미 전 모듈을 import한다.
  - `metrics/ndt.py::correct_thickness(frame, params, *, calibset_id=None) -> ThicknessResult`; `ThicknessResult`(frozen) 필드 = `flattened`, `low_freq`, `method`, `scale_px`, `changed`, `warnings`. `correct_thickness`/`ThicknessResult` 소비자 = `tests/metrics/test_ndt_thickness.py`·`test_ndt_contract.py`·`test_review_fixes_ndt.py`·`test_tc_ndt.py`(전부 `res.flattened`/`res.changed`/`res.low_freq` 등 네이티브 필드 직접 접근). `apps/gui/metrics_panel.py`는 현재 MTF만 배선(`compute_mtf -> MetricResult`), 제네릭 name→run→render 디스패치는 미구현(장래 소비자).
  - `metrics/result.py::MetricResult`(frozen) = `name` · `values`(Mapping) · `condition`(MetricCondition) · `warnings` + `get(key, default)`. 이것이 제네릭 디스패치가 기대하는 형상이다.
- **import-linter 계약(재사용, 변경 없음)**: `pyproject.toml [tool.importlinter]` — 레이어링(pipeline→modules→common, metrics→common), common 상향 import 금지, `modules.*` 상호 독립(independence), modules→metrics/pipeline 금지, core→apps.gui 금지. **재노출은 자기 패키지 하위 모듈에서만 가져와야** 이 계약을 유지한다. `common/__init__`은 `common.*`만, `modules/__init__`은 `modules.*` 모듈 객체만, `metrics/__init__`은 `metrics.*`만 재노출한다. `uv run lint-imports`는 0 broken을 유지해야 한다.
- **순환 import 주의**: `common/__init__.py`의 재노출은 `from common.xframe import XFrame`처럼 **하위 모듈 직접 import**로만 구성하며, 하위 모듈은 최상위 `from common import X`를 top-level에서 하지 않아야 한다(패키지 로드 순환 방지). 신선한 인터프리터에서 `import common; import modules; import metrics`가 순환 없이 성공함이 실행 증거 게이트다(REQ-ERGO-VALIDATE-5, L#1).
- **REQUIRED_PARAMS 형태**: 고정 키 집합 모듈은 `REQUIRED_PARAMS: tuple[str, ...]` 상수, 선택자 의존 모듈(denoise: `method`)은 `required_params(params) -> tuple[str, ...]` 함수. 균일 조회 헬퍼가 두 형태를 모두 해석한다. **키 이름 문자열만** 담으며 표본 수치값을 포함하지 않는다.
- **TC 번호 블록**: 신규 관심사는 **XDET-TC-050~055**(050=재노출/introspection · 051=REQUIRED_PARAMS 매니페스트 · 052=Params 조회/검증 · 053=metric_view 어댑터 · 054=additive 계약(lint-imports+순환+기존 테스트) · 055=하드코딩/격리 가드). Gen 1 형상 동결 범위(`_GEN1_TC_RANGE = range(0,22)`) 무간섭. **예약-미사용**: 022~029·038~039·056~059는 본 SPEC 미사용. 신규 테스트 소스는 Gen 1 TC id(`000`~`021`) 문자열을 포함하지 않는다(SPEC-VIEWER-001 D9 선례).

## Requirements (EARS)

### REQ-ERGO-EXPORTS — 패키지 공개 표면 curated 재노출 + `__all__` (gap #1, SWR-000-8, XDET-TC-050)

- **REQ-ERGO-EXPORTS-1 (Event-Driven)** — WHEN `common`/`modules`/`metrics` 패키지가 import되면, THEN 각 패키지 `__init__`은 큐레이션된 공개 심볼을 재노출하고 `__all__`로 공개 표면을 명시해야 한다(`pipeline/__init__.py` 선례). `metrics`의 `__all__`은 기존 `metrics/__init__.py` docstring이 이미 열거한 목록을 인코딩하고 신규 `metric_view`를 포함한다.
- **REQ-ERGO-EXPORTS-2 (Ubiquitous)** — 재노출은 additive여야 한다: 기존 심층경로 import(예 `from common.contract import Params`, `from metrics.mtf import compute_mtf`, `from modules import gain`)는 의미 변화 없이 계속 동작해야 한다.
- **REQ-ERGO-EXPORTS-3 (Unwanted)** — IF 어떤 패키지 `__init__`의 재노출이 상향/횡단 import(common→modules/metrics/pipeline, 또는 `modules.*` 상호 import 유발)나 순환 import를 발생시키면, THEN 이를 금지해야 한다(재노출은 자기 패키지 하위 모듈에서만; `uv run lint-imports` 0 broken 유지, SWR-000-8).

### REQ-ERGO-PARAMS — 모듈별 필요-파라미터 매니페스트(키 이름 전용) (gap #2, SWR-000-6, XDET-TC-051·055)

- **REQ-ERGO-PARAMS-1 (Event-Driven)** — WHEN 처리 모듈의 필요 Params를 조회하면, THEN 각 `modules/` 처리 모듈은 자신이 요구하는 Params **키 이름** 목록을 모듈 표면에 노출해야 한다: 고정 키 집합 모듈은 `REQUIRED_PARAMS: tuple[str, ...]` 상수로, 선택자(예 `method` ∈ {bm3d, nlm})에 따라 달라지는 모듈은 `required_params(params) -> tuple[str, ...]` 함수로 노출한다.
- **REQ-ERGO-PARAMS-2 (Ubiquitous)** — 매니페스트는 모듈이 **실제로 읽는 키**와 일치해야 한다(예 gain=(`gain_min`,`gain_max`)=`modules/gain.py::P_GAIN_MIN`/`P_GAIN_MAX`; denoise `required_params(params)`=`_required_keys(method)` 반환 집합) — 발명 금지, 소스 상수/헬퍼에서 파생.
- **REQ-ERGO-PARAMS-3 (Unwanted)** — IF 매니페스트가 키 이름 외의 값(표본/팬텀 수치값, 예 `gain_min=0.5`·`gain_max=2.0` — `tests/modules/phantoms/corrections.py` 상주)을 담으면, THEN 이를 금지해야 한다(하드코딩 금지, SPEC-REALDATA-001 격리 존중 — 값은 Params/CalibSet/설정에서만).

### REQ-ERGO-INTROSPECT — Params 조회/검증 표면(additive, backward-compatible) (gap #3, XDET-TC-052)

- **REQ-ERGO-INTROSPECT-1 (Event-Driven)** — WHEN 소비자가 필요한 키의 Params 내 존재를 확인하려 하면, THEN `common/contract.py::Params`는 additive 검증 메서드 `validate(required)`를 제공하여, 누락 키가 있으면 **누락된 모든 키를 나열하는 명확한 오류**를 발생시키고 전부 존재하면 통과해야 한다(단건-우선 실패 아님 — 누락 전건 수집).
- **REQ-ERGO-INTROSPECT-2 (Ubiquitous)** — Params 조회/검증 표면 추가는 backward-compatible이어야 한다: 기존 `.get()`·`.hash()`·`.values`(불변 MappingProxy)의 동작·불변성(frozen)은 변하지 않아야 한다.
- **REQ-ERGO-INTROSPECT-3 (Ubiquitous)** — `Params.validate`는 소비자(GUI/테스트) 편의 표면이며, 기존 처리 모듈의 자체 검증(`modules/denoise.py::DenoiseError`·gain `_require` 등)과 그 **오류 타입을 대체·변경하지 않는다**(모듈의 검증 채택 여부는 본 SPEC 범위 밖 — 표면 추가만).

### REQ-ERGO-METRIC — metric 반환형 통일 어댑터(치환 아님, 거동 보존) (gap #4, XDET-TC-053)

- **REQ-ERGO-METRIC-1 (Event-Driven)** — WHEN 제네릭 지표 디스패치(name→run→render)가 임의의 metric-유사 반환값을 렌더하려 하면, THEN `metrics/result.py`는 additive 정규화 어댑터 `metric_view(obj) -> MetricResult`를 제공하여, `MetricResult`는 **항등**(그대로 반환), `ThicknessResult`는 요약 스칼라(`method`/`scale_px`/`changed`)를 `.values`로 투영한 MetricResult-형상 뷰로 산출해야 한다 — 특수 케이스 없이 균일 디스패치가 가능해야 한다.
- **REQ-ERGO-METRIC-2 (Ubiquitous)** — `metrics/ndt.py::correct_thickness`는 계속 `ThicknessResult`를 반환하며 그 네이티브 필드(`flattened`/`low_freq`/`method`/`scale_px`/`changed`/`warnings`) 접근이 보존되어야 한다(반환형 변경 아님 — additive 투영만; 기존 4개 테스트 파일의 `res.flattened`/`res.changed`/`res.low_freq` 소비 불변).
- **REQ-ERGO-METRIC-3 (Unwanted)** — IF metric 반환형 통일이 기존 `MetricResult` 소비자(`apps/gui/metrics_panel.py::plot_mtf` 등 `.values`/`.get()` 접근)를 깨거나 `ThicknessResult`의 반환형을 `MetricResult`로 치환(mutate)하면, THEN 이를 금지해야 한다(어댑터=additive 투영, 반환형 치환 아님).

### REQ-ERGO-CONTRACT — additive · 거동 보존 불변식 (SWR-000-6/8/9, VIEWER additive 규약)

- **REQ-ERGO-CONTRACT-1 (Ubiquitous)** — 본 작업은 additive이다: 기존 심층경로 import, `process(XFrame,CalibSet,Params)->XFrame` 시그니처, `CANONICAL_ORDER`/파이프라인 순서, `_KIND_BY_STAGE`는 불변(KEPT)이며 신규 `CalibKind`·신규 파이프라인 스테이지·신규 처리 모듈은 없다(본 SPEC은 개발자 소비 표면 개선이지 처리 모듈이 아님).
- **REQ-ERGO-CONTRACT-2 (Ubiquitous)** — 본 SPEC은 `common/contract.py`를 **additive로 수정할 수 있다**(Params 조회/검증이 본 SPEC의 목적 — SPEC-REALDATA-001의 contract.py 무변경 제약과 다름). 수정은 최소·backward-compatible로 한정하며, `Params`의 frozen·MappingProxy 불변성을 유지한다.
- **REQ-ERGO-CONTRACT-3 (Event-Driven)** — WHEN 재노출·매니페스트·`Params.validate`·`metric_view`가 추가되면, THEN 기존 import-linter 계약이 전건 KEPT(0 broken)이고 레이어링·모듈 독립성이 불변이어야 한다.

### REQ-ERGO-VALIDATE — 실행 증거 게이트 + TC 매핑 (lesson L#1, XDET-TC-050~055)

- **REQ-ERGO-VALIDATE-1 (Event-Driven)** — WHEN 공개 표면 introspection 테스트가 실행되면, THEN (a) `common`/`modules`/`metrics` 각 `__all__`이 비어있지 않고, (b) `__all__`의 모든 이름이 해당 패키지에서 실제로 resolve되며(`getattr` 성공), (c) 대표 심층경로 import가 여전히 동작함을 **실제 실행**으로 단정해야 한다(XDET-TC-050; L#1 — "introspection이 된다"는 서술이 아니라 실행 증거).
- **REQ-ERGO-VALIDATE-2 (Event-Driven)** — WHEN 매니페스트 테스트가 실행되면, THEN 각 `modules/` 처리 모듈이 `REQUIRED_PARAMS` 상수 또는 `required_params(params)` 함수를 노출하고, 그 값이 모듈이 실제 읽는 키와 일치함(gain=(`gain_min`,`gain_max`); denoise `required_params`가 method별로 `_required_keys(method)`와 동일 집합 반환)을 단정해야 한다(XDET-TC-051).
- **REQ-ERGO-VALIDATE-3 (Event-Driven)** — WHEN 하드코딩/격리 가드 테스트가 실행되면, THEN 어떤 모듈의 `REQUIRED_PARAMS`/`required_params(...)` 반환도 **문자열 키 이름만** 담고 수치(int/float) 원소나 표본-유도 값을 포함하지 않음을 단정해야 한다(XDET-TC-055; SPEC-REALDATA-001 격리·CLAUDE.md 파라미터 정책 집행).
- **REQ-ERGO-VALIDATE-4 (Event-Driven)** — WHEN `Params.validate` 테스트가 실행되면, THEN (a) 누락 키가 있는 Params에 대해 **누락된 전체 키 목록**을 담은 오류가 발생하고, (b) 전부 존재하는 Params는 통과하며, (c) `.get()`·`.hash()`·`.values` 기존 동작과 frozen 불변성이 변하지 않음을 단정해야 한다(XDET-TC-052). 아울러 `params.validate(module.REQUIRED_PARAMS)` 조합이 매니페스트와 검증 표면을 연결함을 보여야 한다.
- **REQ-ERGO-VALIDATE-5 (Event-Driven)** — WHEN `metric_view` 및 additive-계약 게이트가 실행되면, THEN (a) `metric_view(MetricResult)`는 항등, `metric_view(ThicknessResult)`는 `method`/`scale_px`/`changed`가 담긴 MetricResult-형상 뷰로 투영되고 `correct_thickness`의 ThicknessResult 네이티브 필드 접근이 보존되며(XDET-TC-053), (b) `uv run lint-imports`가 0 broken이고 신선한 인터프리터에서 `import common; import modules; import metrics`가 순환 없이 성공하며 전 기존 테스트가 통과함을 단정해야 한다(XDET-TC-054; L#1 실행 증거 — 헛통과 아님).

## Exclusions (What NOT to Build)

- **처리 모듈·파이프라인 스테이지 신설 없음** — `process(XFrame,CalibSet,Params)->XFrame` 시그니처·`CANONICAL_ORDER`·`_KIND_BY_STAGE`·신규 `CalibKind`를 추가하지 않는다. 본 SPEC은 개발자 소비 표면 개선이다.
- **metric 반환형 치환/mutation 없음** — `correct_thickness`를 `MetricResult` 반환으로 바꾸지 않는다. `ThicknessResult`는 그대로 두고 additive `metric_view` 어댑터만 추가한다(4개 테스트 파일의 네이티브 필드 접근 보존).
- **모듈 검증 로직 이관 없음** — 기존 모듈의 자체 검증(`DenoiseError`·gain `_require`)을 `Params.validate`로 강제 이관하지 않는다(오류 타입 변경 → 테스트 파손 위험). 모듈의 매니페스트/`Params.validate` 채택 리팩터는 본 SPEC 범위 밖(하류/run-phase, 별도 작업).
- **표본-유도 수치 없음** — `REQUIRED_PARAMS`는 키 이름 문자열만 담는다. 어떤 `[B]`/`[T]`/`[P]` 수치값도 유도·하드코딩하지 않는다(SPEC-REALDATA-001 격리, CLAUDE.md 파라미터 정책).
- **import 의미 변경 없음** — 기존 심층경로 import는 불변. 재노출은 additive이며 순환·상향 import를 만들지 않는다.
- **metrics 엔진 함수 매니페스트 없음** — REQUIRED_PARAMS 매니페스트는 `modules/` 처리 모듈에 한정한다. metrics 엔진은 이미 `require_param`(REQ-METRICS-CORE-4) 표면을 가지므로 본 SPEC 범위 밖.
- **GUI 재작성 없음** — 본 SPEC은 GUI가 소비할 표면을 제공할 뿐, `apps/gui/`의 파라미터 폼/모듈 선택 UI 재구성은 하류(SPEC-VIEWER-001 후속) 소관이다.

## 결정 필요/확인 사항

아래 항목 중 **1은 확정(RESOLVED, 근거 대조 완료)**, **2·3·4는 확인 대상**이다. 항목 번호는 하류 참조를 위해 유지한다.

1. **[확정 — RESOLVED] metric 반환형 = 어댑터(치환/wrap 아님).** **결정**: `correct_thickness`는 `ThicknessResult`를 계속 반환하고, `metrics/result.py`에 additive `metric_view(obj) -> MetricResult`(MetricResult=항등, ThicknessResult=요약 스칼라 `method`/`scale_px`/`changed` 투영)를 추가한다. **rationale(근거 대조)**: (a) `res.flattened`/`res.changed`/`res.low_freq`를 직접 접근하는 테스트 4파일(`test_ndt_thickness`·`test_ndt_contract`·`test_review_fixes_ndt`·`test_tc_ndt`)이 반환형을 `MetricResult`로 치환하면 전부 깨진다 → 거동 보존 HARD 위반. (b) `ThicknessResult`는 EV 스칼라 지표가 아니라 SRb/CSa 측정에 소비되는 flatten 변환 산출물(2개 배열 `flattened`/`low_freq` 보유)이므로 `MetricResult`로 강제 wrap하면 "측정 vs 변환" 개념을 혼동하고 네이티브 필드 인체공학을 잃는다. (c) 어댑터는 순수 additive → 무위험. **확인(부차)**: `metric_view`의 정확한 투영 필드 집합(스칼라만 vs 배열 미리보기 포함), 그리고 `ThicknessResult.as_metric_result()` 메서드 미러를 추가로 둘지(기본값: 자유함수 `metric_view` 단일 엔트리만).
2. **[확인] REQUIRED_PARAMS 노출 범위.** 기본값: `modules/` 처리 모듈 12종(offset/gain/defect/lag/line_noise/saturation/geometry/grid/virtual_grid/denoise/mse/window) 전부가 매니페스트를 노출(고정 키=상수, 선택자 의존=함수). 확인: P1에서 전 12종을 요구할지 vs 대표 부분집합 + 패턴 확립으로 충분한지; Params를 읽지 않는 순수-passthrough 모듈은 빈 튜플(`()`)을 노출할지.
3. **[확인] `Params.validate` 오류 타입.** 기본값: 누락 전건을 나열하는 `ValueError`(또는 additive `MissingParamsError(ValueError)`)를 발생. 확인: 기존 `ValueError` 재사용 vs 신규 예외 도입; 비-발생 동반 조회자 `missing(required) -> tuple[str, ...]`(예외 없이 누락 목록 반환)를 함께 둘지.
4. **[확인] 모듈의 매니페스트/`Params.validate` 채택 리팩터.** 기본값: 본 SPEC은 표면 제공까지만(모듈은 자체 검증 유지 — 오류 타입 보존). 확인: 후속 SPEC(run-phase)에서 모듈을 `REQUIRED_PARAMS` + `Params.validate` 기반으로 이관할지(중복 제거 vs 오류-타입 회귀 위험 절충).
