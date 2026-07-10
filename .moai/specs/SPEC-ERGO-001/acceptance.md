# SPEC-ERGO-001 인수 기준 (acceptance.md)

관련: [spec.md](./spec.md) · [plan.md](./plan.md) · GitHub 이슈 #19

모든 시나리오는 **실제 실행 증거**를 단정한다(lesson L#1 — "예외 미발생"·"동작함" 같은 헛통과 금지). 명령은 전부 `uv run`, 한글 출력 시 `PYTHONIOENCODING=utf-8`(L#4).

## Scenario 1 — 패키지 공개 표면 introspection (XDET-TC-050, REQ-ERGO-EXPORTS-1/2, VALIDATE-1)

- **Given** `common`/`modules`/`metrics` 패키지에 재노출 + `__all__`이 추가된 상태에서,
- **When** 각 패키지를 import하고 `__all__`과 대표 심층경로 import를 조사하면,
- **Then** (a) `common.__all__`·`modules.__all__`·`metrics.__all__`이 각각 비어있지 않고, (b) 각 `__all__`의 **모든** 이름이 해당 패키지에서 `getattr`로 resolve되며, (c) `metrics.__all__`이 `metric_view`를 포함하고, (d) 기존 심층경로 import(`from common.contract import Params`, `from metrics.mtf import compute_mtf`, `from modules import gain`)가 여전히 성공한다.
- **Edge** `metrics/__init__.py` docstring이 열거한 목록(result/mtf/nps/dqe/lag/defect_stats/ndt 심볼)이 `metrics.__all__`에 전건 존재함을 단정(문서-코드 일치).

## Scenario 2 — 재노출이 순환/상향 import를 만들지 않음 (XDET-TC-054, REQ-ERGO-EXPORTS-3, CONTRACT-3, VALIDATE-5b)

- **Given** 재노출이 자기 패키지 하위 모듈에서만 구성된 상태에서,
- **When** 신선한 인터프리터에서 `uv run python -c "import common; import modules; import metrics; import pipeline"`를 실행하고 `uv run lint-imports`를 실행하면,
- **Then** (a) import가 순환 오류 없이 성공하고, (b) `lint-imports`가 **0 broken**(전 계약 KEPT)으로 종료하며, (c) `uv run pytest`의 전 기존 테스트가 통과한다.
- **Edge(음성 대조)** `common/__init__`이 `modules`/`metrics`/`pipeline`을 import하지 않음을 단정(상향 import 부재 — 소스 스캔 또는 import-linter forbidden 계약이 잡음).

## Scenario 3 — 모듈별 REQUIRED_PARAMS 매니페스트가 실제 소비 키와 일치 (XDET-TC-051, REQ-ERGO-PARAMS-1/2, VALIDATE-2)

- **Given** `modules/` 처리 모듈이 `REQUIRED_PARAMS` 상수 또는 `required_params(params)` 함수를 노출한 상태에서,
- **When** 각 모듈의 매니페스트를 조회하면,
- **Then** (a) `modules.gain.REQUIRED_PARAMS == (modules.gain.P_GAIN_MIN, modules.gain.P_GAIN_MAX) == ("gain_min", "gain_max")`이고, (b) denoise는 `method="bm3d"`/`"nlm"` 각각에 대해 `modules.denoise.required_params(params)`가 동일 method의 `modules.denoise._required_keys(method)`와 **같은 키 집합**을 반환하며, (c) 매니페스트를 노출한 모든 처리 모듈에서 조회가 `tuple[str,...]`을 산출한다.
- **Edge** 선택자 값이 없는 denoise 호출(`method` 미지정)은 기본 method 키 집합을 반환(모듈 기본 거동과 일치).

## Scenario 4 — 매니페스트는 키 이름만, 표본 수치 배제 (XDET-TC-055, REQ-ERGO-PARAMS-3, VALIDATE-3)

- **Given** 매니페스트가 노출된 상태에서,
- **When** 전 처리 모듈의 `REQUIRED_PARAMS`/`required_params(...)` 반환을 수집하면,
- **Then** (a) 모든 원소가 `str`(키 이름)이고, (b) 어떤 원소도 int/float(수치)가 아니며, (c) 팬텀 수치값(`0.5`·`2.0` 등 `tests/modules/phantoms/corrections.py` 상주값)이 매니페스트에 등장하지 않는다.
- **Edge(음성 대조)** `gain_min`/`gain_max`는 **키 이름**으로 매니페스트에 존재하지만 그 수치(0.5/2.0)는 존재하지 않음을 함께 단정(격리 경계 명시).

## Scenario 5 — Params 조회/검증 표면 (XDET-TC-052, REQ-ERGO-INTROSPECT-1/2, VALIDATE-4)

- **Given** `common/contract.py::Params`에 additive `validate(required)`가 추가된 상태에서,
- **When** 일부 키가 누락된 Params와 전부 존재하는 Params에 대해 `validate`를 호출하면,
- **Then** (a) 누락 Params는 **누락된 전체 키 목록**을 담은 오류를 발생시키고(첫 누락 하나가 아니라 전건), (b) 전부 존재하는 Params는 예외 없이 통과하며, (c) `p.get(k)`·`p.hash()`·`p.values`(MappingProxy)의 기존 반환·불변성(frozen — `p.values[k]=…`가 실패)이 변하지 않는다.
- **Edge(결합)** `p.validate(modules.gain.REQUIRED_PARAMS)`가 gain 필요 키(`gain_min`/`gain_max`) 부재 시 두 키를 모두 나열하는 오류를 발생(매니페스트↔검증 표면 연결).

## Scenario 6 — metric 반환형 통일 어댑터 (XDET-TC-053, REQ-ERGO-METRIC-1/2/3, VALIDATE-5a)

- **Given** `metrics/result.py::metric_view`가 추가되고 `correct_thickness`/`ThicknessResult`가 불변인 상태에서,
- **When** `metric_view`에 `MetricResult`와 `correct_thickness`가 반환한 `ThicknessResult`를 각각 전달하면,
- **Then** (a) `metric_view(MetricResult(...))`가 **동일 객체**(항등)를 반환하고, (b) `metric_view(thickness_result)`가 `MetricResult`이며 그 `.values`에 `method`·`scale_px`·`changed`가 담기고 `.get("changed")`가 원 `ThicknessResult.changed`와 같으며, (c) `correct_thickness(...)`가 여전히 `ThicknessResult`를 반환하고 `res.flattened`·`res.low_freq`·`res.changed` 네이티브 접근이 보존된다.
- **Edge(회귀)** 기존 `apps/gui/metrics_panel.py::plot_mtf`가 반환한 `MetricResult`의 `.get("mtf")`/`.get("frequencies_lpmm")` 접근이 불변임을 단정(기존 MetricResult 소비자 무영향).

## 엣지 케이스 / 음성 대조 요약

- **순환 import 음성 대조**: `common/__init__`이 상위 레이어를 import하지 않음(Scenario 2 Edge).
- **격리 음성 대조**: 매니페스트에 키 이름은 있으나 표본 수치는 없음(Scenario 4 Edge).
- **거동 보존 회귀**: ndt thickness 테스트 4파일(`test_ndt_thickness`·`test_tc_ndt`·`test_review_fixes_ndt`·`test_ndt_contract`) + contract/GUI 테스트 전건 통과(Scenario 2c, Scenario 6 Edge).

## Definition of Done (품질 게이트)

- [ ] **DoD-1** `common`/`modules`/`metrics` 각 `__init__`이 `__all__` + 큐레이션 재노출을 노출하고, `__all__` 전 이름이 resolve됨 (XDET-TC-050 / Scenario 1).
- [ ] **DoD-2** 신선 인터프리터 `import common, modules, metrics, pipeline`가 순환 없이 성공하고 `uv run lint-imports`가 0 broken (XDET-TC-054 / Scenario 2).
- [ ] **DoD-3** 각 `modules/` 처리 모듈이 `REQUIRED_PARAMS` 상수 또는 `required_params(params)` 함수를 노출하고, 값이 실제 소비 키와 일치(gain·denoise 게이트) (XDET-TC-051 / Scenario 3).
- [ ] **DoD-4** 매니페스트 반환 원소가 전부 `str` 키 이름이며 표본 수치를 포함하지 않음 (XDET-TC-055 / Scenario 4).
- [ ] **DoD-5** `Params.validate(required)`가 누락 전건을 나열해 오류를 내고, 전부 존재 시 통과하며, `.get()`/`.hash()`/`.values` 불변 (XDET-TC-052 / Scenario 5).
- [ ] **DoD-6** `metric_view`가 MetricResult=항등·ThicknessResult=요약 투영을 산출하고, `correct_thickness`의 ThicknessResult 네이티브 필드 접근이 보존됨 (XDET-TC-053 / Scenario 6).
- [ ] **DoD-7** 전 기존 테스트 통과(회귀 0) — 특히 ndt thickness 4파일 + contract + GUI 테스트 (XDET-TC-054 / Scenario 2c·6 Edge).
- [ ] **DoD-8** `process` 시그니처·`CANONICAL_ORDER`·`_KIND_BY_STAGE`·신규 `CalibKind` 무변경(KEPT), 신규 처리 모듈/스테이지 없음 (REQ-ERGO-CONTRACT-1).
- [ ] **DoD-9** 신규 테스트 소스는 XDET-TC-050~055 id만 사용하고 Gen 1 TC id(`000`~`021`) 문자열을 포함하지 않음(캡스톤 스캔 `range(0,22)` 무간섭, SPEC-VIEWER-001 D9 선례).
