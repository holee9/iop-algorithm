# iop-algorithm — XDET 영상처리 SW

## 프로젝트 개요

XDET은 X-ray FPD(CsI, 140µm, 3072×3072 / 3072×2560, 16-bit raw) 영상처리 소프트웨어이다. 본 저장소는 그 P1 단계 — SW 레퍼런스/골든 모델 구현을 담고 있다. 정수 최적화나 실시간 처리 성능이 아니라, float 정밀도 기준의 정확한 참조 동작을 정의하는 것이 P1의 유일한 목표이며, 속도 최적화는 의도적으로 P2 이후로 미뤄져 있다.

기술 스택은 Python 3.11+ 및 numpy/scipy 기반 골든 모델, pytest 기반 CI이다. 아키텍처는 `common/` · `modules/` · `pipeline/` · `metrics/` 4계층으로 구성되며, 모든 처리 모듈은 `process(XFrame, CalibSet, Params) -> XFrame` 단일 시그니처를 갖는 순수함수이다.

## 현재 상태

P1(골든 모델)은 2026-07-10 완료되었다. 11개 코어 SPEC(T0~T10)이 GitHub 이슈 #1~#12에 대응되어 전건 main 브랜치에 병합 완료되었고, 이후 검증 GUI·실측 수집·빔질 도메인 계층화·인체공학·측정프로토콜 §1.4 정정 등 지원 SPEC이 추가되었다. 코어 테스트 스위트는 **543 passed**(`uv run pytest --ignore=tests/apps`, 0 실패·0 skip)이다.

검증 GUI(SPEC-VIEWER-001, 이슈 #14)는 별도 서브 프로젝트 `apps/gui/`로 2026-07-10 구현 완료되었다. 2026-07-13 fresh GUI 포함 전체 테스트 스위트는 **632 passed**(`uv run pytest`). 상세는 아래 "검증 GUI" 절과 [`.moai/specs/SPEC-VIEWER-001/`](.moai/specs/SPEC-VIEWER-001/) 참조.

P1(알고리즘 골든모델)은 위 기준으로 완결된 상태다. 이후 제품화(C# UI + 언어중립 엔진 seam → C++ 엔진 이행)는 별도 트랙이다. 구현된 얇은 수직 슬라이스의 역사적 기준은 SPEC-XSEAM-001(이슈 #50), 전체 알고리즘 WPF 확장의 현재 규범은 SPEC-XGUI-MASTER v0.5.1 후보와 SPEC-XSEAM-002(이슈 #58)다.

상세 완료 이력(SPEC별 커밋, plan-audit 점수 추이, 독립 리뷰에서 발견된 critical/major 결함)은 다음 문서를 참조한다.

→ [`docs/P1_COMPLETION_REPORT.md`](docs/P1_COMPLETION_REPORT.md)

## 문서 지도

문서 지도의 단일 출처는 저장소 루트의 [`CLAUDE.md`](CLAUDE.md)이다(중복 방지를 위해 여기서는 목록을 재기술하지 않는다). `docs/` 디렉터리에는 SWR(사양), EVAL(합격기준), TestSpec(시험케이스), measurement protocol(지표산출 엔진 사양), FRD/PRD/MRD/RTM(요구·추적) 등이 있으며, 각 문서의 역할은 CLAUDE.md의 "문서 지도" 표에 정리되어 있다.

## 아키텍처 한눈에

- `common/` — XFrame·CalibSet 데이터 구조 및 5종 공용 컴포넌트(피라미드, FFT/PSD, 강건통계, 마스크연산, 동일성검증 등)
- `modules/` — 순수함수형 처리 모듈(offset·gain·defect·line_noise·saturation·geometry·lag·denoise·mse·window·grid·virtual_grid), 모듈 간 직접 호출 금지
- `pipeline/` — 조합 계층. `orchestrator.py`(CANONICAL_ORDER 기반), `sequence.py`(상태보유 모듈용 시퀀스 러너), `tier.py`(하드웨어 티어 게이팅)
- `metrics/` — T1 측정 엔진(MTF·NPS·DQE·lag IRF·defect 통계·NDT 등)

상세 아키텍처 설명은 [`docs/P1_COMPLETION_REPORT.md`](docs/P1_COMPLETION_REPORT.md)의 "아키텍처 개요" 절을 참조한다.

## 개발/테스트 실행

```bash
uv run pytest
```

## 검증 GUI (`apps/gui/`)

XDET 골든 모델(`common/`·`modules/`·`pipeline/`·`metrics/`)을 수정하지 않고 눈으로 검증하기 위한 도구다(SPEC-VIEWER-001, 이슈 #14). 두 탭으로 구성된다:

- **Module Verifier** — fixture/raw 입력 하나를 선택한 모듈 1개로 직접 실행해 입력/출력/diff/마스크/처리 이력을 비교한다.
- **Pipeline Viewer** — `CANONICAL_ORDER`의 부분 또는 전체 구간을 실행해 스테이지별 전/후를 비교한다.
- **Metrics** — Module Verifier/Pipeline Viewer 출력을 소스로 MTF를 계산하고 ROI round-trip을 검증한다.

모든 버튼·체크박스·슬라이더·입력 필드에 호버 툴팁이 있으며, 메뉴바의 **Help → How to use...**에서 앱 전체 사용법을(3개 탭의 워크플로·핵심 개념) 확인할 수 있다.

핵심 원칙(위반 시 머지 불가):

- **읽기-실행 전용** — `data/` 골든 fixture·CalibSet 파일에 절대 쓰지 않는다. 모든 내보내기는 사용자 지정 디렉터리로만.
- **지표 자체 계산 0** — MTF/NPS/DQE 등은 기존 `metrics/` 엔진 호출 결과만 표시한다.
- **단방향 소비** — `apps/gui`는 코어 4계층을 import만 하고, 코어는 `apps.gui`를 절대 import하지 않는다(import-linter forbidden 계약 + 의도적 위반 카나리로 CI 강제).

스택은 **pyqtgraph + PySide6**다(napari는 Phase 0 스파이크에서 Windows 헤드리스 CI 환경(`QT_QPA_PLATFORM=offscreen`)의 OpenGL 컨텍스트 획득 실패로 기각 — 근거: [`.moai/reports/SPEC-VIEWER-001-spike.md`](.moai/reports/SPEC-VIEWER-001-spike.md)).

```bash
# GUI 의존성 설치 (base 설치에는 포함되지 않음, C-12 격리)
uv sync --extra gui

# 앱 실행 (실제 창이 뜬다 — 디스플레이가 없는 환경에서는 QT_QPA_PLATFORM=offscreen 필요)
uv run python -m apps.gui.app

# 헤드리스 테스트 실행 (CI와 동일 조건)
QT_QPA_PLATFORM=offscreen uv run pytest tests/apps/gui -v

# 로컬 CI 4단계 재현 (import-linter → core-no-gui → gui-offscreen → license-gate)
bash scripts/test.sh          # 또는 pwsh scripts/test.ps1 (Windows)
```

SPEC/설계 근거: [`.moai/specs/SPEC-VIEWER-001/`](.moai/specs/SPEC-VIEWER-001/)(spec.md/plan.md/acceptance.md), [`docs/GUI_CRITERIA.md`](docs/GUI_CRITERIA.md)(품질 기준 C-01~C-20), CI: [`.github/workflows/gui.yml`](.github/workflows/gui.yml).

## 전체 알고리즘 WPF 사용·검증 앱 (`apps/xdet-console/`)

현재 제품화 GUI 대상은 Qt가 아니라 **.NET 9 WPF**다. 기존 코드는 Viewer, 고정 offset→gain Pipeline, Real Image, 합성 MTF의 부분 수직 슬라이스이므로 전체 구현 완료가 아니다.

v0.5.1 기준선 후보는 `modules/`, `metrics/`, `pipeline/`의 대상 public operation 전체를 qualified EntryPoint로 카탈로그화하고, 9개 typed DTO family를 거쳐 8개 목적 그룹 화면과 `XDET-TC-096~167`에 연결한다. 등록 데이터 부재와 알고리즘 미구현을 분리하며, DQE·calibration builder·lag/NDT session·tier까지 실제 engine 호출 경로에 포함한다. 사용자 승인·기준선 동결 전에는 신규 구현을 시작하지 않는다.

- 전체 범위: [algorithm-catalog.md](.moai/specs/SPEC-XGUI-MASTER/algorithm-catalog.md)
- 마스터 요구/계획/인수: [SPEC-XGUI-MASTER](.moai/specs/SPEC-XGUI-MASTER/README.md)
- 구현 착수 통제: [baseline-control.md](.moai/specs/SPEC-XGUI-MASTER/baseline-control.md)
- 요구사항·인수·TC 추적: [traceability-matrix.md](.moai/specs/SPEC-XGUI-MASTER/traceability-matrix.md)
- typed seam: [SPEC-XSEAM-002](.moai/specs/SPEC-XSEAM-002/spec.md)
- GUI 품질 기준: [GUI_CRITERIA.md](docs/GUI_CRITERIA.md)

문서가 기술적으로 구현 가능한 것, 사용자가 기준선을 승인해 구현 착수를 허가한 것, 앱이 구현 완료된 것은 서로 다른 상태다. 현재는 사용자 승인 대기이며 구현 미허가다. 실제 앱 완료는 승인 뒤 catalog→manifest→Contract handler→GUI command→자동화 TC 집합 차이가 0이고 모든 구현 시험이 통과할 때만 선언한다.

## P2 착수 필요성 — 딥싱크 검토 (Deep-Sync Review)

이 섹션은 P1 산출물에 대해 합리적인 독자가 P2 착수 여부를 저울질할 때 참고할 사실들을 제시한다. **결론은 내리지 않는다.**

### 구조적으로 끝난 것

- CLAUDE.md 정의상 "Gen 1 대상 TC-000~021 CI 전체 통과 + 골든 모델 형상 동결"은 구조적으로 달성되었다 — 543 passed, 0 skipped, 캡스톤 테스트(`tests/test_tc_skeletons.py`)가 전 22개 TC ID의 실동작 존재를 강제 검증한다.
- 11개 SPEC(T0~T10) 전건이 plan-audit(EARS 준수 검증) 및 독립 코드 리뷰를 거쳐 main에 병합되었다.

### 실측/문서/특허 검토가 남은 것

- TC-020/021(티어/동일성 프레임)은 SPEC 설계 단계에서부터 절대 수치 판정이 P2로 명시 이연된 상태다. "형상 동결"은 골든모델 코드 자체의 동결을 의미하며, 하드웨어 티어별 실측 성능 기준의 확정을 의미하지 않는다.
- 문서 정합성 갭은 1건이 남아있다(DQE §1.4 갭은 2026-07-11 해소).
  - **[해소]** DQE 측정 프로토콜 문서(`docs/XDET_measurement_protocol_v1.0.md` §1.4)의 IEC 62220-1 공식 차원 오류는 SPEC-DQEDOC-001(이슈 #38)로 문서가 IEC 무차원 형태 `DQE(f)=MTF²(f)/(q·Ka·NNPS(f))`로 정정(v1.2)되고 역전형태 회귀 음성대조가 추가되어, 코드+문서+RTM이 단일 IEC 형태로 정합되었다.
  - SWR 부록 A/A-2의 과거 미결정 레지스터·근거등급 총괄이 11개 SPEC의 반복된 등재 요청에도 갱신되지 않았던 이력이 있다.
- 특허 검토(⚠P 플래그 6개소 이상)가 "릴리스 게이트로 이연"된 상태로 남아있다. PRM v1.1이 요구하는 "상세설계 착수 전 변호사 검토 완료" 절차의 증적은 SWR 문서 상에서 확인되지 않는다. 이는 P1 범위 밖(정책상 의도된 이연)이지만 릴리스 전 반드시 클리어해야 할 게이트다.
- 실측 근거가 필요한 [B] 등급 파라미터가 11개 SPEC 전반에 분포하며, 특히 LAG(IRF 파라미터)와 VGRID(SKS 산란커널)가 실측 의존도가 높다. 실제 패널 하드웨어 데이터 없이는 P1 골든모델이 "이론적으로 정확"할 뿐 "검증된 정확"이라 말하기 어려운 항목들이 남아있다. 이 실측 blocker와 정본 지침(guiding) 취득세트의 취득 요구는 **SPEC-GUIDING-001(이슈 #33)**로 정식화되어(6그룹 36 EARS, TC/EV 매니페스트) 추적된다 — 현 샘플 세트는 QUARANTINE(플러밍/sanity 전용, 수치 golden 검증 불가)이며, 현 시점의 승인되지 않은 SAMPLE은 구조 sanity에만 사용하며 수치 검증은 승인된 합성 oracle과 기존 Python 회귀 범위로 제한한다.

### P2/Gen2 고유 범위

- Gen 2 항목(DL, ADR)은 CLAUDE.md 상 P1 범위에서 명시적으로 제외되어 있으며, 이번 P1 작업 범위에도 포함되지 않았다 — P2 시작 시 최초 논의 대상이다.

이 섹션은 사실관계 요약이며, 착수 여부는 프로젝트 오너의 판단에 달려 있다.

## 제품화 로드맵 (C# UI → C++ 엔진)

P1(알고리즘 골든모델)의 완료는 "정확한 참조 구현"의 완결이지 제품 출하를 뜻하지 않는다. 제품화는 SPEC-XSEAM-001의 얇은 수직 슬라이스를 기반으로 시작됐고, 현재 전체 알고리즘 GUI 확장은 SPEC-XGUI-MASTER v0.5.1 후보와 SPEC-XSEAM-002가 규정한다. 이 절은 두 기준의 관계와 이후 C++ 이행을 요약한다.

### 현재 상태

| 구성요소 | 위치 | 역할 | 상태 |
|---|---|---|---|
| Python 알고리즘 골든모델 | `common/` `modules/` `pipeline/` `metrics/` | 정확도 기준 레퍼런스 구현 | 구현 + 합성 검증 완료 — 코어 **543 passed**, 골든 재현 **23/23** |
| Python 검증 GUI | `apps/gui/`(SPEC-VIEWER-001) | 골든을 눈으로 돌려보는 도구 | 구현 완료 — **89 tests** |
| WPF 전체 알고리즘 검증 앱 | `apps/xdet-console/`(SPEC-XGUI-MASTER v0.5.1 후보) | 모든 대상 알고리즘의 실제 사용·검증 UI | 기존 부분 구현 — 문서 내부 검토 중, 사용자 승인 전 구현 미허가 |

### 핵심 원칙

> **겉(GUI)은 C#, 속(알고리즘)은 Python 그대로, 사이는 데이터만 나르는 얇은 브리지.**

- **알고리즘 재구현 0** — C#/C++ 어느 단계에서도 DSP를 새로 구현하지 않는다. 항상 기존 골든(또는 그 포트)을 호출한다.
- **Python 골든모델 = 영구 오라클** — 제품이 C++/C#로 완전히 이행한 뒤에도 골든모델은 저장소에 남아 CI 회귀의 정답 기준 역할을 계속한다. 다만 제품 배포판에는 포함되지 않는다(Python 런타임 미탑재).

### 3단계 흐름

| 단계 | 범위 | 무엇이 바뀌나 | 검증 게이트 |
|---|---|---|---|
| **Stage 1a — P1.5 기반 슬라이스** (SPEC-XSEAM-001, 이슈 #50; 역사적 기준) | 언어중립 `IXdetEngine` + pythonnet + WPF 스켈레톤. 초기 SPEC의 .NET 8 가정과 달리 현재 소스는 `.NET 9`다. | offset·등록 offset/gain/defect·고정 offset→gain pipeline·합성 MTF·real-image load/process/save의 얇은 수직 슬라이스가 실제 Python 골든을 호출한다. | 현재 회귀: .NET 21 tests. Python 골든 동일성·C-20 쓰기 보호를 유지한다. 전체 알고리즘 완료 증거로 사용하지 않는다. |
| **Stage 1b — 전체 XGUI 확장** (SPEC-XGUI-MASTER v0.5.1 후보 + SPEC-XSEAM-002, 이슈 #58; 현재 규범) | `.NET 9 WPF`, 9-family typed seam, 51 FeatureId, target 67 + common infrastructure 6 = catalog callable 73, 8개 목적 그룹 | 기존 슬라이스를 generic Contract/manifest/handler와 전체 알고리즘 사용·검증 앱으로 확장한다. Python GUI helper나 C# DSP를 실행 경계에 넣지 않는다. | `XDET-TC-096~167` 72개, catalog/manifest/handler/GUI 집합 차이 0, direct-golden fidelity, 성능·메모리·artifact 기준 통과. 사용자 승인·기준선 동결 전 구현 미허가. |
| **Stage 2 — P2** | C++ 엔진 모듈별 포팅 | seam 백엔드가 Python → C++로 스왑된다. **C# UI는 한 줄도 바뀌지 않는다**(동일 `IXdetEngine`) | 각 C++ 모듈은 Python 골든과 **bit-동일(정수 경로) / ±1 LSB(float 경로)** 동일성(XDET-TC-020/021 게이트)을 통과해야 합격 |
| **Stage 3 — 제품** | 순수 C++/C# 제품(엔진 C++, UI C#) | pythonnet 브리지가 제거된다. 제품 배포판에는 Python이 미탑재 | Python 골든모델은 저장소에 남아 **CI 회귀 오라클**로 계속 기능 |

### 병렬 트랙 — 실측 검증 (SPEC-GUIDING-001, 이슈 #33)

정본 지침 영상 취득세트 확보 → 실측 수치로 골든 값을 검증하는 트랙이다. C#/C++ 제품화 트랙과는 **독립적으로** 진행되며(물리 데이터 확보 대기가 blocker), 어느 한쪽이 다른 쪽의 착수를 막지 않는다. 알고리즘이 "이론적으로 정확"에서 "실측으로 검증된 정확"으로 승격되는 지점이 바로 이 트랙이다.

### 근거 문서

- 현재 전체 GUI 규범: `SPEC-XGUI-MASTER` v0.5.1 후보와 `SPEC-XSEAM-002`(이슈 #58) — `.moai/specs/SPEC-XGUI-MASTER/`, `.moai/specs/SPEC-XSEAM-002/`
- 구현된 기반 슬라이스의 역사적 규범: `SPEC-XSEAM-001`(이슈 #50) — `.moai/specs/SPEC-XSEAM-001/`
