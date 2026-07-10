# SPEC-ERGO-001 구현 계획 (plan.md)

관련: [spec.md](./spec.md) · [acceptance.md](./acceptance.md) · GitHub 이슈 #19

/ 시간 추정 없음 — 우선순위(High/Medium/Low)와 단계 순서로만 기술한다(CLAUDE.md 파라미터 정책·시간추정 금지).

## 개요

GUI 검토(#14)에서 발견된 소비자 인체공학 갭 4종을 **additive·거동 보존**으로 해소한다. 네 갭은 상호 독립적이며 병렬 구현 가능하나, 검증은 공통 additive-계약 게이트(`uv run lint-imports` 0 broken + 전 기존 테스트 통과 + 순환 import 없음)로 수렴한다. 본 SPEC은 처리 모듈/스테이지를 신설하지 않고, `common/contract.py`만 additive로 수정한다.

## 기술 접근 (갭별)

### 갭 #1 — 패키지 재노출 + `__all__` (REQ-ERGO-EXPORTS)

- 대상: `common/__init__.py`, `modules/__init__.py`, `metrics/__init__.py`. 선례: `pipeline/__init__.py`.
- **재노출 원천은 자기 패키지 하위 모듈에서만**(레이어링·순환 방지, REQ-ERGO-EXPORTS-3):
  - `common/__init__` ← `common.xframe`(XFrame, new_frame, NoiseModel 등) · `common.contract`(Params, ProcessModule, run_harness 등) · `common.calibset`(CalibSet, CalibKind) · 기타 공용 컴포넌트(io, robust_stats, pyramid, histogram_fov, fft_psd, mask_ops, equivalence) 중 공개 대상만 큐레이션.
  - `modules/__init__` ← 모듈 객체 재노출(`from modules import offset, gain, ...`); `modules/registry.py`가 이미 전 모듈을 import하므로 신규 순환 위험 없음. `independence` 계약은 leaf 모듈 상호 import를 보는 것이지 패키지 `__init__`의 import를 보지 않음(무영향).
  - `metrics/__init__` ← `metrics/__init__.py` docstring이 이미 열거한 목록(result/mtf/nps/dqe/lag/defect_stats/ndt) + 신규 `metric_view`.
- 각 `__init__`에 `__all__`(문자열 튜플) 명시. 기존 심층경로 import는 손대지 않음(additive, REQ-ERGO-EXPORTS-2).
- **순환 주의**: 하위 모듈이 top-level에서 `from common import X`를 하지 않는지 확인(현재 하위 모듈은 `from common.xframe import ...` 식 직접 import 사용). 신선한 인터프리터 import 스모크로 검증.

### 갭 #2 — 모듈별 REQUIRED_PARAMS 매니페스트 (REQ-ERGO-PARAMS)

- 각 `modules/` 처리 모듈 표면에 필요 Params **키 이름**을 노출:
  - 고정 키 모듈(예 gain): `REQUIRED_PARAMS = (P_GAIN_MIN, P_GAIN_MAX)` — 기존 모듈 상수를 재사용(발명 금지, REQ-ERGO-PARAMS-2).
  - 선택자 의존 모듈(denoise): `def required_params(params) -> tuple[str, ...]` — 내부적으로 기존 `_required_keys(method)`를 재사용하여 상수 매니페스트와 헬퍼가 어긋나지 않게 한다.
- 균일 조회: 소비자가 `getattr(mod, "REQUIRED_PARAMS", None)` 또는 `mod.required_params(params)`로 해석. (선택) `modules/registry.py` 또는 신규 얇은 헬퍼가 두 형태를 정규화하여 `(module_name -> tuple[str,...])`를 반환할 수 있으나, 최소 범위 유지를 위해 헬퍼는 필요 시에만.
- **키 이름 문자열만** — 팬텀 수치값(`gain_min=0.5` 등, `tests/modules/phantoms/corrections.py`)은 절대 넣지 않음(REQ-ERGO-PARAMS-3).

### 갭 #3 — Params 조회/검증 표면 (REQ-ERGO-INTROSPECT)

- `common/contract.py::Params`에 additive 메서드 추가(frozen/MappingProxy 불변 유지):
  - `validate(required: Iterable[str]) -> None` — 누락 키 **전건**을 수집해 명확한 오류(누락 키 목록 포함)를 발생, 전부 존재하면 통과. 단건-우선 실패 아님(denoise `_require_present` 정신 계승).
- 기존 `.get()`/`.hash()`/`.values` 무변경(REQ-ERGO-INTROSPECT-2). 모듈 자체 검증(`DenoiseError`·gain `_require`)은 그대로(REQ-ERGO-INTROSPECT-3) — `Params.validate`는 소비자 편의 표면.
- 결합 사용 예: `params.validate(modules.gain.REQUIRED_PARAMS)` — 매니페스트(갭 #2)와 검증 표면이 자연스럽게 연결(REQ-ERGO-VALIDATE-4).

### 갭 #4 — metric 반환형 통일 어댑터 (REQ-ERGO-METRIC)

- `metrics/result.py`에 additive 자유함수 `metric_view(obj) -> MetricResult`:
  - `MetricResult` 입력 → 항등 반환.
  - `ThicknessResult` 입력 → `MetricResult(name="thickness_correction", values={"method":…, "scale_px":…, "changed":…}, warnings=obj.warnings)` 형상 뷰로 투영(요약 스칼라). 배열(`flattened`/`low_freq`) 포함 여부는 「결정 필요/확인」 1의 부차 확인.
- `metrics/ndt.py::correct_thickness`와 `ThicknessResult`는 **불변** — 네이티브 필드 접근 보존(REQ-ERGO-METRIC-2). 기존 `MetricResult` 소비자(`metrics_panel.plot_mtf`) 무영향(REQ-ERGO-METRIC-3).
- `metric_view`를 `metrics/__init__` `__all__`에 포함(갭 #1과 연동).

## 마일스톤 (우선순위 순)

- **M1 (Priority High) — 재노출 + `__all__`**: `common`/`modules`/`metrics` `__init__` 큐레이션 재노출. DoD: XDET-TC-050(introspection) + 신선 인터프리터 import 스모크 통과, `uv run lint-imports` 0 broken.
- **M2 (Priority High) — Params 조회/검증**: `common/contract.py::Params.validate` additive 추가. DoD: XDET-TC-052 통과, 기존 contract 테스트 회귀 0.
- **M3 (Priority Medium) — REQUIRED_PARAMS 매니페스트**: 각 `modules/` 모듈 표면에 키-이름 매니페스트. DoD: XDET-TC-051(일치) + XDET-TC-055(하드코딩/격리 가드) 통과.
- **M4 (Priority Medium) — metric_view 어댑터**: `metrics/result.py::metric_view`. DoD: XDET-TC-053 통과, ndt thickness 테스트 4파일 회귀 0.
- **M5 (Priority High) — additive-계약 수렴 게이트**: XDET-TC-054(`uv run lint-imports` 0 broken + 순환 없음 + 전 기존 테스트 통과). 전 마일스톤 통합 후 실행.

의존: M1은 M4의 `metric_view` 재노출을 위해 M4와 느슨히 연동(순서상 M4 후 M1의 metrics `__all__` 최종화 가능하나, `metric_view` 이름을 먼저 예약하면 병렬 가능). M5는 전 마일스톤 뒤 수렴.

## 파일 변경 목록 (전부 additive)

| 파일 | 변경 | 근거 |
|---|---|---|
| `common/__init__.py` | 재노출 + `__all__` 추가 | REQ-ERGO-EXPORTS |
| `modules/__init__.py` | 재노출 + `__all__` 추가 | REQ-ERGO-EXPORTS |
| `metrics/__init__.py` | 재노출 + `__all__`(+`metric_view`) 추가 | REQ-ERGO-EXPORTS/METRIC |
| `common/contract.py` | `Params.validate` additive 메서드 | REQ-ERGO-INTROSPECT (본 SPEC 유일 허용 contract 수정) |
| `metrics/result.py` | `metric_view` additive 자유함수 | REQ-ERGO-METRIC |
| `modules/*.py`(처리 모듈) | `REQUIRED_PARAMS` 상수 또는 `required_params()` 함수 | REQ-ERGO-PARAMS (범위=「결정 필요/확인」 2) |
| `tests/…`(신규) | XDET-TC-050~055 실행 증거 테스트 | REQ-ERGO-VALIDATE |

`CANONICAL_ORDER`·`_KIND_BY_STAGE`·`process` 시그니처·`common/xframe.py`·`pipeline/orchestrator.py`·`pyproject.toml` import-linter 계약 = **무변경(KEPT)**.

## 리스크

- **순환 import(중간)** — `common/__init__` 재노출이 하위 모듈 top-level `from common import ...`와 만나면 순환. 완화: 하위 모듈은 하위-모듈 직접 import만 사용함을 확인 + 신선 인터프리터 import 스모크를 M1 DoD에 포함.
- **매니페스트-소스 drift(낮음)** — `REQUIRED_PARAMS`가 모듈 실제 소비 키와 어긋날 위험. 완화: denoise는 `required_params`가 `_required_keys`를 재사용, gain은 기존 `P_GAIN_*` 상수 재사용 → 단일 출처. XDET-TC-051이 일치를 게이트.
- **오류 타입 회귀(낮음)** — 모듈을 `Params.validate`로 강제 이관하면 `DenoiseError` 등을 기대하는 테스트가 깨짐. 완화: 이관은 범위 밖(REQ-ERGO-INTROSPECT-3/Exclusions), 본 SPEC은 표면 추가만.
- **격리 위반(낮음)** — 매니페스트에 표본 수치 유입. 완화: XDET-TC-055가 반환 원소가 문자열 키 이름만임을 게이트(SPEC-REALDATA-001 격리).

## 검증 명령 (전부 `uv run`, 한글 출력 시 `PYTHONIOENCODING=utf-8`)

- 레이어링/순환: `uv run lint-imports`(0 broken) + `uv run python -c "import common, modules, metrics"`(순환 없음).
- 신규 TC: `uv run pytest tests/ -k "tc_050 or tc_051 or tc_052 or tc_053 or tc_054 or tc_055"`.
- 회귀: `uv run pytest`(전 기존 테스트 통과 — 특히 `tests/metrics/test_ndt_thickness.py`·`test_tc_ndt.py`·`test_review_fixes_ndt.py`·`test_ndt_contract.py` 및 contract 테스트).
