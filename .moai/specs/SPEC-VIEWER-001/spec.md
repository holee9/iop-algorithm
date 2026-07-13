---
id: SPEC-VIEWER-001
title: "검증 GUI — 단위 모듈 검증기 + 파이프라인 비교 뷰어"
version: 0.2.0
status: implemented
created: 2026-07-10
updated: 2026-07-10
author: drake.lee
priority: high
issue_number: 14
labels: [gui, viewer, verification-tool]
---

# SPEC-VIEWER-001 — 검증 GUI: 단위 모듈 검증기 + 파이프라인 비교 뷰어 (단계형 Phase 0 → 0.5 → 1 → 2)

> **현재 위치:** 이 SPEC은 2026-07-10 구현된 `apps/gui/` Python 검증 도구의 정본 기록이다. 2026-07-13 이후 목적별 GUI 신규 구현의 기준선 후보는 `SPEC-XGUI-MASTER` v0.5.1이며 대상은 `apps/xdet-console/` WPF다. 본 도구는 동작·회귀 선례로 보존되지만 WPF의 실행 경계로 import하거나 확장하지 않는다. v0.5.1 사용자 승인·동결 전 신규 구현은 금지된다.

XDET 영상처리 SW P1(11개 SPEC, T0~T10, `common/ modules/ pipeline/ metrics/` 4계층 순수 라이브러리)의 **검증용 GUI**를 `apps/gui/` 서브 프로젝트로 도입한다. raw 파일을 열어 보정 전/후 결과를 눈으로 확인·비교하는 재현 가능한 사용자 진입점이 현재 pytest뿐이라는 문제(이슈 #14)를 해결한다. 본 SPEC은 두 능력을 하나의 앱(탭/도크 전환)·하나의 SPEC에서 **단계형**으로 제공한다 — **Phase 1** 단위 모듈 검증기(fixture/raw 입력 → 모듈 1개 실행 → 입력·출력·diff·마스크 시각화, 출력 XFrame은 `common/contract.py`의 `ProcessModule.process`가 직접 산출하고 expected 골든이 동봉된 fixture에서만 `run_harness` 검증을 병행), **Phase 2** 파이프라인 비교 뷰어(raw+CalibSet → `CANONICAL_ORDER` 부분/전체 실행 → 스테이지별 전/후 + 지표 플롯). GUI는 **읽기-실행 전용**(C-20)이며 **지표를 자체 계산하지 않고**(C-09) 기존 `metrics/` 엔진 결과만 표시한다.

**본 SPEC은 골든 모델 처리 모듈이 아니라 검증 도구다.** SWR ID에 대응하는 파이프라인 스테이지를 신설하지 않으며, `common/modules/pipeline/metrics`를 **단방향으로 import만 하는 소비자**로서 코어 4계층의 아키텍처 계약(SWR-000-6~12)과 오케스트레이터 표면(`CANONICAL_ORDER`)을 변경하지 않는다. 코어는 `apps.gui`를 역참조하지 않으며(C-11, import-linter forbidden 계약 + 의도적 위반 카나리 테스트), GUI 전용 의존성은 `[project.optional-dependencies] gui`로 격리된다(C-12). 요구는 SWR가 아니라 **`docs/GUI_CRITERIA.md`의 품질 기준 카탈로그 C-01~C-20 및 스파이크 게이트 SG-1~SG-3**를 단일 출처로 인용하며, `[T]` 임계 수치는 Params/설정에 외부화한다(측정=판정 분리).

- 근거: `docs/GUI_CRITERIA.md`(품질 기준 C-01~C-20 · 스택 결정 §2 · 스파이크 게이트 SG-1~SG-3 · 선행 코드 개선 §4 · SPEC 작성 준수사항 §5) · `docs/GUI_REVIEW.md`(§4.5 `apps/gui/` 서브 프로젝트 확정 · `[gui]` optional extras · import-linter forbidden 계약)
- 스택 결정(GUI_CRITERIA §2): **1순위 napari**(임베디드) + magicgui 도크 + Qt 바인딩 **PySide6**(LGPL); **폴백 pyqtgraph**(PySide6 위); **PyQt6 배제**(GPL/상용). napari→pyqtgraph는 스파이크 결과에 따른 **단일 순서 결정**이다(§2.3).
- 선행 코드 개선 의존(GUI_CRITERIA §4): #16(raw+JSON 로더), #15(모듈 `default_registry`), #18(합성 CalibSet 팩토리 배포 승격)은 Phase 1의 load-bearing 선행 갭 — 본 SPEC의 **Phase 0.5 작업 패키지**로 포함하되 코어 계약·전 import-linter 계약을 불변 유지한다. #17(XFrame 직렬화/이력 JSON 내보내기)은 Phase 2 축소판 load-bearing. #19(인체공학: 재수출/`REQUIRED_PARAMS`/Params 검증/반환형 통일)는 GUI 도입을 막지 않는 코어 인체공학 별건으로 본 SPEC 범위 밖(Exclusions 참조).
- 완료 정의(DoD): 4단계를 순차 게이트로 성립 — **Phase 0** 스파이크(SG-1~SG-3 실측, 미충족 시 폴백 확정, XDET-TC-030) → **Phase 0.5** 선행 코어 갭(#15/#16/#18) + 계약 보존(XDET-TC-031) → **Phase 1** 단위 모듈 검증기(입력/출력/diff/마스크/이력·지표 위임·ROI, XDET-TC-032~034) → **Phase 2** 파이프라인 비교 뷰어(스테이지별 전/후·결정론, XDET-TC-035) → 아키텍처·설치·헤드리스·자원(XDET-TC-036~037). 자원 `[T]` 임계·픽셀 그랩 시각 단정은 P1 구조 성립 + 설정 외부화(하드 수치 단정 아님).
- 선행/소비 계약: [SPEC-INFRA-001](../SPEC-INFRA-001/spec.md) — `common/contract.py`(`ProcessModule`·`run_harness`·`Params`)·`common/xframe.py`(XFrame 불변·`MaskFlag` 4종·history 체인)·`pipeline/orchestrator.py`(`CANONICAL_ORDER`·`run_pipeline`·`_calibration_gate`)·`common/calibset.py`(CalibSet)를 **단방향 소비**(변경 없음). 기존 import-linter 계약(코어 계층 방향)은 전건 유지(KEPT).
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.2.0 (2026-07-10)** — **구현 완료(status: implemented).** Phase 0(스파이크, pyqtgraph 확정) → 0.5(선행 코어 갭 #15/#16/#18 additive, `common/io.py`·`modules/registry.py`·`common/synth_calibset.py`) → 1(단위 모듈 검증기, `apps/gui/{config,layers,probe,history_panel,io_panel,module_panel,metrics_panel}.py`) → 2(파이프라인 비교 뷰어 + 내보내기, `apps/gui/{pipeline_panel,export}.py`) 순차 게이트 전건 통과. 아키텍처 게이트: import-linter `apps.gui` forbidden 계약 신설 + `tests/fixtures/badgui/` 카나리(REQ-VIEW-ARCH-1/2), pip-licenses 게이트(PySide6 LGPL 선택 vs GPL-only 구분 판정기, REQ-VIEW-ARCH-4), `.github/workflows/gui.yml` 4개 독립 CI 잡(core-no-gui/gui-offscreen/license-gate/import-linter). REQ-VIEW-ARCH-8(장시간 작업 스레드 밖 실행 + 진행/취소)은 `apps/gui/worker.py`(`CallableWorker`)로 구현 — 코어에 취소 훅을 추가하지 않고(REQ-VIEW-CORE-4 준수) 완료 시 결과 폐기 방식의 최선노력 취소. `apps/gui/app.py`의 `MainWindow`가 모든 조각을 실제 동작하는 앱(Module Verifier + Pipeline Viewer 탭)으로 배선하고, `tests/apps/gui/test_tc_viewer_headless.py`가 `qtbot` 마우스 클릭으로 이 앱을 헤드리스 구동하는 e2e 스모크(XDET-TC-037)를 제공 — 개별 함수 단위 테스트를 넘어선 실제 구동 검증. XDET-TC-030~037 전 블록 등록, Gen 1(000~021) 문자열 미포함 확인(D9). 헤드리스 GUI 스위트 68/68, core-no-gui 465/465, 전체 회귀 533/533, 로컬 CI 4잡 재현(`scripts/test.sh`) 전건 통과. 상세 DoD 체크리스트는 acceptance.md 참조.
- **v0.1.5 (2026-07-10)** — Phase 0 스파이크 실측 완료(`.moai/reports/SPEC-VIEWER-001-spike.md`) 반영 — 이는 재설계가 아니라 REQ-VIEW-SPIKE-2가 이미 예견한 폴백 시나리오의 사후 문서 반영이다. **확정 스택: pyqtgraph(PySide6 위).** napari는 Windows 헤드리스 CI 구성(`QT_QPA_PLATFORM=offscreen`)에서 `napari.Viewer()` 생성 자체가 OpenGL 컨텍스트 획득 실패(vispy `get_max_texture_sizes()` GLError, `QT_OPENGL=software` 강제 전환도 실패)로 SG-3 하드 실패, SG-1/SG-2는 애초에 측정 불가였음을 확인. pyqtgraph는 동일 헤드리스 조건에서 SG-1(호버 float32 원값 4/4 좌표 일치)·SG-2(W/L 응답 최대 0.09ms)·SG-3(콜드 스타트 0.52s) 전부 PASS. REQ-VIEW-SPIKE-2(단일 순서 결정)에 따라 pyqtgraph로 즉시 확정. `[project.optional-dependencies] gui`는 `pyqtgraph>=0.14`·`pyside6>=6.10`·`qtpy>=2.4`·`pytest-qt>=4.4`로 확정(napari/magicgui/vispy 등 전이 의존성 제거, pyproject.toml에 이미 반영 완료). 「확정 사항」 1, Environment/Assumptions 스택·헤드리스 CI 서술, REQ-VIEW-ARCH-6 괄호 HOW(napari `make_napari_viewer` → qtbot 단일 경로)를 정정. EARS 구조·REQ ID·Exclusions는 변경 없음(HOW 레벨 서술 정정만).
- **v0.1.4 (2026-07-10)** — 「결정 필요/확인 사항」 1~6 사용자 확정(딥리서치·저장소 관례 조사 근거)으로 전부 접힘 → 해당 절을 「확정 사항」으로 재작성. **1**: 스택 napari 1순위/pyqtgraph 폴백 유지 + 스택 버전 재확인(2026-07: napari 0.7.1, pyqtgraph 0.14.0) + SG-2/SG-3을 포함한 전 `[T]` 임계 등재 위치를 GUI 전용 설정 모듈 `apps/gui/config.py`로 확정(`modules/window.py`의 `P_*`+`_require` 관례 승계 — 코어 `Params` 아님·`pyproject` tool 섹션 아님). **2·4·5**: 기존 기본값(Phase 0.5 additive·`common/synth_calibset.py` 단일 배치 / `badgui` 픽스처 카나리 / XDET-TC-030~037) 그대로 확정. **3**: #17 Phase 2 축소판 내보내기 스키마 확정 — npz(pixel float32, masks uint8, validation_mode 시 pixel_f64) + JSON 사이드카(noise·validation_mode·history[HistoryEntry 5필드]·array_keys), `CalibSet.save/load` npz+JSON 사이드카 선례 준수, 내보내기 유틸 `apps/gui` 소재. **6**: 자원 `[T]` 설정 외부화 유지 + **Linux xvfb 픽셀 그랩 잡은 본 SPEC 범위에 두지 않음(후속 별건 가능)**으로 확정. **D-M1**: 디스플레이 픽셀 히스토그램을 W/L 렌더 경로 UI(C-01 계열)로 재분류 — 위임 지표(C-09) 목록에서 제외(napari/pyqtgraph HistogramLUTItem/ImageJ/ITK-SNAP/3D Slicer/VGSTUDIO MAX/ISee! 전 뷰어가 픽셀 히스토그램을 표시·대비 UI로 취급, ImageJ는 B/C 히스토그램(렌더)과 Analyze>Histogram(분석)을 명시 분리; `metrics/`에 히스토그램 엔진 부재 확인). **용어 분리(D-m1)**: ROI round-trip 문맥의 "하네스"를 "지표 재계산 경로(metrics 엔진 재호출)"로 분리(run_harness 계약 검증과 구분). **문서 위생**: spec/plan frontmatter `title` 동기화, GUI_REVIEW §4/§5 확정 주석, plan §3 `common/` 블록 병합.
- **v0.1.3 (2026-07-10)** — 최종 교차검토(evaluator-active, READY-WITH-NOTES, `.moai/reports/SPEC-VIEWER-001-final-crosscheck.md`) F1~F5 반영. **F2**: CI 잡 구현 대상을 GitHub Actions 워크플로 신설(`.github/workflows/gui.yml`) + `scripts/` 확장으로 확정. **F3**: plan §8 명령 예시에 uv 전용 환경 규약(`uv run` 접두) 반영. **F4**: 스파이크 리포트 산출 경로/필수 필드 확정(`.moai/reports/SPEC-VIEWER-001-spike.md`). **F5**: acceptance 분류표에 SPIKE-1 리포트 산출·SG-1 프로브 로직(자동 검출) 귀속 + C-01/C-17 스파이크 실측 처리 대칭화. **F1**은 `docs/GUI_REVIEW.md` addendum으로 별도 반영.
- **v0.1.2 (2026-07-10)** — plan-audit iter2 **PASS 0.94** 확정 후 잔여 minor 2건 반영. **N1**: plan.md §5 fixture 전략 표·§7 Phase 1 마일스톤의 pre-D1 구본 문구("모듈 1개 `run_harness` 실행"/"run_harness 출력")를 v0.1.1 실행 모델(`process` 유일 산출 + fixture 모드 `run_harness` 검증 병행)로 정정. **N2**: IMAGE-2 무복사 판정을 acceptance 분류표의 코드리뷰 설계 규칙(프로파일러 확인 + 리뷰)으로 귀속.
- **v0.1.1 (2026-07-10)** — plan-audit iter1(FAIL 0.72) 결함 D1~D10 반영(코드 사실 재검증: `common/contract.py` L131~152, `tests/fixtures/badlayers/`, `pyproject.toml` `packages`/`testpaths`).
  - **D1 (major)**: RUN-1 실행 경로를 코드 현실과 정합화 — 출력 XFrame은 `ProcessModule.process`가 산출(raw·fixture 공통 유일 경로), `run_harness(...,expected)->MismatchReport`는 expected 골든이 동봉된 fixture-verification 모드에서만 통과/위반 검증으로 병행(하네스는 출력 프레임 미반환). spec L15/L48/RUN-1, acceptance Scenario 4·5·DoD, plan §1·§3 파급 반영.
  - **D2 (major)**: #18 합성 CalibSet 팩토리 배치를 `common/synth_calibset.py` 단일 확정(apps/gui 분기 제거 — `packages` 목록상 배포 불가). plan §3·결정 필요 2 정합.
  - **D3**: import 카나리를 `tests/fixtures/badgui/` 전용 픽스처 패키지(`root_packages` 밖) + 임시 import-linter 설정으로 확정(`tests/fixtures/badlayers/`·`test_tc000_B` 음성대조 선례). "프로덕션 트리 밖 심기" 자기모순 해소.
  - **D4**: RUN-4 Unwanted→Ubiquitous(정상 조건 금지 불변식), COMPARE-7 Optional의 THEN 키워드 제거.
  - **D5**: SPIKE-3(마일스톤 게이트 리뷰)·CORE-4(자동 검출, Scenario 2(d))를 acceptance 자동/리뷰 분류표에 귀속.
  - **D6**: CORE-4/RUN-2/ARCH-5 규범 본문의 구현 식별자(`process(...)`·`CANONICAL_ORDER`·`QT_QPA_PLATFORM`)를 괄호로 이동.
  - **D7**: ARCH 그룹 헤더 C-11~C-19 → C-11~C-16·C-18·C-19(C-17은 SPIKE-1/SG-3 소관).
  - **D8**: #19 인체공학을 Exclusions로 확정(GUI 비차단 별건, 범위 밖).
  - **D9**: GUI 테스트 소스는 Gen 1 TC id(000~021) 문자열 미포함 제약 추가(캡스톤 스캔 오등록 방지).
  - **D10**: core-no-gui 잡에 `--ignore=tests/apps` + GUI 모듈 `pytest.importorskip` 수집 배제 메커니즘 명시(`testpaths=["tests"]` 전역 수집의 ImportError 방지).
- **v0.1.0 (2026-07-10)** — 초안 생성. GitHub 이슈 #14. `apps/gui/` 검증 GUI(옵션 C 단계형: 단위 모듈 검증기 + 파이프라인 비교 뷰어). 6개 요구 그룹(SPIKE/CORE/IMAGE/COMPARE/RUN/ARCH) EARS 구조 확정. 핵심 범위 결정:
  1. **단계형 단일 SPEC — Phase 0(스파이크) → 0.5(선행 코어 갭) → 1(모듈 검증기) → 2(파이프라인 뷰어)**: GUI_CRITERIA §1 옵션 C를 마일스톤으로 구분. Phase 1이 CI 통과·기준 충족으로 완료된 뒤에만 Phase 2 착수. 「결정 필요/확인 사항」 2.
  2. **스택 = napari 1순위 + PySide6, 폴백 pyqtgraph, PyQt6 배제(GPL)**: GUI_CRITERIA §2 딥리서치 확정. 스파이크(SG-1~SG-3)로 실측 후 미충족 시 pyqtgraph 폴백 — **단일 순서 결정**(택일·"또는" 없음). 「결정 필요/확인 사항」 1.
  3. **선행 코어 갭 #15/#16/#18 = 본 SPEC Phase 0.5 작업 패키지, additive only**: raw+JSON 로더·모듈 레지스트리·합성 CalibSet 팩토리는 Phase 1 load-bearing. 코어 계약(SWR-000-6~12)·전 import-linter 계약을 변경하지 않는 additive 확장으로 구현. 「결정 필요/확인 사항」 2.
  4. **읽기-실행 전용(C-20) + 지표 자체 계산 0(C-09)**: GUI는 `data/` 골든 fixture·CalibSet을 절대 쓰지 않고 내보내기는 사용자 지정 디렉터리로만. 지표 플롯은 기존 `metrics/` 엔진 호출 결과만 사용. 「결정 필요/확인 사항」 3.
  5. **import 격리 = forbidden 계약 + 의도적 위반 카나리**: 코어 4계층 → `apps.gui` 역참조 금지를 import-linter로 강제하되, lesson #1(import-linter 헛통과)을 반영해 위반을 심으면 lint가 실제로 실패함을 assert하는 카나리 테스트를 동반. 「결정 필요/확인 사항」 4.
  6. **TC 번호 = 신규 블록 XDET-TC-030+**: Gen 1 대상 XDET-TC-000~021은 P1 골든 모델 형상 동결 완료(캡스톤 스캔 `range(0,22)`, `tests/test_tc_skeletons.py`). GUI는 `apps/gui/` 별도 검증 능력이므로 030+ 블록으로 Gen 1 범위와 충돌·간섭을 회피한다. 「결정 필요/확인 사항」 5.

## Environment / Assumptions

- Python 3.11+, numpy/scipy 기반 float 골든 모델(tech.md, CLAUDE.md). 검증 GUI도 정확성·재현성이 목적이며 성능/배포 목적이 아니다(속도 최적화 금지 승계).
- **배치: `apps/gui/` 서브 프로젝트**(GUI_REVIEW §4.5 확정). GUI 전용 의존성은 루트 `pyproject.toml` `[project.optional-dependencies] gui`로 격리하며 `uv pip install .[gui]`로 설치한다. base 패키지는 Qt/napari 없이 설치되고 전체 코어 TC를 통과한다(C-12).
- **스택**: **확정: pyqtgraph(PySide6 위)** — `ImageView` 히스토그램 기반 W/L·LUT·ROI, Qt 바인딩 PySide6(LGPL). napari는 Phase 0 스파이크 실패(Windows 헤드리스 CI에서 OpenGL 컨텍스트 획득 불가, SG-3)로 폐기(`.moai/reports/SPEC-VIEWER-001-spike.md`). **PyQt6 배제**(GPL/상용, C-13/§2.2). napari→pyqtgraph 전환은 REQ-VIEW-SPIKE-2 단일 순서 결정에 따른 실측 확정 결과다(§2.3, 「확정 사항」 1).
- **무손실 수신(C-04)**: 뷰어는 파이프라인의 float32 배열을 무변형 수신하고 8-bit 매핑은 렌더 경로에서만 발생한다. 호버 프로브는 저장된 float32 원값을 노출한다(C-03; 8-bit 표시값 아님).
- **읽기-실행 전용(C-20)**: GUI는 `data/` 골든 fixture·CalibSet 파일을 절대 쓰지 않는다. 내보내기는 사용자 지정 출력 디렉터리로만.
- **단방향 소비(C-11)**: `apps/gui`는 `common`·`modules`·`pipeline`·`metrics`를 import만 하고, 코어 4계층은 `apps.gui`를 import하지 않는다. import-linter forbidden 계약으로 CI에서 강제하며, 의도적 위반 카나리 테스트로 계약의 실효성(헛통과 아님)을 증명한다(lesson #1).
- **선행 코어 갭(Phase 0.5, GUI_CRITERIA §4)**: #16 raw+JSON 프레임 로더, #15 모듈 `default_registry`, #18 합성 CalibSet 팩토리(배포 코드 승격)는 Phase 1의 load-bearing 전제. 전부 **additive** 구현으로 기존 아키텍처 계약(SWR-000-6~12: `process(XFrame,CalibSet,Params)->XFrame` 단일 시그니처, 순수함수형, 모듈 간 직접 호출 금지, CalibSet 공통 스키마 등)과 **기존 import-linter 계약을 불변 유지**(KEPT)한다. 실측 CalibSet 부재 시 합성 팩토리가 대체한다(T1~T10 테스트가 이미 사용하는 패턴).
- **헤드리스 CI(C-14/C-15)**: 모든 GUI CI 테스트는 `QT_QPA_PLATFORM=offscreen`(pytest-qt)로 실행하며 Windows 러너에 xvfb를 요구하지 않는다. 로직 레벨 검증은 qtbot(pytest-qt) 기반 — 스파이크 결과 napari 폐기(napari는 동일 헤드리스 구성에서 뷰어 생성 자체가 실패하여 로직 레벨 검증 대상에서 제외, `.moai/reports/SPEC-VIEWER-001-spike.md`). 픽셀 그랩/스크린샷 시각 단정은 Windows CI에서 제외한다(C-15; Linux xvfb 픽셀 그랩 잡은 본 SPEC 범위에 두지 않음 — 후속 별건 가능).
- **파라미터·수치 정책(HARD)**: 전 `[T]` 임계는 GUI 코드에 하드코딩되지 않고 **GUI 전용 설정 모듈 `apps/gui/config.py`**에 외부화된다(코어 `P_*` 명명 상수 + `_require` 검증 관례 승계 — `modules/window.py` 선례; 코어 `Params`는 프레임 처리 계약이고 GUI 런타임 예산은 의미가 다르므로 `Params`에 넣지 않으며, `pyproject` tool 섹션은 도구 설정 전용이므로 배제) — W/L 갱신 응답 100ms(C-01·SG-2), 콜드 스타트 10s(C-17·SG-3), RSS 상한 2GB·LRU K프레임(C-18), 이벤트 루프 블로킹 200ms(C-19), diff 기본 범위 ±max|diff|(C-06). P1은 구조를 성립시키고 `[T]` 수치 단정은 스파이크(SG-3)·구조 게이트·설정으로 처리한다.
- **TC 번호 블록**: GUI TC는 **XDET-TC-030~037**을 사용한다. Gen 1 대상 XDET-TC-000~021은 P1 골든 모델 형상 동결 완료 범위(`tests/test_tc_skeletons.py` `_GEN1_TC_RANGE = range(0,22)`)이며, GUI는 그 범위 밖의 별도 검증 도구 능력이므로 030+ 블록으로 캡스톤 스캔과의 충돌을 회피한다(「결정 필요/확인 사항」 5). 캡스톤 스캔은 `tests/` 전체를 `rglob("*.py")`하므로 신규 `tests/apps/gui/` 소스도 corpus에 포함된다 — 따라서 GUI 테스트 소스는 Gen 1 TC id 문자열(`000`~`021`)을 포함하지 않아, 삭제된 Gen 1 테스트를 '살아있음'으로 오등록하지 않는다(캡스톤 무간섭의 성립 조건, D9).
- **소비 대상 계약(변경 없음)**: `common/contract.py`(`ProcessModule.process(XFrame,CalibSet,Params)->XFrame` = 출력 XFrame 생산자 · `run_harness(module,input,calib,params,expected)->MismatchReport` = expected 필수·출력 프레임 미반환의 fixture 검증 전용 · `Params`), `common/xframe.py`(XFrame 불변·`MaskFlag`={DEFECT,SATURATION,INTERPOLATION,SATURATION_BAND}·`HistoryEntry`={module_name,module_version,params_hash,calibset_id}), `pipeline/orchestrator.py`(`CANONICAL_ORDER`·`run_pipeline`·`_calibration_gate`), `common/calibset.py`(CalibSet).

## Requirements (EARS)

### REQ-VIEW-SPIKE — Phase 0 스파이크: SG-1~SG-3 실측 · 결정론적 폴백 · 게이트 순서 (GUI_CRITERIA §2.3, XDET-TC-030)

- **REQ-VIEW-SPIKE-1 (Event-Driven)** — WHEN Phase 0 스파이크가 실행되면, THEN 시스템은 napari 후보에 대해 SG-1(호버 픽셀 프로브가 저장된 float32 원값을 노출하는지)·SG-2(3072×3072 float32 W/L 조작 응답)·SG-3(콜드 스타트→상호작용 가능 시간)을 실측한 스파이크 리포트를 산출해야 한다(SG-1~SG-3; 응답·시간 임계는 `[T]`로 외부화, 하드코딩 금지).
- **REQ-VIEW-SPIKE-2 (Unwanted)** — IF 스파이크 리포트에서 SG-1·SG-2·SG-3 중 하나라도 미충족이면, THEN 시스템은 구현 스택을 pyqtgraph 폴백으로 전환해야 한다(napari 1순위 → pyqtgraph 폴백의 단일 순서 결정 — 비결정적 택일·"또는" 없음; GUI_CRITERIA §2.3).
- **REQ-VIEW-SPIKE-3 (State-Driven)** — WHILE Phase 0 스파이크가 미완인 동안, 시스템은 Phase 1 구현 착수를 진행하지 않아야 한다(스파이크 통과 또는 폴백 확정이 Phase 1의 선행 게이트 — GUI_CRITERIA §2.3 "구현 착수 전 1일 검증").

### REQ-VIEW-CORE — Phase 0.5 선행 코어 갭 · additive 계약 보존 (GUI_CRITERIA §4, 이슈 #15/#16/#18, XDET-TC-031)

- **REQ-VIEW-CORE-1 (Event-Driven)** — WHEN raw 16-bit 프레임과 메타데이터 JSON 경로가 주어지면, THEN 프레임 로더가 float32 XFrame을 생성해야 한다(#16 load-bearing, C-04 무손실; raw+메타데이터 JSON 기존 데이터 규약 재사용).
- **REQ-VIEW-CORE-2 (Event-Driven)** — WHEN 모듈 선택 UI가 사용 가능한 처리 모듈을 질의하면, THEN 모듈 레지스트리가 기본 등록 모듈 집합을 반환해야 한다(#15 load-bearing, Phase 1 모듈 선택 UI의 생산자).
- **REQ-VIEW-CORE-3 (Event-Driven)** — WHEN 실측 CalibSet이 부재한 상태로 raw 입력 경로가 실행되면, THEN 배포 가능한 합성 CalibSet 팩토리가 대체 CalibSet을 제공해야 한다(#18 load-bearing, 합성 팬텀 fixture 패턴 승계).
- **REQ-VIEW-CORE-4 (Unwanted)** — IF 선행 코어 갭(#15/#16/#18) 구현이 기존 코어 처리 계약·오케스트레이터 실행 순서·기존 import-linter 계약을 변경하려 하면, THEN 그 변경을 금지하고 코어 계약을 불변 유지해야 한다(SWR-000-6~12: `process(XFrame,CalibSet,Params)->XFrame`·`CANONICAL_ORDER`·import-linter 계약 불변, additive only — 검증 도구를 위한 코어 표면 변경 금지).

### REQ-VIEW-IMAGE — Phase 1 영상 상호작용: W/L · 줌/팬 · 프로브 · 무손실 표시 (GUI_CRITERIA C-01~C-04, XDET-TC-032)

- **REQ-VIEW-IMAGE-1 (Event-Driven)** — WHEN 사용자가 contrast limits(W/L)를 조정하거나 정확한 수치를 직접 입력하면, THEN 뷰어가 float32 전체 범위에 대해 표시를 갱신해야 한다(C-01; 조정당 표시 갱신 응답 `[T]` 100ms, SG-2).
- **REQ-VIEW-IMAGE-2 (Event-Driven)** — WHEN 사용자가 드래그 팬 또는 휠 줌을 하면, THEN 뷰어가 이벤트당 전체 프레임 재계산·배열 복사 없이 연속 상호작용을 제공해야 한다(C-02, GPU/픽스맵 경로).
- **REQ-VIEW-IMAGE-3 (Event-Driven)** — WHEN 포인터가 픽셀 위를 호버하면, THEN 뷰어가 정수 픽셀 좌표와 모든 가시 레이어의 저장된 float32 원값을 표시해야 한다(C-03; 표시용 8-bit 값 아님).
- **REQ-VIEW-IMAGE-4 (Ubiquitous)** — 뷰어는 파이프라인의 float32 배열을 무변형 수신하고 8-bit 매핑을 렌더 경로에서만 수행해야 한다(C-04 무손실 표시 원칙).

### REQ-VIEW-COMPARE — Phase 1/2 비교·마스크·이력: 전/후 · diff · 마스크 오버레이 · 처리 이력 (GUI_CRITERIA C-05~C-08, XDET-TC-033)

- **REQ-VIEW-COMPARE-1 (Event-Driven)** — WHEN 전/후 프레임 쌍이 표시되면, THEN 뷰어가 줌·팬·W/L이 연동된 나란히 보기를 제공해야 한다(C-05).
- **REQ-VIEW-COMPARE-2 (Event-Driven)** — WHEN 사용자가 블링크 토글 키를 누르면, THEN 뷰어가 단일 키로 레이어 가시성을 토글해야 한다(C-05 블링크 모드).
- **REQ-VIEW-COMPARE-3 (Event-Driven)** — WHEN 모듈 또는 파이프라인의 출력·입력(after/before) 쌍이 산출되면(REQ-VIEW-RUN-1·REQ-VIEW-RUN-2 산출), THEN 뷰어가 부호 있는 차(after−before)를 0 중심 대칭 diverging 컬러맵으로 렌더해야 한다(C-06; 기본 범위 `[T]` ±max|diff|, 사용자 조정 가능).
- **REQ-VIEW-COMPARE-4 (Event-Driven)** — WHEN 포인터가 diff 위를 호버하면, THEN 뷰어가 부호 있는 float 차값을 표시해야 한다(C-06).
- **REQ-VIEW-COMPARE-5 (Event-Driven)** — WHEN XFrame 마스크 스택이 표시되면, THEN 뷰어가 각 플래그(DEFECT/SATURATION/INTERPOLATION/SATURATION_BAND)를 고유 색·불투명도 슬라이더·가시성 토글의 독립 오버레이로 렌더해야 한다(C-07, `MaskFlag` 4종).
- **REQ-VIEW-COMPARE-6 (Ubiquitous)** — 마스크 오버레이는 모든 줌 레벨에서 기저 픽셀과 정렬되어야 한다(C-07 픽셀 정렬).
- **REQ-VIEW-COMPARE-7 (Optional)** — WHERE 로드된 XFrame이 처리 이력(history) 체인을 가지면, 뷰어가 그 체인(module_name/version/params_hash/calibset_id)을 표시해야 한다(C-08, 오케스트레이터 경로 검증 수단; history 부재 시 미표시).

### REQ-VIEW-RUN — Phase 1/2 실행·지표 위임·ROI·읽기전용 (GUI_CRITERIA C-09/C-10/C-20, XDET-TC-034/035)

- **REQ-VIEW-RUN-1 (Event-Driven)** — WHEN 사용자가 fixture 또는 raw 입력과 처리 모듈 1개를 선택하면, THEN 시스템이 그 모듈을 처리 계약 표면으로 직접 실행해 출력 XFrame을 산출하고 입력·출력 XFrame 쌍을 시각화에 제공해야 한다(Phase 1, `ProcessModule.process(XFrame,CalibSet,Params)->XFrame`; raw·fixture 두 입력 모두 `process` 직접 실행이 유일한 출력 산출 경로 — C-05/C-06/C-07 레이어의 생산자. expected 골든 출력이 동봉된 fixture-verification 모드에서는 `run_harness(...,expected)->MismatchReport`를 통과/위반 검증으로 부가 표시하되, 이 하네스는 출력 XFrame을 반환하지 않으므로 시각화 산출 경로와 분리된다 — 측정=판정 분리).
- **REQ-VIEW-RUN-2 (Event-Driven)** — WHEN 사용자가 파이프라인의 부분 또는 전체 실행을 요청하면, THEN 시스템이 파이프라인을 실행해 스테이지별 전/후 XFrame을 산출해야 한다(Phase 2, `run_pipeline`·`CANONICAL_ORDER`; 스테이지별 비교의 생산자).
- **REQ-VIEW-RUN-3 (Event-Driven)** — WHEN 지표 플롯(MTF/NPS/DQE 등)이 요청되면, THEN 시스템이 기존 `metrics/` 엔진을 호출해 지표 결과를 산출하고 그 결과만 플롯 값으로 사용해야 한다(C-09; 플롯 값 = 엔진 출력과 배열 단위 일치)(디스플레이 픽셀 히스토그램은 W/L 렌더 경로 UI 구성요소(C-01 계열)로서 본 위임 대상이 아니며, metrics 엔진 내부의 통계 계산과도 무관하다).
- **REQ-VIEW-RUN-4 (Ubiquitous)** — 시스템은 모든 지표 산출을 GUI 코드 경로에서 계산하지 않고 `metrics/` 엔진에 위임해야 한다(C-09 GUI 자체 지표 계산 0 — 금지 불변식).
- **REQ-VIEW-RUN-5 (Event-Driven)** — WHEN 지표 계산용 ROI가 선택되면, THEN 시스템이 사용된 정확한 경계를 표기해야 한다(C-10).
- **REQ-VIEW-RUN-6 (State-Driven)** — WHILE 동일 ROI 경계가 지표 재계산 경로(metrics 엔진 재호출)에 투입되는 동안, 표시 지표 값과 재계산 값이 일치해야 한다(C-10 round-trip 재현; REQ-VIEW-RUN-3 산출 지표 소비).
- **REQ-VIEW-RUN-7 (Event-Driven)** — WHEN 사용자가 내보내기를 요청하면, THEN 시스템이 사용자 지정 출력 디렉터리로만 산출물을 써야 한다(C-20; Phase 2 축소판 내보내기 #17).
- **REQ-VIEW-RUN-8 (Unwanted)** — IF 어떤 GUI 동작이 `data/` 골든 fixture·CalibSet 파일 쓰기를 시도하면, THEN 시스템은 그 쓰기를 거부해야 한다(C-20 읽기-실행 전용 — 단일 결정론 경로).

### REQ-VIEW-ARCH — 아키텍처·설치·시험·자원 계약 (GUI_CRITERIA C-11~C-16·C-18·C-19, XDET-TC-036/037; C-17은 SPIKE-1/SG-3 소관)

- **REQ-VIEW-ARCH-1 (Ubiquitous)** — `apps/gui`는 `common`·`modules`·`pipeline`·`metrics`를 단방향으로만 소비하고, 코어 4계층은 `apps.gui`를 import하지 않아야 한다(C-11, import-linter forbidden 계약).
- **REQ-VIEW-ARCH-2 (Event-Driven)** — WHEN import-linter가 CI에서 실행되고 `apps.gui`로의 의도적 위반이 카나리로 심어지면, THEN forbidden 계약이 실제로 실패해야 한다(C-11 카나리 — lesson #1 import-linter 헛통과 방지; 린터가 실제로 실행되어 심은 위반을 잡음을 assert).
- **REQ-VIEW-ARCH-3 (Event-Driven)** — WHEN base 패키지가 `[gui]` extras 없이 설치되면, THEN 전체 코어 TC가 통과해야 한다(C-12 extras 격리).
- **REQ-VIEW-ARCH-4 (Unwanted)** — IF 의존성 집합에 allowlist 외의 GPL-only 라이선스가 존재하면, THEN `pip-licenses` CI 게이트가 실패해야 한다(C-13; PyQt6 명시 배제).
- **REQ-VIEW-ARCH-5 (Ubiquitous)** — 모든 GUI CI 테스트는 오프스크린으로 실행되어야 한다(C-14 헤드리스; `QT_QPA_PLATFORM=offscreen`, Windows 러너 xvfb 불요).
- **REQ-VIEW-ARCH-6 (State-Driven)** — WHILE 오프스크린 CI 컨텍스트인 동안, 파일 로드(raw+JSON)·모듈/파이프라인 하네스 호출·입력/출력/diff/마스크 레이어 생성·W/L 수치 적용·프로브 값 정확성이 로직 레벨로 검증되어야 한다(C-15; qtbot(pytest-qt) 기반 — 스파이크 결과 napari 폐기).
- **REQ-VIEW-ARCH-7 (State-Driven)** — WHILE 동일 fixture 입력과 동일 params인 동안, GUI 코드 경로를 통과한 diff 레이어 배열과 표시 지표 배열이 실행 간 bit-동일해야 한다(C-16 결정론 — 파이프라인 순수성 상속).
- **REQ-VIEW-ARCH-8 (Event-Driven)** — WHEN 파이프라인 실행 등 장시간 작업이 트리거되면, THEN 시스템이 그 작업을 GUI 스레드 밖에서 실행하고 진행 표시와 취소를 제공해야 한다(C-19 응답성; 이벤트 루프 블로킹 `[T]` 200ms 초과 금지).
- **REQ-VIEW-ARCH-9 (Ubiquitous)** — 다중 프레임 로드는 명시적 LRU K프레임(`[T]`) 상한으로 제한되어 무한 증가하지 않아야 한다(C-18 메모리; 전/후 1쌍+diff+마스크 로드 시 RSS `[T]` 2GB 이하 목표).

## Exclusions (What NOT to Build)

- **배포·서버·엔트리포인트 없음** — 로컬 검증 앱만 제공한다. 웹 서버·REST 엔드포인트·CLI 배포 엔트리포인트·컨테이너 배포는 P1 범위 밖(GUI_REVIEW: 이 프로젝트에 없는 배포 문제를 푸는 스택 기각).
- **다중 사용자 없음** — 단일 로컬 사용자 검증 도구다. 세션 관리·인증·동시 접속은 범위 밖.
- **GUI 내부 지표 계산 없음(C-09)** — MTF/NPS/DQE 등 지표는 기존 `metrics/` 엔진 호출 결과만 사용한다. GUI 코드에 지표 산출 로직을 두지 않는다. 디스플레이 픽셀 히스토그램(W/L 보조)은 지표가 아니라 렌더 경로 UI다.
- **`data/` 쓰기 없음(C-20)** — GUI는 `data/` 골든 fixture·CalibSet을 절대 변경하지 않는다. 모든 내보내기는 사용자 지정 출력 디렉터리로만.
- **오케스트레이터 표면·코어 계약 변경 없음** — `CANONICAL_ORDER`·`process` 시그니처(SWR-000-6~12)·기존 import-linter 계약은 불변(KEPT). GUI는 소비자이며 선행 코어 갭(#15/#16/#18)도 additive 확장으로만 구현한다.
- **#19 인체공학 개선 별건(범위 밖)** — 재수출/`REQUIRED_PARAMS`/Params 검증/반환형 통일(이슈 #19)은 GUI 검증기 도입을 차단하지 않는 코어 인체공학 개선으로(GUI_CRITERIA §4 "병행 가능"), 본 SPEC in-scope가 아니라 별도 작업으로 처리한다.
- **PyQt6 사용 없음** — Qt 바인딩은 PySide6(LGPL)로 고정. PyQt6(GPL/상용)는 라이선스 게이트로 배제(C-13/§2.2).
- **Windows CI 픽셀 그랩·스크린샷 시각 단정 없음(C-15)** — 헤드리스 CI 검증은 로직 레벨(레이어 생성·수치 적용·프로브 값)만. 픽셀 스크린샷 시각 비교는 Windows CI에서 제외(napari 문서화된 제약; Linux xvfb 픽셀 그랩 잡은 본 SPEC 범위에 두지 않음 — 후속 별건 가능).
- **Gen 2 항목 없음** — DL·ADR 등 CLAUDE.md Gen 2 항목은 구현하지 않는다. 검증 GUI는 Gen 1 골든 모델 파이프라인만 대상으로 한다.
- **속도·메모리 미세 최적화 없음** — 검증 도구의 목적은 정확성·재현성이며 렌더/실행 성능 미세 최적화는 범위 밖(자원 `[T]` 상한 준수 외).

## 확정 사항 (구 「결정 필요/확인 사항」 — v0.1.4에서 접힘)

아래 6건은 GUI_CRITERIA·GUI_REVIEW·코어 구현 대조에서 남았던 열린 질문으로, v0.1.4에서 사용자 확정(딥리서치·저장소 관례 조사 근거)으로 전부 접혔다. 더 이상 열린 결정이 아니며 run 착수의 선행 확인은 완료되었다(항목 번호는 종전 「결정 필요/확인 사항」 N 교차참조와 동일하게 유지).

1. **[확정] Phase 0 실측 완료 — pyqtgraph(PySide6) 확정.** napari는 Windows 헤드리스 CI 구성(`QT_QPA_PLATFORM=offscreen`)에서 `napari.Viewer()` 생성 자체가 OpenGL 컨텍스트 획득 실패로 크래시하여 SG-3 하드 실패(SG-1/SG-2는 측정 불가) — `.moai/reports/SPEC-VIEWER-001-spike.md` 참조. pyqtgraph는 동일 헤드리스 조건에서 SG-1(호버 float32 원값 4/4 좌표 일치)·SG-2(W/L 응답 최대 0.09ms)·SG-3(콜드 스타트 0.52s) 전부 PASS. REQ-VIEW-SPIKE-2(단일 순서 결정)에 따라 pyqtgraph로 확정(비결정적 택일 아님). SG-2(W/L 100ms)·SG-3(콜드 스타트 10s)을 포함한 전 `[T]` 임계의 등재 위치는 **GUI 전용 설정 모듈 `apps/gui/config.py`**로 확정 — 코어 `P_*` 명명 상수 + `_require` 검증 관례를 승계하며(`modules/window.py` 선례), 코어 `Params`(프레임 처리 계약)도 `pyproject` tool 섹션(도구 설정 전용)도 아니다. 확정 스택 버전(스파이크 실측 환경, 2026-07-10): pyqtgraph 0.14.0, PySide6 6.10.3. 문헌 근거(임계값 자체는 유지): W/L ≤100ms(Nielsen 0.1s·RAIL <100ms — 의료 워크스테이션 문헌의 ≤50ms 왕복 권고를 감안한 안전 상한), 콜드 스타트 ≤10s(Nielsen 10s 주의 한계; pyqtgraph 실측 기동 0.52s).
2. **[확정] 선행 코어 갭 #15/#16/#18 = 본 SPEC Phase 0.5 작업 패키지, additive only, 계약 KEPT.** 코어 계약(SWR-000-6~12)·전 import-linter 계약을 불변 유지하는 additive 확장으로 구현(REQ-VIEW-CORE-1~4). #18 합성 CalibSet 팩토리는 `common/synth_calibset.py` 단일 배치(REQ-VIEW-CORE-3 "배포 가능" 요건 + `pyproject` `packages`가 apps 미포함 → apps/gui 하위 배포 불가 → 단일 답 강제; plan.md §3).
3. **[확정] 읽기-실행 전용 + 지표 위임 + #17 축소판 스키마 확정.** GUI는 `data/`에 절대 쓰지 않고(REQ-VIEW-RUN-8) 내보내기는 사용자 지정 디렉터리로만(REQ-VIEW-RUN-7), 지표는 `metrics/` 엔진 위임(REQ-VIEW-RUN-3/4). #17 Phase 2 축소판 내보내기 스키마 확정: **npz(arrays: pixel float32, masks uint8, validation_mode 시 pixel_f64) + JSON 사이드카 {noise{alpha,sigma}, validation_mode, history[HistoryEntry 5필드: module_name/module_version/params_hash/calibset_id/extra], array_keys}** — `CalibSet.save/load`의 npz+JSON 사이드카 선례(`common/calibset.py`) 준수, HistoryEntry 전 필드 JSON 호환(`common/xframe.py`), 중간 산출물(intermediates)은 축소판에서 제외, 내보내기 유틸은 `apps/gui`에 위치(코어 표면 불변). 외부 선례: BIDS GeneratedBy / OME 사이드카 최소 교집합.
4. **[확정] import 격리 카나리 = forbidden 계약 + `badgui` 픽스처 임시 설정.** 코어 4계층 → `apps.gui` forbidden 계약 + `tests/fixtures/badgui/`(`pyproject` `root_packages` 밖 — 실계약 무영향)에 심은 코어→`apps.gui` 위반을 임시 import-linter 설정으로 검출해 `returncode≠0`(위반 출력 비어있지 않음)를 assert(REQ-VIEW-ARCH-1/2, lesson #1). 프로덕션 원본 트리 무변경 — `tests/fixtures/badlayers/`·`test_tc000_B_import_linter_detects_violation` 선례.
5. **[확정] TC 번호 블록 = XDET-TC-030~037.** Gen 1 XDET-TC-000~021 형상 동결 범위 밖 신규 블록으로 캡스톤 스캔(`tests/test_tc_skeletons.py` `_GEN1_TC_RANGE = range(0,22)`) 간섭 회피 + GUI 테스트 소스는 Gen 1 TC id(`000`~`021`) 문자열 미포함(D9).
6. **[확정] 자원 `[T]` 임계 설정 외부화 + 픽셀 그랩 Windows CI 제외 + Linux xvfb 픽셀 그랩 잡 미포함.** C-17(콜드 스타트 10s)은 스파이크 SG-3 실측, C-18(RSS 2GB/LRU K)·C-19(200ms)는 구조 게이트 + `[T]` 설정(`apps/gui/config.py`), 픽셀 그랩 시각 단정은 로직 레벨만(REQ-VIEW-ARCH-6~9). **Linux xvfb 픽셀 그랩 잡은 본 SPEC 범위에 두지 않는다** — 어떤 인수 기준도 픽셀 그랩에 의존하지 않고 P1은 정확성 도구이므로 후속 별건으로만 추가 가능.
