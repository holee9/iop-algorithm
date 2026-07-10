# GUI 기준 문서 — 검증 GUI 품질 기준 및 기술 결정 (v1.0)

> 이 문서는 `docs/GUI_REVIEW.md`(검토 메모, 이슈 #14)의 후속으로, **SPEC-VIEWER-001 작성에 앞서 딥리서치로 확정한 기준의 단일 출처**다. SPEC은 이 문서의 기준 번호(C-NN)를 인용하며, 기준 수치 중 `[T]` 표기는 튜닝 항목으로 Params/설정에 외부화한다.
>
> 리서치 방법: (1) 코드베이스 정밀 인벤토리(계약면·모듈·지표 API·fixture·패키징·과거 plan-audit 이력), (2) 후보 프레임워크 6종 웹 딥리서치(2026-07 기준 릴리스/라이선스/유지보수 상태를 PyPI·공식 문서로 검증).

관련 이슈: #14 (검토), #15~#19 (리서치 중 발견한 코드 개선)

---

## 1. 범위 결정

**옵션 C(A+B 통합)를 단계형으로 채택한다** — GUI_REVIEW §4의 옵션 중, 사용자 목표가 "사용 + 검증" 양쪽이므로:

- **Phase 1 (= 옵션 A)**: 단위 모듈 검증기 — fixture/raw 입력 → 모듈 1개 실행 → 입력/출력/마스크/diff 시각화. `run_harness`(`common/contract.py:131`) 직결.
- **Phase 2 (= 옵션 B)**: 파이프라인 비교 뷰어 — raw+CalibSet → `CANONICAL_ORDER` 부분/전체 실행 → 스테이지별 전/후 + 지표(MTF/NPS/DQE).
- Phase 1이 CI 통과 + 기준 충족으로 완료된 뒤에만 Phase 2 착수. 하나의 앱(탭/도크 전환), 하나의 SPEC(SPEC-VIEWER-001)에서 Phase를 마일스톤으로 구분.

운영 형태는 GUI_REVIEW §4.5 확정대로 `apps/gui/` 서브 프로젝트 + `[gui]` optional extras.

## 2. 기술 스택 결정

### 2.1 결론

| 구분 | 선택 | 근거 요약 |
|---|---|---|
| **1순위** | **napari** (라이브러리/임베디드 모드) + magicgui 도크 위젯, Qt 바인딩은 **PySide6** | float32 contrast limits(W/L)·GPU 줌/팬·레이어 기반 마스크 오버레이·블링크·호버 값 표시가 **내장**. `make_napari_viewer` + pytest-qt + `QT_QPA_PLATFORM=offscreen` 헤드리스 CI 문서화. BSD-3, v0.7.1(2026-06) 활발 |
| **폴백** | **PySide6 + pyqtgraph** | `ImageView`가 히스토그램 영역 기반 W/L·LUT·ROI 내장(MIT, v0.14.0 2025-11). 앱 셸(도킹/파일선택/스레딩)을 직접 구현하는 비용이 대가. Qt+pytest-qt 공유로 피벗 비용 낮음 |
| **기각** | Streamlit | rerun 실행 모델이 상태형 뷰어와 충돌, 네이티브 W/L 부재, 매 조작마다 18MB 프레임 8-bit 재인코딩, streamlit-image-comparison 3년 방치(v0.0.4, 2023-03) |
| **기각** | Panel/HoloViews | 줌/팬마다 서버 재래스터화 라운드트립, 가파른 학습곡선 — 이 프로젝트에 없는 배포 문제를 푸는 스택 |
| **기각** | Jupyter/stackview | 기능 적합성은 근접하나 alpha 성숙도·단일 유지자·노트북 종속·CI 취약. 탐색 보조 도구로는 병용 가능 |
| **기각** | Dear PyGui / NiceGUI | 과학 영상 위젯(W/L 히스토그램) 부재, 전부 수제작 필요 |

가중 매트릭스(영상 상호작용 0.30 / 지표 플롯 0.15 / 개발속도 0.15 / CI 시험성 0.15 / 의존성 0.10 / 유지보수 0.15): napari 4.23, pyqtgraph 4.28로 사실상 동률 — 실효 개발속도("뷰어의 80%를 빌려 씀")로 napari를 1순위로 확정. (주: 매트릭스 점수는 정성 평가의 상대 서열 보조 수단이며 소수점 정밀도에 판정 의미를 두지 않는다 — 동률 판정 후 정성 근거로 확정했다.)

### 2.2 라이선스 제약

- **PyQt6 배제** (GPL/상용). napari Qt 백엔드는 PySide6(LGPL) 지정.
- 의존성 전체에 GPL-only 부재를 CI에서 `pip-licenses` allowlist로 게이트 (기준 C-13).

### 2.3 스파이크 게이트 (구현 착수 전 1일 검증, 미충족 시 폴백 전환)

웹 리서치로 확정 불가능해 실측이 필요한 3건 — SPEC의 Phase 0(스파이크)로 편성:

- **SG-1**: napari 호버 픽셀 프로브가 표시값(8-bit)이 아닌 **저장된 float32 원값**을 노출하는지
- **SG-2**: 3072×3072 float32에서 W/L 조작 응답 100ms `[T]` 이내인지
- **SG-3**: 콜드 스타트 → 상호작용 가능까지 10s `[T]` 이내인지 (크게 초과 시 pyqtgraph 폴백 트리거)

## 3. 품질 기준 카탈로그 (C-01 ~ C-20)

SPEC-VIEWER-001의 인수 기준은 아래를 인용해 작성한다. 측정과 판정 분리 원칙(EV 준용): 수치는 여기서 정의하고 SPEC은 번호로 인용.

### 영상 상호작용

- **C-01 W/L**: float32 전체 범위에 대해 contrast limits 조정 + 정확한 수치 직접 입력 가능. 3072×3072 기준 프레임에서 조정당 표시 갱신 100ms `[T]` 이내.
- **C-02 줌/팬**: 드래그 팬·휠 줌이 연속적으로 상호작용 가능(이벤트당 전체 프레임 재계산/배열 복사 없음 — GPU/픽스맵 경로).
- **C-03 픽셀 프로브**: 호버 시 정수 픽셀 좌표 + 해당 위치 모든 가시 레이어의 **저장된 float32 원값**(표시용 8-bit 값 아님) 표기.
- **C-04 무손실 표시 원칙**: 뷰어는 파이프라인의 float32 배열을 무변형 수신. 8-bit 매핑은 렌더 경로에서만 발생.

### 비교·마스크

- **C-05 전/후 비교**: 줌/팬/W/L 연동된 나란히 보기 + 블링크 모드(단일 키 레이어 가시성 토글).
- **C-06 diff 뷰**: 부호 있는 차(after−before)를 0 중심 대칭 diverging 컬러맵으로 렌더. 기본 범위 ±max|diff|, 사용자 조정 가능. diff 위 프로브는 부호 있는 float 값 표시.
- **C-07 마스크 오버레이**: XFrame 마스크 스택(DEFECT/SATURATION/INTERPOLATION/SATURATION_BAND, `common/xframe.py:61-73`)의 각 플래그가 독립 오버레이 — 고유 색·불투명도 슬라이더·가시성 토글. 모든 줌 레벨에서 픽셀 정렬.
- **C-08 처리 이력 표시**: 로드된 XFrame의 history 체인(module_name/version/params_hash/calibset_id)을 그대로 표시 — 오케스트레이터 경로 검증 수단.

### 지표

- **C-09 지표 계산 위임**: MTF/NPS/DQE 등 플롯은 기존 `metrics/` 엔진 호출 결과만 사용 — **GUI 자체 지표 계산 0**. 플롯 값 = 엔진 출력과 배열 단위 일치(테스트로 비교). 디스플레이 픽셀 히스토그램은 W/L 렌더 UI(C-01)의 구성요소로 C-09의 위임 대상이 아니다(ImageJ가 B/C 히스토그램과 Analyze>Histogram을 분리하는 관행과 동일).
- **C-10 ROI 왕복 재현**: 지표용 ROI 선택 시 사용된 정확한 경계를 표기하고, 동일 경계를 하네스에 투입하면 동일 지표 값 재현(round-trip 테스트).

### 아키텍처·설치

- **C-11 import 방향**: `apps/gui` → 코어 4계층 단방향. 코어는 GUI를 import하지 않음. import-linter forbidden 계약으로 CI 강제. **lessons #1(헛통과) 반영: 의도적 위반 카나리 테스트 동반** — 위반을 심으면 lint가 실제로 실패함을 assert.
- **C-12 extras 격리**: `uv pip install .[gui]`로 설치. base 패키지는 Qt/napari 없이 설치되고 전체 코어 TC 통과 — `[gui]` 미설치 CI 잡으로 증명.
- **C-13 라이선스**: GPL-only 의존성 0 (PyQt6 명시 배제). `pip-licenses` allowlist CI 게이트.

### 테스트 (CI, 디스플레이 서버 없음)

- **C-14 헤드리스**: 모든 GUI CI 테스트는 `QT_QPA_PLATFORM=offscreen`(pytest-qt)로 실행. Windows 러너에 xvfb 요구 없음.
- **C-15 로직 레벨 커버리지**: 파일 로드(raw+JSON) / 모듈·파이프라인 하네스 호출 / 입력·출력·diff·마스크 레이어 생성 / W/L 수치 적용 / 프로브 값 정확성 — `make_napari_viewer`(폴백 시 qtbot) 기반. 픽셀 그랩/스크린샷 단정은 Windows CI에서 제외(napari 문서화된 제약), 원하면 Linux xvfb 잡에서만 `[T]`.
- **C-16 결정론**: 동일 fixture 입력+params → diff 레이어 배열·표시 지표 배열이 실행 간 bit-동일(파이프라인 순수성 상속, GUI 코드 경로 통과로 검증).

### 자원 한도

- **C-17 기동**: 콜드 런치 → 상호작용 가능 10s `[T]` 이내 (스파이크 SG-3에서 실측).
- **C-18 메모리**: 전/후 1쌍 + diff + 마스크 3장 로드 시 RSS 2GB `[T]` 이하. N쌍 로드는 명시적 LRU K프레임 `[T]`로 상한 — 무한 증가 금지.
- **C-19 응답성**: 파이프라인 실행 등 장시간 작업은 GUI 스레드 밖에서 실행. 이벤트 루프 200ms `[T]` 초과 블로킹 금지, 진행 표시 + 취소 제공.

### 범위 가드

- **C-20 읽기-실행 전용**: GUI는 `data/` 골든 fixture·CalibSet 파일을 절대 쓰지 않음. 모든 내보내기는 사용자 지정 출력 디렉터리로만.

## 4. 선행 코드 개선 의존성

리서치에서 검증된 갭과 GUI Phase의 의존 관계:

| 이슈 | 내용 | 구분 | 필요 시점 |
|---|---|---|---|
| #16 | raw+JSON 프레임 로더 (`common/io.py`) | **load-bearing** | Phase 1 (raw 입력 경로) |
| #15 | 모듈 레지스트리 `default_registry()` | **load-bearing** | Phase 1 (모듈 선택 UI) |
| #18 | 합성 CalibSet 팩토리 배포 코드 승격 | **load-bearing** | Phase 1 (실측 CalibSet 부재 대체) |
| #17 | XFrame 직렬화/이력 JSON 내보내기 | load-bearing(축소판) | Phase 2 (결과 내보내기) |
| #19 | 재수출/`REQUIRED_PARAMS`/Params 검증/반환형 통일 | 인체공학 | 병행 가능 |

SPEC-VIEWER-001은 #15/#16/#18을 선행 작업 패키지(Phase 0.5)로 포함하거나 명시적 선행 SPEC 의존으로 선언해야 한다. 코어 수정이므로 기존 아키텍처 계약(SWR-000-6~12)과 import-linter 전 계약 유지가 인수 조건.

## 5. SPEC 작성 시 준수 사항 (과거 plan-audit 이력 반영)

- XDET-TC-NNN 표기 통일 (bare TC-NNN 금지)
- EARS 라벨 1개당 요구 1개(복합 금지), 뒤따르는 비양태 문장 금지
- 결정론 규칙에 "또는" 금지 — 고정 폴백 순서 명시
- 모든 REQ ID ↔ AC 양방향 추적, 산출물 WHEN 트리거에는 생산자 REQ 존재
- 규범 REQ 본문에 파일/클래스 식별자(HOW) 금지 — plan.md/괄호로 이동
- 자동 검출 가능 범위와 코드리뷰 설계 규칙을 분리 (과잉 약속 금지)
- frontmatter 8필드(id/version/status/created/updated/author/priority/issue_number), 시간 예측 금지(Priority 라벨)

---

Version: 1.0.0
작성: 2026-07-10 (딥리서치 산출물 통합)
다음 단계: manager-spec 위임 → SPEC-VIEWER-001 (spec.md/plan.md/acceptance.md) → plan-audit 반복
