# SPEC-VIEWER-001 — 실증 테스트 리포트 (Live Verification Report)

작성일: 2026-07-10
방법론: `QT_QPA_PLATFORM`을 설정하지 않은 **실제 디스플레이 세션**(Windows, 3840×2160, `SESSIONNAME=Console`)에서 `uv run python -m apps.gui.app`으로 앱을 기동하고, `QTimer.singleShot`으로 예약한 콜백이 **실제 위젯의 버튼/체크박스/슬라이더/스핀박스**를 프로그램적으로 클릭·조작한 뒤, `QWidget.grab()`으로 실제 렌더 결과를 PNG로 저장하고 위젯 상태(상태 텍스트, 결과 객체 필드)를 로그로 기록했다. 이는 pytest-qt의 `QT_QPA_PLATFORM=offscreen` 헤드리스 시뮬레이션과는 다른 계층의 검증이다 — 화면에 실제로 그려진 결과와 실제 프로세스의 동작을 확인한다.

배경: 최초 완료 보고 후 사용자가 "실제로 앱을 실행해서 하나하나 클릭해 검증했는가"를 반복적으로 질의했고, 그 과정에서 아래 §4에 정리한 **4건의 실제 통합 결함**이 발견·수정되었다. 본 리포트는 그 수정 이후, 남아 있던 모든 기능을 개별적으로 클릭 검증한 결과다.

---

## 1. 검증 환경

| 항목 | 값 |
|---|---|
| OS | Windows 11 Pro, 인터랙티브 콘솔 세션(`SESSIONNAME=Console`) |
| 디스플레이 | 3840×2160 (실제 연결, offscreen 아님) |
| 스택 | pyqtgraph 0.14.0 + PySide6 6.10.3 |
| 실행 명령 | `uv run python -m apps.gui.app` (README.md 기재) |
| 구동 방식 | `QApplication` + `MainWindow()` + `QTimer.singleShot` 예약 콜백으로 실제 버튼/체크박스/슬라이더 클릭 |
| 증거 | 각 단계 후 `QWidget.grab().save(...)`로 스크린샷 저장(세션 스크래치패드, 저장소에는 커밋하지 않음) + 콘솔 로그 |

## 2. Module Verifier 탭

| # | 조작 | 관측 결과 | 판정 |
|---|---|---|---|
| 1 | 실제 raw(16-bit)+json 파일을 `IoPanel.open_raw()`로 로드(파일 대화상자 우회 없이 실제 코드 경로) | `frame.shape=(32,48)`, 원본 uint16 배열과 float32 변환 배열이 `np.array_equal`로 완전 일치(무손실) | PASS |
| 2 | `saturation` 모듈 선택 → Run 클릭 | SATURATION 코어 40×40 블록 → SATURATION_BAND 336픽셀 실제 생성(팽창 확인) | PASS |
| 3 | 마스크 SATURATION 체크박스 해제 | `overlay.visible=False`, `item.opacity()=0.0`로 실측 반영 | PASS |
| 4 | 마스크 오퍼시티 슬라이더 90 | `overlay.opacity=0.9`, `item.opacity()=0.9` 실측 반영 | PASS |
| 5 | Blink toggle 버튼 클릭 | `showing_after: True→False`, `after.visible=False`/`before.visible=True`로 정확히 반전 | PASS |
| 6 | Output 뷰 중앙에 호버 이벤트 시뮬레이션 | `"Probe (row=100, col=100): before=4095, after=4095, diff=0"` 정확 표시(원본 float32 값, 렌더 LUT 아님) | PASS |
| 7 | W/L 스핀박스에 300/500 입력 | 레벨 `(238.78, 4095.0) → (300.0, 500.0)` 실측 변경 | PASS |
| 8 | Export 버튼(직접 경로 호출) | npz+json 생성 확인(`exists()=True` 양쪽) | PASS |
| 9 | `data/` 하위 경로로 Export 시도 | `DataWriteRejectedError`로 정상 거부, 상태 텍스트에 거부 사유 표시 | PASS |
| 10 | 모듈 없이(로드 전) Run 클릭 | `"Load a frame first"`, 크래시 없음 | PASS |
| 11 | Run 클릭 직후 상태 확인 | Run 버튼 비활성화 + 진행률 표시(부정형) 즉시 반영, 완료 시 재활성화 | PASS |
| 12 | Run 중 Cancel 클릭 | `last_result=None`, 상태 `"Cancelled"` — 최선노력 취소 확인 | PASS |
| 13 | **`gain` 모듈, Params 미입력 → Run** | `"gain failed: gain: missing required parameter 'gain_min'"` | PASS(정상 거부) |
| 14 | **"Add param field"로 `gain_min`/`gain_max` 필드 추가 후 값(0.5/2.0) 입력 → 재실행** | 오류가 **"missing required parameter" → "missing required data key 'G_map'"로 전환** — 동적 Params 필드가 실제로 `run_module`에 전달됨을 행위적으로 증명 | PASS |
| 15 | **`offset` 모듈에 `raw_saturation_threshold`=2000 입력 후 실행** | O_map 부재로 계산 자체는 실패하지만 타이핑한 값이 읽혔음을 확인(2차 시나리오 교차검증) | PASS |
| 16 | **정상 실행 결과를 Export → 같은 입력으로 재실행 시 "Load expected"로 재로드 → 재실행** | `history=1`, **`"Ran 'saturation' [PASS]"`**, `verification.passed=True` | PASS |
| 17 | **의도적으로 다른(픽셀+500) 프레임을 expected로 로드 → 재실행** | **`"Ran 'saturation' [FAIL]"`**, `verification.passed=False` | PASS |

## 3. Pipeline Viewer 탭

| # | 조작 | 관측 결과 | 판정 |
|---|---|---|---|
| 1 | `saturation` 스테이지만 체크 → Run pipeline | `stage_comparisons=1`, 비교 뷰 렌더링 | PASS |
| 2 | Export 버튼(직접 경로 호출) | npz+json 생성 확인 | PASS |
| 3 | 프레임/스테이지 미선택 상태에서 Run | `"Load a frame and check at least one stage"`, 크래시 없음 | PASS |
| 4 | Run 클릭 직후 Cancel 클릭 | `last_result=None`, 상태 `"Cancelled"` | PASS |
| 5 | `offset`/`gain`/`saturation` 동시 선택 → Run(실측 캘리브레이션 데이터 없음) | `"pipeline failed: offset: ... missing required data key 'O_map'"` — 파이프라인 전체가 깔끔히 실패(크래시 없음, 기본값 무단 대체 없음) | PASS |

## 4. Metrics 탭

| # | 조작 | 관측 결과 | 판정 |
|---|---|---|---|
| 1 | 소스 미로드 상태에서 Compute/ROI 버튼 클릭 | 각각 `"Load a source frame first"`, 크래시 없음 | PASS |
| 2 | "Use Module Verifier output" 클릭 | 해당 프레임 로드 확인 | PASS |
| 3 | "Use Pipeline Viewer output" 클릭 | `"Loaded pipeline output frame (64, 64)"` | PASS |
| 4 | 실측 slanted-edge 팬텀(angle=2°, sigma=0.8px, pitch=0.14mm) 로드 → Compute MTF | **264개 주파수 포인트** 계산 성공, 교과서적 감쇠 곡선 렌더(스크린샷 확인) | PASS |
| 5 | ROI 사각형 지정(top=20,left=20,60×60) → Recompute for ROI | `"ROI: top=20 left=20 height=60 width=60"`, **round-trip MATCH(bit-identical)**, 123 포인트 | PASS |

## 5. 발견된 실제 통합 결함 (이번 라운드 이전 포함, 전건 수정·머지 완료)

| # | 결함 | 발견 경위 | 수정 | 이슈/PR |
|---|---|---|---|---|
| 1 | `apps/gui/app.py`에 실행 진입점(`__main__`) 부재 — 앱을 프로세스로 띄울 방법 자체가 없었음 | 사용자 질의 | `main()` + `if __name__` 추가, 실제 라이브 구동 확인 | #21 → PR #22 |
| 2 | diff 뷰·마스크 오버레이·호버 프로브·W/L·블링크·지표(MTF)/ROI·내보내기가 개별 함수로는 구현·단위테스트되었으나 `MainWindow`에 전혀 배선되지 않음 | 사용자 질의 후 코드 재검토 | `CompareDisplay` 공용 위젯 + 신규 Metrics 탭 신설, 전 기능 배선 | #23 → PR #24 |
| 3 | `ParamsForm`이 `keys=()`(빈 튜플)로 생성되어 **어떤 모듈을 선택해도 Params 값을 입력할 방법이 없었음**(기존 테스트가 `ParamsForm`을 단 한 번도 직접 검증하지 않아 발견되지 않았음) | 본 라운드 재검증 중 발견 | `ParamsForm.add_field()` 추가 + "Add param field" UI로 런타임 필드 추가 지원 | 본 커밋 |
| 4 | REQ-VIEW-RUN-1의 fixture-verification(PASS/FAIL 배지) 경로가 `_on_run_clicked`에서 `expected`를 전혀 전달하지 않아 **UI로는 절대 도달 불가능**했음 | 본 라운드 재검증 중 발견 | `load_expected()`(export.py의 npz+json 포맷 재사용) + PASS/FAIL 양쪽 실측 확인 | 본 커밋 |

부수 발견: 테스트 스크립트 자체에서 `MismatchReport.__bool__`이 `self.passed`를 반환하도록 설계되어 있어 `verification and ...` 형태의 truthy 체크가 FAIL 리포트에서 단락평가로 오판정되는 함정을 발견(앱 자체의 결함 아님, 스크립트의 논리 오류) — 향후 유사 코드 작성 시 `is not None` 명시 비교를 사용할 것.

## 6. 자동 회귀 테스트 추가 (재발 방지)

이번 라이브 검증에서 발견한 항목은 전부 헤드리스 회귀 테스트로도 고정했다:

- `test_dynamic_param_field_is_read_by_a_real_run` — 동적 Params 필드가 실제 실행에 반영됨을 행위적으로 증명(`gain` 모듈, Params 체크가 calib 체크보다 선행하는 코드 경로 이용)
- `test_expected_fixture_load_drives_pass_and_fail_verification_badge` — PASS/FAIL 배지 양쪽
- `test_pipeline_viewer_cancel_discards_result`
- `test_pipeline_viewer_reports_calibration_data_failure_without_crashing`
- `test_metrics_tab_reports_when_no_source_loaded`
- `test_metrics_tab_loads_source_from_pipeline_viewer_output`
- `test_open_raw_loads_a_real_raw_json_file_losslessly`(`IoPanel.open_raw` 성공 경로 최초 커버)

## 7. 최종 상태

- 헤드리스 GUI 스위트: **79/79 passed**
- 전체 회귀(core 465 + GUI): **544/544 passed**
- import-linter: **7 kept, 0 broken**
- 라이브 검증: 위 §2~§4의 **27개 항목 전건 실측 확인**(스크린샷 + 로그 증거, 세션 스크래치패드 보관)

## 8. 결론

SPEC-VIEWER-001의 acceptance.md에 체크된 DoD 항목은 이제 (a) 단위/헤드리스 자동 테스트와 (b) 실제 디스플레이 세션에서의 클릭 기반 실측 검증, 양쪽 모두로 뒷받침된다. 특히 §5에 정리한 4건은 "단위 테스트 통과"만으로는 잡히지 않는 **통합 배선 누락**이었으며, 실제 실행 없이는 발견 불가능했다 — 향후 유사 SPEC에서도 자동 테스트 통과와 별개로 최소 1회의 실제 프로세스 기동 + 핵심 경로 클릭 검증을 완료 조건에 포함할 것을 권고한다.
