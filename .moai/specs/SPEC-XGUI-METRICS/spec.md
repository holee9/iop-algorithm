---
id: SPEC-XGUI-METRICS
version: 0.5.1
status: planned
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-12
updated: 2026-07-13
author: drake.lee
priority: medium
issue_number: 58
labels: [xgui, gui-redesign, verification-gui, metrics, mtf, nps, dqe, golden-frozen]
---

# SPEC-XGUI-METRICS — Metrics(MTF/NPS/DQE) 알고리즘 그룹 GUI 검증 탭

> 본 사양은 `../SPEC-XGUI-MASTER/baseline-control.md`의 G0와 `traceability-matrix.md`를 상속한다. 사용자 승인·기준선 동결·`implementation_authorized=true` 전에는 구현 입력으로 실행하지 않으며, 승인 뒤 규범 변경은 버전 상승과 재승인을 요구한다.

XDET 검증 GUI 재설계(이슈 #58)의 **그룹 8 — Metrics** 검증 탭이다. 대상 골든 모듈은 `metrics/mtf.py`·`metrics/nps.py`·`metrics/dqe.py`(+ `metrics/defect_stats.py`·`metrics/defect_map.py`)이며, 전 그룹 공유 사실은 [SPEC-XGUI-MASTER](../SPEC-XGUI-MASTER/foundation.md)와 [algorithm-catalog.md](../SPEC-XGUI-MASTER/algorithm-catalog.md)를 상속한다. frontmatter/구조는 [SPEC-XSEAM-002](../SPEC-XSEAM-002/spec.md)를 미러링한다.

**이 그룹이 다른 그룹과 근본적으로 다른 점:** Metrics는 `process(XFrame, CalibSet, Params) -> XFrame` **모듈 실행 그룹이 아니다**. CalibKind를 소비하지 않고 `MetricResult`(metrics/result.py:41)를 산출하는 **지표 엔진**이다(foundation §6). 따라서 본 탭은 이미지 before/after/diff 뷰어(그룹 1~6)도 시간축 시퀀스 뷰어(그룹 2)도 아닌 **주파수축 곡선 플롯 + 스칼라 판독 뷰**이며, "build/apply(run_pipeline)" 워크플로 대신 "입력세트 조립 → 지표 엔진 위임 호출 → 곡선/수치 렌더" 워크플로를 갖는다.

**문제(사용자 요구):** 각 지표는 **서로 다른 입력 형태**를 요구한다 — MTF는 단일 슬랜티드-엣지 슬랩 프레임 + ROI, NPS/NNPS는 균일(flat) 프레임 **스택**, DQE는 앞서 산출한 MTF 결과와 NPS 결과의 **합성**(새 입력 없음), defect 통계는 dark 스택 + flat 스택이다. 사용자는 각 지표를 실제로 실행하고 곡선·수치를 확인할 수 있어야 하며 모든 수치는 골든 엔진이 내야 한다. MTF와 NPS의 자연 축은 다르지만, 골든에는 `metrics.mtf.mtf_value_at(result, freq_lpmm)` 공개 보간 연산이 존재한다. 따라서 engine seam이 MTF support 안의 NPS bin에서 이 함수를 호출한 뒤 `compute_dqe`를 호출하면 골든 무변경·UI DSP 0으로 DQE를 구현할 수 있다.

**Python 선례:** [SPEC-VIEWER-001](../SPEC-VIEWER-001/spec.md)의 **REQ-VIEW-RUN-3/4**(지표는 반드시 `metrics/` 엔진 호출의 반환값만 플롯; `apps/gui`에서 인라인 계산 금지 — 배열 동일성 단언으로 "GUI 계산 0" 강제, metrics_panel.py:5-9)와 **REQ-METRICS-CORE-4/5/6**(Params 외부화 / 엔진은 측정만·게이팅 없음 / `MetricResult` 단일 반환)를 상속한다. 현행 `MetricsTab`(C-09 delegation + C-10 ROI 왕복)은 MTF에 대해 이 선례를 이미 구현했고(app.py:571-706, metrics_panel.py:65/77), 본 SPEC은 그것을 NPS/DQE/defect-통계로 확장한다.

- 근거(변경 없음, 소비만):
  - `metrics/mtf.py::compute_mtf(frame: XFrame, params, *, calibset_id=None, direction="vertical") -> MetricResult`(mtf.py:142) · `estimate_edge_angle(image)`(자동 각도추정, mtf.py:48) · `mtf_value_at(result, freq_lpmm)`(mtf.py:212)
  - `metrics/nps.py::compute_nps(frames: list[XFrame], params, *, calibset_id=None, dose_level=None) -> MetricResult`(nps.py:83, **프레임 스택**) · `detect_line_noise(frames, params, *, calibset_id=None)`(nps.py:152)
  - `metrics/dqe.py::compute_dqe(frequencies_lpmm, mtf, nnps, params, *, calibset_id=None, dose_level=None) -> MetricResult`(dqe.py:31, **프레임 아님 — 배열 합성**) · `dqe_value_at(result, freq_lpmm)`(dqe.py:96)
  - `metrics/defect_stats.py::classify_defects(dark_frames, flat_frames, params, *, calibset_id=None, truth_map=None)`(defect_stats.py:57, E2597 7-class `DefectClass` IntEnum:40) · `metrics/defect_map.py::build_defect_map`(defect_map.py:83 → CalibKind.DEFECT)
  - `metrics/result.py::MetricResult`(result.py:41)·`MetricCondition`(:22)·`MetricReadError`(:60)·`require_param`(:73) — 엔진은 측정만·판정 안 함(EV min/typ/max는 엔진 밖, result.py:10-12)
  - GUI 위임 진입점: `apps/gui/metrics_panel.py::plot_mtf`(:65)·`recompute_mtf_for_roi`(:77) — 배열 동일성으로 C-09 검증됨
- 상속 원칙: SPEC-VIEWER-001의 [HARD]를 상속 — **읽기-실행 전용**(C-20), **지표/DSP 자체 계산 0**(C-09: UI/어댑터는 스스로 계산하지 않고 실제 엔진 결과만 표시), **단방향 소비**(C-11). 판정(EV pass/fail)은 엔진에도 GUI에도 없다(result.py:10-12).
- 완료 정의(DoD): (1) WPF가 MTF·NPS·DQE·line-noise·defect를 dedicated `IXdetEngine` metric DTO로 호출하고 반환 `MetricResultEnvelope`만 렌더 → (2) ROI 왕복 재현성 → (3) 등록 nps_flat SAMPLE로 NPS sanity → (4) DQE engine composition이 `mtf_value_at`+`compute_dqe`를 실제 호출하고 무외삽을 증명 → (5) strict 사용자 실측 입력 실행과 evidence label → (6) report/run manifest 내보내기 → (7) GUI DSP·판정 0. 골든 무변경.
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.4.0 (2026-07-13)** — 전체 알고리즘 구현 목표 반영. 소스 재검토에서 공개 골든 `metrics.mtf.mtf_value_at`을 확인해 DQE 영구 비활성 결정을 수정했다. NPS support 고정축 정책, 무외삽, upstream compatibility/provenance, user-supplied evidence를 실행 계약으로 추가했다.

- **v0.2.0 (2026-07-13)** — 중단 작업 복구 마무리. 구현 대상을 C# WPF `apps/xdet-console/`로 확정하고 Python `apps/gui/`는 참조 선례로 한정했다. 그룹별 결정·중앙 TC 레지스트리·plan/research를 확정했다. 골든 알고리즘은 변경하지 않는다.

- **v0.1.1 (2026-07-12)** — 라운드 1 교차검증(audit-r1.md, 판정 FAIL) 결함 교정. 전 항목 골든 소스 재대조. (D1) DQE "완전 지원" 단언을 정정하고 DQE 한정 차단 결정을 당시 설계 결정 섹션에 기록했다(골든 헬퍼 부재 및 `test_nps_dqe.py:84` `mtf_ideal=np.ones_like` 회피를 근거로). (D2) defect-통계 7개 [P] 키를 REQ-XMETRIC-PARAM-1·HISTORY(c)에 완전 열거(+ `NOISY_MEDIAN_MULTIPLIER=6.0`은 [S]로 Param 아님). (D3) defect-통계 뷰(E2597 클래스 히스토그램/분율 + 선택적 2D `class_map`)를 REQ-XMETRIC-VIEW-2로 신설하고 "주파수축 곡선"을 MTF/NPS/DQE로 한정(VIEW 재번호 2→3, 3→4). (D4) plan.md·acceptance.md 동반 문서 생성으로 끊긴 링크 해소. (D5) REQ-XMETRIC-DATA-3의 `classify_defects` 입력을 dark+flat 스택(선택 `truth_map`)으로 정정 — BPM은 입력 스택 아님. 골든 무변경(문서 측 보강만).
- **v0.1.0 (2026-07-12)** — 초안 생성. GitHub 이슈 #58(GUI 재설계), 그룹 8(Metrics). 5개 요구 그룹(INPUT/PARAM/COMPUTE/VIEW/DATA/EXPORT/GUARD) EARS. 저작 시 **AUTHORITATIVE 골든 소스로 Grep/Read 대조검증한 사실**:
  - (a) **세 지표의 입력 형태가 모두 다르다** — `compute_mtf`는 단일 `XFrame`(mtf.py:142), `compute_nps`는 `list[XFrame]` **스택**(nps.py:83, `if not frames` 가드 :101), `compute_dqe`는 **프레임을 받지 않고** `(frequencies_lpmm, mtf, nnps)` **배열**을 받는다(dqe.py:31). DQE는 앞선 MTF 결과의 `mtf` 배열과 NPS 결과의 `nnps` 배열의 **합성**이며 새 입력을 로드하지 않는다.
  - (b) **DQE 합성은 공통축을 요구하며 기존 공개 골든 연산으로 구현 가능하다.** `compute_dqe`는 `freq.shape == mtf.shape == nnps.shape`를 강제하고 불일치 시 `ValueError`(dqe.py:57-58). MTF축과 NPS축의 범위·간격은 다르지만 `metrics.mtf.mtf_value_at(result, freq_lpmm)`은 MTF `MetricResult`의 `frequencies_lpmm`/`mtf`를 사용해 골든 내부 `np.interp`로 값을 반환한다(mtf.py:212-216). engine은 MTF support 안의 NPS bin만 target으로 사용해 이 함수를 호출하고 범위 밖 bin을 제외한다. UI/transport가 자체 `np.interp`를 구현하거나 endpoint 외삽하는 것은 여전히 C-09 위반이다.
  - (c) **정확한 Params 키(엔진 상수, `require_param`로 강제, 결여 시 `MetricReadError` 키 명시, result.py:73/89-91)**:
    - MTF: `pixel_pitch_mm, mtf_oversample, mtf_angle_min_deg, mtf_angle_max_deg, mtf_angle_margin_deg`(mtf.py:28-32/167-171). 현행 GUI는 이 5개를 사용(app.py:669-675), pitch만 편집 가능(pitch_spin, 기본 0.14mm=140µm CsI, app.py:603).
    - NPS: `pixel_pitch_mm, nps_roi_size, nps_detrend_order, nps_exclude_axis_bins, nps_average_lines, nps_central_frac`(nps.py:28-33/103-108). `nps_roi_size` 기본 256(IEC)이나 **하드코딩 아님 — Param 외부화**. `detect_line_noise`는 `pixel_pitch_mm, line_noise_sig_factor`(nps.py:28,34).
    - DQE: `dqe_q, dqe_ka, dqe_nps_floor`(dqe.py:26-28/60-62). q·Ka는 측정프로토콜 §1.4 차원 교정을 반영 — `fluence=q*ka [1/mm^2]`, `NNPS [mm^2]` → DQE 무차원(dqe.py:1-9/63). NNPS≤floor 주파수는 `NaN`(0-나눗셈 가드, dqe.py:65-68).
    - 공통 optional provenance Params: `beam_quality`, `dose_level`, `added_filter`, `temperature_c`. MTF/NPS `MetricCondition`에 그대로 보존하며 필수 계산 Params와 혼동하거나 UI 기본값을 만들지 않는다.
    - defect 통계: `classify_defects`는 7개 [P] 키를 `require_param`로 강제 — `defect_min_frames, defect_over_value, defect_under_value, defect_dead_gain_frac, defect_nonuniform_frac, defect_lag_frac, defect_unstable_frac`(defect_stats.py:31-37, require :78/98-103). `NOISY_MEDIAN_MULTIPLIER=6.0`은 ASTM E2597-22 확정 [S] 상수로 **Param 아님**(defect_stats.py:27-29, 튜닝 금지).
  - (d) **엔진은 측정만·판정 안 함** — EV min/typ/max pass/fail은 `MetricResult`에 의도적으로 부재하고 엔진 밖에서 평가(result.py:10-12, REQ-METRICS-CORE-5). 따라서 탭은 곡선·수치·`warnings`·`MetricCondition`을 표시하되 합격/불합격 판정을 산출하지 않는다(C-09를 판정까지 확장).
  - (e) **뷰어 특성** — 그룹 8은 이미지 처리가 아니라 **곡선 플롯 + ROI 선택**(foundation §2 그룹 8). 현행 `MetricsTab`은 상류 탭(Module Verifier/Pipeline Viewer) 출력을 소스로 소비(C-09, 자체 파일 로드 안 함, app.py:572-573/647-654)하고 ROI 왕복 재현성(C-10, app.py:688-706)을 확인한다.
  - (f) **등록 SAMPLE 가용성(비정본, QUARANTINE 이슈 #29)** — `nps` 등록 폴더로 `compute_nps` sanity 구동 가능하다. 등록 슬랜티드-엣지 팬텀이 없어 MTF/DQE의 등록 정본 증거는 #33 대기지만, 합성 입력과 strict 사용자 제공 실측 입력으로 알고리즘 자체는 실행할 수 있다. `classify_defects`는 SAMPLE dark/flat 스택으로 sanity 가능하다. 어떤 SAMPLE 수치도 골든/튜닝 근거가 아니다.
  - 확정 설계 결정: 조립·재샘플·판정 권한을 GUI에 두지 않고, DQE 축 합성은 engine-owned service가 공개 골든 `mtf_value_at`과 `compute_dqe`를 호출한다.

## Environment / Assumptions

- **본 SPEC은 T-스테이지가 아니다.** 골든 `metrics/{mtf,nps,dqe,defect_stats,defect_map,result}.py`의 함수 시그니처·Params 키·`MetricResult` 계약은 전부 불변이며, 본 SPEC은 그 위에 **곡선/수치 뷰어(그룹 8 탭)** 를 additive로 얹는다(SPEC-VIEWER-001·SPEC-XSEAM-002 검증 도구 계열의 확장). 신규 Params 키·신규 지표·신규 반환 필드 없음.
- **지표 그룹은 모듈 실행 그룹과 다르다.** Metrics는 `run_pipeline`을 사용하지 않고 `MetricResult`를 낸다. WPF는 dedicated `IXdetEngine` methods를 호출하며 PythonNet adapter만 공개 Python 지표 함수에 위임한다. DQE는 `DqeComposeRequest`로 실행한다.
- **입력세트(검증됨).** 이 탭이 조립하는 입력은 지표마다 다르다:
  - **MTF** = 단일 슬랜티드-엣지 슬랩 `XFrame` + ROI(부분 프레임). 소스는 상류 탭 엔진 출력(C-09) 또는 등록 폴더 브라우저(foundation §4).
  - **NPS/NNPS** = 균일(flat) `XFrame`의 **정렬 스택**(`list[XFrame]`). 중앙영역 256×256 ROI 반겹침 타일링은 엔진 내부(nps.py:53-80). 단일 프레임이 아니라 스택.
  - **DQE** = 새 입력 없음 — 앞서 산출한 **MTF `MetricResult`의 `mtf` 배열** + **NPS `MetricResult`의 `nnps` 배열**을 공통 주파수축에서 합성(dqe.py:31). q·Ka·floor는 Params.
  - **defect 통계** = dark `XFrame` 스택 + flat `XFrame` 스택(classify_defects, defect_stats.py:57).
- **정확한 Params 키(검증됨).** HISTORY (c) 참조. `require_param`(result.py:73)이 필수 키를 강제하고 결여 시 키를 명시한 `MetricReadError`를 던진다(기본값 대체 없음, result.py:89-91). pitch는 세션/검출기별로 유의미하게 변하는 유일한 편집 입력이고, MTF 각도-윈도우·오버샘플 등 [P] 피팅 상수는 `tests/metrics/phantoms/params.py::make_params` 기본과 동일(app.py:664-668).
- **엔진은 측정만·판정 안 함(검증됨).** EV min/typ/max는 `MetricResult`에 없고 엔진 밖에서 평가(result.py:10-12). 탭은 곡선·스칼라·`warnings`(예: MTF 각도 경계근접, mtf.py:182-187)·`MetricCondition`(beam_quality/dose_level/params_hash/calibset_id, result.py:22-37)을 표시하되 합격/불합격을 계산하지 않는다.
- **뷰어 특성(그룹 고유).** MTF/NPS/DQE는 주파수축(lp/mm) 곡선 + 스칼라 판독이 핵심 — MTF 곡선·`mtf_at_nyquist`·`edge_angle_deg`·`nyquist_lpmm`(mtf.py:199-205), NPS/NNPS 곡선·`mean_signal`·`n_roi`(nps.py:140-147), DQE(f) 곡선·`invalid_indices`(dqe.py:79-84). **defect-통계만은 곡선이 아니라 E2597 클래스 히스토그램(`counts`/`fractions`) + 선택적 2D `class_map` 공간 표시이며 `miss_rate`는 `truth_map` 있을 때만**(defect_stats.py:142-150). 이미지 before/after/diff(그룹 1~6)나 시간 시퀀스(그룹 2)와 구별된다. ROI는 MTF 소스 프레임에서 선택(C-10 왕복 재현성).
- **실측 데이터 가용성(SAMPLE·비정본, QUARANTINE 이슈 #29).**
  - **NPS: 실행가능 sanity** — `nps`(nps_flat) 등록 스택 → `compute_nps`(유한·비퇴화 NNPS 구조 확인). 그룹 7 SNR과 flat 스택 공유.
  - **MTF: #33 대기** — 슬랜티드-엣지 팬텀이 등록세트에 없음. 엔진은 합성 팬텀(가우시안 블러 엣지, tests/metrics/phantoms)으로 검증하고 SAMPLE-구동 MTF는 합성/#33 라벨(등록데이터 실행 주장 없음).
  - **DQE: 등록 정본 #33 대기, 알고리즘 실행 가능** — 합성 또는 strict 사용자 제공 MTF/NPS로 실행하며 evidence grade를 구분한다.
  - **defect 통계: SAMPLE dark/flat sanity** — 등록 dark/flat 스택으로 E2597-class 분류 sanity(입력은 dark+flat 스택, 등록 BPM은 선택적 `truth_map`; 수치 골든/튜닝 금지).
  - 모든 SAMPLE 구동은 sanity(유한·비퇴화·구조 성립)일 뿐 수치 골든 주장·튜닝·적합이 아니다(비정본, G-5).
- **환경.** Python은 `uv run`으로만 실행(`uv run pytest`, `uv run lint-imports`). 정확성·재현성이 목적이며 성능/렌더 최적화는 목적이 아니다(P2).

## Requirements (EARS)

### REQ-XMETRIC-TARGET — 구현 대상 경계

- **REQ-XMETRIC-TARGET-1 (Ubiquitous)** — 시스템은 `apps/xdet-console/` C# WPF 앱을 구현 대상으로 사용해야 하며, `apps/gui/`와 Python 테스트·패널은 계약 및 검증 선례로만 참조해야 한다. WPF는 Python 모듈을 직접 호출하지 않고 `IXdetEngine`/PythonNet seam을 경유해야 한다.

### REQ-XMETRIC-INPUT — 지표별 입력세트 조립 (C-09/C-11, SPEC-VIEWER-001 RUN-3 확장)

- **REQ-XMETRIC-INPUT-1 (Event-Driven)** — WHEN 사용자가 한 지표(MTF/NPS/DQE/defect-통계)를 선택하고 그 지표의 입력세트를 공급하면, THEN 탭은 그 지표의 정확한 엔진 입력 형태를 조립해야 한다 — MTF는 단일 엣지-슬랩 `XFrame` + ROI, NPS는 flat `XFrame`의 정렬 스택(`list[XFrame]`), DQE는 앞선 MTF `MetricResult`와 NPS `MetricResult`(새 프레임 로드 없음), defect-통계는 dark 스택 + flat 스택 — 그리고 그 입력을 변형 없이 엔진에 전달해야 한다.
- **REQ-XMETRIC-INPUT-2 (Event-Driven)** — WHEN 지표 소스가 상류 탭의 엔진 출력이면, THEN 탭은 그 출력 프레임을 자체 파일 로드 없이 직접 소비해야 하고(C-09, 현행 app.py:647-654 선례); WHEN 소스가 등록 데이터셋이면, THEN 상주 폴더 브라우저(foundation §4)로 로드해야 한다(합성 목업 사용자탭 금지).
- **REQ-XMETRIC-INPUT-3 (Ubiquitous)** — 탭은 NPS·defect-통계의 다중 프레임 입력을 **정렬 스택**(`list[XFrame]`)으로 다뤄야 하며 단일 프레임으로 축약해선 안 된다(`compute_nps`·`classify_defects`의 리스트 계약 반영, nps.py:83 / defect_stats.py:57).

### REQ-XMETRIC-PARAM — 정확한 Params 키 (REQ-METRICS-CORE-4, 외부화)

- **REQ-XMETRIC-PARAM-1 (Ubiquitous)** — 탭은 각 지표에 대해 골든이 요구하는 정확한 Params 키만 공급해야 한다: MTF=`{pixel_pitch_mm, mtf_oversample, mtf_angle_min_deg, mtf_angle_max_deg, mtf_angle_margin_deg}`, NPS=`{pixel_pitch_mm, nps_roi_size, nps_detrend_order, nps_exclude_axis_bins, nps_average_lines, nps_central_frac}`(+ line-noise 시 `line_noise_sig_factor`), DQE=`{dqe_q, dqe_ka, dqe_nps_floor}`, defect-통계=`{defect_min_frames, defect_over_value, defect_under_value, defect_dead_gain_frac, defect_nonuniform_frac, defect_lag_frac, defect_unstable_frac}`(defect_stats.py:31-37, require :78/98-103). `pixel_pitch_mm`는 검출기/세션별 편집 입력, 나머지 [P] 상수는 골든 기본과 동일한 외부화 값이어야 하며 GUI가 새 상수를 발명해선 안 된다. defect-통계의 `NOISY_MEDIAN_MULTIPLIER=6.0`은 ASTM E2597-22 확정 [S] 상수이므로 Param으로 공급되지 않는다(defect_stats.py:27-29).
- **REQ-XMETRIC-PARAM-2 (Unwanted)** — IF 어떤 지표의 필수 Params 키가 결여되면, THEN 엔진은 그 키를 명시한 `MetricReadError`를 던지고(require_param, result.py:89-91) 탭은 이를 그대로 표면화해야 하며, 어떤 기본값도 대체돼선 안 된다(엔진은 기본 추정치를 대신 넣지 않는다, result.py:60-67).
- **REQ-XMETRIC-PARAM-3 (Ubiquitous)** — optional acquisition provenance `beam_quality`, `dose_level`, `added_filter`, `temperature_c`는 제공된 값만 `MetricCondition`으로 운반하고, 없을 때 UI/adapter가 추정하거나 기본값을 삽입하지 않아야 한다.

### REQ-XMETRIC-COMPUTE — 위임 산출: DSP 0 (C-09, SPEC-VIEWER-001 RUN-3/4 C-09 확장)

- **REQ-XMETRIC-COMPUTE-1 (Event-Driven)** — WHEN 사용자가 산출을 트리거하면, THEN WPF는 지표별 dedicated `IXdetEngine` request를 호출하고 반환된 `MetricResultEnvelope`의 axes/series/scalars/warnings/condition만 렌더해야 한다. UI/adapter는 지표 값을 계산·보간·재스케일하지 않는다.
- **REQ-XMETRIC-COMPUTE-2 (Event-Driven)** — WHEN 사용자가 호환되는 MTF/NPS 결과로 DQE를 실행하면 THEN engine은 `NPS_BINS_WITHIN_MTF_SUPPORT_V1`로 target bin을 선택하고 각 bin에서 `metrics.mtf.mtf_value_at`을 호출한 뒤 `metrics.dqe.compute_dqe`를 호출해야 한다. 결과는 선택/제외 bin과 upstream run/hash를 포함해야 한다.
- **REQ-XMETRIC-COMPUTE-4 (Unwanted)** — IF MTF/NPS unit·pixel pitch·domain·beam quality가 불일치하거나 axis가 비유한/비단조이면 THEN DQE는 명시 오류로 거부돼야 한다. IF NPS bin이 MTF support 밖이면 THEN endpoint clamp·외삽하지 않고 제외해야 한다.
- **REQ-XMETRIC-COMPUTE-3 (Ubiquitous)** — 탭은 곡선·스칼라·`warnings`·`MetricCondition`을 표시하되 EV min/typ/max 합격/불합격 **판정을 산출해선 안 된다** — 엔진은 측정만 하고 게이팅하지 않으며 판정은 엔진 밖 몫이다(result.py:10-12, REQ-METRICS-CORE-5). GUI가 판정을 계산하면 C-09 위반이다.

### REQ-XMETRIC-VIEW — 곡선/히스토그램·스칼라 뷰어 특성 + ROI 왕복 (C-10, 그룹 고유)

- **REQ-XMETRIC-VIEW-1 (Ubiquitous)** — MTF/NPS/DQE의 뷰는 주파수축(lp/mm) 곡선 플롯 + 스칼라 판독이어야 한다(MTF 곡선·`mtf_at_nyquist`·`edge_angle_deg`·`nyquist_lpmm`; NPS/NNPS 곡선·`mean_signal`·`n_roi`; DQE(f)·`invalid_indices`) — 이미지 before/after/diff 뷰어(그룹 1~6)나 시간 시퀀스 뷰어(그룹 2)와 구별된다.
- **REQ-XMETRIC-VIEW-2 (Ubiquitous)** — defect-통계의 뷰는 주파수축 곡선이 아니라 **E2597 클래스 히스토그램(`counts`)·분율(`fractions`) + 선택적 2D `class_map` 공간 표시**여야 한다(`class_map`은 주파수축이 없는 2D 이미지, defect_stats.py:145-149). `miss_rate`는 `truth_map`이 공급된 경우에만 표시하고, 부재 시 `None`이므로(defect_stats.py:132-140) 표시하지 않는다. 이 뷰는 VIEW-1의 곡선 프레이밍과도, 그룹 1의 이미지 마스크 오버레이(분류 적용 결과)와도 목적이 다르다(분류 통계 판독).
- **REQ-XMETRIC-VIEW-3 (Event-Driven)** — WHEN 사용자가 MTF 소스 프레임에서 ROI를 이동·리사이즈하고 재산출하면, THEN 사용된 정확한 ROI 경계(top/left/height/width)가 보고되고, 동일 경계를 두 번 재슬라이스해 재산출한 `MetricResult`는 bit-동일해야 한다(왕복 재현성, 결정론적 엔진 — 현행 recompute_mtf_for_roi 선례 app.py:688-706 / metrics_panel.py:77).
- **REQ-XMETRIC-VIEW-4 (Ubiquitous)** — 탭은 각 곡선/히스토그램 옆에 비치명 `warnings`(예: MTF 각도 경계근접 mtf.py:182-187, DQE 무효 bin dqe.py:71-75)와 `MetricCondition` 메타데이터(beam_quality, dose_level, temperature_c, added_filter, correction_state, roi, params_hash, calibset_id; result.py:22-37)를 함께 표시해 추적성을 보존해야 한다.

### REQ-XMETRIC-DATA — 등록 SAMPLE 적용성 + #33 (QUARANTINE, G-5)

- **REQ-XMETRIC-DATA-1 (Optional)** — WHERE 등록 nps_flat SAMPLE 스택이 가용하면, 탭은 `compute_nps`를 sanity(유한·비퇴화 NNPS·구조 성립) 확인용으로 구동할 수 있어야 한다 — 수치 골든이 아니라(QUARANTINE).
- **REQ-XMETRIC-DATA-2 (Ubiquitous)** — 등록세트에는 슬랜티드-엣지 팬텀이 없어 MTF/DQE의 등록 정본 증거는 #33 대기다. 합성 실행은 `SYNTHETIC_VERIFIED`, strict 외부 실측 실행은 승인 전 `USER_SUPPLIED_UNVERIFIED`로 표시하고 알고리즘 자체를 비활성화하지 않아야 한다.
- **REQ-XMETRIC-DATA-3 (Optional)** — WHERE 등록 dark/flat SAMPLE 스택이 가용하면, 탭은 `classify_defects(dark_frames, flat_frames, ...)`를 E2597-class sanity 확인용으로만 구동할 수 있어야 한다 — `classify_defects`의 입력은 dark 스택 + flat 스택이며(defect_stats.py:57), 등록 BPM(DEFECT `K_CLASS_MAP`)은 입력 스택이 아니라 dark/flat로부터 산출되는 CalibSet이므로 필요 시 **선택적 `truth_map`(진리맵)** 으로만 전달돼 miss-rate sanity에 쓰인다(defect_stats.py:63/132-140).
- **REQ-XMETRIC-DATA-4 (Unwanted)** — IF SAMPLE(비정본, panel_id `SAMPLE-EDROGI-16BIT`) 데이터가 사용되면, THEN 결과는 sanity 라벨로 표기되고 수치 골든/튜닝/적합·EV 임계 도출에 쓰여선 안 된다(QUARANTINE, foundation G-5).

### REQ-XMETRIC-EXPORT — 내보내기 게이트 (C-20)

- **REQ-XMETRIC-EXPORT-1 (Event-Driven)** — WHEN 사용자가 지표 결과를 내보내면, THEN C# export choke point는 사용자 지정 폴더에 `<name>_metrics.json`과 `<name>_run_manifest.json`을 기록하고 `data/` 하위를 typed validation error로 거부해야 한다. WPF/adapter는 Python export/GUI helper를 직접 호출하지 않는다.
- **REQ-XMETRIC-EXPORT-2 (Ubiquitous)** — `<name>_metrics.json`은 `schema_version: xdet.metrics-report/1.0`, run_id, FeatureId, ordered EntryPoints, metric, source_artifacts(path/hash/evidence_grade), params_hash, condition, axes(name/unit/values), series(name/unit/values), scalars, warnings를 포함한다. 선택 CSV는 각 axis/series 열과 단위를 헤더에 기록한다. source/ROI frame을 별도 저장할 때만 `xdet.frame-artifact/1.0`을 사용하며 곡선을 raw frame으로 저장하지 않는다. `xdet.run-manifest/1.0`은 리포트와 source frame hash를 연결한다.

### REQ-XMETRIC-GUARD — 골든 FROZEN + DSP-0 가드 (G-1/G-2, C-09/C-11)

- **REQ-XMETRIC-GUARD-1 (Unwanted)** — IF GUI 또는 어댑터가 어떤 지표 값을 스스로 계산하거나, 엔진 산출을 새 지표 값으로 재계산·재스케일하거나, EV 합격/불합격 판정을 도출하면, THEN 이는 거부돼야 한다(C-09 DSP-0 + 엔진 측정-전용, result.py:10-12).
- **REQ-XMETRIC-GUARD-2 (Unwanted)** — IF 어떤 변경이 골든 `metrics/*`(mtf/nps/dqe/defect_stats/defect_map/result)의 시그니처·수치·상수를 수정하면, THEN 이는 거부돼야 한다 — 탭은 호출만 하고, 신규 GUI 지원 코드는 `apps/xdet-console/`에만 additive로 두며(그리고 필요 시 additive apps 헬퍼) `metrics/`에 두지 않는다(foundation G-1, FROZEN 오라클).

### REQ-XMETRIC-COVERAGE — 지표 공개 연산 전수 귀속

- **REQ-XMETRIC-COVERAGE-1 (Ubiquitous)** — Metrics 탭은 `compute_mtf`, `compute_nps`, `detect_line_noise`, `compute_dqe`, `classify_defects`를 ACTION으로 노출하고 `estimate_edge_angle`, `mtf_value_at`, `dqe_value_at`을 부모 MetricResult의 DERIVED diagnostics로 귀속해야 한다.
- **REQ-XMETRIC-COVERAGE-2 (Event-Driven)** — WHEN 사용자가 곡선의 지정 주파수 값을 조회하면 THEN engine은 실제 `mtf_value_at` 또는 `dqe_value_at`을 호출해 값을 반환하고 UI가 보간하지 않아야 한다.
- **REQ-XMETRIC-COVERAGE-3 (Event-Driven)** — WHEN line-noise 분석을 요청하면 THEN 실제 `metrics.nps.detect_line_noise`가 호출되고 MetricResult가 표시·export돼야 한다.

## Exclusions (What NOT to Build)

- **골든 지표 모델 변경 없음** — `metrics/{mtf,nps,dqe,defect_stats,defect_map,result}.py`는 동결 오라클로 편집하지 않는다. 탭은 이들을 읽기-실행 전용으로 소비한다(REQ-XMETRIC-GUARD-2). 모든 사실은 Grep/Read 대조검증했고 지어내지 않았다.
- **GUI에서의 DSP·지표 재계산 없음** — 모든 지표 값은 골든 엔진 반환값이다. GUI는 곡선/수치 렌더와 입력세트 조립만 하며 MTF/NPS/DQE/분류 계산을 인라인으로 재구현하지 않는다(C-09).
- **EV 판정(합격/불합격) 산출 없음** — 엔진은 측정만 하고 게이팅하지 않는다(result.py:10-12). 탭은 EV min/typ/max pass/fail을 계산·표시하지 않는다; 판정은 엔진 밖(수용 시험/외부 평가) 몫이다.
- **신규 Params 키·신규 지표·신규 반환 필드 없음** — 산출은 기존 공개 엔진 함수·기존 Params 키로만 이뤄진다. 본 SPEC은 지표나 Params 키를 신설하지 않는다.
- **모듈 실행(run_pipeline) 조합 없음** — Metrics는 CalibKind 소비 모듈 그룹이 아니다. 본 탭은 `run_pipeline`/`PipelineDefinition`/스테이지 조합을 사용하지 않는다(그건 그룹 1~6 조합 SPEC 몫). DQE의 "합성"은 파이프라인 조합이 아니라 두 지표 결과의 산술 합성이다.
- **정본 수치 검증 없음(QUARANTINE)** — SAMPLE(에드로지) 구동은 sanity(유한·비퇴화·구조)일 뿐 수치 골든/EV 임계 도출·튜닝·적합에 쓰지 않는다(이슈 #29). 정본 MTF/DQE 수치 검증은 정본 지침세트(이슈 #33) 도착 후 별건이다.
- **등록 MTF/DQE 정본 주장 없음** — 슬랜티드-엣지 등록 정본이 없으므로 `GOLDEN_APPROVED`를 주장하지 않는다. 다만 strict 사용자 제공 실측 입력 실행은 허용하고 `USER_SUPPLIED_UNVERIFIED`로 표시한다.
- **성능·렌더 최적화 없음** — 대용량 3072² 스택의 NPS ROI 타일링·곡선 렌더 스루풋 최적화는 범위 밖이다(정확성·재현성 증명이 목적, P2).
- **Gen 2·배포 없음** — DL/ADR, 웹 서버·다중 사용자·배포는 범위 밖(foundation 승계).

## 확정 결정 (v0.5.1)

1. MTF, NPS, Defect는 입력 계약이 다르므로 지표별 source widget을 분리한다.
2. 지표 리포트는 `<name>_metrics.json`을 필수로 하고 곡선 CSV를 선택 산출물로 제공한다. frame raw는 frame export일 때만 사용한다.
3. DQE는 engine-owned `NPS_BINS_WITHIN_MTF_SUPPORT_V1` service가 골든 `mtf_value_at`+`compute_dqe`를 호출해 활성화한다. UI interpolation과 support 밖 외삽은 금지한다.
4. SAMPLE sanity는 유한성·shape·비퇴화 같은 구조 조건만 검사하며 새로운 수치 임계값이나 EV 판정을 만들지 않는다.
5. 중앙 TC 레지스트리는 G8 블록 XDET-TC-152~159이다.

## v0.5.1 public operation closure

| Python EntryPoint | GUI 노출 | TC |
|---|---|---|
| `metrics.mtf.estimate_edge_angle` | MTF diagnostic/sub-command | 152 |
| `metrics.mtf.compute_mtf` | MTF action | 153 |
| `metrics.mtf.mtf_value_at` | scalar-at action 및 DQE engine composition | 154~155 |
| `metrics.nps.compute_nps` | NPS action | 153 |
| `metrics.nps.detect_line_noise` | line-noise metric action | 154 |
| `metrics.dqe.compute_dqe` | DQE composition action | 155 |
| `metrics.dqe.dqe_value_at` | DQE scalar-at action | 156 |
| `metrics.defect_map.classify_morphology` | defect morphology diagnostic | 157 |
| `metrics.defect_map.build_defect_map` | defect-map build action | 157 |
| `metrics.defect_stats.classify_defects` | defect-stats action | 158 |
| `metrics.result.MetricResult.get` | typed result access | 159 |
| `metrics.result.require_param` | Params validation | 159 |
| `metrics.result.metric_view` | read-only result serialization | 159 |

모든 행은 engine call trace 또는 부모 call 내부 trace와 golden-direct fidelity로 검증한다. TC-164는 DQE support-bin 정책과 두 golden EntryPoint 호출을 추가로 검증한다.
