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

# SPEC-XGUI-METRICS — 인수 기준 (acceptance)

> 본 인수기준의 모든 EARS ID·중앙 TC·필수 증거 연결은 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따른다. `baseline-control.md`의 G0와 사용자 승인 전에는 이 체크리스트를 구현 완료 증거로 사용할 수 없으며 모든 TC는 `PLANNED` 상태를 유지한다.

> **구현 대상:** `apps/xdet-console/` C# WPF 앱. `apps/gui/`와 Python 테스트는 계약·검증 선례이며 구현 대상이 아니다.
Metrics 그룹(MTF/NPS/DQE/line-noise + defect 통계) 검증 GUI 탭의 Given-When-Then. 모든 기준은 관측 가능해야 한다 — strict 입력 열기, 모든 지표 실제 위임 구동, DQE golden-owned composition, 반환 DTO 렌더, report/export, 명시 오류, 골든 무변경. 각 시나리오는 XDET-TC-152~159와 공통 164/166에 귀속한다.

이 그룹은 **모듈 실행 그룹이 아니다.** `run_pipeline` 대신 WPF가 dedicated `IXdetEngine` metric DTO를 호출하고 PythonNet adapter만 Python 지표 엔진에 위임한다. 워크플로는 **입력세트 조립 → typed metric request → 곡선/히스토그램/수치 렌더 → 리포트/프레임 저장**이다.

실측 SAMPLE 구동은 QUARANTINE이며 정본 수치 주장을 하지 않는다. 등록 NPS/defect는 SAMPLE sanity로 사용한다. 등록 MTF/DQE 정본은 없지만 합성 또는 `xdet.input-set/1.0` 사용자 제공 실측으로 실행 가능하며 각각 `SYNTHETIC_VERIFIED` 또는 `USER_SUPPLIED_UNVERIFIED`로 표시한다.

골든 대상(FROZEN, 호출만): `metrics/mtf.py::compute_mtf`(mtf.py:142)·`estimate_edge_angle`(mtf.py:48)·`mtf_value_at`(mtf.py:212) · `metrics/nps.py::compute_nps`(nps.py:83)·`detect_line_noise`(nps.py:152) · `metrics/dqe.py::compute_dqe`(dqe.py:31)·`dqe_value_at`(dqe.py:96) · `metrics/defect_stats.py::classify_defects`(defect_stats.py:57) · `metrics/result.py::{MetricResult,MetricCondition,MetricReadError,require_param}`(result.py:41/22/60/73) · `apps/gui/metrics_panel.py::{plot_mtf,recompute_mtf_for_roi}`(metrics_panel.py:65/77, 배열 동일성 :5-9) · `common.io.load_raw_frame`(io.py:35) · C# engine/adapter raw export(신설, foundation §3, 프레임 저장 전용) · C# engine/adapter C-20 guard (Python `apps.gui.io_panel.guard_output_path` 선례)(io_panel.py:27).

## Scenarios (Given-When-Then)

### Scenario 1 — 지표별 입력세트 조립 + 소스(상류/폴더 브라우저) (XDET-TC-152, REQ-XMETRIC-INPUT-1/2/3)
- **Given** Metrics 탭과 상주 폴더 브라우저(폴더트리 + 가상화 썸네일 + 형제 필름스트립 + 이전/다음)가 있고, 기본 소스가 등록 실측 세트(에드로지 SAMPLE / #33)이며,
- **When** 사용자가 한 지표(MTF/NPS/DQE/defect-통계)를 선택하고 그 지표의 입력세트를 공급하면,
- **Then** (i) 탭이 그 지표의 **정확한 엔진 입력 형태**를 조립한다 — MTF는 단일 엣지-슬랩 `XFrame` + ROI(`compute_mtf(frame, ...)`, mtf.py:142), NPS는 flat `XFrame`의 정렬 **스택** `list[XFrame]`(`compute_nps(frames, ...)`, nps.py:83, `if not frames` 가드 nps.py:101), DQE는 앞선 MTF `MetricResult`와 NPS `MetricResult`(새 프레임 로드 없음, dqe.py:31), defect-통계는 dark `XFrame` 스택 + flat `XFrame` 스택(`classify_defects(dark_frames, flat_frames, ...)`, defect_stats.py:57) — 그리고 그 입력을 변형 없이 엔진에 전달하며, (ii) 소스가 상류 탭 엔진 출력이면 자체 파일 로드 없이 직접 소비하고(C-09, app.py:647-654 선례), 등록 데이터셋이면 상주 폴더 브라우저(`load_raw_frame`, io.py:35)로 로드하고 지정 파일의 **부모 폴더 형제 목록**(필름스트립 + 이전/다음)을 함께 표시하며(파일 단독 열기 아님; 합성 목업 사용자탭 금지), (iii) NPS·defect-통계의 다중 프레임 입력을 정렬 스택으로 다루고 단일 프레임으로 축약하지 않는다(리스트 계약 nps.py:83 / defect_stats.py:57).

### Scenario 2 — 정확한 Params 키(4지표, defect 7키 포함) + 결여 시 명시 오류 (XDET-TC-153, REQ-XMETRIC-PARAM-1/2)
- **Given** 각 지표의 Params 입력 폼이 노출되고,
- **When** 사용자가 지표별 Params를 입력하거나 필수 키를 비우면,
- **Then** (i) 탭이 골든이 요구하는 정확한 키만 공급한다 — MTF=`{pixel_pitch_mm, mtf_oversample, mtf_angle_min_deg, mtf_angle_max_deg, mtf_angle_margin_deg}`(mtf.py:28-32/167-171), NPS=`{pixel_pitch_mm, nps_roi_size, nps_detrend_order, nps_exclude_axis_bins, nps_average_lines, nps_central_frac}`(nps.py:28-33/103-108, +line-noise 시 `line_noise_sig_factor` nps.py:34), DQE=`{dqe_q, dqe_ka, dqe_nps_floor}`(dqe.py:26-28/60-62), **defect-통계=`{defect_min_frames, defect_over_value, defect_under_value, defect_dead_gain_frac, defect_nonuniform_frac, defect_lag_frac, defect_unstable_frac}`**(defect_stats.py:31-37, require defect_stats.py:78/98-103) — `pixel_pitch_mm`만 검출기/세션별 편집 입력이고 나머지 [P] 상수는 골든 기본과 동일한 외부화 값이며 UI가 새 상수를 발명하지 않고, (ii) defect-통계의 `NOISY_MEDIAN_MULTIPLIER=6.0`은 ASTM E2597-22 확정 [S] 상수이므로 **Param으로 공급되지 않으며**(defect_stats.py:27-29, 튜닝 금지), (iii) 어떤 지표의 필수 키가 결여되면 엔진 `require_param`(result.py:73)이 그 키를 명시한 `MetricReadError`(result.py:60/89-91)를 던지고 탭이 이를 그대로 표면화하며 어떤 기본값도 대체하지 않는다.

### Scenario 3 — 위임 산출 DSP-0: MTF/NPS/defect + 판정 없음 (XDET-TC-154, REQ-XMETRIC-COMPUTE-1/3) — **load-bearing**
- **Given** MTF 엣지-슬랩 프레임(합성/#33 또는 상류 출력)·NPS flat 스택(등록 nps_flat SAMPLE)·defect dark/flat 스택이 각각 조립되고,
- **When** 사용자가 각 지표 산출을 트리거하면,
- **Then** (i) 탭이 지표별 dedicated `IXdetEngine` method를 호출하고 반환 `MetricResultEnvelope`의 배열/스칼라만 렌더하며 PythonNet adapter만 `compute_mtf`/`compute_nps`/`classify_defects`에 위임하고, (ii) 탭은 EV min/typ/max 합격/불합격 판정을 산출하지 않으며, (iii) NPS의 nnps/mean_signal/n_roi와 defect의 counts/fractions/class_map이 유한·비퇴화로 렌더된다(C-09/C-11).

### Scenario 4 — DQE engine-owned 실제 합성 (XDET-TC-155/164, REQ-XMETRIC-COMPUTE-2/4)
- **Given** MTF `MetricResult`(주파수축 = `rfftfreq(n, d=1/oversample)/pitch`, 오버샘플·Nyquist 배수까지, mtf.py:126/138)와 NPS `MetricResult`(주파수축 = `axial_1d_nps`, Nyquist까지, nps.py:123)가 산출되어 **두 축의 범위·간격이 다르고**,
- **When** 사용자가 DQE 산출을 시도하면,
- **Then** (i) engine이 두 axis의 유한성·엄격 증가·`lp/mm` 단위와 pixel pitch/domain/beam quality 호환성을 확인하고, (ii) `NPS_BINS_WITHIN_MTF_SUPPORT_V1`로 MTF support 안 NPS bin만 선택하며, (iii) 각 선택 bin에서 실제 `metrics.mtf.mtf_value_at`을 호출한 뒤 실제 `metrics.dqe.compute_dqe`를 호출하고, (iv) support 밖 bin은 외삽하지 않고 index/reason을 기록하며, (v) UI/transport 자체 보간은 0건이어야 한다.

### Scenario 5 — 그룹 고유 뷰: 곡선(MTF/NPS/DQE/line-noise) + defect 히스토그램/class_map + ROI 왕복 (XDET-TC-156, REQ-XMETRIC-VIEW-1/2/3/4)
- **Given** MTF/NPS/DQE/line-noise 결과와 defect-통계 결과가 산출되고,
- **When** 탭이 각 지표를 렌더하고 사용자가 MTF ROI를 이동·리사이즈해 재산출하면,
- **Then** (i) MTF/NPS/DQE는 **주파수축(lp/mm) 곡선 + 스칼라 판독**으로 렌더되고(MTF 곡선·`mtf_at_nyquist`·`edge_angle_deg`·`nyquist_lpmm` mtf.py:199-205; NPS/NNPS 곡선·`mean_signal`·`n_roi` nps.py:145-146; DQE(f)·`invalid_indices` dqe.py:82), (ii) **defect-통계만은 곡선이 아니라 E2597 클래스 히스토그램(`counts`)·분율(`fractions`) + 선택적 2D `class_map` 공간 표시**로 렌더되며 `class_map`은 주파수축 없는 2D 이미지이고(defect_stats.py:145-149) `miss_rate`는 `truth_map`이 공급된 경우에만 표시하고 부재 시 `None`이라 표시하지 않으며(defect_stats.py:132-140), (iii) 사용자가 MTF 소스 프레임에서 ROI를 이동·리사이즈해 재산출하면 사용된 정확한 ROI 경계(top/left/height/width)가 보고되고 동일 경계를 두 번 재슬라이스해 재산출한 `MetricResult`가 **bit-동일**하며(왕복 재현성, recompute_mtf_for_roi 선례 app.py:688-706 / metrics_panel.py:77), (iv) 각 곡선/히스토그램 옆에 비치명 `warnings`(MTF 각도 경계근접 mtf.py:182-187, DQE 무효 bin dqe.py:71-75)와 `MetricCondition` 메타데이터(beam_quality/dose_level/params_hash/calibset_id, result.py:22-37)를 함께 표시한다.

### Scenario 6 — 등록 SAMPLE과 사용자 제공 실측 증거 분리 (XDET-TC-157/166, REQ-XMETRIC-DATA-1/2/3/4)
- **Given** 등록 실측(에드로지 SAMPLE, panel_id `SAMPLE-EDROGI-16BIT`) 세트가 있고,
- **When** 각 지표를 등록 데이터로 구동 시도하면,
- **Then** (i) 등록 nps_flat은 `SAMPLE_SANITY`로 `compute_nps`를 실행하고, (ii) 등록 MTF/DQE 정본은 없음을 표시하되 합성 입력은 `SYNTHETIC_VERIFIED`, strict 외부 실측은 `USER_SUPPLIED_UNVERIFIED`로 실행하며, (iii) defect dark/flat은 가용할 때 SAMPLE sanity로 실행하고 BPM은 선택적 truth map으로만 사용하며, (iv) 어떤 낮은 evidence 결과도 정본 수치/EV/튜닝 근거로 승격하지 않아야 한다.

### Scenario 7 — 저장/열기 E2E: 지표 리포트 + 프레임 `<name>_result.raw` + C-20 게이트 + 재적재 (XDET-TC-158, REQ-XMETRIC-EXPORT-1/2) — **load-bearing E2E**
- **Given** 상주 폴더 브라우저로 연 등록 SAMPLE(nps_flat) 스택과 그 `compute_nps` 결과(곡선·스칼라·`MetricCondition`)가 있고,
- **When** 사용자가 **열기 → 지표 위임 산출 → 저장 → 재적재 검증** E2E를 수행하면,
- **Then** (i) `<name>_metrics.json`은 `xdet.metrics-report/1.0`의 run_id, FeatureId, ordered EntryPoints, metric, source_artifacts(path/hash/evidence_grade), params_hash, condition, axes(name/unit/values), series(name/unit/values), scalars, warnings를 포함하고 선택 CSV는 단위 헤더를 가지며, (ii) 곡선을 raw frame으로 저장하지 않고 source/ROI frame에만 `xdet.frame-artifact/1.0`을 적용하며, (iii) `<name>_run_manifest.json`이 source/report/frame hash를 연결하고, (iv) C# export choke point가 `data/` 하위를 typed error로 거부하며, (v) SAMPLE 왕복은 IO·산출·왕복 sanity일 뿐 수치 golden/EV 도출·튜닝에 쓰지 않는다.

### Scenario 8 — 불변 가드: 골든 FROZEN + DSP-0 + 판정 없음 + 골든 무변경 (XDET-TC-159, REQ-XMETRIC-GUARD-1/2)
- **Given** 탭·어댑터가 지표를 위임 구동하고,
- **When** 실행 후 코드 경로·의존 방향·쓰기 대상·골든 트리를 검사하면,
- **Then** (i) 어떤 지표 값도 UI/adapter가 계산·보간·재스케일·판정하지 않고, (ii) 모든 WPF 호출이 dedicated `IXdetEngine` DTO를 통과하며 Python `apps.gui` helper 의존이 0건이고, (iii) 골든 metrics 시그니처·수치·상수가 무변경이며, (iv) C# export choke point가 `data/` 하위를 거부하고, (v) `metrics/`·`common/`·`pipeline/`이 무변경이어야 한다(C-09/C-11/C-20).

### Scenario — line-noise와 scalar-at 파생 연산

- **Given** flat stack과 MTF/DQE MetricResult가 있고,
- **When** line-noise 분석과 지정 주파수 scalar 조회를 실행하면,
- **Then** 실제 `detect_line_noise`, `mtf_value_at`, `dqe_value_at` 호출 결과가 golden-direct와 동일하고 UI 보간 코드가 없어야 한다.

## Edge Cases

- **DQE 축/metadata 불일치는 FAIL (REQ-XMETRIC-COMPUTE-2/4)** — 비단조·비유한 축, `lp/mm` 이외 단위, pixel pitch/domain/beam quality 불일치는 명시 거부돼야 한다.
- **GUI 보간 또는 support 밖 외삽은 FAIL·C-09 위반** — UI/transport가 `np.interp`류로 MTF를 만들거나 engine이 MTF support 밖 NPS bin에 endpoint 값을 대입하면 인수 실패한다.
- **필수 Params 키 결여는 FAIL·무단 대체 없음 (REQ-XMETRIC-PARAM-2)** — 어느 지표든 필수 키(예: MTF `pixel_pitch_mm`, defect `defect_min_frames`)를 비우고 구동하면 골든 `MetricReadError`로 거부돼야 하고 UI가 기본값을 지어내면 인수 실패(음성 대조: 키 제거 시 실제 예외 발생 확인).
- **MTF 각도 범위 밖은 FAIL, 경계근접은 비치명 warning (REQ-XMETRIC-VIEW-4)** — 엣지 각도가 `[mtf_angle_min_deg, mtf_angle_max_deg]` 밖이면 골든 `MetricReadError`(mtf.py:178)로 거부되고(0/90도 언더샘플링 방어), margin 이내 경계근접이면 거부가 아니라 비치명 `warnings`(mtf.py:183-187)로 표시돼야 한다.
- **defect 스택 부족은 FAIL (REQ-XMETRIC-INPUT-3)** — dark/flat 스택 수가 `defect_min_frames` 미만이거나(defect_stats.py:79-83) 유효 픽셀이 없어(비양수 median gain, defect_stats.py:90-93) 골든 `MetricReadError`가 나면 탭이 그대로 표면화해야 한다.
- **EV 판정(합격/불합격) 산출은 FAIL (REQ-XMETRIC-COMPUTE-3, GUARD-1)** — 탭이 EV min/typ/max pass/fail을 계산·표시하면 인수 실패 — 엔진은 측정만 하고(result.py:10-12) 판정은 엔진 밖 몫이다.
- **곡선을 `_result.raw`로 저장은 FAIL (REQ-XMETRIC-EXPORT-2)** — 지표 곡선(frequencies+values)을 16-bit `<name>_result.raw` 프레임으로 저장하면 인수 실패 — 곡선은 `<name>_metrics.json`/CSV 리포트로만, `_result.raw`는 소스/ROI **프레임** 저장에만 적용된다.
- **`data/` 하위 저장은 FAIL (REQ-XMETRIC-EXPORT-1, GUARD-1)** — 리포트/프레임 저장 경로가 `<project_root>/data` 하위이면 C# export choke point가 쓰기 전에 typed error로 거부해야 한다.
- **등록 MTF/DQE를 정본으로 주장은 FAIL (REQ-XMETRIC-DATA-2)** — 등록 슬랜티드-엣지 정본이 없으므로 `GOLDEN_APPROVED`로 표시하면 실패다. strict 외부 실측 실행 자체는 허용하되 `USER_SUPPLIED_UNVERIFIED`여야 한다.
- **SAMPLE 실측의 수치 오용 (QUARANTINE, 이슈 #29)** — 등록 SAMPLE(에드로지) NPS/defect sanity 결과를 정본 수치/EV 임계 도출·튜닝·적합에 쓰면 인수 실패 — sanity(유한·비퇴화·구조)만 허용, 정본 수치 검증은 #33 도착 후 별건.

## Definition of Done (체크리스트)

- [ ] 지표별 정확한 입력 형태 조립 — MTF 단일 엣지 프레임+ROI / NPS flat 정렬 스택 / DQE 두 `MetricResult` 합성(새 프레임 없음) / defect dark+flat 스택 — 변형 없이 엔진 전달 (XDET-TC-152, INPUT-1)
- [ ] 소스 이원화: 상류 출력 직접 소비(C-09) + 등록 데이터 상주 폴더 브라우저(부모 폴더 형제 목록 동시 표시, 합성 목업 금지) (XDET-TC-152, INPUT-2)
- [ ] NPS·defect 다중 프레임을 정렬 스택으로 다룸(단일 프레임 축약 없음) (XDET-TC-152, INPUT-3)
- [ ] 4지표 정확한 Params 키 공급 — MTF 5키 / NPS 6키(+line-noise 1키) / DQE 3키 / **defect 7키**; `NOISY_MEDIAN_MULTIPLIER=6.0`은 [S]로 Param 아님 (XDET-TC-153, PARAM-1)
- [ ] 필수 키 결여 시 골든 `MetricReadError`(키 명시) 그대로 표면화 + 무단 기본값 대체 없음 (XDET-TC-153, PARAM-2; 음성 대조 포함)
- [ ] MTF/NPS/defect를 정확한 엔진 진입점으로 위임 호출 + 반환 `MetricResult` 배열/스칼라만 렌더(GUI DSP 0) (XDET-TC-154, COMPUTE-1)
- [ ] EV 합격/불합격 판정 미산출(엔진 측정-전용, result.py:10-12) (XDET-TC-154, COMPUTE-3)
- [ ] DQE engine composition은 support 안 NPS bin마다 실제 `mtf_value_at` 호출 후 `compute_dqe` 호출 + 선택/제외 bin/upstream hash 기록 + GUI 보간 0건 (XDET-TC-155/164, COMPUTE-2/4)
- [ ] MTF/NPS/DQE 주파수축 곡선+스칼라 렌더 (XDET-TC-156, VIEW-1)
- [ ] defect-통계 E2597 클래스 히스토그램/분율 + 선택적 2D `class_map` + `miss_rate`는 `truth_map` 있을 때만 (XDET-TC-156, VIEW-2)
- [ ] MTF ROI 왕복 재현성 — 정확한 ROI 경계 보고 + 동일 경계 2회 재산출 bit-동일(C-10) (XDET-TC-156, VIEW-3)
- [ ] 비치명 `warnings` + `MetricCondition` 메타데이터 표시(추적성) (XDET-TC-156, VIEW-4)
- [ ] NPS 등록 nps_flat 스택 `compute_nps` sanity(유한·양수·비퇴화 NNPS) (XDET-TC-157, DATA-1)
- [ ] MTF/DQE 합성은 `SYNTHETIC_VERIFIED`, strict 외부 실측은 `USER_SUPPLIED_UNVERIFIED`, 등록 정본은 #33 대기 (XDET-TC-157/166, DATA-2)
- [ ] defect-통계는 등록 dark/flat 가용 시 optional sanity(BPM은 선택적 `truth_map`, 입력 아님) (XDET-TC-157, DATA-3)
- [ ] SAMPLE 결과 sanity 라벨 표기 + 수치 golden/EV/튜닝 미사용 (XDET-TC-157, DATA-4; QUARANTINE 이슈 #29)
- [ ] `xdet.metrics-report/1.0`(+단위 CSV)과 `xdet.run-manifest/1.0` 저장 — 곡선을 raw frame으로 저장 안 함 (XDET-TC-158, EXPORT-2)
- [ ] 프레임 저장 시에만 `<name>_result.raw`(16-bit `<u2`)+사이드카(C# engine/adapter raw export) (XDET-TC-158, EXPORT-2)
- [ ] C# export choke point의 `data/` 거부, frame artifact round-trip, source/report/frame manifest hash 일치 (XDET-TC-158, EXPORT-1)
- [ ] UI DSP 0 + 재계산/재스케일/판정 도출 없음 + 단방향 소비 (XDET-TC-159, GUARD-1)
- [ ] `metrics/{mtf,nps,dqe,defect_stats,defect_map,result}.py` 무변경(git diff 없음) + 신규 코드는 `apps/xdet-console/` additive; C# engine/adapter raw export는 기존 표면 무변경 (XDET-TC-159, GUARD-2)
- [ ] `uv run pytest` 무회귀 green + `uv run lint-imports` green·불변

## 판정 원칙 (측정=판정 분리)

- **골든이 산출, UI는 표시.** 모든 MTF/NPS/DQE/defect 값·`warnings`·`MetricCondition`은 골든 엔진(`compute_*`·`classify_defects`)에서 발생한다. 탭의 load-bearing 인수 기준은 골든 결과의 정확한 소비·표시·ROI 왕복 재현성·무회귀·명시 거부이지 SAMPLE 절대 수치가 아니다(C-09/C-11).
- **엔진은 측정만·판정 안 함.** EV min/typ/max pass/fail은 `MetricResult`에 없고(result.py:10-12) 엔진 밖 몫이다. 탭은 곡선·수치·`warnings`·`MetricCondition`을 표시하되 합격/불합격을 계산하지 않는다(C-09를 판정까지 확장).
- **DQE는 실행 기능이다.** engine-owned 고정 정책이 골든 `mtf_value_at`과 `compute_dqe`를 호출한다. GUI interpolation과 support 밖 외삽은 금지다.
- **리포트≠프레임.** 지표 곡선은 확정 `xdet.metrics-report/1.0` JSON/CSV로, source/ROI frame만 `xdet.frame-artifact/1.0`으로 저장하고 run manifest가 둘을 연결한다.
- **Evidence는 실행 가능성과 별개다.** 에드로지 SAMPLE NPS/defect는 sanity만, 합성 MTF/DQE는 synthetic, strict 외부 실측은 user-supplied unverified, 정본 수치/EV 검증은 #33 뒤 승격한다.
- **TC 넘버링은 중앙 스킴 인용.** XDET-TC-152~159는 8그룹 GUI 패밀리 스킴(그룹당 8슬롯·096 시작)의 그룹8(Metrics) 블록이며 탭 내부에 하드코딩하지 않는다(foundation 중앙 레지스트리 확정).

## 요구사항-TC 추적

| 요구사항 | 중앙 TC |
|---|---|
| `REQ-XMETRIC-TARGET-1` | 152~159 |
| `REQ-XMETRIC-INPUT-{1..3}` | 152, 153, 158 |
| `REQ-XMETRIC-PARAM-{1..3}` | 152~155 |
| `REQ-XMETRIC-COMPUTE-{1..4}` | 152~155, 159 |
| `REQ-XMETRIC-VIEW-{1..4}` | 152~156 |
| `REQ-XMETRIC-DATA-{1..4}` | 156, 157, 159 |
| `REQ-XMETRIC-EXPORT-{1..2}` | 157 |
| `REQ-XMETRIC-GUARD-{1..2}` | 158, 159 |
| `REQ-XMETRIC-COVERAGE-{1..3}` | 152~159 |

각 범위는 모든 개별 ID로 전개한다. 필수 증거 필드는 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따르며 누락·중복·orphan은 인수 실패다.

## v0.5.1 operation closure acceptance

- **Given** edge/flat/dark/defect 또는 compatible MTF·NPS series input-set이 있고,
- **When** 사용자가 `metrics.mtf.estimate_edge_angle`, `metrics.mtf.compute_mtf`, `metrics.mtf.mtf_value_at`, `metrics.nps.compute_nps`, `metrics.nps.detect_line_noise`, `metrics.dqe.compute_dqe`, `metrics.dqe.dqe_value_at`, `metrics.defect_map.classify_morphology`, `metrics.defect_map.build_defect_map`, `metrics.defect_stats.classify_defects`에 대응하는 action/sub-command를 실행하면,
- **Then** 각 qualified EntryPoint의 typed result/error와 golden-direct fidelity가 XDET-TC-152~159에 남아야 한다. `metrics.result.MetricResult.get`, `metrics.result.require_param`, `metrics.result.metric_view`는 typed access/validation/serialization trace로 검증한다.
