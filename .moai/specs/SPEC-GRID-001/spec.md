---
id: SPEC-GRID-001
version: 0.1.1
status: draft
created: 2026-07-09
updated: 2026-07-09
author: drake.lee
priority: high
issue_number: 8
labels: [T7, WP8, grid-suppression]
---

# SPEC-GRID-001 — T7 WP8 Grid line suppression 처리 모듈 (modules/)

XDET 영상처리 SW P1의 여덟 번째 작업 T7. 물리 anti-scatter grid에서 유래한 격자선(grid line) 성분을 억제하는 작업 **WP8(SWR-1001~1006)**를 전용 처리 모듈 `modules/grid.py`로 T0 프레임워크의 단일 계약 `process(XFrame, CalibSet, Params) -> XFrame` 순수함수형으로 구현한다. 핵심 설계는 **aliasing 전제**다 — 상용 grid 밀도(30~85 lines/cm = 3.0~8.5 lp/mm)는 자사 Nyquist f_N = 3.571 lp/mm(pitch 140µm)를 상회하는 대부분에서 f_a = |f_grid − k·f_s| (f_s = 7.143/mm)로 접혀 나타나므로, **명목 grid 주파수가 아니라 관측 스펙트럼 피크를 직접 탐색**해야 한다(SWR-1001, [HARD] 금지 사항). 처리 순서는 **(1) grid 방향 추정(행/열 1D PSD 에너지 비교) → (2) 해당 축 1D PSD(Welch)에서 탐색 대역 [0.3, f_N] 협대역 피크 탐색(유의성 ≥ D_th dB) + 접힘 고려 고조파 후보 검사(SWR-1002) → (3) 검출 피크별 주파수 도메인 1D Gaussian notch(대역폭 = FWHM × 1.5, grid 직교축, 2D 등방 notch 금지, SWR-1003) → (4) 저주파 접힘(< 0.5/mm) 시 감쇠 상한 제한 + grid 교체 권고 경고(SWR-1004) → (5) 유의 피크 미검출 시 무처리 통과 + "grid 미검출" 로그(SWR-1005, FR-M007)**로 구성된다. 이 스테이지는 고정 파이프라인 순서에서 전용 `grid` 스테이지(기하 보정 `geometry`와 잡음 억제 `denoise` 사이)에서만 실행된다(결정 1, 「결정 필요/확인 사항」 1). **실측 grid 취득 세트 도착 전에는 기지 grid 주파수(밀도 3부류: f_grid < f_N / ≈ f_N / > f_N aliased)를 주입한 합성 팬텀으로 검출 정확도·잔존 grid line 비가시·moiré 무발생·무검출 통과를 선검증**한다.

- 근거: SWR-1001~1006(Grid line suppression, FR-M006/M007, aliasing 설계 반영) · SWR-000-1~12(아키텍처, 특히 SWR-000-9 공용 컴포넌트 ③ FFT·PSD) — `docs/XDET_SWR_spec_v1.2.md`; EVAL v1.1 XDET-EV-203(grid line suppression: 잔존 grid line 비가시 / Moiré·aliasing 0건) / XDET-EV-102(MTF·SRb 열화 — 해부 손실 가드레일, 맥락 인용); TestSpec XDET-TC-015·016; FR-M007(실패 처리 무처리 통과)
- 완료 정의(DoD): **grid 밀도 3부류 합성 팬텀으로 검출 정확도 + 잔존 grid line 억제 + moiré 무발생 + 무검출 통과를 검증** — 실측 grid 세트 도착 전, (a) **[하드 DoD] 잔존 grid line 비가시**(XDET-TC-015): 밀도 3부류(f_grid < f_N / ≈ f_N / > f_N aliased)에 대해 관측 스펙트럼 탐색이 올바른(aliased 포함) 피크를 검출하고, 1D Gaussian notch 후 해당 주파수 잔존 피크 전력이 유의성 임계(국소 배경 대비 D_th dB) 이하로 떨어짐(=비가시)을 결정론적으로 이진 판정하며, 가드레일로 grid 직교축 MTF@Nyquist 유지율이 EV-102 min(≥90%) 이상임을 판정한다(EV-203 min). (b) **관측-스펙트럼 탐색 부하 검증**(XDET-TC-015 aliased 부류 negative control, SWR-1001): 명목 f_grid ≠ 관측 f_a인 aliased 팬텀에서 관측 스펙트럼 탐색이 aliased 피크를 검출하고, 대조로 명목 주파수 위치에는 유의 피크가 없어 명목-기반 탐색은 실패함을 확인한다. (c) **moiré/aliasing 무발생 + 무검출 통과**(XDET-TC-016, PARTIAL/FR-M007): 표준 부류에서 처리 후 잔존 moiré 피크가 없고(0건), 저주파 접힘 경계 사례에서 감쇠 상한 + 경고가 기록되며, 유의 피크 미검출 입력이 수치 동일 통과 + "grid 미검출" 로그로 처리됨을 판정한다. XDET-TC-015·016을 pytest skeleton(skip)에서 실동작 케이스로 전환
- 선행 계약: [SPEC-INFRA-001](../SPEC-INFRA-001/spec.md) — `process` 계약·XFrame 불변·마스크 스택 비트플래그(DEFECT=1/SATURATION=2/INTERPOLATION=4/SATURATION_BAND=8)·이력 체인(`HistoryEntry.extra` 스칼라 진단 위탁 채널)·오케스트레이터 진입 게이트(CalibSet 존재·해상도·패널 ID·유효기간·종류-단계 배선)·import-linter 레이어링(`module → common` 단방향)·`CANONICAL_ORDER`·공용 컴포넌트 ③ FFT·PSD `common/fft_psd.py`(SWR-000-9); [SPEC-METRICS-001](../SPEC-METRICS-001/spec.md) — 판정 엔진 `metrics/mtf.compute_mtf`/`mtf_value_at`(MTF 가드레일)·공용 컴포넌트 `common/fft_psd.py`(compute_psd/nps 최초 구현, 헤더 @MX:ANCHOR가 T7 grid-suppression을 소비자로 명시); [SPEC-POST-001](../SPEC-POST-001/spec.md) — 전용 스테이지 부분수열-삽입 하위호환 선례(결정 1)·검출기 캘리브레이션 없는 스테이지의 CalibSet(OTHER) 빈 placeholder + `_KIND_BY_STAGE` 미등재 + 신규 CalibKind 미신설 방침·`HistoryEntry.extra` 진단 위탁·EV 무-수치 지표의 조작적 정의 + 가드레일 PARTIAL 게이트 선례
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.1.0 (2026-07-09)** — 초안 생성. GitHub 이슈 #8. 6개 요구 그룹(SEARCH/NOTCH/MOIRE/PASSTHROUGH/CONTRACT/VALIDATE) EARS 구조 확정. 핵심 범위 결정:
  1. **전용 `grid` 스테이지 신설([확정 — RESOLVED], plan-audit iteration 1 CANONICAL_ORDER 대조 승인)**: WP8이 단일 스테이지에 대응하나, WP별 개별 스테이지 선례(line_noise/saturation/geometry/denoise/mse/window)와 T5·T6 부분수열-삽입 하위호환 선례를 따라 전용 `grid` 스테이지를 `geometry`와 `denoise` **사이**에 신설한다(`CANONICAL_ORDER = … → saturation → geometry → grid → denoise → mse → window → post`). **rationale**: (a) 관측 스펙트럼 피크 탐색은 기하 왜곡 보정 후의 축-정렬 영상이 필요하므로 `geometry` 뒤; (b) 강한 주기 패턴을 먼저 제거해야 BM3D(`denoise`) 블록 매칭이 grid 패턴을 텍스처로 오인·번짐 없이 처리하므로 `denoise` 앞; (c) MSE/DRC 대비강화(`mse`, WP6)는 잔존 grid line을 증폭하므로 그 앞에서 억제해야 함. 가정 default이며 T0 표면(`CANONICAL_ORDER`) 변경이므로 run-blocking. 기각 대안: `denoise` 뒤(피크 탐색 잡음 floor는 낮아지나 BM3D가 이미 grid 패턴을 왜곡·확산시켜 notch가 부정확).
  2. **관측 스펙트럼 직접 탐색([HARD], SWR-1001)**: aliasing 전제상 f_grid > f_N grid는 f_a로 접혀 나타나므로 notch 대상 주파수는 **오로지 관측 스펙트럼 피크**에서만 도출한다. 명목 grid 주파수를 탐색·notch 대상 산출 입력으로 쓰는 것은 금지(CLAUDE.md 금지 사항, Unwanted REQ-GRID-SEARCH-4). grid 장착 메타데이터는 SWR-1005 불일치 경고에만(선택적) 소비하고 피크 위치 산출에는 절대 유입하지 않는다(「결정 필요/확인 사항」 2).
  3. **1D Gaussian notch(SWR-1003)·2D 등방 notch 금지(Unwanted)**: 검출 피크별 주파수 도메인 1D Gaussian notch(대역폭 = FWHM × 1.5 [T])를 grid 직교축에만 적용하며 2D 등방 notch는 해부 손실을 유발하므로 금지한다(REQ-GRID-NOTCH-2, Unwanted).
  4. **무검출 무처리 통과(SWR-1005, FR-M007)·무단 억제 금지(Unwanted)**: 유의 피크 미검출 시 프레임을 수치 동일로 통과시키고 "grid 미검출" 로그만 남긴다. 유의 피크가 없을 때 어떤 notch·화소 변경도 하지 않는다(무단 억제 금지, REQ-GRID-PASSTHROUGH-2 Unwanted 단일 경로).
  5. **저주파 접힘 moiré 경고(SWR-1004)**: 접힘 피크가 저주파(< 0.5/mm [무등급])로 들어와 notch 대역이 해부와 중첩하면 감쇠 계수 상한을 제한하고 grid 교체 권고 품질 경고를 `HistoryEntry.extra`에 기록한다(REQ-GRID-MOIRE-1).
  6. **공용 컴포넌트 ③ FFT·PSD 소비(SWR-000-9)**: 스펙트럼 추정은 `common/fft_psd.py`(T1 구현, 헤더 @MX:ANCHOR가 grid-suppression을 소비자로 명시)를 소비·확장하며 FFT/PSD를 모듈 내부에 재구현하지 않는다. 1D Welch 축 PSD 추정기가 부재하면 `common/fft_psd.py`에 최초-소비자 확장으로 추가한다(POST-001의 `common/pyramid.py`·`common/histogram_fov.py` 확장 선례). **line noise(T3 SWR-501~504, `metrics/nps.detect_line_noise`)와 구별** — line noise는 판독 전자계에서 유래한 저주파 행/열 오프셋 밴딩(공간 도메인 라인별 오프셋 보정)이고, grid line은 물리 grid에서 유래한 고주파 주기 변조(aliased 가능)로 주파수 도메인 notch로 억제한다. 서로 다른 현상·다른 계층(전자는 metrics 엔진, 후자는 modules 처리 모듈).
  - 파라미터 등급 확정(SWR 부록 A/A-2 대조): 피크 유의성 임계 D_th(SWR-1002)=**TBD-[T]**(부록 A 명시); notch 대역폭 계수 FWHM×1.5(SWR-1003)=**TBD-[T]**(부록 A 명시); 탐색 대역 [0.3, f_N](SWR-1002)=SWR 본문 명시·부록 A 미등재(무등급, 등재 요청); moiré 저주파 컷오프 0.5/mm(SWR-1004)=SWR 본문 명시·부록 A 미등재(무등급, 등재 요청); 감쇠 계수 상한(SWR-1004)=미정량(무등급 [T] 등재 요청); 고조파 최대 차수·grid 방향 판정 마진=부록 A 미등재([T] 등재 요청). f_N=3.571 lp/mm·f_s=7.143/mm은 pitch 140µm에서 파생되는 물리 상수(Params pitch 소비, 하드코딩 아님).
  - status: draft (run 단계 착수 전까지 유지).
- **v0.1.1 (2026-07-09)** — plan-audit iteration 1 (FAIL, 프론트매터 스키마 D1) 반영: `labels` 필드 추가(저장소 SPEC 프론트매터 하우스 스키마 정합). 결정 1(전용 `grid` 스테이지 배치)은 실제 `CANONICAL_ORDER` 대조 검증 후 확정(RESOLVED) — `geometry`·`denoise` 인접 관계 무변경, T5/T6 기병합 결정과 무충돌 확인.

## Environment / Assumptions

- Python 3.11+, numpy/scipy 기반 float 골든 모델(tech.md). **속도 최적화 금지 — 정확도 단일 목표**(P2에서 최적화). 현재 `pyproject.toml` 의존성은 numpy/scipy 전용이며, 방향 추정·1D PSD·Gaussian notch를 전부 자체 numpy/scipy로 구현하므로 신규 의존성을 추가하지 않는다.
- 대상 프레임: 3072×3072 / 3072×2560, 16-bit unsigned raw, pitch 140µm, Nyquist f_N = 3.571 lp/mm(EVAL v1.1 §0), 샘플링 f_s = 7.143/mm. 상용 grid 밀도 30~85 lines/cm = 3.0~8.5 lp/mm — 약 36 lines/cm(≈ f_N) 초과 grid는 aliased 주파수 f_a = |f_grid − k·f_s|로 접혀 나타난다(SWR-1001). f_N·f_s는 Params pitch에서 파생 산출한다(하드코딩 금지).
- **실측 grid 취득 세트 도착 전 — 합성 팬텀으로 모듈을 검증한다.** 기지 grid 주파수(밀도 3부류: f_grid < f_N / ≈ f_N / > f_N aliased)·기지 방향(수평/수직)·기지 해부 신호를 주입한 합성 팬텀으로 검출 정확도·잔존 grid line 비가시·moiré 무발생·무검출 통과를 확인한다.
- **용어 정의 — 합성 검증 컨텍스트(synthetic-validation context)**: 합성 팬텀 fixture 시험 실행(기지 grid 주파수·방향·해부 신호 주입 → 처리 후 판정)을 가리키는 단일 용어로, T0(SPEC-INFRA-001)의 검증 모드(validation_mode — float64 병행 버퍼·단계별 중간 XFrame 보존)와는 별개 개념이다. SPEC-CORR/LNSG/LAG/DENOISE/POST의 동명 정의를 계승한다.
- T0 계약 소비: `grid` 모듈은 XFrame(불변)을 입력받아 새 XFrame을 반환하는 **무상태 처리 모듈**이며(lag과 달리 내부 상태 없음) `process(XFrame, CalibSet, Params) -> XFrame` 계약을 따른다. 마스크 스택 비트플래그·이력 체인·오케스트레이터 진입 게이트·`CANONICAL_ORDER`를 그대로 소비한다. 의존 방향은 `modules → common` 단방향(import-linter). 지표 엔진(`metrics/mtf`)·기지값 대조 판정은 `tests/`에서만 소비한다(모듈은 `metrics` 미import).
- **공용 컴포넌트 ③ FFT·PSD 소비(SWR-000-9)**: 스펙트럼 추정은 `common/fft_psd.py`(T1 구현; 헤더 @MX:ANCHOR가 "later grid-suppression (T7)"을 소비자로 명시)를 소비하며 FFT/PSD를 `modules/grid.py` 내부에 재구현하지 않는다. SWR-1002의 "해당 축 1D PSD(전 행 평균, Welch)" 추정기가 `common/fft_psd.py`에 부재하면 **최초-소비자 확장**으로 그곳에 추가한다(POST-001이 `common/pyramid.py`를 최초 구현·`common/histogram_fov.py`를 확장한 SWR-000-9 첫-소비자 이연 원칙 계승). 중복 구현 금지, 계층은 `module → common` 단방향 유지.
- **line noise와의 구별**: `metrics/nps.detect_line_noise`(T3, SWR-501~504)는 판독 라인 잡음(저주파 행/열 오프셋 밴딩)을 프레임 평균 1D 프로파일에서 검출하는 T1 지표 엔진 함수로, `grid` 모듈과 현상·계층·소비 위치가 모두 다르다. `grid` 모듈은 단일 영상의 2D→1D 축 PSD에서 고주파(aliased 가능) 협대역 피크를 탐색해 주파수 도메인 notch로 억제하는 `modules/` 처리 모듈이며, `metrics`를 import하지 않는다.
- 물리·튜닝·무등급 상수(피크 유의성 임계 D_th, notch 대역폭 계수 FWHM×1.5, 탐색 대역 [0.3, f_N], moiré 저주파 컷오프 0.5/mm, 감쇠 계수 상한, 고조파 최대 차수, grid 방향 판정 마진)는 전부 **Params 단일 소재**로 외부화한다(하드코딩 금지). CalibSet(OTHER)는 진입 게이트 충족용 빈 placeholder이며 파라미터 payload를 담지 않는다(「결정 필요/확인 사항」 2). 등급은 SWR 부록 A/A-2를 따르며 미등재 항목은 등재 요청한다(TBD-[T]: D_th·FWHM 계수; 무등급 등재 요청: [0.3, f_N]·0.5/mm·감쇠 상한·고조파 차수·방향 마진).
- **grid 장착 메타데이터(선택)**: SWR-1005의 "grid 장착 메타데이터와 불일치 시 경고"를 위한 grid 장착 여부·명목 밀도는 **선택적 Params 필드(취득 컨텍스트)**로 소비하며, **오로지 검출 결과 대조 경고에만** 쓰고 피크 위치 산출에는 절대 유입하지 않는다(SWR-1001 [HARD] 금지). 미제공 시 대조 경고는 생략된다(「결정 필요/확인 사항」 2).
- EV 판정 수치(EVAL v1.1 EV-203 잔존 grid line 비가시/Moiré·aliasing 0건 / EV-102 min 가드레일)와 잔존 피크 유의성 임계·D_th는 **엔진·모듈 외부에서 주입**된다(측정=판정 분리, METRICS/CORR/LNSG/LAG/DENOISE/POST 계승). 처리 모듈·판정 코드는 게이트 임계를 내장하지 않는다.

## Requirements (EARS)

### REQ-GRID-SEARCH — 관측 스펙트럼 피크 직접 탐색(방향 추정 + 1D PSD 협대역 피크 + 접힘 고조파) (SWR-1001~1002, FR-M006)

- **REQ-GRID-SEARCH-1 (Event-Driven)** — WHEN `grid` 모듈이 입력 XFrame을 처리하면, THEN 시스템은 행/열 1D PSD 에너지 비교로 grid 방향(수평선=행 방향 / 수직선=열 방향)을 추정해야 한다(SWR-1002; 방향 판정 마진 [T] Params 외부화). 방향 판정에 필요한 스펙트럼 추정은 공용 컴포넌트 `common/fft_psd.py`를 소비하며 FFT/PSD를 모듈 내부에 재구현하지 않는다(SWR-000-9 ③).
- **REQ-GRID-SEARCH-2 (Event-Driven)** — WHEN grid 방향이 추정되면, THEN 시스템은 해당 축 1D PSD(전 행/열 평균, Welch)에서 탐색 대역 [0.3, f_N](f_N = 1/(2·pitch), Params pitch 파생)의 협대역 피크를 탐색하고, 국소 배경 대비 유의성이 D_th dB 이상인 피크만 검출로 채택해야 한다(SWR-1002; D_th = TBD-[T] Params, 탐색 대역 무등급 등재 요청). 탐색 대역은 Params로 외부화한다(하드코딩 금지).
- **REQ-GRID-SEARCH-3 (Event-Driven)** — WHEN 기본(fundamental) 피크가 검출되면, THEN 시스템은 접힘(aliasing)을 고려한 고조파 후보 — f_a의 정수배 및 f_s 접힘 조합 위치 — 를 함께 검사하여 유의성 D_th 이상인 고조파 피크를 검출 집합에 추가해야 한다(SWR-1002 "고조파: 접힘 고려 f_a의 정수배±접힘 조합 후보 검사"; 고조파 최대 차수 [T] Params). 각 검출 피크 주파수는 관측 스펙트럼에서 산출된 값이다.
- **REQ-GRID-SEARCH-4 (Unwanted)** — IF 피크 위치 탐색·notch 대상 주파수 산출이 명목(nominal) grid 주파수 또는 grid 장착 메타데이터의 밀도값을 입력으로 사용하려 하면, THEN 시스템은 이를 [HARD] 계약 위반으로 취급해야 한다(SWR-1001 "명목 grid 주파수가 아니라 관측 스펙트럼 피크를 직접 탐색", CLAUDE.md 금지 사항 "명목 grid 주파수 기반 notch"). notch 대상 주파수는 **오로지 관측 스펙트럼 피크(REQ-GRID-SEARCH-2/3)에서만** 도출된다. 결정론적 단일 경로 — 명목값 유입 분기 없음. grid 메타데이터는 REQ-GRID-PASSTHROUGH-3(대조 경고)에만 소비된다.

### REQ-GRID-NOTCH — 1D Gaussian notch 억제(검출 피크별, grid 직교축, 2D 등방 금지) (SWR-1003, FR-M006)

- **REQ-GRID-NOTCH-1 (Event-Driven)** — WHEN REQ-GRID-SEARCH-2/3이 유의 피크 집합을 산출하면, THEN 시스템은 검출 피크별로 주파수 도메인 1D Gaussian notch(대역폭 = 해당 피크 FWHM × 1.5, [T])를 grid 직교축(수직 grid → 수평 주파수축, 수평 grid → 수직 주파수축)에만 적용하여 grid 성분을 억제해야 한다(SWR-1003; FWHM 계수 TBD-[T] Params). 스펙트럼 변환·역변환은 `common/fft_psd.py`를 소비한다(SWR-000-9 ③). 검출 피크 집합은 REQ-GRID-SEARCH-2/3이 산출한다(SEARCH → NOTCH 상류 추적).
- **REQ-GRID-NOTCH-2 (Unwanted)** — IF `grid` 모듈이 2D 등방(isotropic) notch를 적용하려 하면, THEN 시스템은 이를 계약 위반으로 취급해야 한다(SWR-1003 "1D 적용(grid 직교축) — 2D 등방 notch 금지(해부학 손실 최소화)"). notch는 grid 직교 1축에만 적용되는 단일 경로이며 등방 notch 분기가 없다.

### REQ-GRID-MOIRE — 저주파 접힘(moiré) 감쇠 상한 + 품질 경고 (SWR-1004, FR-M006)

- **REQ-GRID-MOIRE-1 (Event-Driven)** — WHEN REQ-GRID-SEARCH가 검출한 (접힘) 피크가 저주파 컷오프(< 0.5/mm, [무등급] Params) 미만으로 들어와 notch 대역이 해부 신호와 중첩하면, THEN 시스템은 해당 피크의 감쇠 계수를 상한([T] Params)으로 제한하고, grid 교체 권고 품질 경고("해당 grid는 본 패널과 조합 부적합")를 이력 체인(`HistoryEntry.extra`)에 기록해야 한다(SWR-1004). 감쇠 상한·저주파 컷오프는 Params로 외부화한다(하드코딩 금지). 트리거 피크는 REQ-GRID-SEARCH가 산출한다(SEARCH → MOIRE 상류 추적).

### REQ-GRID-PASSTHROUGH — 무검출 무처리 통과 + 로그 + 메타데이터 대조 경고 (SWR-1005, FR-M007)

- **REQ-GRID-PASSTHROUGH-1 (Event-Driven)** — WHEN 탐색 대역 [0.3, f_N]에서 유의성 D_th 이상의 피크가 하나도 검출되지 않으면, THEN 시스템은 입력 프레임을 무처리로 통과(화소·마스크 수치 동일)시키고 "grid 미검출" 진단을 이력 체인(`HistoryEntry.extra`)에 기록해야 한다(SWR-1005 실패 처리, FR-M007).
- **REQ-GRID-PASSTHROUGH-2 (Unwanted)** — IF 유의 피크가 검출되지 않았는데 `grid` 모듈이 notch 또는 화소 값 변경을 수행하려 하면, THEN 시스템은 이를 계약 위반으로 취급해야 한다(무단 억제 금지). 무검출 시 화소·마스크는 불변이며 억제 분기가 없다(결정론적 단일 통과 경로). 무피크 통과는 화소 수치 동일성이 관측 가능한 검증 대상이다(REQ-GRID-VALIDATE-5).
- **REQ-GRID-PASSTHROUGH-3 (Optional)** — WHERE grid 장착 메타데이터(장착 여부·명목 밀도)가 Params로 제공되면, 시스템은 검출 결과(피크 유무·관측 주파수)와 메타데이터의 정합 여부를 대조하여 불일치 시 경고를 이력 체인(`HistoryEntry.extra`)에 기록해야 한다(SWR-1005 "grid 장착 메타데이터와 불일치 시 경고"). 메타데이터 미제공 시 본 요구는 적용되지 않으며 대조 경고는 생략된다. 메타데이터는 대조 경고에만 소비되고 피크 위치 산출에는 유입하지 않는다(REQ-GRID-SEARCH-4).

### REQ-GRID-CONTRACT — 공통 모듈 계약 준수 (SWR-000-2~12, REQ-INFRA-* 소비)

- **REQ-GRID-CONTRACT-1 (Ubiquitous)** — `grid` 모듈은 단일 시그니처 `process(XFrame, CalibSet, Params) -> XFrame` 순수함수형이어야 하며(SWR-000-7, REQ-INFRA-CONTRACT-1), 입력 XFrame을 불변으로 취급(원본 미변경)하고 새 XFrame을 반환해야 한다(SWR-000-3, REQ-INFRA-DATA-6). 모듈은 내부 상태를 보유하지 않는다(lag과 달리 상태 재귀 없음).
- **REQ-GRID-CONTRACT-2 (Event-Driven)** — WHEN `grid` 모듈이 출력 XFrame을 생성하면, THEN 시스템은 처리 메타(모듈 버전 · 파라미터 해시 · 소비 CalibSet ID)와 스칼라 진단(추정 grid 방향 · 방향 에너지비 · 검출 피크 주파수·유의성(dB)·개수 · 적용 notch 대역폭 · 감쇠 상한 적용 여부 · moiré 경고 · "grid 미검출" 여부 · 메타데이터 불일치 경고 등)을 이력 체인 엔트리(`HistoryEntry.extra`)에 결정론적으로 추가해야 한다(SWR-000-4, REQ-INFRA-DATA-4, IEC 62304 추적).
- **REQ-GRID-CONTRACT-3 (Ubiquitous)** — 의존 방향은 `modules → common` 단방향이어야 하며, `grid` 모듈은 다른 처리 모듈 · `pipeline` · `metrics`를 import해서는 안 된다(SWR-000-8, REQ-INFRA-STATIC import-linter 계약). 실행 순서·조합은 오케스트레이터 단독 소관이며 모듈 간 직접 호출은 금지된다(REQ-INFRA-ORCH-1/2). 스펙트럼 추정은 공용 컴포넌트 `common/fft_psd.py`(③ FFT·PSD)를 소비·확장하며 FFT/PSD를 모듈 내부에 재구현하지 않는다(SWR-000-9). 지표 엔진(`metrics/mtf`) 소비는 `tests/`에서만 이뤄진다.
- **REQ-GRID-CONTRACT-4 (Unwanted)** — IF `grid` 모듈이 XFrame 컨테이너 외 채널(전역 상태 · 부가 반환값 · 파일 우회)로 데이터를 전달하려 하면, THEN 시스템은 이를 계약 위반으로 취급해야 한다(SWR-000-6 사이드채널 금지). 자동 검출 가능 범위는 시그니처·부가 반환값 위반(계약 검사)과 의존 방향 위반(import-linter 정적 검사)이며(acceptance.md EC-5의 검증 범위와 동일), 전역 상태·파일 우회는 테스트 가능 AC가 아닌 설계 규칙으로서 코드 리뷰 게이트로 다룬다(SPEC-INFRA-001 REQ-INFRA-DATA-2 방식 계승).
- **REQ-GRID-CONTRACT-5 (Ubiquitous)** — `grid` 모듈은 고정 파이프라인 순서 `CANONICAL_ORDER`의 전용 `grid` 스테이지(`geometry`와 `denoise` 사이, 결정 1)에서만 실행되어야 하며(SWR-000-2, REQ-INFRA-ORCH-3; 등록 stages는 `CANONICAL_ORDER`의 부분수열), 합성 입력 + 기대 출력 fixture로 harness 단독 시험이 가능해야 한다(SWR-000-11, XDET-TC-000). 스테이지는 검출기 캘리브레이션이 없으므로 `_KIND_BY_STAGE`에 종류-단계를 강제하지 않으며, 진입 게이트 충족을 위해 CalibSet(OTHER)를 소비한다(saturation/geometry/mse/window 선례; 「결정 필요/확인 사항」 1·2).
- **REQ-GRID-CONTRACT-6 (Unwanted)** — IF `grid` 모듈이 포화 화소 값을 "복원"하거나(SWR-602 [HARD] 복원 금지 계승) 마스크 플래그를 신규 설정·해제하면, THEN 시스템은 이를 계약 위반으로 취급해야 한다. 모듈은 마스크를 소비만 하고 substrate를 변경하지 않으며 조사야·포화 화소를 재구성하지 않는다. 결정론적 단일 경로.

### REQ-GRID-VALIDATE — 합성 검증(검출 정확도 + 잔존 grid line 비가시 + moiré 무발생 + 무검출 통과) (XDET-TC-015·016, EV-203/102, FR-M007)

- **REQ-GRID-VALIDATE-1 (State-Driven)** — WHILE 실측 grid 세트 도착 전 합성 검증 컨텍스트인 동안, 시스템은 기지 grid 주파수 밀도 3부류(f_grid < f_N / ≈ f_N / > f_N aliased, aliased 필수 포함)·기지 방향·기지 해부 신호를 주입한 합성 팬텀으로 검출 정확도·잔존 grid line 비가시·moiré 무발생·무검출 통과를 보여야 한다(DoD 전제, SWR-1006 "TC-015 grid 매트릭스에 3부류 반드시 포함", CLAUDE.md T7 "grid 밀도 3부류 합성 데이터 포함").
- **REQ-GRID-VALIDATE-2 (Event-Driven)** — WHEN 밀도 3부류 합성 팬텀에 grid 억제를 적용하면, THEN 시스템은 `tests/`에서 (a) 관측 스펙트럼 탐색이 올바른(aliased 포함) 피크를 검출하고, (b) 1D Gaussian notch 후 해당 주파수 잔존 피크 전력이 유의성 임계(국소 배경 대비 D_th dB) 이하로 떨어짐(=잔존 grid line 비가시), (c) 가드레일로 `metrics/mtf.compute_mtf`/`mtf_value_at` grid 직교축 MTF@Nyquist 유지율이 EV-102 min(≥90%) 이상임을 결정론적으로 이진 판정 가능해야 한다(XDET-TC-015 "Grid 성분 검출 정확도 + 잔존 grid line", EV-203 min). 이것이 T7의 하드 DoD이다.
- **REQ-GRID-VALIDATE-3 (Event-Driven)** — WHEN 명목 f_grid ≠ 관측 f_a인 > f_N aliased 부류 합성 팬텀에 적용하면, THEN 시스템은 `tests/`에서 관측 스펙트럼 탐색이 aliased 피크(f_a)를 검출·억제하고, 대조로 명목 주파수 위치에는 유의 피크가 없어 명목-기반 탐색은 실패함을 확인 가능해야 한다(SWR-1001 aliasing 전제 negative control — 관측-스펙트럼 탐색이 부하 핵심임을 증명, REQ-GRID-SEARCH-4의 시험측 대조). 명목-기반 탐색은 테스트-로컬 대조 계산일 뿐 모듈 경로가 아니다(모듈은 REQ-GRID-SEARCH-4로 명목값을 금지).
- **REQ-GRID-VALIDATE-4 (Event-Driven)** — WHEN 저주파 접힘(< 0.5/mm) 경계 사례 합성 팬텀에 적용하면, THEN 시스템은 `tests/`에서 감쇠 계수 상한 제한 + grid 교체 권고 품질 경고가 `HistoryEntry.extra`에 기록되고 표준 부류에서 처리 후 잔존 moiré 피크가 없음(0건)을 판정 가능해야 한다(XDET-TC-016 "Moiré/aliasing 발생 검사", EV-203 Moiré 0건; 저주파 접힘은 감쇠 상한 하 잔존을 특성화 — PARTIAL).
- **REQ-GRID-VALIDATE-5 (Event-Driven)** — WHEN 유의 피크가 없는(grid 무장착) 합성 입력에 적용하면, THEN 시스템은 `tests/`에서 프레임이 무처리로 수치 동일 통과되고 "grid 미검출" 로그가 기록됨을 확인 가능해야 한다(XDET-TC-016 "GLS 실패 시 무처리 통과 확인", FR-M007). 무검출 시 화소·마스크 불변(무단 억제 없음)이 관측 가능한 판정 대상이다(REQ-GRID-PASSTHROUGH-1/2).
- **REQ-GRID-VALIDATE-6 (Ubiquitous)** — EV-203(잔존 grid line 비가시/Moiré·aliasing 0건)·EV-102 min 가드레일 및 D_th·잔존 피크 유의성 임계 판정 수치는 EVAL v1.1/Params에서 외부 주입되어야 하며, 검증은 산출값과 외부 임계의 비교로만 이뤄져야 한다(측정=판정 분리 계승). 처리 모듈·판정 코드는 게이트 임계를 내장하지 않는다. 시험 케이스 XDET-TC-015·XDET-TC-016은 현재 pytest skeleton(skip)에서 합성 입력·판정 연동의 실동작 케이스로 전환되어야 한다(REQ-INFRA-CI-1 계승; 모듈은 `metrics` 미import이므로 MTF 가드레일 판정은 `tests/`에서 모듈 + 지표 엔진을 함께 소비).

## Exclusions (What NOT to Build)

- **명목 grid 주파수 기반 억제 없음** — [HARD] 명목 grid 주파수·메타데이터 밀도값을 notch 대상 산출에 사용하지 않는다(SWR-1001, CLAUDE.md 금지 사항). notch 주파수는 오로지 관측 스펙트럼 피크에서 도출한다. grid 메타데이터는 SWR-1005 대조 경고 전용.
- **2D 등방 notch 없음** — notch는 grid 직교 1축에만 적용한다(SWR-1003). 2D 등방 notch는 해부 손실을 유발하므로 금지(REQ-GRID-NOTCH-2).
- **무검출 시 무단 억제 없음** — 유의 피크 미검출 시 어떤 notch·화소 변경도 하지 않고 수치 동일 통과 + 로그만 남긴다(SWR-1005, FR-M007, REQ-GRID-PASSTHROUGH-2). 저신호·저유의 피크를 임의로 억제하지 않는다.
- **대각선·회전 grid 억제 없음** — SWR-1002 방향 추정은 행/열(축-정렬) 기반이다. 대각선·임의 회전 grid는 P1 범위 밖이며, 방향 에너지비가 판정 마진 미만으로 모호하면 무검출 통과로 처리한다(「결정 필요/확인 사항」 4). 방향·에너지비는 진단 기록.
- **scatter 보정·virtual grid 없음** — 무그리드 scatter 보정(EV-202)·커널 virtual grid(SWR-1101~1103/T8)는 T7 범위 밖. T7은 물리 grid line의 억제만 담당한다.
- **line noise 재처리 없음** — 판독 라인 잡음(SWR-501~504/T3, `metrics/nps.detect_line_noise`)은 별개 현상·별개 스테이지(`line_noise`)로 이미 처리된다. `grid` 모듈은 line noise를 재검출·재보정하지 않는다.
- **후속·타 WP 처리 모듈 없음** — 커널 virtual grid(SWR-1101~1103/T8)·NDT(SWR-1201~1204/T9)·티어·동일성(SWR-1301~1303/T10)은 T7 범위 밖. 선행 offset/gain/defect(T2)·lag(T4)·line noise/포화/기하(T3)·denoise(T5)·MSE/DRC·윈도잉/GSDF(T6)도 본 SPEC 범위 밖(이미 구현됨).
- **`post` 스테이지 실현 없음** — 결정 1로 전용 `grid` 스테이지를 `geometry`와 `denoise` 사이에 신설하며 `post`는 예약 tail로 유지한다(T5·T6 "기존 post 실현" 기각 계승).
- **관찰자 "비가시" 판정 없음** — EV-203 "잔존 grid line 비가시(표준)"의 관찰자 판독(EV-204 계열)은 인허가 제출용 관찰자 연구 대상으로 개발 게이트 아님. T7은 잔존 피크 유의성 임계 이하(결정론)·moiré 0건(객관 대리)·MTF 가드레일로만 판정한다.
- **신규 마스크 플래그 없음** — grid 방향·검출 피크·경고는 `HistoryEntry.extra` 진단으로 다루며 XFrame 마스크 스택에 신규 플래그를 도입하지 않는다(T0 표면 무변경).
- **신규 CalibKind·의존성 없음** — `grid`는 검출기 캘리브레이션이 없어 CalibSet(OTHER) 빈 placeholder를 소비하고 신규 CalibKind를 신설하지 않는다(POST-001 선례). 방향 추정·1D PSD·Gaussian notch 전부 자체 numpy/scipy 구현으로 `pyproject.toml` 신규 의존성 미추가.
- **EV 게이트 임계·D_th 내장 없음** — EV-203/102 및 D_th·잔존 피크 유의성 임계는 외부 주입. 처리 모듈·판정 코드는 합격/불합격 임계를 내장하지 않는다.
- **성능·처리시간·티어 게이트 없음** — EV-401/402, XDET-TC-020/021은 P2.

## 결정 필요/확인 사항

SWR 조항이 T0/T1 구현과 모호하거나 상충하는 지점. **「1」은 run-blocking 확정 대상**(T0 표면 `CANONICAL_ORDER` 변경 — 전용 `grid` 스테이지 신설). **「2~5」는 확인 대상**으로 각 항목에 가정 default를 명시한다. 최종 확정은 orchestrator 결정(plan-audit)을 따른다.

1. **[run-blocking] grid 파이프라인 스테이지 배치** — 전용 `grid` 스테이지를 `geometry`와 `denoise` **사이**에 신설한다(`CANONICAL_ORDER = … → saturation → geometry → grid → denoise → mse → window → post`). `post`는 예약 tail로 유지. **rationale**: (a) 관측 스펙트럼 피크 탐색은 기하 왜곡 보정 후의 축-정렬(행/열=검출기 축) 영상이 필요하므로 `geometry` 뒤에 둔다(SWR-1002 방향 추정 전제); (b) 강한 주기 패턴을 먼저 제거해야 BM3D(`denoise`) 블록 매칭이 grid 패턴을 반복 텍스처로 오인해 보존·번짐시키지 않으므로 `denoise` 앞; (c) MSE/DRC 대비강화(`mse`, WP6)·범위 정규화가 잔존 grid line을 증폭하므로 그 앞에서 억제해야 한다. 오케스트레이터 진입 게이트는 등록 stages가 `CANONICAL_ORDER` 부분수열이면 통과하므로 스테이지 신설은 하류 미등록 SPEC에 하위호환(T5·T6 선례). **기각 대안**: `denoise` 뒤(`… → denoise → grid → mse …`) — 잡음 floor는 낮아지나 BM3D가 이미 grid 주기 패턴을 왜곡·확산시켜 피크가 넓어지고 notch 정확도가 저하; grid는 denoise가 보는 영상을 깨끗하게 만들어 주는 선처리가 자연스럽다. T0 표면(`CANONICAL_ORDER`) 변경 run-blocking — plan-audit 확정 필요.
2. **[확인] grid 장착 메타데이터 소재·역할(SWR-1005)** — SWR-1005 "grid 장착 메타데이터와 불일치 시 경고"의 메타데이터(장착 여부·명목 밀도) 소재와, SWR-1001 명목-주파수-금지와의 양립. **가정 default**: 메타데이터는 **선택적 Params 필드(취득 컨텍스트)**로 소비하고, **오로지 검출 결과(피크 유무·관측 주파수) 대조 경고에만** 쓰며 피크 위치 산출에는 절대 유입하지 않는다(REQ-GRID-SEARCH-4 금지 유지). CalibSet payload 미탑재(검출기 캘리브레이션 아님). 미제공 시 대조 경고 생략. 확인: 메타데이터를 Params vs 취득 JSON 어디서 읽을지, 불일치 경고의 심각도 등급.
3. **[확인] EV-203 "잔존 grid line 비가시(표준)" 조작적 정의** — EV-203은 수치 임계가 없다("비가시(표준)"). **가정 default**: 합성 데이터에서 notch 후 기지 grid/aliased 주파수의 **잔존 피크 전력이 검출과 동일한 유의성 임계(국소 배경 대비 D_th dB) 이하**로 떨어짐(=관측 스펙트럼상 비가시)을 결정론적 이진 판정 leg로 삼고, 여기에 grid 직교축 MTF@Nyquist 유지율 ≥ EV-102 min(≥90%) 가드레일을 더한다(1D notch가 해부를 건드릴 수 있으므로). 관찰자 "비가시"(EV-204 계열)는 인허가 이연(PARTIAL). POST-001 TC-012 IQA 대리 + 가드레일 선례. 확인: 잔존 피크 유의성 임계 크기(D_th 재사용 vs 별도 [T]), MTF 가드레일 대상 주파수.
4. **[확인] grid 방향 가정(축-정렬) 및 모호 시 처리** — SWR-1002 방향 추정은 행/열 1D PSD 에너지 비교(축-정렬 전제)다. **가정 default**: 수평/수직(축-정렬) grid만 지원하고 대각선·회전 grid는 P1 범위 밖(Exclusions). 행/열 에너지비가 방향 판정 마진([T]) 미만으로 모호하면 확신 방향 없음 → 무검출 통과(REQ-GRID-PASSTHROUGH-1)로 처리(임의 축 추정 금지). 방향·에너지비는 `HistoryEntry.extra` 진단. 확인: 방향 판정 마진 기본값, 양축 동시 grid(교차 격자) 처리 여부.
5. **[확인] D_th·notch FWHM 계수·탐색 대역·moiré 컷오프·감쇠 상한·고조파 차수의 부록 A 등재** — 피크 유의성 D_th·notch 대역폭 계수(FWHM×1.5)는 SWR 본문 TBD-[T]; 탐색 대역 [0.3, f_N]·moiré 컷오프 0.5/mm은 SWR 본문 명시·부록 A 미등재(무등급); 감쇠 계수 상한·고조파 최대 차수·방향 마진은 미정량(부록 A 미등재). **가정 default**: 전부 Params로 외부화하고 부록 A 등재를 요청한다(TBD 항목은 [T], SWR 본문 명시값은 무등급 등재 요청). f_N·f_s는 pitch 파생 물리 상수로 하드코딩하지 않는다(Params pitch 소비). 미등재 항목에 등재된 등급을 단정하지 않는다(DENOISE ε_unbias·POST β 등재 요청 선례). 확인: 각 항목의 [T]/무등급 등재 등급·기본값 크기.
