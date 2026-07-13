---
id: SPEC-XGUI-MASTER
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
labels: [xgui, gui-redesign, verification-gui, foundation, factsheet, golden-frozen]
---

# SPEC-XGUI-MASTER — 8개 알고리즘 그룹 GUI 재설계 공유 팩트시트 (foundation)

이 문서는 `apps/xdet-console/` C# WPF 검증 GUI 재설계(이슈 #58)를 위해 **8개 알고리즘 그룹**별 SPEC 8종이 공유하는 **단일 사실 출처(foundation)** 이다. 기존 `apps/gui/` Python GUI는 계약·시험 선례이며 구현 대상이 아니다. 모든 항목은 동결(FROZEN) Python 골든의 실제 소스 `file:line`로 대조하여 기록했다. 그룹별 SPEC은 본 문서를 참조하며 사실을 재기술하지 않는다.

본 팩트시트는 [baseline-control.md](baseline-control.md)의 G0를 상속한다. `approval_state=pending_user` 또는 `implementation_authorized=false`인 동안 아래 계약은 구현 입력으로 동결되지 않았으며, M1 이후 코드 변경을 허가하지 않는다.

마스크 저장·전달의 단일 권위는 `common/xframe.py`의 `MASK_DTYPE = numpy.uint8`과 DEFECT=1, SATURATION=2, INTERPOLATION=4, SATURATION_BAND=8 bit flag다. `bool`, `uint16`, 픽셀별 enum 배열로 바꾸면 fidelity 실패다.

- **AUTHORITATIVE 대조 원칙:** 아래 표의 모든 process 시그니처·Params 키·CalibKind·데이터 가용성은 골든 소스에서 Grep/Read로 검증됨. 지어내기(fabrication) 금지 — 미확인 항목은 명시적으로 "[미확인]"으로 표기한다.
- **선례 미러링:** frontmatter/구조는 [SPEC-XSEAM-002](../SPEC-XSEAM-002/spec.md)를 미러링. 검증 GUI 계보는 [SPEC-VIEWER-001](../SPEC-VIEWER-001/spec.md)(구현됨) → SPEC-XSEAM-001/002(C# 심 확장) → 본 재설계.

---

## 1. 불변 HARD 제약 (전 그룹 공통 · FROZEN)

이 제약들은 모든 그룹 SPEC이 위반 불가로 상속한다.

| # | 제약 | 근거 (file:line) |
|---|---|---|
| G-1 | **알고리즘 골든 FROZEN** — `modules/`·`metrics/`·`common/`·`pipeline/`는 동결 오라클. GUI는 **호출만** 하고 수정 금지. 시그니처·수치·상수 변경 금지. 모든 사실은 Grep/Read로 대조검증 필수, 지어내기 금지. | CLAUDE.md "완료 정의(P1 전체)", SPEC-XSEAM-002 spec.md:66 Exclusions |
| G-2 | **C-09 UI는 DSP 0** — WPF UI와 transport는 어떤 지표·처리·리샘플링 결과도 스스로 계산하지 않는다. 실제 engine/adapter 결과만 표시한다. | Python `apps/gui/app.py:571-613` 선례, SPEC-XSEAM-002 spec.md:22/55 |
| G-3 | **C-11 단방향 소비** — GUI는 골든을 읽기-실행 전용으로만 소비. 조합/순서 권한은 오케스트레이터에 남긴다. | SPEC-XSEAM-002 spec.md:22, REQ-XSEAM-COMPOSE-5 spec.md:59 |
| G-4 | **C-20 내보내기는 사용자 지정 폴더만** — `data/` 하위 쓰기 거부. C#은 `IXdetEngine`/PythonNet export 경계에서 동일 가드를 강제한다. | `PythonNetXdetEngine.SaveProcessedFrame`, Python `apps/gui/io_panel.py:27` 선례 |
| G-5 | **QUARANTINE** — 등록 실측(에드로지 SAMPLE)은 sanity(유한·비퇴화·구조 성립) 확인만. 수치 golden 도출/튜닝/적합 금지. 비정본(panel_id=`SAMPLE-EDROGI-16BIT`, provenance `sample=true`). | scripts/ingest_edrogi.py:9-14/63-74, 이슈 #29 |
| G-6 | **SWR-000-2 고정 파이프라인 순서** — `CANONICAL_ORDER` 부분수열만 허용. 재정렬 시 `PipelineOrderError`. C# 측 정렬 금지. | pipeline/orchestrator.py:30-78, PipelineDefinition.__post_init__ :104-116 |
| G-7 | **SWR-000-5 무단 기본 캘리브레이션 대체 금지** — 부재/해상도·panel_id·kind 불일치 CalibSet은 `CalibrationError`로 거부. 기본값 대체 금지. | pipeline/orchestrator.py:178-280 `_calibration_gate`, :214-217 |
| G-8 | **`IXdetEngine` = WPF의 유일한 Python 경계** — 처리 조합은 `run_pipeline`, Lag는 `run_sequence`, NDT/Metrics는 지표 전용 seam 메서드로 미러한다. WPF는 Python 모듈을 직접 호출하지 않으며 순서/게이트/상태/지표 계산은 각 Python 골든 진입점이 강제한다. | SPEC-XSEAM-002 REQ-XSEAM-CONTRACT-6, SPEC-XGUI-MASTER REQ-XGUI-MASTER-SEAM-1/5 |
| G-9 | **탭 = 목적(알고리즘 그룹)별** — 탭은 알고리즘 그룹 단위로 구성. | 본 재설계 요구 (현재 app.py:729-736은 Module/Pipeline/Metrics 3탭 → 그룹별로 재편) |
| G-10 | **공개 알고리즘 전수 분류** — 모든 공개 처리·지표·builder·조합 연산은 `algorithm-catalog.md`에서 ACTION/SESSION/DERIVED/INFRASTRUCTURE 중 하나와 typed DTO·GUI·TC를 가져야 한다. | [algorithm-catalog.md](algorithm-catalog.md), XDET-TC-160 |
| G-11 | **실행 가능성과 증거 등급 분리** — 구현 여부는 `AlgorithmAvailability`, 실행 데이터의 권위는 `EvidenceGrade`로 각각 표시한다. 등록 데이터 부재만으로 구현된 알고리즘을 비활성화하지 않고, 합성 통과를 실측 승인으로 과대표현하지 않는다. | SPEC-XGUI-MASTER REQ-XGUI-MASTER-CAP-1~4, XDET-TC-166 |

문서 언어: ko. 식별자/EARS 키워드/코드 심볼: en.

---

## 2. 그룹별 팩트 표

CalibKind는 `pipeline.orchestrator.calib_kind_for_stage(stage)`(공개 접근자, app.py:79에서 GUI가 실제 사용)로 결정. `_KIND_BY_STAGE`(orchestrator.py:148-162)에 없는 스테이지는 `CalibKind.OTHER`.

모든 모듈 process 시그니처는 단일 계약 **`process(frame: XFrame, calib: CalibSet, params: Params) -> XFrame`** (예외: `lag`은 상태형 `LagCorrector().process(...)`, 인스턴스 메서드). 레지스트리 형태 주의: `modules/registry.py::default_registry()`는 **모듈 객체**(`lag`만 `LagCorrector()` 인스턴스)를 반환하며, `run_pipeline`이 요구하는 것은 **bare 콜러블 `{stage: module.process}`** 이다(`apps/gui/pipeline_panel.py:47-49 build_pipeline_registry`가 어댑트). registry.py:1-17 도크스트링 명시.

### 그룹 1 — Calibration (WP1: offset/gain/defect)

| 스테이지 | 모듈 (process) | REQUIRED_PARAMS (정확한 키) | CalibKind | 데이터 가용성 | 오류형 |
|---|---|---|---|---|---|
| offset | `modules/offset.py:85` | `("raw_saturation_threshold",)` (P_RAW_SAT, offset.py:36) [B] | OFFSET | **실행가능(SAMPLE sanity)** — MasterDark → `K_OFFSET_MAP` (ingest_edrogi.py:278-293) | — |
| gain | `modules/gain.py:87` | `("gain_min","gain_max")` (gain.py:39) [T] | GAIN | **실행가능(SAMPLE sanity)** — CalSet_19008 → `K_GAIN_MAP` 단일점 (ingest_edrogi.py:296-318) | — |
| defect | `modules/defect.py:282` | `("defect_cmax_pixels",)` (P_CMAX, defect.py:54) [T] | DEFECT | **실행가능(SAMPLE sanity)** — BPM → `K_CLASS_MAP` (ingest_edrogi.py:321-343) | DefectMapSchemaError (defect.py:73) |

- 뷰어 특성: 이미지 before/after/diff + 마스크 오버레이(DEFECT/INTERPOLATION) + 픽셀 probe(float32 정확값) + W/L + blink. 현행 `CompareDisplay`(app.py:90-233)가 그대로 적용.

### 그룹 2 — Lag (WP2)

| 스테이지 | 모듈 (process) | REQUIRED_PARAMS | CalibKind | 데이터 가용성 | 상태 |
|---|---|---|---|---|---|
| lag | `modules/lag.py:127` (`LagCorrector.process`, **상태형**) | `()` (lag.py:63) | LAG (payload: `irf_a`/`irf_b`, calibset.py:82-84) [B] | **placeholder 고정 IRF(비정본)**; GHOST 실측 폴더 존재하나 튜닝 금지 | 시퀀스 리셋 필요 |

- 관련 metrics: `metrics/lag.py:38 compute_first_frame_lag`, `:144 compute_ghost_cnr`; IRF 피팅 `metrics/lag_irf.py:72 fit_lag_irf`(→ CalibKind.LAG, lag_irf.py:169), 입력 `StepResponse`(lag_irf.py:50).
- 뷰어 특성 차이: **다중 프레임 시퀀스(시간축)** 가 핵심. 단일 `run_pipeline` 반복이 아니라 `pipeline/sequence.py::run_sequence`(시퀀스당 하나의 상태형 `LagCorrector`) 사용(SPEC-XSEAM-002 spec.md:41). first-frame lag/ghost CNR 곡선, IRF 지수합(M=3~4) 피팅 플롯 필요.

### 그룹 3 — Line/Sat/Geo (WP3+WP4)

| 스테이지 | 모듈 (process) | REQUIRED_PARAMS (정확한 키) | CalibKind | 데이터 가용성 | 오류형 |
|---|---|---|---|---|---|
| line_noise | `modules/line_noise.py:198` | `("line_noise_profile_window","line_noise_highpass_cutoff","line_noise_contam_k")` (line_noise.py:54) [T] | LINE_NOISE | **합성 전용 / #33 대기** | — |
| saturation | `modules/saturation.py:61` | `()` (saturation.py:53); P_BAND_WIDTH `"saturation_band_width"`는 선택(saturation.py:48) | OTHER | **합성 전용 / #33 대기** | — |
| geometry | `modules/geometry.py:178` | `("geometry_activation_residual_px","geometry_poly_degree")` (geometry.py:65) [B] | OTHER | **합성 전용 / #33 대기** | — |

- 뷰어 특성 차이: saturation은 SATURATION_BAND(팽창 경계 버퍼) 마스크 오버레이가 핵심 — 포화 "복원" 금지(SWR-602). geometry는 왜곡 벡터장/격자 시각화가 유용(다항 왜곡, degree [B]).

### 그룹 4 — Denoise (WP5: VST+BM3D)

| 스테이지 | 모듈 (process) | REQUIRED_PARAMS (셀렉터 의존) | CalibKind | 데이터 가용성 | 오류형 |
|---|---|---|---|---|---|
| denoise | `modules/denoise.py:616` | **함수** `required_params(params)`(denoise.py:92-101) — method 셀렉터 의존. 공통: `denoise_strength_ks, denoise_inv_lut_lambda_max, denoise_inv_lut_nodes, denoise_inv_lut_gh_nodes`; method=`bm3d`(기본) 추가: block/step/max_match/search_window/lambda3d/kaiser_beta/match_tau_hard/match_tau_wiener; method=`nlm` 추가: nlm_h/nlm_patch/nlm_window (denoise.py:104-114) | NOISE (payload: `alpha`/`sigma`, calibset.py:90-92) [B] | **합성 전용 / #33 대기** — NOISE (α,σ) CalibSet 필요 | DenoiseError (denoise.py:81) |

- 관련 metrics: `metrics/noise_model.py:78 fit_noise_model`(→ CalibKind.NOISE, noise_model.py:168), `DoseLevel`(noise_model.py:51).
- 뷰어 특성 차이: 노이즈 텍스처 before/after. `(α,σ)` NOISE CalibSet 미제공 시 `_resolve_noise`(denoise.py:129-144)가 하드 실패(SWR-000-5). XFrame 기본 NoiseModel(0,0) 폴백 금지. 점근 역 Anscombe 금지(SWR-703).

### 그룹 5 — Enhancement (WP6+WP7: MSE/DRC/자동윈도우/GSDF)

| 스테이지 | 모듈 (process) | REQUIRED_PARAMS | CalibKind | 데이터 가용성 | 오류형 |
|---|---|---|---|---|---|
| mse | `modules/mse.py:328` | **함수** `required_params(params)`(mse.py:97-105) — method 셀렉터 의존. 공통 `_REQUIRED_COMMON`: `mse_levels, mse_gamma, mse_noise_beta, mse_drc_gamma, mse_norm_plow, mse_norm_phigh`(mse.py:79-86); method=`power_law`(기본) 추가 `mse_power`; method=`soft_clip` 추가 `mse_softclip_gain, mse_softclip_knee`(mse.py:89-94) | OTHER | **합성 전용 / #33 대기** | MseError (mse.py:123) |
| window | `modules/window.py:303` | `("gsdf_lum_min","gsdf_lum_max","window_pvalue_levels","window_collim_rel_threshold","window_direct_fence_k")` (window.py:64-70) — VOI 선택(override/presets/region/default)·`gsdf_jnd_grid_size`는 선택 | OTHER | **합성 전용 / #33 대기** | WindowError (window.py:95) |

- 뷰어 특성 차이: **출력이 raw-DN이 아니라 정규화 [0,1] 표시 도메인**(mse.py:107-115: SATURATION 픽셀은 `_DOMAIN_MAX=1.0`에 핀, raw-DN 통과 없음). window은 GSDF LUT 곡선(DICOM PS3.14, window.py:75-92)·VOI 윈도우 표시. mse는 상류 noise (α,σ)>0 필요 — `_resolve_noise(frame)`(mse.py:134-147)가 XFrame.noise에서 소비, 결여 시 MseError(조합 시 denoise 선행 필요, SPEC-XSEAM-002 spec.md:41).

### 그룹 6 — Grid/VGrid (WP8+WP9)

| 스테이지 | 모듈 (process) | REQUIRED_PARAMS (정확한 키) | CalibKind | 데이터 가용성 | 오류형 |
|---|---|---|---|---|---|
| grid | `modules/grid.py:409` | `("grid_pitch_mm","grid_search_band_lo_lpmm","grid_peak_significance_db","grid_direction_margin_db","grid_harmonic_max_order","grid_notch_fwhm_mult","grid_moire_lowfreq_cutoff_lpmm","grid_moire_atten_cap")` (grid.py:83-92); 메타 `grid_meta_mounted/grid_meta_nominal_lpmm`·`grid_bg_window_bins`는 선택 | OTHER (검출 캘리 없음, placeholder) | **합성 전용 / #33 대기** | GridError (grid.py:98) |
| virtual_grid | `modules/virtual_grid.py:302` | `("vgrid_sks_iterations","vgrid_downsample_levels","vgrid_grid_ratio_w","vgrid_lowsignal_threshold","vgrid_lowsignal_softness")` (virtual_grid.py:82-88) [T] | SCATTER (payload: `scatter_amp`/`scatter_sigma`, calibset.py:105-107) [B] | **합성 전용 / #33 대기** — SCATTER 커널 CalibSet 필요 | VirtualGridError (virtual_grid.py:97) |

- 관련 metrics: `metrics/scatter_kernel.py:144 build_scatter_kernel`(→ CalibKind.SCATTER, scatter_kernel.py:128), `:213 fit_scatter_kernel_from_samples`, ScatterKernelCalibrationError(:74).
- 뷰어 특성 차이: grid은 **관측 스펙트럼 피크 직접 탐색**(명목 grid 주파수 금지, SWR-1001) → FFT/PSD 스펙트럼 + 1D Gaussian notch 시각화. 미검출 시 무처리 통과. virtual_grid은 SKS x8 다운샘플 반복·이중 Gaussian 산란 커널 프로파일. ⚠P 특허 대조 플래그(SKS, WP9).

### 그룹 7 — NDT (WP10)

| 함수/클래스 (지표 엔진) | 시그니처 (file:line) | 데이터 가용성 |
|---|---|---|
| `read_duplex_srb` | metrics/ndt.py:70 (duplex wire 20% dip 자동판독) | **합성 전용 / #33 대기** |
| `compute_snr` | metrics/ndt.py:129 → (snr, mean, std) | nps flat set로 sanity 가능 |
| `compute_snrn` | metrics/ndt.py:144 → MetricResult; `SNRn = SNR × 88.6µm / SRb`, `P_SRB_NORM_UM` 필요 | |
| `SNRnAccumulator` | metrics/ndt.py:206 (Welford 적산 실시간 SNRn, ShotLogEntry:188) | |
| `correct_thickness` | metrics/ndt.py:383 (ThicknessResult:341) | |
| `read_single_wire_iqi`/`build_iqi_report` | metrics/ndt.py:495/583 (WireElement:483, IqiShot:554, ShotVerdict:571) | |

- NDT는 CalibKind를 소비하지 않는 **지표 엔진**(모듈 process 아님). 뷰어 특성 차이: 이미지 diff보다 **리포트/판정 테이블**(SNRn 누적 스트리밍, IQI wire 판독, 두께보정)이 중심이다. 등록 SAMPLE은 SRb가 없으므로 SNR-only sanity로 제한하며 SNRn을 생성하지 않는다. domain=NDT(측정프로토콜 §1b, E2597), calibset.py:64-76.

### 그룹 8 — Metrics (MTF/NPS/DQE + defect stats)

| 함수 (지표 엔진) | 시그니처 (file:line) | 데이터 가용성 |
|---|---|---|
| `compute_mtf` | metrics/mtf.py:142 → MetricResult; Params: `pixel_pitch_mm, mtf_oversample, mtf_angle_min_deg, mtf_angle_max_deg, mtf_angle_margin_deg`(app.py:669-675 실사용) | **#33 대기** (엣지 팬텀); 합성으로 엔진 검증 |
| `estimate_edge_angle` | metrics/mtf.py:48 (자동 각도추정) | |
| `mtf_value_at` | metrics/mtf.py:212 | |
| `compute_nps` | metrics/nps.py:83 (256×256 ROI 스택) | nps flat set로 sanity 가능 |
| `detect_line_noise` | metrics/nps.py:152 | |
| `compute_dqe`/`dqe_value_at` | metrics/dqe.py:31/96 (MTF+NNPS 합성, IEC 62220-1) | 실행 가능 — `mtf_value_at`으로 NPS support 내 bin을 정렬한 뒤 engine에서 합성; 승인 edge/RQA 세트는 #33 대기 |
| `classify_defects` | metrics/defect_stats.py:57 (DefectClass IntEnum:40, E2597 분류) | SAMPLE BPM sanity |
| `build_defect_map` | metrics/defect_map.py:83 (→ CalibKind.DEFECT :117) | |

- Metrics는 CalibKind를 소비하지 않고 `MetricResult`(metrics/result.py:41)를 산출. 뷰어 특성 차이: **곡선 플롯 + ROI 선택**(이미지 처리 아님). 현행 MetricsTab(app.py:571-706)은 상류 탭 출력을 소스로 소비(C-09), ROI 왕복 재현성(C-10) 확인. `require_param`(result.py:73)로 Params 강제.

**등록 실측(에드로지 SAMPLE) 폴더 → 그룹 매핑** (ingest_edrogi.py:86-91/117-126):
- `16bit cal`(MasterDark/BPM/CalSet_19008) → 그룹 1 offset/gain/defect **실행가능 sanity**
- `아크릴`(acrylic step + DOSE METER.txt) → 두께/선량 참조(표시전용, 임계화 금지)
- `최소선량선형`(min dose linear) → 선형성(QUARANTINE, 적합 금지)
- `GHOST`(ghost_lag) → 그룹 2 lag/ghost 참조(placeholder)
- `nps`(nps_flat) → 그룹 8 NPS / 그룹 7 SNR sanity

## 2.1. 중앙 TC 레지스트리

| 범위 | 소유자 | 용도 |
|---|---|---|
| 096~103 | Calibration | apply, builder/import, fidelity, artifact/evidence |
| 104~111 | Lag | sequence, state snapshot/restore, lag metrics |
| 112~119 | Line/Sat/Geo | 세 stage 개별·조합, mask, 오류·저장 |
| 120~127 | Denoise | 동적 Params, BM3D/NLM, noise/NPS/SNR, evidence |
| 128~135 | Enhancement | MSE, window, GSDF LUT, P-value remap |
| 136~143 | Grid/VGrid | analyze/notch/process, scatter estimate/build/fit |
| 144~151 | NDT | 7 action, accumulator session, report/evidence |
| 152~159 | Metrics | MTF/NPS/line-noise/DQE/defect, report/evidence |
| 160~167 | Shared | catalog 전수성, 9 family seam, pipeline/sequence, tier, DQE, IO/evidence/GUI reachability |

## 2.2. 실행 가능 상태와 증거 등급 기준선

두 축을 절대 합치지 않는다.

- `AlgorithmAvailability`: `IMPLEMENTED`, `NOT_IMPLEMENTED`, `PREREQUISITE_MISSING`, `UNSUPPORTED`
- `EvidenceGrade`: `SYNTHETIC_VERIFIED`, `SAMPLE_SANITY`, `USER_SUPPLIED_UNVERIFIED`, `GUIDING_CANDIDATE`, `GOLDEN_APPROVED`

등록 실측 자료가 없다는 이유로 구현된 알고리즘을 비활성화하지 않는다. strict schema를 통과한 사용자 입력은 실행하고 결과를 `USER_SUPPLIED_UNVERIFIED`로 표시한다. 반대로 SAMPLE이나 합성 시험 통과를 수치 정본 승인으로 승격하지 않는다.

| 그룹/기능 | 현재 가능한 증거 | 정본 승격 조건 |
|---|---|---|
| Calibration offset/gain/defect | `SAMPLE_SANITY`, `SYNTHETIC_VERIFIED` | 승인 dark/flat/BPM 지침세트와 EV 기준 |
| Lag apply/first-frame/ghost | `SAMPLE_SANITY`, `SYNTHETIC_VERIFIED` | #33 정본 IRF·step/ghost 시퀀스 |
| Line/Sat/Geo | `SYNTHETIC_VERIFIED`; SAMPLE은 plumbing sanity | #33 banding·포화·기하 팬텀 |
| Denoise | `SYNTHETIC_VERIFIED`; SAMPLE flat은 plumbing sanity | #33 다선량 flat·구조 팬텀과 승인 NOISE CalibSet |
| Enhancement | `SYNTHETIC_VERIFIED`; SAMPLE은 IO/window sanity | #33 구조·선량별 영상과 승인 판정 기준 |
| Grid/Virtual-Grid | `SYNTHETIC_VERIFIED`; SAMPLE은 no-grid sanity | #33 물리 grid·scatter 팬텀 |
| NDT SNR/thickness | `SAMPLE_SANITY`, `SYNTHETIC_VERIFIED` | #33 duplex/single-wire/weld/연속 취득 세트 |
| NDT SRb/SNRn/IQI | `SYNTHETIC_VERIFIED` | #33 정본 IQI 세트 |
| Metrics MTF/DQE | `SYNTHETIC_VERIFIED` 또는 strict user input | #33 slanted-edge/RQA 세트 |
| Metrics NPS/defect | `SAMPLE_SANITY`, `SYNTHETIC_VERIFIED` | 승인 flat/dark 통계 세트와 EV 기준 |

`GOLDEN_APPROVED` 승격은 파일 존재만으로 이루어지지 않는다. `SPEC-GUIDING-001` 승인, 데이터 hash 등록, 대응 알고리즘 TC와 GUI-E2E 통과, 리포트의 `run_manifest` 보존을 모두 요구한다.

---

## 3. 저장 규약: 운영 frame artifact

**현재 상태:** Python `common/io.py`는 raw load를 제공하고, 현재 C# `SaveProcessedFrame`은 Python `apps.gui.export.export_frame`의 npz+JSON 형식을 사용한다. 목표 raw 계약은 이후 구현 단계에서 C# Contract/PythonNet export 경계를 확장해 제공한다. 이 문서 작업은 코드를 변경하지 않는다.

**확정 규약:**

- frame 결과는 `<name>_result.raw`(headerless little-endian uint16)와 `<name>_result.json`을 사용자 지정 폴더에 저장한다.
- raw-DN 출력은 `clip[0,65535] → rint → <u2`, display-normalized 출력은 `clip[0,1] × 65535 → rint → <u2`로 양자화한다.
- sidecar schema는 `xdet.frame-artifact/1.0`으로 고정하고 최소 `resolution`, `dtype`, `source_domain`, `export_domain`, `domain_max`, `quantization`, 적용 stage sequence와 아래 `run_manifest`를 기록한다. 하위 그룹 문서의 `{resolution,dtype}` 예시는 입력 로더의 최소 메타데이터일 뿐 결과 sidecar 스키마가 아니다.
- XFrame mask가 있으면 `<name>_result_mask.raw`를 uint8로 저장하고 sidecar에 `DEFECT=1`, `SATURATION=2`, `INTERPOLATION=4`, `SATURATION_BAND=8`을 기록한다.
- 이 raw 세트는 사용·검증을 위한 **운영 산출물**이며 noise/history/intermediates까지 포함하는 완전한 XFrame snapshot이 아니다. 실행 중의 in-memory DTO/XFrame이 fidelity의 권위 있는 상태다.
- 모든 쓰기는 C# engine/adapter의 C-20 단일 경계를 통과하고 `data/` 하위 경로를 거부한다. Python `guard_output_path`는 동작 선례다.
- 동결 `common/`에 writer를 추가하는 것은 본 SPEC의 요구가 아니다.

### 3.1. 공통 `run_manifest` (`xdet.run-manifest/1.0`)

frame sidecar, Metrics `<name>_metrics.json`, NDT `<name>_report.json`은 모두 같은 `run_manifest` 객체를 포함한다.

| 필드 | 형식·의미 |
|---|---|
| `schema_version` | 문자열 `xdet.run-manifest/1.0` |
| `run_id` / `started_at_utc` / `completed_at_utc` | GUID 문자열 / ISO-8601 UTC |
| `feature` | catalog `feature_id`, 9-family kind, `algorithm_availability` |
| `entry_points` | 실행 중 실제 호출한 qualified Python 공개 함수/메서드의 순서 보존 배열 |
| `input` | 표시 경로, SHA-256, `evidence_grade`, resolution, dtype, source domain, panel id |
| `stage_sequence` | 처리 그룹은 실제 실행 순서, 지표 그룹은 빈 배열 |
| `params` | 엔진에 전달한 전체 canonical 값과 `sha256` |
| `calibsets` | stage별 id, kind, resolution, panel id, provenance, payload manifest와 `sha256` |
| `engine` | Contract/adapter assembly version, Python version, 저장소 commit, dirty 여부 |
| `validation` | validation mode, `evidence_grade`, warnings, typed error code/type/message, 선택 정책(DQE axis/tier/state 등) |
| `artifacts` | 생성된 raw/mask/report 각각의 상대 파일명, byte length, SHA-256 |

canonical hash 규약은 다음과 같다.

1. JSON 객체 키는 ordinal 정렬하고 UTF-8, 공백 없는 JSON으로 직렬화한다. 숫자는 round-trip 표현을 사용하며 NaN/Infinity는 거부한다.
2. ndarray는 C-contiguous little-endian 바이트의 SHA-256과 `dtype`·`shape` descriptor로 대체한다.
3. Params hash는 전체 canonical Params JSON에, CalibSet payload hash는 정렬된 scalar/array descriptor JSON에 적용한다.
4. 저장 결과 hash는 raw/mask/report 파일을 닫은 뒤 계산한다. JSON은 자기 자신을 hash하지 않는다.

`artifact round-trip`은 저장 직전 DTO의 양자화 예상값과 재열기 픽셀·마스크 비교다. `run reproducibility`는 동일 input/Params/CalibSet으로 엔진을 다시 실행해 in-memory DTO fidelity를 비교하는 별도 판정이다. 전자를 통과했다고 후자를 통과한 것으로 표시하지 않는다.

## 4. 열기 규약: 상주 폴더 브라우저

- WPF 셸은 폴더 트리, 가상화 썸네일, 형제 필름스트립, 이전/다음 이동을 상주시킨다.
- 파일 하나를 직접 지정해도 부모 폴더의 형제 목록과 현재 선택을 함께 유지한다.
- raw는 `IXdetEngine`/PythonNet seam을 통해 Python `load_raw_frame` 계약으로 읽고 UI가 직접 dtype 변환이나 downsample을 수행하지 않는다.
- sidecar가 있으면 `resolution`과 `dtype`을 사용한다. 없으면 현재 C# loader의 명시 rows/cols 또는 검증된 inference 결과를 표시하고, 모호한 shape는 오류로 거부한다.
- 등록 SAMPLE, 합성, 사용자 입력, 향후 #33 데이터는 `EvidenceGrade`를 표시한다. 합성/사용자 입력이 승인 실측처럼 보이게 해서는 안 된다.

## 5. 파이프라인 조합 사실 (그룹 조합 SPEC 공통)

- `CANONICAL_ORDER`(orchestrator.py:30-78): `offset→gain→defect→lag→line_noise→saturation→geometry→grid→virtual_grid→denoise→mse→window→post`. `post`는 예약 tail(등록 모듈 없음).
- **구동 가능 전체 = `tuple(s for s in CANONICAL_ORDER if s != "post")`** — `post` 구동 시 `CalibrationError("no processing callable registered")`(orchestrator.py:327-330; SPEC-XSEAM-002 spec.md:37). GUI는 `SELECTABLE_STAGES = tuple(s for s in CANONICAL_ORDER if s in default_registry())`(pipeline_panel.py:42-44)로 이를 이미 반영.
- `PipelineDefinition(stages)`(orchestrator.py:92-143): 정렬된 부분집합만(부분수열 강제). `.full()`은 post 포함 전체 반환.
- 검증 모드: 입력 `XFrame.validation_mode=True` → `run_pipeline`이 스테이지별 출력을 `intermediates`로 부착(orchestrator.py:334-341). 단일 패스로 전 스테이지 전/후 확보.
- 진입 게이트: `_calibration_gate`(orchestrator.py:178-280) — 부재/해상도/kind-vs-stage/panel_id/유효기간 + CALDOM domain/beam_quality 교차검사(11 분기). 미등록 kind 스테이지(saturation/geometry/grid/mse/window)는 `CalibSet(OTHER)` placeholder로 게이트 통과.
- 합성 CalibSet: `common/synth_calibset.py::make_synthetic_calibset(shape, kind)`(app.py:76/372, pipeline_panel.py:28/52) — GUI가 kind 매칭 placeholder 생성. **SAMPLE 실측 구동 시에는 실제 CalibSet 사용, 합성은 #33 대기 스테이지 sanity 전용.**

---

## 6. 확정 경계 — 기능 보류 없는 구현 목표

- Enhancement의 display-normalized 출력은 `×65535` 양자화와 domain sidecar를 사용한다. 원본 raw는 별도 pre-stage artifact다.
- Lag는 `run_sequence`와 실행별 fresh state를 사용한다.
- NDT와 Metrics는 pipeline stage 탭이 아니라 지표/report 탭이다.
- NDT SAMPLE은 SNR-only, profile은 integer/nearest, 리포트는 JSON 필수·CSV 선택이다.
- Metrics는 지표별 source widget을 사용하고 JSON 필수·CSV 선택으로 내보낸다.
- DQE는 `metrics.mtf.mtf_value_at`과 `metrics.dqe.compute_dqe`를 순서대로 호출하는 engine-owned `NPS_BINS_WITHIN_MTF_SUPPORT_V1` 정책으로 구현한다. NPS bin은 MTF support 안에서만 선택하며 외삽하지 않는다. UI는 보간하지 않는다.
- `pipeline.tier`의 decide/select/run/time과 lag state snapshot/restore는 공통 실행 설정·세션 계약으로 노출한다. 숨은 기본 tier·암묵 state 재사용은 금지한다.
- 등록 실측 세트가 없는 기능도 strict `xdet.input-set/1.0`을 만족하는 사용자 제공 입력으로 실행할 수 있다. 승인 전 결과는 `USER_SUPPLIED_UNVERIFIED`다.

## 7. 전체 알고리즘 카탈로그 권위

[algorithm-catalog.md](algorithm-catalog.md)는 다음 범위의 단일 추적성 권위다.

1. `CANONICAL_ORDER`의 12개 구동 모듈(`post` 제외)
2. defect/lag IRF/noise/scatter calibration builder
3. MTF/NPS/DQE/defect/lag/NDT 지표와 상태형 accumulator
4. pipeline/sequence/tier orchestration
5. load/CalibSet/equivalence와 공개 지원 연산

직접 버튼이 아닌 공개 helper도 부모 결과의 typed diagnostics 또는 세션 state로 귀속해야 한다. `modules.grid.analyze`, `modules.window.build_gsdf_lut`, `metrics.mtf.mtf_value_at`, `LagCorrector.serialize_state` 같은 연산을 문서에서 생략하거나 C#으로 다시 계산하면 실패다.

## 8. 입력과 검증 승격

- 모든 실행 입력은 `xdet.input-set/1.0`의 `single-frame`, `ordered-stack`, `sequence`, `profile`, `calibration-series`, `metric-series` 중 하나다.
- `AlgorithmAvailability`는 `IMPLEMENTED`, `NOT_IMPLEMENTED`, `PREREQUISITE_MISSING`, `UNSUPPORTED` 중 하나다.
- `EvidenceGrade`는 `SYNTHETIC_VERIFIED`, `SAMPLE_SANITY`, `USER_SUPPLIED_UNVERIFIED`, `GUIDING_CANDIDATE`, `GOLDEN_APPROVED` 중 하나이며 실행별로 결정된다.
- #33 정본 데이터가 도착하면 코드를 갈아엎지 않고 동일 input-set/DTO를 사용해 evidence grade와 acceptance evidence만 승격한다.
- 문서·manifest·Python 공개 façade의 차이는 `AlgorithmCatalogCoverageTests`가 차단한다.
