# SPEC-VIEWER-001 Phase 0 스파이크 리포트

- SPEC: `.moai/specs/SPEC-VIEWER-001/spec.md` REQ-VIEW-SPIKE-1~3
- 근거 문서: `docs/GUI_CRITERIA.md` §2.3 (스파이크 게이트), §2 (스택 결정)
- 측정 스크립트: `scripts/spike_gui_probe.py` (본 리포트 생성 후 저장소에 정식 배치, 커밋 대상 아님 — Phase 0.5에서 일괄 커밋)
- 측정 일자: 2026-07-10

## 측정 환경

- OS: Windows 11 Pro 10.0.26200 (x86_64)
- Python: 3.12.10
- uv: 0.11.19
- Qt 바인딩: PySide6 6.10.3
- napari: 0.7.1 (스파이크 목적으로 임시 설치, 결론에 따라 최종 extras에서 제거)
- pyqtgraph: 0.14.0
- GPU: 실측 시 하드웨어 가속 없는 오프스크린 경로(Qt `offscreen` QPA 플랫폼) 사용 — Windows 러너 헤드리스 CI 조건(C-14/C-15)과 동일

## 결론 요약

**확정 스택: pyqtgraph (PySide6 위) — 폴백 채택.**

결정적 이유: SG-3(콜드 스타트) 측정 중 napari가 **C-14/C-15가 요구하는 정확한 헤드리스 CI 구성**(`QT_QPA_PLATFORM=offscreen`, Windows 러너에 xvfb 불요구)에서 `napari.Viewer()` 생성 자체가 크래시한다. napari의 vispy 캔버스는 예외 처리 없이 실제 OpenGL 컨텍스트를 요구하는데(`napari/_vispy/utils/gl.py::get_max_texture_sizes`, try/except 없음), Windows의 Qt `offscreen` QPA 플러그인은 `createPlatformOpenGLContext`를 지원하지 않는다(`WARNING: This plugin does not support createPlatformOpenGLContext!` — Qt 자체 경고, napari 버그 아님). 이는 SG-1/SG-2 측정 이전에 뷰어 생성 단계에서 발생하는 구조적 실패이며, `QT_OPENGL=software` 등 소프트웨어 렌더러 강제 전환도 동일하게 실패해 회피 불가능함을 확인했다. REQ-VIEW-SPIKE-2(SG-1~3 중 하나라도 미충족 시 pyqtgraph 폴백 — 단일 순서 결정)에 따라 즉시 폴백을 확정한다.

참고로 실제 데스크톱 세션(오프스크린이 아닌 일반 Qt 플랫폼)에서는 napari가 정상 동작하며 SG-1/SG-2도 통과했다(아래 "참고: 비-헤드리스 napari 측정" 참조). 즉 이번 실패는 napari 자체의 결함이 아니라 **"Windows CI 러너에서 xvfb 없이 offscreen만으로 헤드리스 검증"이라는 C-14/C-15의 하드 요구조건과 napari의 OpenGL 의존성이 근본적으로 충돌**하는 문제이며, 대화형 환경에서의 성공 여부와 무관하게 SPEC이 요구하는 CI 조건에서는 채택 불가하다.

## SG-1: 호버 픽셀 프로브 — 저장된 float32 원값 노출 여부

측정 방법: `napari.layers.Image.get_value(position=(row, col), world=False)`로 4개 임의 좌표를 프로브하고, 3072×3072 `np.random.default_rng(0).standard_normal(...).astype(np.float32)` 합성 프레임의 원본 배열값과 정확히 일치하는지 비교(오프스크린이 아닌 대화형 Qt 세션에서 측정 — 헤드리스 offscreen에서는 뷰어 생성 자체가 SG-3 실패로 불가능했음).

| 좌표 | 원본 float32 | 프로브 값 | 정확히 일치 |
|---|---|---|---|
| (0, 0) | 0.1257302165031433 | 0.1257302165031433 | Yes |
| (1536, 1536) | 1.8942281007766724 | 1.8942281007766724 | Yes |
| (3071, 3071) | 0.9654712080955505 | 0.9654712080955505 | Yes |
| (777, 2222) | 1.0561987161636353 | 1.0561987161636353 | Yes |

**판정: PASS** (대화형 환경 기준. `layer.get_value()`가 8-bit 표시값이 아닌 원본 float32 데이터 배열 값을 그대로 반환함을 확인.)
**단, 헤드리스 CI 구성(offscreen)에서는 뷰어 생성 자체가 SG-3에서 실패하므로 이 PASS는 CI 조건에서 재현되지 않는다.**

## SG-2: 3072×3072 float32 W/L(contrast_limits) 조작 응답 시간 — `[T]` 100ms 이내

측정 방법: 동일 프레임에 대해 `layer.contrast_limits = (lo, hi)` 5회 반복 설정, `time.perf_counter()`로 각 호출 소요시간 측정(대화형 Qt 세션).

- 개별 측정값(ms): 1.071, 0.613, 0.459, 0.449, 0.441
- 평균: 0.607ms / 최대: 1.071ms

**판정: PASS** (100ms 임계 대비 약 100배 여유. 단 SG-1과 동일하게 대화형 환경 한정 — 헤드리스 CI 조건에서는 측정 불가.)

## SG-3: 콜드 스타트(임포트+뷰어 생성) → 상호작용 가능 시간 — `[T]` 10s 이내

측정 방법: 별도 하위 프로세스에서 `QT_QPA_PLATFORM=offscreen` 환경변수(C-14/C-15 CI 구성과 동일)로 `import napari; viewer = napari.Viewer(show=False)` 실행.

결과: **에러로 종료** (10s 임계 판정 불가 — 애초에 뷰어 생성 실패).

```
WARNING: QOpenGLWidget is not supported on this platform.
WARNING: This plugin does not support createPlatformOpenGLContext!
...
OpenGL.error.GLError: GLError(
    err = 1282,
    description = b'invalid operation',
    baseOperation = glGetIntegerv,
    ...
)
```

경로: `napari.Viewer()` → `Window.__init__` → `QtViewer.__init__` → `VispyCanvas.__init__` → `get_max_texture_sizes()` → `gl.glGetParameter(GL_MAX_TEXTURE_SIZE)` → OpenGL 컨텍스트 부재로 크래시. `get_max_texture_sizes()`는 `@lru_cache`로 감싸여 있고 OpenGL 호출에 예외 처리가 없어(napari 0.7.1 소스 확인), 오프스크린 QPA 플랫폼에서 회피 불가능한 하드 실패다. `QT_OPENGL=software` 환경변수를 추가해도 동일 에러가 재현되어(Qt의 offscreen 플러그인 자체가 OpenGL 컨텍스트 생성을 지원하지 않음), 대안적 소프트웨어 렌더링 경로도 없음을 확인했다.

**판정: FAIL** (C-14/C-15가 요구하는 정확한 헤드리스 CI 구성에서 재현 불가능한 하드 블로커. REQ-VIEW-SPIKE-2에 따라 즉시 pyqtgraph 폴백 트리거.)

### 참고: 비-헤드리스 napari 측정 (동일 프로세스, offscreen 미사용)

CI 조건이 아닌 일반 대화형 Qt 세션에서는 정상 동작을 확인함(참고용, SPEC의 판정 기준은 아님):

- import: 0.088s
- 뷰어 준비: 3.324s (누적 3.412s)
- 10s 임계 대비 여유 있게 통과 (대화형 환경 한정)

## 폴백 확정 스택 실측: pyqtgraph (PySide6) — 동일 SG-1~3을 offscreen 헤드리스 구성에서 재측정

napari가 SG-3에서 실패함에 따라 REQ-VIEW-SPIKE-2 절차대로 pyqtgraph 폴백을 동일한 `QT_QPA_PLATFORM=offscreen` 헤드리스 구성에서 실측했다.

### SG-1 (pyqtgraph, offscreen)

`pyqtgraph.ImageView.setImage(frame)` 후 `iv.image[row, col]`로 저장된 배열값을 직접 조회(`ImageView`는 원본 배열을 무변형 보관하며 `setLevels`는 표시 LUT에만 영향):

| 좌표 | 원본 float32 | 프로브 값 | 정확히 일치 |
|---|---|---|---|
| (0, 0) | 0.1257302165031433 | 0.1257302165031433 | Yes |
| (1536, 1536) | 1.8942281007766724 | 1.8942281007766724 | Yes |
| (3071, 3071) | 0.9654712080955505 | 0.9654712080955505 | Yes |
| (777, 2222) | 1.0561987161636353 | 1.0561987161636353 | Yes |

**판정: PASS** (offscreen 헤드리스 구성에서 재현됨)

### SG-2 (pyqtgraph, offscreen)

`iv.setLevels(lo, hi)` 5회 반복(동일 5개 구간):

- 개별 측정값(ms): 0.091, 0.068, 0.088, 0.066, 0.059
- 평균: 0.074ms / 최대: 0.091ms

**판정: PASS** (100ms 임계 대비 약 1000배 여유, offscreen 헤드리스 구성에서 재현됨)

### SG-3 (pyqtgraph, offscreen, 별도 하위 프로세스)

`QT_QPA_PLATFORM=offscreen` 하위 프로세스에서 `import pyqtgraph; ...; pg.ImageView()` 콜드 스타트:

- import: 0.382s
- 뷰어 준비: 0.420s (누적)
- 전체 wall time: 0.520s

**판정: PASS** (10s 임계 대비 약 20배 여유, offscreen 헤드리스 구성에서 재현됨)

## 종합 판정표

| 게이트 | napari (offscreen/CI 구성) | napari (참고: 대화형) | pyqtgraph (offscreen/CI 구성) |
|---|---|---|---|
| SG-1 (float32 원값 프로브) | 측정 불가 (뷰어 생성 실패) | PASS | PASS |
| SG-2 (W/L 응답 ≤100ms) | 측정 불가 (뷰어 생성 실패) | PASS (max 1.07ms) | PASS (max 0.09ms) |
| SG-3 (콜드 스타트 ≤10s) | **FAIL** (GLError, offscreen에서 뷰어 생성 자체 불가) | PASS (3.41s) | PASS (0.52s) |

**확정 스택: pyqtgraph + PySide6.** napari는 REQ-VIEW-SPIKE-2에 명시된 단일 순서 결정에 따라 폴백으로 전환되었으며, 이는 감정적 선호가 아닌 실측(SG-3 하드 실패)에 근거한다.

## pyproject.toml `[gui]` extras 변경 내역

기존(스파이크 설치 시점, 임시):
```
gui = [
    "napari[pyside6]>=0.7",
    "magicgui>=0.10",
    "pyqtgraph>=0.14",
    "qtpy>=2.4",
    "pytest-qt>=4.4",
]
```

최종 확정(본 리포트 결론 반영):
```
gui = [
    "pyqtgraph>=0.14",
    "pyside6>=6.10",
    "qtpy>=2.4",
    "pytest-qt>=4.4",
]
```

napari/magicgui 및 그 전이 의존성(vispy, app-model, dask, pandas, scikit-image, npe2 등 다수)을 제거했다 — SG-3 하드 실패로 채택 불가능한 스택을 굳이 설치 대상에 남겨 base 이외 설치 용량과 CI 표면적을 늘릴 이유가 없기 때문이다(근거는 본 리포트로 충분히 남았으므로 코드 내 존치는 불필요). `napari[pyside6]`를 통해서만 전이 도입되던 `pyside6`는 pyqtgraph의 Qt 바인딩으로서 명시적 직접 의존성으로 승격했다.

## 검증

- `uv sync --all-extras` 재실행으로 napari/magicgui/vispy 등 제거, pyside6 명시적 설치 확인.
- 기존 코어 테스트 스위트(`uv run pytest tests -q`) 465개 전부 통과 — `[gui]` extras 변경이 base 패키지(C-12 격리 요구사항)에 영향 없음을 확인.

## 남은 리스크 및 Phase 0.5 주의사항

1. **pyqtgraph는 앱 셸을 직접 구현해야 한다**(GUI_CRITERIA §2 폴백 행 비고: "앱 셸(도킹/파일선택/스레딩)을 직접 구현하는 비용이 대가"). napari가 제공하던 레이어 관리·블링크·마스크 오버레이 등 내장 기능을 `apps/gui/`에서 직접 구현해야 하며, 이는 애초 SPEC 스택 결정 매트릭스(GUI_CRITERIA §2, "실효 개발속도")가 napari를 1순위로 둔 이유였다는 점을 상기할 것 — Phase 1 일정/범위 재추정이 필요할 수 있다.
2. **C-15 로직 레벨 커버리지 문구 재확인 필요**: spec.md는 "napari 후보에서 make_napari_viewer(폴백에서 qtbot 기반)"이라 표기하는데, 본 스파이크로 napari 후보 자체가 Windows 헤드리스 CI에서 성립하지 않음이 확인되었으므로 스펙 문서(spec.md REQ-VIEW-ARCH-6, GUI_CRITERIA C-15)에서 "napari 후보" 관련 서술을 pyqtgraph/qtbot 단일 경로로 갱신해야 한다. 이는 SPEC 문서 정정(EARS 재작성) 범위이며 본 스파이크 실행 범위 밖이다 — Phase 0.5 또는 뒤이은 spec.md 개정에서 처리 필요.
3. **magicgui 제거로 인한 대체 필요**: napari 경로에서 magicgui가 담당하던 "함수 시그니처 → 자동 GUI 폼" 기능이 사라졌다. pyqtgraph 경로에서 파라미터 입력 위젯(모듈 Params 조작 등)은 PySide6 위젯을 직접 구성해야 한다.
4. **본 스파이크의 SG-1/SG-2 napari 수치는 대화형 세션 한정**이며 C-14/C-15가 요구하는 CI 조건(offscreen)에서는 애초에 재현 불가능하다는 점을 향후 참조 시 혼동하지 않도록 리포트 본문에 명시해 두었다(참고용 데이터임을 반드시 구분).
5. `scripts/spike_gui_probe.py`는 P1 골든 모델 파이프라인(common/modules/pipeline/metrics)과 무관한 Phase 0 도구이며 import-linter 계약 대상이 아니다. 저장소에 정식 배치할지, 스파이크 종료 후 삭제할지는 Phase 0.5에서 결정한다(현재는 유지 — 회귀 재현 스크립트로서 가치가 있다고 판단, 필요시 삭제).
