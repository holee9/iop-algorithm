# GUI 기준 문서 — 검증 GUI 품질 기준 및 기술 결정 (v1.3)

> 이 문서는 `docs/GUI_REVIEW.md`와 초기 `SPEC-VIEWER-001`의 Python GUI 연구를 계승하되, 현재 구현 기준선 후보는 `SPEC-XGUI-MASTER` v0.5.1과 `SPEC-XSEAM-002` v0.5.1이다. 구현 대상은 `apps/xdet-console/` C# WPF이며 `apps/gui/`는 동작·시험 선례일 뿐 배포 대상이나 실행 경계가 아니다. v1.3의 GUI 평가 수치는 동결된 기준이며 임시 임계는 없다.
>
> 리서치 방법: (1) 코드베이스 정밀 인벤토리(계약면·모듈·지표 API·fixture·패키징·과거 plan-audit 이력), (2) 후보 프레임워크 6종 웹 딥리서치(2026-07 기준 릴리스/라이선스/유지보수 상태를 PyPI·공식 문서로 검증).

관련 이슈: #14 (검토), #15~#19 (리서치 중 발견한 코드 개선)

---

## 1. 범위 결정

사용자 목표는 알고리즘의 **실제 사용 + 검증**이다. 구현은 다음 단계로 고정한다.

- **Gate 0:** 계획·사양·인수·시험·평가 문서가 내부 교차검토를 통과하고 사용자가 v0.5.1 기준선을 명시적으로 승인·동결한다. 승인 전 구현은 금지한다.
- **Phase 0:** 9-family typed DTO, `AlgorithmCatalogManifest`, run coordinator, export provenance를 `IXdetEngine` 경계에 구현한다.
- **Phase 1:** 공통 folder browser/compare/parameter/export shell과 Calibration 탭을 구현한다.
- **Phase 2:** Lag → Line/Saturation/Geometry → Denoise → Enhancement → Grid → NDT → Metrics 순으로 그룹 탭을 추가한다.
- **Phase 3:** xUnit/PythonNet integration/UI Automation과 중앙 TC 증거를 등록한다.

각 그룹은 개별 실행 → 정렬 조합 → artifact 저장/재열기 → 재현성 검증 순으로 완료한다. 공개 ACTION/SESSION 전체는 catalog→9-family seam→GUI command→TC로 추적한다. DQE는 engine-owned `NPS_BINS_WITHIN_MTF_SUPPORT_V1` 정책으로 `mtf_value_at`과 `compute_dqe`를 호출하며 UI 보간·외삽은 금지한다.

## 2. 기술 스택 결정

### 2.1 결론

| 구분 | 선택 | 근거 요약 |
|---|---|---|
| 구분 | 선택 | 역할 |
|---|---|---|
| 앱 셸 | **.NET 9 WPF** (`net9.0-windows`) | 목적별 8개 탭, MVVM, Windows 배포 |
| 엔진 경계 | **Xdet.Engine.Contract + PythonNet 3.0.5** | typed DTO, 직렬 엔진 호출, Python golden 위임 |
| 영상 렌더 | WPF bitmap/visual transform 경로 | float32 원본 보존, 표시 시 W/L 매핑, 줌/팬/overlay |
| 곡선·지표 | **ScottPlot.WPF 5.1.59** | 엔진 반환 axes/series/scalars 렌더 |
| 시험 | xUnit + Python regression/import-linter + Windows UI Automation | contract→integration→ViewModel→UIA 계층 검증 |

초기 napari/PySide6 비교 연구는 역사적 후보 평가로만 보존되며 현재 구현 선택을 재개방하지 않는다.

### 2.2 라이선스 제약

- WPF 배포물은 Qt/napari/PyQt를 참조하지 않는다.
- NuGet과 Python 런타임 의존성 모두 허용 라이선스 목록으로 검사하며 GPL-only 의존성은 허용하지 않는다(C-13).

### 2.3 스파이크 게이트 (구현 착수 전 1일 검증, 미충족 시 폴백 전환)

WPF spike는 다음 3건을 실측한다.

- **SG-1:** hover probe가 표시용 byte가 아닌 DTO의 float32 원값을 반환한다.
- **SG-2:** 3072×3072에서 W/L 조작 응답 p95 100ms 이내, 최대 200ms 이내이며 조작마다 전체 float 배열을 복사하지 않는다.
- **SG-3:** cold start 10s, C-18 memory, C-19 UI responsiveness/cancel 기준을 함께 측정한다.

## 3. 품질 기준 카탈로그 (C-01 ~ C-21)

SPEC-VIEWER-001의 인수 기준은 아래를 인용해 작성한다. 측정과 판정 분리 원칙(EV 준용): 수치는 여기서 정의하고 SPEC은 번호로 인용.

### 영상 상호작용

- **C-01 W/L**: float32 전체 범위에 대해 contrast limits 조정 + 정확한 수치 직접 입력 가능. 3072×3072 기준 프레임 100회 조작에서 표시 갱신 p95 100ms 이내, 최대 200ms 이내.
- **C-02 줌/팬**: 드래그 팬·휠 줌이 연속적으로 상호작용 가능하고 이벤트당 원본 float 프레임 재계산·배열 복사가 없어야 한다(캐시된 bitmap/visual transform 경로).
- **C-03 픽셀 프로브**: 호버 시 정수 픽셀 좌표 + 해당 위치 모든 가시 레이어의 **저장된 float32 원값**(표시용 8-bit 값 아님) 표기.
- **C-04 무손실 표시 원칙**: 뷰어는 파이프라인의 float32 배열을 무변형 수신. 8-bit 매핑은 렌더 경로에서만 발생.

### 비교·마스크

- **C-05 전/후 비교**: 줌/팬/W/L 연동된 나란히 보기 + 블링크 모드(단일 키 레이어 가시성 토글).
- **C-06 diff 뷰**: 부호 있는 차(after−before)를 0 중심 대칭 diverging 컬러맵으로 렌더. 기본 범위 ±max|diff|, 사용자 조정 가능. diff 위 프로브는 부호 있는 float 값 표시.
- **C-07 마스크 오버레이**: XFrame 마스크 스택(DEFECT/SATURATION/INTERPOLATION/SATURATION_BAND, `common/xframe.py:61-73`)의 각 플래그가 독립 오버레이 — 고유 색·불투명도 슬라이더·가시성 토글. 모든 줌 레벨에서 픽셀 정렬.
- **C-08 처리 이력 표시**: 로드된 XFrame의 history 체인(module_name/version/params_hash/calibset_id)을 그대로 표시 — 오케스트레이터 경로 검증 수단.

### 지표

- **C-09 지표 계산 위임**: MTF/NPS/DQE 및 검증에 사용하는 곡선·히스토그램·벡터장은 engine DTO 결과만 사용한다. **UI/adapter 자체 DSP·지표·판정 계산 0**이며 플롯 배열은 엔진 결과와 동일해야 한다. W/L 보조 histogram을 UI에서 그릴 경우 표시 전용으로 명시하고 report/export/판정에는 사용할 수 없다.
- **C-10 ROI 왕복 재현**: 지표용 ROI 선택 시 사용된 정확한 경계를 표기하고, 동일 경계를 하네스에 투입하면 동일 지표 값 재현(round-trip 테스트).

### 아키텍처·설치

- **C-11 의존 방향**: WPF → `Xdet.Engine.Contract` → `Xdet.Engine.PythonNet` → Python golden 단방향이다. 모든 WPF Python 실행은 typed `IXdetEngine` DTO를 통과하고 Python `apps.gui` helper 직접 의존은 0이어야 한다. Python core는 UI를 import하지 않으며 import-linter 카나리로 검증한다.
- **C-12 런타임 격리**: WPF 앱은 Qt/napari 없이 빌드·시험되어야 하고 Python base/core 회귀도 GUI extras 없이 통과해야 한다.
- **C-13 라이선스**: NuGet/Python 의존성에서 GPL-only 0. 허용 목록 CI 게이트를 사용한다.

### 테스트 (CI, 디스플레이 서버 없음)

- **C-14 자동화 계층**: CI는 .NET contract/xUnit, PythonNet integration, WPF ViewModel test, Windows UI Automation을 분리한다. Python 알고리즘 회귀와 import-linter는 `uv run`으로 별도 실행한다.
- **C-15 로직 레벨 커버리지**: raw+JSON 로드, typed pipeline/sequence/metric 호출, before/after/diff/mask, W/L/probe, job phase/cancel/late-result suppression, artifact/run-manifest round-trip을 커버한다. 화면 픽셀 단정은 UIA smoke와 구조/상태 증거를 우선한다.
- **C-16 결정론**: 동일 fixture 입력+params → diff 레이어 배열·표시 지표 배열이 실행 간 bit-동일(파이프라인 순수성 상속, GUI 코드 경로 통과로 검증).

### 자원 한도

- **C-17 기동**: 새 프로세스 5회 각각 콜드 런치부터 상호작용 가능까지 10s 이내. 측정 환경과 캐시 상태를 기록한다.
- **C-18 메모리**: 전/후 1쌍 + diff + `uint8` 마스크 3장 로드 시 peak RSS 2GiB 이하. full-frame LRU `K=8`, thumbnail LRU `K=256`으로 상한을 고정하고 50프레임 두 번째 순회 뒤 RSS 증가가 64MiB 이하여야 한다.
- **C-19 응답성**: 파이프라인 실행 등 장시간 작업은 GUI 스레드 밖에서 실행한다. 50ms heartbeat의 이벤트 루프 최대 공백 200ms 이하, 취소 후 Canceled 표시 250ms 이하, 늦은 결과 commit 0을 만족해야 한다.

### 범위 가드

- **C-20 읽기-실행 전용**: GUI는 `data/` 골든 fixture·CalibSet 파일을 절대 쓰지 않음. 모든 내보내기는 사용자 지정 출력 디렉터리로만.

### 다단계 조합 검증

- **C-21 다단계 조합 검증**: 검증기는 각 보정/처리 스테이지를 **개별로** — 각 스테이지 고유의 구별되는 CalibSet 입력과 Params로 — 적용해 그 스테이지의 스테이지별 입력/출력/diff/마스크 결과를 표시할 수 있어야 하고, 개별 스테이지가 확인된 뒤에는 선택한 정렬된 부분집합 또는 전체 파이프라인을 적용해 조합 출력을 각 스테이지의 전/후와 함께 표시해야 한다. 순서/조합은 전적으로 `pipeline.orchestrator`에 위임한다(고정 `CANONICAL_ORDER` SWR-000-2; 무단 기본 캘리브레이션 대체 금지 SWR-000-5). UI는 DSP를 스스로 계산하지 않고(C-09), 코어를 단방향 소비하며(C-11), 골든 데이터를 쓰지 않는다 — 내보내기는 사용자 지정 디렉터리로만(C-20). (C# 검증 GUI가 인용: SPEC-XSEAM-002 — Python 뷰어 REQ-VIEW-RUN-1(개별)/RUN-2(부분/전체)의 심 경유 미러.)

## 4. 선행 코드 개선 의존성

리서치에서 검증된 갭과 GUI Phase의 의존 관계:

| 이슈 | 내용 | 구분 | 필요 시점 |
|---|---|---|---|
| 순서 | 선행 결과 | 정본 |
|---|---|---|
| 1 | 9-family typed request/result, generic pipeline/sequence/session/tier, typed error | SPEC-XSEAM-002 v0.5.1 |
| 2 | `AlgorithmCatalogManifest`, availability/evidence 분리, selector-dependent Params validation | SPEC-XGUI-MASTER v0.5.1 |
| 3 | `RunCoordinator`의 run_id/직렬 실행/soft cancel/late-result suppression | SPEC-XGUI-MASTER JOB |
| 4 | `xdet.frame-artifact/1.0`, mask bitfield, `xdet.run-manifest/1.0`, C-20 | foundation §3 |
| 5 | shared shell 후 그룹별 탭 순차 구현 | master plan M1~M3 |
| 6 | 중앙 TC를 PLANNED에서 실제 자동화 상태로 승격 | `docs/XDET_TestSpec_v1.0.md` |

Python golden 4계층은 동결한다. 새 GUI 기능을 이유로 알고리즘이나 `apps/gui` helper를 변경·복제하지 않는다.

## 5. SPEC 작성 시 준수 사항 (과거 plan-audit 이력 반영)

- XDET-TC-NNN 표기 통일 (bare TC-NNN 금지)
- EARS 라벨 1개당 요구 1개(복합 금지), 뒤따르는 비양태 문장 금지
- 결정론 규칙에 "또는" 금지 — 고정 폴백 순서 명시
- 모든 REQ ID ↔ AC 양방향 추적, 산출물 WHEN 트리거에는 생산자 REQ 존재
- 규범 REQ 본문에 파일/클래스 식별자(HOW) 금지 — plan.md/괄호로 이동
- 자동 검출 가능 범위와 코드리뷰 설계 규칙을 분리 (과잉 약속 금지)
- frontmatter 8필드(id/version/status/created/updated/author/priority/issue_number), 시간 예측 금지(Priority 라벨)

---

Version: 1.3.0
작성: 2026-07-10, WPF v0.5.1 문서 기준선 개정: 2026-07-13
다음 단계: G0 내부 검토와 사용자 승인·기준선 동결 이후에만 M1 공통 셸 구현에 진입
