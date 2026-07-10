---
id: SPEC-VIEWER-001
title: "검증 GUI — 단위 모듈 검증기 + 파이프라인 비교 뷰어"
version: 0.1.5
status: draft
created: 2026-07-10
updated: 2026-07-10
author: drake.lee
priority: high
issue_number: 14
labels: [gui, viewer, verification-tool]
---

# SPEC-VIEWER-001 구현 계획 (초안) — 검증 GUI

> 상태: **draft** (run 단계 착수 전까지 유지). EARS 확정본은 [spec.md](./spec.md), 인수 기준은 [acceptance.md](./acceptance.md). 근거는 `docs/GUI_CRITERIA.md`(C-01~C-20·SG-1~SG-3·§4 선행 갭·§5 준수사항)·`docs/GUI_REVIEW.md`(§4.5 `apps/gui/` 확정). 소비 대상 계약은 [SPEC-INFRA-001](../SPEC-INFRA-001/spec.md)(`run_harness`·`ProcessModule`·`run_pipeline`·`CANONICAL_ORDER`·XFrame·`MaskFlag`, 변경 없음).

## 1. 개요

XDET P1 골든 모델(`common/ modules/ pipeline/ metrics/`)의 **검증용 GUI**를 `apps/gui/` 서브 프로젝트로 도입한다(이슈 #14). 두 능력을 하나의 앱·하나의 SPEC에서 단계형으로 제공: **Phase 1** 단위 모듈 검증기(fixture/raw → 모듈 1개 `ProcessModule.process` 실행으로 출력 XFrame 산출 + expected 동봉 fixture 시 `run_harness` 검증 병행 → 입력/출력/diff/마스크/이력 + 지표), **Phase 2** 파이프라인 비교 뷰어(raw+CalibSet → `CANONICAL_ORDER` 부분/전체 → 스테이지별 전/후 + 지표). GUI는 **읽기-실행 전용**(C-20)·**지표 자체 계산 0**(C-09)·코어 4계층을 **단방향 소비**(C-11)한다. 요구는 SWR가 아니라 GUI_CRITERIA의 C-NN·SG-N을 인용하며 `[T]` 수치는 설정에 외부화한다.

## 2. 기술 스택

| 항목 | 선택 | 근거 |
|---|---|---|
| 언어/런타임 | Python 3.11+ | tech.md |
| 확정 UI | **pyqtgraph**(PySide6 위, `ImageView` W/L·LUT·ROI) + Qt 바인딩 **PySide6**(LGPL) | Phase 0 스파이크 실측 확정(`.moai/reports/SPEC-VIEWER-001-spike.md`) — napari는 Windows 헤드리스 CI에서 OpenGL 컨텍스트 획득 실패로 SG-3 하드 실패, pyqtgraph는 SG-1~3 전부 PASS(W/L 최대 0.09ms, 콜드 스타트 0.52s) |
| 배제 | **napari**(Phase 0 스파이크 폐기, 헤드리스 CI 불가), **PyQt6**(GPL/상용), Streamlit/Panel/DearPyGui 등 | GUI_CRITERIA §2.1/§2.2 + 스파이크 리포트 |
| 시험 프레임워크 | pytest + pytest-qt, `QT_QPA_PLATFORM=offscreen`; qtbot 기반(napari 폐기) | C-14/C-15 |
| 라이선스 게이트 | `pip-licenses` allowlist(GPL-only 0, PyQt6 배제) | C-13 |
| 정적 검사 | import-linter forbidden(코어 4계층 → `apps.gui` 금지) + 의도적 위반 카나리 | C-11, lesson #1 |
| 의존성 격리 | 루트 `pyproject.toml` `[project.optional-dependencies] gui` | C-12, GUI_REVIEW §4.5 |
| 지표 | **기존 `metrics/` 엔진 호출 결과만**(GUI 계산 0) | C-09 |
| 수치 정책 | W/L 100ms·콜드 10s·RSS 2GB/LRU K·200ms·diff ±max\|diff\| = `[T]` 설정 외부화 | C-01/17/18/19/06, HARD 파라미터 정책 |

원칙: **정확성·재현성 단일 목표, 속도 최적화 금지.** `[T]` 임계 하드코딩 금지(설정 외부화). 코어 표면 불변(소비만). 지표 위임(계산 0). 읽기-실행 전용.

### napari→pyqtgraph 폴백 결정 — Phase 0 실측 완료 (REQ-VIEW-SPIKE HOW)

스파이크(Phase 0)에서 SG-1(호버 float32 원값)·SG-2(W/L 응답 `[T]` 100ms)·SG-3(콜드 스타트 `[T]` 10s)을 napari와 pyqtgraph 양쪽으로 Windows 헤드리스 CI 구성(`QT_QPA_PLATFORM=offscreen`)에서 실측 완료했다(`.moai/reports/SPEC-VIEWER-001-spike.md`). **napari는 SG-3에서 하드 실패**했다 — `napari.Viewer()` 생성 단계에서 vispy 캔버스가 OpenGL 컨텍스트 획득에 실패(`get_max_texture_sizes()` GLError, `QT_OPENGL=software` 강제 전환도 실패)하여 SG-1/SG-2는 애초에 측정이 불가능했다. **pyqtgraph는 동일 헤드리스 조건에서 SG-1~3 전부 PASS**했다 — W/L 응답 평균 0.074ms/최대 0.091ms(100ms 임계 대비 약 1000배 여유), 콜드 스타트 0.52s(10s 임계 대비 약 20배 여유), 호버 프로브 float32 원값 4개 좌표 전부 정확히 일치. REQ-VIEW-SPIKE-2(단일 순서 결정, 택일 없음)에 따라 **pyqtgraph로 즉시 확정**했다. 두 스택은 Qt+pytest-qt를 공유하므로 로직 레벨 테스트(레이어 생성·수치 적용·프로브)는 pyqtgraph 단일 경로로 구현하며, 백엔드 추상화 계층의 필요성은 낮아졌다(§3 참조).

## 3. 파일 레이아웃 (apps/gui/ 서브 프로젝트 — 코어 additive 확장 최소화)

```
apps/gui/
  __init__.py
  app.py              # PySide6+pyqtgraph 뷰어 셸(napari 폐기, 스파이크 확정)
  backend.py          # pyqtgraph 단일 백엔드로 확정(추상화 계층은 향후 재도입 가능성 대비 최소 유지 또는 단순화 — 판단은 Phase 1 구현자에게 위임)
  io_panel.py         # 파일 선택 → common/io 로더 호출 (raw+JSON, C-04)
  module_panel.py     # 모듈 선택(default_registry) → ProcessModule.process 출력 산출(+ expected 동봉 fixture 시 run_harness 검증) (Phase 1, C-05..07 생산)
  pipeline_panel.py   # CANONICAL_ORDER 부분/전체 실행 → run_pipeline (Phase 2)
  layers.py           # 입력/출력/diff/마스크 레이어 구성 (C-04/C-06/C-07)
  probe.py            # float32 원값 호버 프로브 (C-03)
  history_panel.py    # XFrame history 체인 표시 (C-08, WHERE history 존재)
  metrics_panel.py    # metrics/ 엔진 호출 결과 플롯 + ROI (C-09/C-10)
  export.py           # 사용자 지정 디렉터리 내보내기 (C-20, Phase 2 #17 축소판)

common/
  io.py               # [신규 #16] raw 16-bit + 메타데이터 JSON → XFrame 로더 (additive)
  synth_calibset.py   # [승격 #18] 합성 CalibSet 팩토리 (tests/fixtures → 배포 코드, additive; common/ 단일 배치 — packages 목록 포함으로 배포 가능, REQ-VIEW-CORE-3)
modules/
  registry.py         # [신규/확장 #15] default_registry() (additive)

tests/apps/gui/
  test_tc_viewer_spike.py       # XDET-TC-030 (SG-1~3, 폴백)
  test_tc_viewer_core.py        # XDET-TC-031 (#15/#16/#18 + 계약 KEPT)
  test_tc_viewer_image.py       # XDET-TC-032 (C-01~04)
  test_tc_viewer_module.py      # XDET-TC-033 (C-05~08, run_harness)
  test_tc_viewer_metrics.py     # XDET-TC-034 (C-09/C-10)
  test_tc_viewer_pipeline.py    # XDET-TC-035 (Phase 2, C-16)
  test_tc_viewer_arch.py        # XDET-TC-036 (C-11~13, import 카나리)
  test_tc_viewer_headless.py    # XDET-TC-037 (C-14/15/18/19/20)
tests/architecture/
  test_import_contracts.py      # [확장] forbidden 계약 KEPT + apps.gui 역참조 금지 + 카나리
tests/fixtures/badgui/
  __init__.py, core_analog.py   # [카나리] 코어→apps.gui 위반을 심은 전용 픽스처(root_packages 밖); 임시 import-linter 설정을 대상으로 lint 실패(returncode≠0) assert — tests/fixtures/badlayers 음성대조 선례, 프로덕션 원본 트리 무변경
```

배치 원칙: GUI는 `apps/gui/`에 격리하고 코어 4계층을 단방향 소비한다. 코어에 추가되는 것은 **additive 3건**(#16 `common/io.py`, #15 `modules/registry.py`, #18 합성 CalibSet 팩토리 승격)뿐이며 기존 `process` 시그니처·`CANONICAL_ORDER`·기존 import-linter 계약을 변경하지 않는다(REQ-VIEW-CORE-4). 헤드리스 GUI 테스트는 `tests/apps/gui/` 전용이고, import 카나리 위반은 `tests/fixtures/badgui/`(root_packages 밖)에 심어 임시 import-linter 설정으로만 검출한다 — 프로덕션 원본 트리·실계약 무변경.

## 4. EARS 구조 설계 (확정본은 spec.md)

6개 요구 그룹. `[Ubiquitous]`/`[Event]`/`[State]`/`[Unwanted]`/`[Optional]`는 EARS 패턴 표기.

- **REQ-VIEW-SPIKE** (§2.3, XDET-TC-030) — SG-1~3 스파이크 리포트 산출(`[Event]`), 미충족 시 pyqtgraph 폴백 단일 순서(`[Unwanted]`), 스파이크 미완 동안 Phase 1 착수 금지(`[State]`).
- **REQ-VIEW-CORE** (§4, #15/#16/#18, XDET-TC-031) — raw+JSON 로더(`[Event]`), 모듈 레지스트리(`[Event]`), 합성 CalibSet 팩토리(`[Event]`), 코어 계약 불변(`[Unwanted]`).
- **REQ-VIEW-IMAGE** (C-01~04, XDET-TC-032) — W/L 조정/수치 입력(`[Event]`), 줌/팬 무복사(`[Event]`), 프로브 float32 원값(`[Event]`), 무손실 수신(`[Ubiquitous]`).
- **REQ-VIEW-COMPARE** (C-05~08, XDET-TC-033) — 전/후 연동(`[Event]`), 블링크(`[Event]`), diff 렌더(`[Event]`), diff 프로브(`[Event]`), 마스크 오버레이(`[Event]`), 픽셀 정렬(`[Ubiquitous]`), 이력 표시(`[Optional]` WHERE history 존재).
- **REQ-VIEW-RUN** (C-09/10/20, XDET-TC-034/035) — 모듈 `process` 실행 산출(`[Event]`), 파이프라인 실행(`[Event]`), 지표 엔진 위임 산출(`[Event]`), 지표 GUI 계산 금지(`[Ubiquitous]`), ROI 경계 표기(`[Event]`), ROI round-trip(`[State]`), 사용자 디렉터리 내보내기(`[Event]`), data/ 쓰기 거부(`[Unwanted]`).
- **REQ-VIEW-ARCH** (C-11~C-16·C-18·C-19, XDET-TC-036/037; C-17은 SPIKE-1/SG-3) — import 단방향(`[Ubiquitous]`), 카나리 위반 실패(`[Event]`), extras-less 코어 TC 통과(`[Event]`), GPL-only 라이선스 게이트 실패(`[Unwanted]`), 오프스크린 실행(`[Ubiquitous]`), 로직 레벨 커버리지(`[State]`), 결정론 bit-동일(`[State]`), 장시간 작업 스레드 밖+취소(`[Event]`), 다중 프레임 LRU 상한(`[Ubiquitous]`).

## 5. 검증 fixture 전략

| 대상 | 합성/구조 fixture | 검증 대상 |
|---|---|---|
| 스파이크(SG-1~3) | 3072×3072 float32 합성 프레임 | 호버 float32 원값 노출·W/L 응답·콜드 스타트 실측(리포트); `[T]` 임계 판정은 설정 |
| 폴백 결정 | SG 미충족 리포트 | pyqtgraph 폴백 전환(단일 경로) |
| 코어 갭 | raw 16-bit+JSON 임시 파일 / 모듈 목록 / 실측 CalibSet 부재 | 로더 XFrame 생성·레지스트리 집합 반환·합성 CalibSet 대체 |
| 계약 보존 | 기존 코어 계약·import-linter | additive 후 `process` 시그니처·CANONICAL_ORDER·계약 전건 KEPT |
| 영상 상호작용 | 합성 float32 프레임 + W/L·호버 이벤트 | W/L 수치 적용·프로브 저장값 일치·8-bit 렌더 경로 국한 |
| 비교·마스크·이력 | fixture → `process` 출력 XFrame(expected 동봉 시 `run_harness` 검증 병행) + MaskFlag 스택 + history 체인 | 입력/출력/diff/마스크 레이어 생성·이력 표시(WHERE) |
| 지표 위임 | 합성 팬텀 → metrics 엔진 | 플롯 값 = 엔진 출력 배열 일치(C-09)·ROI round-trip 재현(C-10) |
| 파이프라인 | raw+합성 CalibSet → run_pipeline 부분/전체 | 스테이지별 전/후 산출·동일 입력 결정론 bit-동일 |
| 아키텍처·설치 | import-linter 카나리·`[gui]`-less 설치·pip-licenses | forbidden 실효(카나리 실패)·코어 TC 통과·GPL-only 게이트 실패 |
| 헤드리스·자원 | offscreen 컨텍스트·data/ 불변·LRU | 로직 레벨 통과·data/ 해시 불변·LRU 상한 |

원칙: fixture·카나리·헤드리스 테스트는 `tests/`에 두고 `[T]` 수치를 하드코딩하지 않는다(설정 외부화). 픽셀 그랩 시각 단정은 Windows CI 제외(C-15).

## 6. 리스크 분석 (요약)

| 리스크 | 완화 | 우선순위 |
|---|---|---|
| 스파이크 미충족(napari 부적합) | SG-1~3 실측 후 pyqtgraph 폴백 단일 순서(REQ-VIEW-SPIKE-2); 두 스택 Qt+pytest-qt 공유로 피벗 저비용 | High |
| import-linter 헛통과(lesson #1) | forbidden 계약 + 의도적 위반 카나리로 실효 assert(REQ-VIEW-ARCH-2) | High |
| 코어 계약 오염(선행 갭이 표면 변경) | #15/#16/#18 additive only, 기존 계약·import-linter 전건 KEPT(REQ-VIEW-CORE-4) | High |
| 지표 GUI 재계산(C-09 위반) | 플롯 값 = metrics 엔진 출력 배열 일치 테스트 + 계산 위임(REQ-VIEW-RUN-3/4) | High |
| data/ 오염(C-20 위반) | data/ 쓰기 거부 + 내보내기 사용자 디렉터리 국한 + data/ 해시 불변 테스트(REQ-VIEW-RUN-7/8) | High |
| PyQt6/GPL 유입 | pip-licenses allowlist 게이트, PyQt6 명시 배제(REQ-VIEW-ARCH-4) | Medium |
| 헤드리스 CI 실패(디스플레이 서버) | offscreen + qtbot(napari 폐기, pyqtgraph 단일 경로), 픽셀 그랩 제외(REQ-VIEW-ARCH-5/6) | Medium |
| 자원 한도 초과(메모리·응답성) | LRU K프레임 상한 + 장시간 작업 스레드 밖·취소(REQ-VIEW-ARCH-8/9); `[T]` 설정 | Medium |
| Phase 2 범위 팽창(export 스키마) | #17 축소판 최소 내보내기 + npz+JSON 사이드카 스키마 확정(「결정 필요/확인 사항」 3) | Medium |
| magicgui 자동 폼 생성 기능 부재(napari 폐기 파생) | Phase 1에서 모듈 Params 입력 위젯을 PySide6로 직접 구성 필요 — 스파이크 리포트 "남은 리스크" 항목 3 | Medium |

## 7. 마일스톤 (Phase 순차 게이트, 시간 추정 없음)

- **[완료] Priority High — Phase 0 (스파이크)**: napari·pyqtgraph 양쪽으로 SG-1(호버 float32 원값)·SG-2(W/L 응답 `[T]`)·SG-3(콜드 스타트 `[T]`)를 Windows 헤드리스 CI 구성(`QT_QPA_PLATFORM=offscreen`)에서 실측 완료 → 스파이크 리포트 산출(`.moai/reports/SPEC-VIEWER-001-spike.md`). **결과: napari SG-3 하드 실패(OpenGL 컨텍스트 획득 불가) → pyqtgraph 폴백 확정**(단일 순서, REQ-VIEW-SPIKE-2). pyqtgraph 실측치: SG-1 호버 프로브 4/4 좌표 정확 일치, SG-2 W/L 응답 평균 0.074ms/최대 0.091ms(100ms 임계), SG-3 콜드 스타트 0.52s(10s 임계). **DoD 충족**: XDET-TC-030 — SG-1~3 실측 리포트 산출 완료 + 폴백 트리거 구조 성립(스택 확정: pyqtgraph). Phase 1의 선행 게이트 통과.
- **Priority High — Phase 0.5 (선행 코어 갭)**: #16 raw+JSON 로더(`common/io.py`) · #15 모듈 `default_registry` · #18 합성 CalibSet 팩토리 승격 — 전부 additive. **DoD**: XDET-TC-031 — 로더 XFrame 생성 + 레지스트리 집합 반환 + 합성 CalibSet 대체 + **기존 코어 계약·import-linter 계약 전건 KEPT**(SWR-000-6~12 불변).
- **Priority High — Phase 1 (단위 모듈 검증기)**: 파일 선택 → 모듈 1개 `ProcessModule.process` 실행으로 출력 XFrame 산출(expected 동봉 fixture 시 `run_harness` 검증 병행) → 입력/출력/diff/마스크/이력 시각화(C-01~08) + 지표 위임(C-09)·ROI round-trip(C-10). **DoD**: XDET-TC-032(영상 상호작용)·XDET-TC-033(모듈 검증기 레이어·이력)·XDET-TC-034(지표 위임·ROI) 로직 레벨 통과. **Phase 1 CI 통과·기준 충족이 Phase 2 착수의 선행 게이트.**
- **Priority Medium — Phase 2 (파이프라인 비교 뷰어)**: raw+CalibSet → `CANONICAL_ORDER` 부분/전체 `run_pipeline` → 스테이지별 전/후 + 지표 플롯(MTF/NPS/DQE) + 결정론(C-16). #17 축소판 내보내기(C-20). **DoD**: XDET-TC-035 — 스테이지별 전/후 산출 + 동일 입력 bit-동일 결정론 통과.
- **Priority High — 아키텍처·설치·헤드리스·자원 (전 Phase 병행)**: import-linter forbidden + 카나리(C-11) · `[gui]`-less 코어 잡(C-12) · pip-licenses 게이트(C-13) · offscreen 헤드리스(C-14/15) · 자원 LRU·응답성(C-18/19) · data/ 읽기전용(C-20). **DoD**: XDET-TC-036(import 카나리·extras·라이선스)·XDET-TC-037(헤드리스·자원·읽기전용) 통과.
- 순서 원칙: **Phase 0 → 0.5 → 1 → 2 순차 게이트.** Phase 0(스파이크)로 스택 확정 후 Phase 0.5(코어 갭) 착수. Phase 1은 Phase 0.5 완료 후. Phase 2는 Phase 1 CI 통과 후. 아키텍처·설치·헤드리스·자원(REQ-VIEW-ARCH)은 전 Phase에 걸쳐 병행하되 Phase 0.5부터 CI 잡으로 상시 게이트.

## 8. CI 잡 추가 (GUI_CRITERIA C-12/C-13/C-14 게이트)

구현 대상(F2 확정): 저장소에 `.github/`가 아직 없으므로 CI 잡은 **GitHub Actions 워크플로 신설**(`.github/workflows/gui.yml`, Phase 0.5에서 도입)로 구현하고, 로컬 재현은 기존 `scripts/test.ps1`/`test.sh` 확장으로 동일 명령을 실행한다. 이 저장소는 uv 전용 환경(`python` PATH 부재 — lessons #4)이므로 아래 모든 명령은 `uv run` 접두를 사용한다.

- **core-no-gui**: base 패키지를 `[gui]` extras 없이 설치하고 `uv run pytest --ignore=tests/apps`로 전체 코어 TC(XDET-TC-000~021 포함)만 수집·실행 → 통과. `pyproject` `testpaths=["tests"]` 기본 수집은 `tests/apps/gui/`까지 포함하므로, 배제 메커니즘을 `--ignore=tests/apps`로 고정하고(1차) 각 GUI 테스트 모듈 상단 `pytest.importorskip("qtpy")` 가드로 Qt 부재 시 수집 단계 ImportError를 방지한다(2차)(C-12 extras 격리 증명, D10; napari 폐기로 해당 가드는 불필요).
- **gui-offscreen**: `uv pip install .[gui]` + `QT_QPA_PLATFORM=offscreen` + `uv run pytest tests/apps/gui` 실행(pyqtgraph 단일 경로, qtbot 기반 — napari 폐기); 픽셀 그랩 시각 단정 제외(C-14/C-15). Linux xvfb 픽셀 그랩 잡은 본 SPEC 범위에 두지 않음(후속 별건 가능, 「결정 필요/확인 사항」 6).
- **license-gate**: `uv run pip-licenses` allowlist로 GPL-only 의존성 0 확인, PyQt6 명시 배제 → 위반 시 실패(C-13).
- **import-linter(확장)**: 기존 코어 계층 방향 계약 전건 유지(KEPT) + 신규 forbidden(코어 4계층 → `apps.gui` 금지) + 의도적 위반 카나리(린터 실효 assert, C-11/lesson #1). 카나리는 `tests/fixtures/badgui/`(root_packages 밖)에 코어→`apps.gui` 방향 위반을 심고, 그 패키지를 대상으로 하는 임시 import-linter 설정을 `uv run lint-imports --config <tmp>`(콘솔 스크립트 직접 호출 — `python -m importlinter.cli` 헛통과 금지, lessons #1)로 실행해 `returncode≠0`를 assert한다 — 프로덕션 원본 트리 무변경(`tests/fixtures/badlayers/`·`tests/test_tc000.py test_tc000_B` 선례).
- 원칙: core-no-gui는 GUI 도입이 순수 라이브러리 설치를 깨지 않음을 상시 증명한다. GUI 잡 실패가 코어 잡을 막지 않도록 잡을 분리한다.
