# SPEC-VIEWER-001 — 인수 기준 (Acceptance Criteria)

DoD: **검증 GUI를 단계형(Phase 0→0.5→1→2)으로 성립** — Phase 0 스파이크로 스택 확정, Phase 0.5 선행 코어 갭(계약 KEPT), Phase 1 단위 모듈 검증기, Phase 2 파이프라인 비교 뷰어. 모든 기준은 관측 가능(테스트 출력·산출 레이어/구조·오류/거부 발생·배열 일치·CI 잡 통과/실패)해야 한다. **`[T]` 임계 수치는 설정 외부화**(하드코딩 아님)이며 스파이크(SG-3)·구조 게이트로 처리한다. GUI는 **읽기-실행 전용**(C-20)·**지표 자체 계산 0**(C-09)이며 코어 4계층 계약(SWR-000-6~12)·`CANONICAL_ORDER`를 변경하지 않는다. TC는 신규 블록 **XDET-TC-030~037**(Gen 1 XDET-TC-000~021 범위 밖).

## 자동 검출 vs 코드리뷰 설계 규칙 (과잉 약속 방지)

- **자동 검출(인수 기준 = 테스트/CI 게이트)**: 로더 XFrame 생성(#16)·레지스트리 집합 반환(#15)·합성 CalibSet 대체(#18)·선행 갭 additive 후 코어 계약·`CANONICAL_ORDER`·import-linter 전건 KEPT(CORE-4, Scenario 2(d) — 계약 서명·import-linter 실행으로 자동 검출)·W/L 수치 적용·프로브 저장 float32 값 일치·diff/마스크 레이어 생성·플롯 값=엔진 출력 배열 일치(C-09)·ROI round-trip 값 일치(C-10)·import-linter forbidden + 카나리 실패(C-11)·`[gui]`-less 코어 TC 통과(C-12)·pip-licenses 게이트(C-13)·offscreen 실행(C-14/15)·결정론 bit-동일(C-16)·`data/` 해시 불변(C-20)·스파이크 리포트 산출(SPIKE-1: `.moai/reports/SPEC-VIEWER-001-spike.md` 존재 + SG-1~3 필수 필드 — 파일/필드 존재는 자동 검출)·SG-1 프로브 원값 로직(저장 float32 값 일치 — 로직 레벨 자동 검출).
- **코드리뷰 설계 규칙(테스트 단정 아님)**: GUI 코드에 지표 산출 로직 부재(C-09의 "계산 0"은 배열 일치로 발산을 잡되 코드 경로 부재는 리뷰)·Phase 게이트 순서(SPIKE-3: 스파이크 미완 중 Phase 1 착수 금지 — 워크플로/마일스톤 게이트 리뷰 규칙, 자동 이진 판정 아님)·마스크 오버레이 시각 정렬(C-07 픽셀 정렬은 레이어 변환 동일성으로 근사, 전 줌 레벨 시각은 리뷰)·줌/팬 체감 연속성(C-02 성능, 단정 아님)·W/L·줌/팬 무복사 경로(IMAGE-2: 이벤트당 전체 프레임 배열 복사 부재는 프로파일러 확인 + 리뷰, 자동 이진 단정 아님)·자원·응답 `[T]` 절대값(C-01 100ms(SG-2)·C-17 10s(SG-3)는 스파이크 실측 + `[T]` 설정 — C-17과 동일 처리로 대칭화, C-18 2GB·C-19 200ms는 구조 게이트 + `[T]` 설정, 하드 수치 단정 아님).

## Given-When-Then 시나리오

### Scenario 1 — Phase 0 스파이크 · 결정론적 폴백 · 게이트 순서 (REQ-VIEW-SPIKE-1, -2, -3)
- **Given** 3072×3072 float32 합성 프레임과 napari 후보 스택이 주어져 있다.
- **When** Phase 0 스파이크가 SG-1(호버 float32 원값 노출)·SG-2(W/L 조작 응답)·SG-3(콜드 스타트→상호작용 가능)을 실측한다.
- **Then** (a) 세 게이트 실측값을 담은 스파이크 리포트가 산출되고(SG-1~3, 응답·시간 임계는 `[T]` 설정), (b) 리포트에서 SG-1·SG-2·SG-3 중 하나라도 미충족이면 구현 스택이 pyqtgraph 폴백으로 전환되며(napari→pyqtgraph 단일 순서, 택일 없음), (c) 스파이크가 미완인 동안 Phase 1 구현 착수가 진행되지 않는다(선행 게이트).

### Scenario 2 — Phase 0.5 선행 코어 갭 · additive 계약 보존 (REQ-VIEW-CORE-1, -2, -3, -4)
- **Given** raw 16-bit 프레임 + 메타데이터 JSON 임시 파일, 모듈 목록 질의, 실측 CalibSet 부재 상태가 주어져 있다.
- **When** 프레임 로더·모듈 레지스트리·합성 CalibSet 팩토리가 실행된다.
- **Then** (a) 로더가 float32 XFrame을 생성하고(#16, C-04 무손실), (b) 레지스트리가 기본 등록 모듈 집합을 반환하며(#15), (c) 실측 CalibSet 부재 시 합성 CalibSet 팩토리가 대체 CalibSet을 제공하고(#18), (d) 이 additive 확장 후에도 기존 `process(XFrame,CalibSet,Params)->XFrame` 시그니처·`CANONICAL_ORDER`·기존 import-linter 계약이 전건 불변(KEPT)이다(SWR-000-6~12).

### Scenario 3 — Phase 1 영상 상호작용: W/L · 줌/팬 · 프로브 · 무손실 (REQ-VIEW-IMAGE-1, -2, -3, -4)
- **Given** 로드된 float32 XFrame이 뷰어에 표시되어 있다.
- **When** 사용자가 W/L을 조정(또는 수치 직접 입력)하고, 드래그 팬·휠 줌을 하고, 픽셀 위를 호버한다.
- **Then** (a) 뷰어가 float32 전체 범위에 대해 표시를 갱신하고(C-01, 응답 `[T]` 100ms), (b) 이벤트당 전체 프레임 재계산·배열 복사 없이 연속 상호작용을 제공하며(C-02, GPU/픽스맵 경로), (c) 정수 픽셀 좌표와 모든 가시 레이어의 저장된 float32 원값을 표시하고(C-03, 8-bit 값 아님), (d) 파이프라인 float32 배열을 무변형 수신하고 8-bit 매핑은 렌더 경로에서만 발생한다(C-04).

### Scenario 4 — Phase 1 비교·마스크·이력: 전/후 · diff · 마스크 오버레이 (REQ-VIEW-COMPARE-1, -2, -3, -4, -5, -6)
- **Given** fixture/raw 입력을 `ProcessModule.process`로 실행한 입력·출력 XFrame 쌍(REQ-VIEW-RUN-1 산출)과 MaskFlag 스택이 주어져 있다.
- **When** 뷰어가 전/후 쌍·diff·마스크를 표시하고 사용자가 블링크 토글과 diff 호버를 수행한다.
- **Then** (a) 줌·팬·W/L 연동 나란히 보기(C-05)와 단일 키 블링크 토글(C-05)이 제공되고, (b) 부호 있는 차(after−before)가 0 중심 대칭 diverging 컬러맵으로 렌더되며(C-06, 기본 범위 `[T]` ±max|diff|), (c) diff 호버 시 부호 있는 float 차값이 표시되고(C-06), (d) 각 마스크 플래그(DEFECT/SATURATION/INTERPOLATION/SATURATION_BAND)가 고유 색·불투명도·가시성 토글의 독립 오버레이로 렌더되며(C-07), (e) 마스크 오버레이가 모든 줌 레벨에서 기저 픽셀과 정렬된다(C-07 픽셀 정렬).

### Scenario 5 — Phase 1 실행 · 지표 위임 · ROI round-trip (REQ-VIEW-RUN-1, -3, -4, -5, -6)
- **Given** fixture/raw 입력과 처리 모듈 1개, 지표 계산용 ROI가 주어져 있다.
- **When** 사용자가 모듈을 실행하고 지표 플롯을 요청하며 ROI를 선택한다.
- **Then** (a) 모듈이 `ProcessModule.process`로 직접 실행되어 입력·출력 XFrame이 산출되고(REQ-VIEW-RUN-1, raw·fixture 공통 유일 산출 경로; expected 골든이 동봉된 fixture-verification 모드에서는 `run_harness`의 `MismatchReport`가 검증으로 병행 표시되며 이 하네스는 출력 프레임을 산출하지 않음 — C-05/06/07 생산), (b) 지표 플롯이 기존 `metrics/` 엔진 호출 결과만 사용하고 플롯 값이 엔진 출력과 배열 단위로 일치하며(C-09), (c) GUI 코드 경로가 지표를 계산하지 않고 엔진에 위임하고(C-09 계산 0), (d) 사용된 ROI 경계가 표기되며(C-10), (e) 동일 ROI 경계를 지표 재계산 경로에 투입하면 표시 지표 값과 재계산 값이 일치한다(C-10 round-trip).

### Scenario 6 — Phase 2 파이프라인 비교 뷰어 · 결정론 (REQ-VIEW-RUN-2, REQ-VIEW-ARCH-7)
- **Given** raw + 합성 CalibSet 입력과 `CANONICAL_ORDER` 부분/전체 실행 요청이 주어져 있다.
- **When** 파이프라인이 `run_pipeline`로 실행되고 동일 입력·동일 params로 재실행된다.
- **Then** (a) 스테이지별 전/후 XFrame이 산출되어 비교로 표시되고(REQ-VIEW-RUN-2, C-05 스테이지별 전/후), (b) GUI 코드 경로를 통과한 diff 레이어 배열과 표시 지표 배열이 실행 간 bit-동일하다(C-16 결정론, 파이프라인 순수성 상속).

### Scenario 7 — 읽기-실행 전용: 내보내기 · data/ 거부 (REQ-VIEW-RUN-7, -8)
- **Given** 사용자 지정 출력 디렉터리와 `data/` 골든 fixture·CalibSet이 주어져 있다.
- **When** 사용자가 내보내기를 요청하고, 별도로 어떤 GUI 동작이 `data/` 하위 파일 쓰기를 시도한다.
- **Then** (a) 내보내기 산출물이 사용자 지정 출력 디렉터리로만 쓰이고(C-20, #17 축소판), (b) `data/` 하위 파일 쓰기 시도가 거부되며(C-20, 단일 결정론 경로), (c) 전체 로드+실행 사이클 후 `data/` fixture·CalibSet 파일 해시가 불변이다.

### Scenario 8 — 아키텍처·설치·라이선스 (REQ-VIEW-ARCH-1, -2, -3, -4)
- **Given** `apps/gui`가 코어 4계층을 소비하는 구성, `[gui]`-less base 설치, 의존성 라이선스 집합이 주어져 있다.
- **When** import-linter·`core-no-gui` 잡·`pip-licenses` 게이트가 CI에서 실행된다.
- **Then** (a) `apps/gui`→코어 단방향이 유지되고 코어 4계층이 `apps.gui`를 import하지 않으며(C-11 forbidden), (b) `apps.gui`로의 의도적 위반을 카나리로 심으면 forbidden 계약이 실제로 실패하고(C-11 카나리, lesson #1 헛통과 방지), (c) `[gui]` extras 없이 설치한 base에서 전체 코어 TC가 통과하며(C-12), (d) allowlist 외 GPL-only 라이선스(PyQt6 포함)가 존재하면 라이선스 게이트가 실패한다(C-13).

### Scenario 9 — 헤드리스 · 로직 커버리지 · 자원 (REQ-VIEW-ARCH-5, -6, -8, -9)
- **Given** `QT_QPA_PLATFORM=offscreen` CI 컨텍스트, 다중 프레임 로드, 장시간 파이프라인 작업이 주어져 있다.
- **When** GUI 테스트가 오프스크린으로 실행되고 다중 프레임이 로드되며 장시간 작업이 트리거된다.
- **Then** (a) 모든 GUI CI 테스트가 오프스크린으로 실행되고(C-14, xvfb 불요), (b) 파일 로드·하네스 호출·레이어 생성·W/L 수치 적용·프로브 값 정확성이 로직 레벨로 검증되며(C-15, `make_napari_viewer`/qtbot; 픽셀 그랩 시각 단정 제외), (c) 장시간 작업이 GUI 스레드 밖에서 실행되고 진행 표시·취소가 제공되며(C-19, 이벤트 루프 블로킹 `[T]` 200ms 초과 금지), (d) 다중 프레임 로드가 명시적 LRU K프레임(`[T]`) 상한으로 제한되어 무한 증가하지 않는다(C-18).

### Scenario 10 — 처리 이력 표시 (조건부) (REQ-VIEW-COMPARE-7)
- **Given** 처리 이력(history) 체인이 있는 XFrame과 이력이 없는(빈 체인) XFrame이 각각 주어져 있다.
- **When** 뷰어가 각 XFrame을 로드한다.
- **Then** WHERE 로드된 XFrame이 history 체인을 가지면 그 체인(module_name/version/params_hash/calibset_id)을 표시하고(C-08, 오케스트레이터 경로 검증), history가 없으면 표시하지 않는다.

## Edge Cases (부정/경계 케이스)

### EC-1 — 스파이크 미충족 → pyqtgraph 폴백 (REQ-VIEW-SPIKE-2)
- **Given** SG-1·SG-2·SG-3 중 하나 이상이 미충족인 스파이크 리포트.
- **When** 폴백 결정이 리포트를 소비한다.
- **Then** 구현 스택이 pyqtgraph 폴백으로 전환된다(napari→pyqtgraph 단일 순서 — 비결정적 택일·"또는" 없음).

### EC-2 — import-linter 의도적 위반 카나리 (REQ-VIEW-ARCH-2)
- **Given** `tests/fixtures/badgui/`(`pyproject` `root_packages` 밖) 전용 픽스처 패키지에 코어→`apps.gui` 방향 위반이 심어져 있고, 그 패키지를 대상으로 하는 임시 import-linter forbidden 설정이 준비되어 있다(프로덕션 원본 트리 무변경; `tests/fixtures/badlayers/`·`test_tc000_B` 음성대조 선례).
- **When** 그 임시 설정으로 import-linter(`lint-imports --config <tmp>`)가 실행된다.
- **Then** 린터가 실제로 실행되어 심은 위반을 검출하고 실패한다(`returncode≠0` + 위반 출력 비어있지 않음 — lesson #1 헛통과 아님을 assert). import-linter는 `root_packages` 트리만 그래프에 올리므로 실계약(코어→`apps.gui` forbidden)은 무변경으로 유지된다.

### EC-3 — GPL-only 의존성 → 라이선스 게이트 실패 (REQ-VIEW-ARCH-4)
- **Given** allowlist 외 GPL-only 라이선스(예: PyQt6)를 가진 의존성.
- **When** `pip-licenses` allowlist 게이트가 실행된다.
- **Then** 게이트가 실패한다(PyQt6 명시 배제, C-13).

### EC-4 — data/ 쓰기 시도 거부 (REQ-VIEW-RUN-8)
- **Given** `data/` 하위 골든 fixture·CalibSet 파일 쓰기를 시도하는 GUI 동작.
- **When** 그 동작이 실행된다.
- **Then** 쓰기가 거부되고 로드+실행 사이클 후 `data/` 파일 해시가 불변이다(C-20 읽기-실행 전용, 단일 결정론 경로).

### EC-5 — 실측 CalibSet 부재 → 합성 팩토리 대체 (REQ-VIEW-CORE-3)
- **Given** raw 입력 경로 + 실측 CalibSet 부재.
- **When** 파이프라인/모듈 실행이 CalibSet을 요구한다.
- **Then** 배포 가능한 합성 CalibSet 팩토리가 대체 CalibSet을 제공한다(#18; 무단 기본값 대체가 아니라 명시적 합성 팩토리 경로).

### EC-6 — 지표 GUI 재계산 발산 검출 (REQ-VIEW-RUN-4)
- **Given** 동일 입력에 대한 GUI 플롯 값과 `metrics/` 엔진 직접 호출 값.
- **When** 두 배열을 비교한다.
- **Then** 배열이 단위별로 일치한다(C-09; 불일치 시 GUI가 자체 계산했음을 의미하므로 실패 — 계산 0 위반 검출).

## PARTIAL (구조 성립 · `[T]` 설정 · 시각/성능 이연)

### 자원 `[T]` 절대 임계 (REQ-VIEW-ARCH-8, -9, C-17/C-18/C-19)
- 콜드 스타트 10s(C-17)는 스파이크(SG-3)에서 실측하고, RSS 2GB(C-18)·이벤트 루프 200ms(C-19)는 구조 게이트 + `[T]` 설정 외부화로 처리한다. P1은 구조(LRU 상한·스레드 밖 실행·진행/취소)를 성립시키며 하드 절대 수치를 CI 단정으로 고정하지 않는다.

### 시각 정렬·체감 성능 (REQ-VIEW-COMPARE-6, REQ-VIEW-IMAGE-2, C-02/C-07/C-15)
- 마스크 오버레이 전 줌 레벨 시각 정렬(C-07)·줌/팬 체감 연속성(C-02)·픽셀 그랩 스크린샷 시각 비교(C-15)는 코드리뷰 설계 규칙이며 Windows CI 자동 단정에서 제외한다(로직 레벨 근사 검증만). Linux xvfb 픽셀 그랩 잡은 본 SPEC 범위에 두지 않음(후속 별건 가능, 「결정 필요/확인 사항」 6).

## 품질 게이트 / Definition of Done

- [x] Phase 0 스파이크: SG-1(호버 float32 원값)·SG-2(W/L 응답)·SG-3(콜드 스타트) 실측 리포트 산출 완료(SPIKE-1, Scenario 1, XDET-TC-030) — `.moai/reports/SPEC-VIEWER-001-spike.md`
- [x] Phase 0 폴백: SG 미충족 시 pyqtgraph 폴백 단일 순서 전환 완료(SPIKE-2, Scenario 1, EC-1) — napari SG-3 하드 실패로 pyqtgraph 확정
- [ ] Phase 게이트 순서: 스파이크 미완 동안 Phase 1 착수 금지(SPIKE-3, Scenario 1)
- [ ] Phase 0.5 로더: raw 16-bit+JSON → float32 XFrame 생성(CORE-1, Scenario 2, XDET-TC-031)
- [ ] Phase 0.5 레지스트리: 기본 등록 모듈 집합 반환(CORE-2, Scenario 2)
- [ ] Phase 0.5 합성 CalibSet: 실측 부재 시 대체 팩토리 제공(CORE-3, Scenario 2, EC-5)
- [ ] Phase 0.5 계약 보존: `process` 시그니처·`CANONICAL_ORDER`·기존 import-linter 계약 전건 KEPT(CORE-4, Scenario 2)
- [ ] W/L 조정·수치 입력 → float32 전체 범위 표시 갱신(IMAGE-1, Scenario 3, C-01)
- [ ] 줌/팬 무복사 연속 상호작용(IMAGE-2, Scenario 3, C-02)
- [ ] 호버 프로브: 정수 좌표 + 저장 float32 원값(IMAGE-3, Scenario 3, C-03)
- [ ] 무손실 수신 + 8-bit 매핑 렌더 경로 국한(IMAGE-4, Scenario 3, C-04)
- [ ] 전/후 연동 나란히 보기(COMPARE-1, Scenario 4, C-05) + 블링크 토글(COMPARE-2, Scenario 4, C-05)
- [ ] diff 0 중심 diverging 렌더(COMPARE-3, Scenario 4, C-06) + diff 부호 float 프로브(COMPARE-4, Scenario 4, C-06)
- [ ] 마스크 4종 독립 오버레이(COMPARE-5, Scenario 4, C-07) + 픽셀 정렬(COMPARE-6, Scenario 4, C-07)
- [ ] 처리 이력 표시(WHERE history 존재) / 부재 시 미표시(COMPARE-7, Scenario 10, C-08)
- [ ] 모듈 `ProcessModule.process` 실행 → 입력/출력 XFrame 산출(+ expected 동봉 fixture 시 `run_harness` MismatchReport 검증 병행)(RUN-1, Scenario 5, XDET-TC-033)
- [ ] 파이프라인 `run_pipeline` 부분/전체 → 스테이지별 전/후(RUN-2, Scenario 6, XDET-TC-035)
- [ ] 지표 플롯 = `metrics/` 엔진 출력 배열 일치(RUN-3, Scenario 5, C-09, XDET-TC-034)
- [ ] 지표 GUI 계산 0 — 엔진 위임(RUN-4, Scenario 5, EC-6, C-09)
- [ ] ROI 경계 표기(RUN-5, Scenario 5, C-10) + ROI round-trip 값 일치(RUN-6, Scenario 5, C-10)
- [ ] 내보내기 사용자 지정 디렉터리 국한(RUN-7, Scenario 7, C-20) + data/ 쓰기 거부(RUN-8, Scenario 7, EC-4, C-20)
- [ ] import 단방향 유지(ARCH-1, Scenario 8, C-11) + 의도적 위반 카나리 실패(ARCH-2, Scenario 8, EC-2, C-11)
- [ ] `[gui]`-less base 코어 TC 통과 — core-no-gui 잡은 `pytest --ignore=tests/apps`로 GUI 테스트를 수집에서 배제(ARCH-3, Scenario 8, C-12, XDET-TC-036)
- [ ] GPL-only 라이선스 게이트 실패(ARCH-4, Scenario 8, EC-3, C-13)
- [ ] 오프스크린 실행(ARCH-5, Scenario 9, C-14) + 로직 레벨 커버리지(ARCH-6, Scenario 9, C-15, XDET-TC-037)
- [ ] 결정론 bit-동일(ARCH-7, Scenario 6, C-16)
- [ ] 장시간 작업 스레드 밖 + 진행/취소(ARCH-8, Scenario 9, C-19) + 다중 프레임 LRU 상한(ARCH-9, Scenario 9, C-18)
- [ ] 자원 `[T]` 임계 하드코딩 0 — 설정 외부화 · 픽셀 그랩 Windows CI 제외(PARTIAL, C-17/18/19/15)
- [ ] TC 블록 XDET-TC-030~037 등록 · Gen 1(000~021) 범위·캡스톤 스캔 무간섭 · GUI 테스트 소스 Gen 1 TC id(000~021) 문자열 미포함(「결정 필요/확인 사항」 5, D9)
- [ ] **단계형 Phase 0→0.5→1→2 순차 게이트 성립 PASS** — Phase 1 CI 통과가 Phase 2 착수 선행 게이트 — DoD
