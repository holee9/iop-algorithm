---
id: SPEC-XGUI-ENHANCE
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
labels: [xgui, gui-redesign, verification-gui, enhancement, mse, drc, window, gsdf, golden-frozen]
---

# SPEC-XGUI-ENHANCE — 인수 기준 (acceptance)

> 본 인수기준의 모든 EARS ID·중앙 TC·필수 증거 연결은 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따른다. `baseline-control.md`의 G0와 사용자 승인 전에는 이 체크리스트를 구현 완료 증거로 사용할 수 없으며 모든 TC는 `PLANNED` 상태를 유지한다.

> **구현 대상:** `apps/xdet-console/` C# WPF 앱. `apps/gui/`와 Python 테스트는 계약·검증 선례이며 구현 대상이 아니다.
Enhancement 그룹(MSE/DRC + 자동윈도우/GSDF) 검증 GUI 탭의 Given-When-Then. 모든 기준은 관측 가능해야 한다 — 폴더 브라우저 열기 / 골든 `process`·`run_pipeline` 구동 / 엔진 진단(`history.extra`) read-only 표시 / `<name>_result.raw`(16-bit) 저장·재적재 / 오케스트레이터·모듈 명시 오류로 거부 / 골든 파일 무변경(git diff 없음). 각 시나리오는 **XDET-TC-128~135**에 귀속한다(8그룹 GUI 패밀리 중앙 넘버링 스킴: 그룹당 8슬롯·096 시작 → 그룹5 Enhancement = 128~135; spec.md 확정 결정, foundation 중앙 레지스트리 확정).

실측(SAMPLE·에드로지) 구동은 **QUARANTINE(이슈 #29)** — sanity(유한·비퇴화·구조 성립)만 단언하고 수치 golden/EV 임계 주장은 하지 않는다. Enhancement에는 등록 실측 *직접 구동 스테이지*(고유 등록 CalibSet 소비)가 없으므로(offset/gain/defect는 그룹 1), 실측은 **입력 프레임을 window/저장 경로에 흘려보내는 IO·렌더·왕복 sanity**로만 쓰고, 기능 검증(Params 매니페스트·도메인 렌더·진단·조합)은 α>0 주입 합성 프레임으로 한다. 정본 수치 검증은 #33 지침세트 도착 후 별건이다.

골든 대상(FROZEN, 호출만): `modules/mse.py::process`(mse.py:328) · `modules/mse.py::required_params`(mse.py:97-105) · `modules/window.py::process`(window.py:303) · `modules/window.py::REQUIRED_PARAMS`(window.py:64-70) · `modules/window.py::build_gsdf_lut`(window.py:133-138) · `pipeline.orchestrator.run_pipeline`/`PipelineDefinition` · `common.io.load_raw_frame`(io.py:35) · C# engine/adapter raw export(신설, foundation §3) · C# engine/adapter C-20 guard (Python `apps.gui.io_panel.guard_output_path` 선례)(io_panel.py:27) · `common.synth_calibset.make_synthetic_calibset`(OTHER placeholder).

## Scenarios (Given-When-Then)

### Scenario 1 — 입력세트: 상주 폴더 브라우저 + OTHER placeholder + mse 노이즈 하드 의존 (XDET-TC-128, REQ-XENH-INPUT-1/2/3)
- **Given** Enhancement 탭과 상주 폴더 브라우저(폴더트리 + 가상화 썸네일 + 형제 필름스트립 + 이전/다음)가 있고, 기본 소스가 등록 실측 세트(에드로지 SAMPLE / #33)이며,
- **When** 사용자가 어느 raw 프레임(또는 그 파일)을 지정하면,
- **Then** (i) 탭이 `common.io.load_raw_frame`(io.py:35, headerless 16-bit + `.json` `{resolution,dtype}` 사이드카)으로 프레임을 로드하고 지정 파일의 **부모 폴더 형제 목록**(필름스트립 + 이전/다음)을 함께 표시하며(파일 단독 열기 아님), (ii) mse·window 진입 시 각 스테이지에 `make_synthetic_calibset(shape, CalibKind.OTHER)` placeholder를 공급해 게이트를 통과시키되 그 placeholder가 **검출 캘리브레이션이 아니라 미등록-kind 게이트 충족용**임을 UI에 표기하고(SWR-000-5 무단 대체 아님), (iii) mse 개별 실행 입력이 노이즈 모델을 결여/퇴화(`XFrame.noise` α<=0)하면 골든 자신의 `MseError`(mse.py:134-150)로 거부되고 탭이 그 오류를 그대로 표면화하며 임의 기본 (α,σ)를 합성하지 않는다.

### Scenario 2 — Params 셀렉터 매니페스트: 골든에서만 도출 + method 전환 (XDET-TC-129, REQ-XENH-PARAM-1/2/3)
- **Given** mse `method` 셀렉터와 window Params 입력 폼이 노출되고,
- **When** 사용자가 mse·window Params를 입력·전환하면,
- **Then** (i) mse 필수 키는 골든 `mse.required_params(params)`(mse.py:97-105) 반환 매니페스트로만 수집·강제되고 — 공통 `(mse_levels, mse_gamma, mse_noise_beta, mse_drc_gamma, mse_norm_plow, mse_norm_phigh)`; `method="power_law"`(기본) 추가 `mse_power`; `method="soft_clip"`(⚠P) 추가 `(mse_softclip_gain, mse_softclip_knee)`; 선택 `(mse_drc_bmid, mse_drc_low_levels)` — method 변경 시 `required_params` 재질의로 `mse_power`↔`mse_softclip_*` 세트가 교체되며 `soft_clip` 경로에 특허 검토 플래그(⚠P)가 표기되고, (ii) window 필수 키는 골든 `window.REQUIRED_PARAMS`(window.py:64-70) `(gsdf_lum_min, gsdf_lum_max, window_pvalue_levels, window_collim_rel_threshold, window_direct_fence_k)`로 강제되며 VOI 소스 `window_voi_override` | (`window_voi_presets`+`window_region_code`) | `window_voi_default` **최소 하나** 결여 시 골든 `WindowError`(window.py:211-215)가 표면화되고 `gsdf_jnd_grid_size`는 선택으로 다뤄지며, (iii) 어떤 수치 기본값도 UI가 지어내지 않는다(키 이름만 골든 도출; C-09).

### Scenario 3 — 그룹 고유 뷰어: [0,1] 표시 도메인 + read-only 진단 + SATURATION 오버레이 (XDET-TC-130, REQ-XENH-VIEW-1/2/3)
- **Given** α>0 합성 프레임으로 mse 또는 window가 실행되어 정규화 [0,1] 표시 도메인 출력이 산출되고,
- **When** 탭이 입력·출력·비교·진단을 렌더하면,
- **Then** (i) 입력(raw-DN, W/L 렌더)과 출력([0,1] 표시 도메인)이 **각기 올바른 도메인**으로 렌더되고 두 도메인을 뒤섞은 raw-DN 단위 `(after-before)` diff를 표시하지 않으며(도메인 정합 비교; 표시 스트레치는 렌더 변환일 뿐 엔진 재실행 아님), (ii) 표시 진단은 엔진이 `history.extra`에 기록한 값만 읽어 표시하고(C-09 자체 계산 금지) — mse 11키 `gamma_mean, drc_gamma, drc_low_levels, drc_compression_rate, b_mid, norm_low, norm_high, method, noise_beta, resolved_alpha, resolved_sigma`(mse.py:316-324/356-367); window 8키 `voi_low, voi_high, override, voi_source, anatomy_fraction, gsdf_max_dev, gsdf_lum_min, gsdf_lum_max`(window.py:292-299/339-344) — (iii) SATURATION/SATURATION_BAND 픽셀이 표시 도메인 최대(mse `_DOMAIN_MAX=1.0`, mse.py:309-314 / window `lut_display[-1]`, window.py:289-290)에 핀된 것을 마스크 오버레이로 식별 가능해(무복원 핀, SWR-602) 조작 디테일이 아님이 드러난다.

### Scenario 4 — DRC 전후 A/B + GSDF 곡선(골든 함수 호출) (XDET-TC-131, REQ-XENH-VIEW-4/5)
- **Given** 동일 입력 프레임과 window Params가 있고,
- **When** (a) 사용자가 DRC 전후 비교를 요청하고, (b) GSDF 표시 매핑 곡선 표시를 요청하면,
- **Then** (a) 탭이 동일 입력에 대해 서로 다른 Params(`mse_drc_gamma`=1 vs <1)로 골든 엔진을 **두 번 실행**해 두 골든 출력을 나란히 비교하고(UI가 DRC를 스스로 끄고/켜 계산하지 않음; 두 결과 모두 골든 산출, C-09), (b) 탭이 골든 `window.build_gsdf_lut(pvalue_levels, lum_min, lum_max, grid_size)`(window.py:133-138, **Params 오버로드 없는 4개 위치 스칼라**)를 `window.process`(window.py:310-315) 선례대로 window 실행과 동일 Params 값(`window_pvalue_levels`→`pvalue_levels`, `gsdf_lum_min`→`lum_min`, `gsdf_lum_max`→`lum_max`, `gsdf_jnd_grid_size`(기본 4096)→`grid_size`)을 추출해 호출하고 반환 `(jnd_index, display, max_dev)`로 P-value→정규화 display/JND-index 곡선과 `max_dev`를 렌더하며, DICOM PS3.14 다항식(window.py:79-89)을 UI에서 재구현하지 않는다(C-09/C-11 — LUT는 골든 계산, UI는 호출만).

### Scenario 5 — build/apply: 개별 → 조합 부분집합 → 검증 모드 중간 프레임 (XDET-TC-132, REQ-XENH-RUN-1/2/3) — **load-bearing**
- **Given** α>0 노이즈가 상류 `denoise` 또는 사전 적재로 확보된 프레임과 mse·window Params가 있고,
- **When** 사용자가 (a) 단일 스테이지(mse 또는 window)를 apply하거나, (b) 정렬된 조합(`("denoise","mse","window")` 또는 `("mse","window")`)을 부분집합으로 build하면,
- **Then** (a) 탭이 그 스테이지를 골든 `process(frame, calib_OTHER, params)`로 개별 구동해 입력/출력/도메인정합 diff/진단을 표시하고(모든 DSP 골든), (b) 탭이 `run_pipeline`(CONTRACT-6 심 미러) **단일 실행**으로 그 부분수열을 구동해 조합 출력과 스테이지별 전/후(입력 `XFrame.validation_mode=True` → `intermediates`)를 추가 실행 없이 스크럽하며 — 순서/조합 권한은 오케스트레이터에 남고 UI는 미러 DTO만 전달(C-11) — (c) 조합에 mse가 포함되면 (α,σ)>0이 상류 `denoise`(`_KIND_BY_STAGE["denoise"]="noise"` 공급자) 또는 α>0 사전적재로 확보됨을 전제로 구성되고 결여 시 실패가 조합 버그가 아니라 모듈 자신의 `MseError`로 표면화된다.

### Scenario 6 — 거부 가드: 비-부분수열 + 결여/불일치 캘리브레이션 (XDET-TC-133, REQ-XENH-RUN-4)
- **Given** 조합 build 요청이 임의 스테이지 집합·CalibSet 맵을 받고,
- **When** (a) `CANONICAL_ORDER` 부분수열이 아닌 집합(예: `("window","mse")` 역순)을 요청하거나, (b) 선택 스테이지 중 하나가 해상도·panel_id 일치 CalibSet(또는 OTHER placeholder)을 결여하도록 요청하면,
- **Then** (a)는 `PipelineDefinition.__post_init__`의 `PipelineOrderError`로, (b)는 `_calibration_gate`의 `CalibrationError`로 프레임 처리 이전에 거부되고, 어떤 기본 캘리브레이션도 대체되지 않으며(SWR-000-2 + SWR-000-5), 그 명시 오류가 탭에 그대로 전파돼 표시된다.

### Scenario 7 — 저장/열기 E2E: `<name>_result.raw` + 표시 도메인 16-bit 규약 + edrogi sanity (XDET-TC-134, REQ-XENH-DATA-1/2/3)
- **Given** 상주 폴더 브라우저로 연 프레임(등록 SAMPLE 에드로지 또는 α>0 합성)과 Enhancement 실행 결과([0,1] 표시 도메인)가 있고,
- **When** 사용자가 **열기→build/apply→저장→검증** E2E를 수행하면,
- **Then** (i) 탭이 `<name>_result.raw`, `xdet.frame-artifact/1.0` sidecar, `xdet.run-manifest/1.0` `<name>_run_manifest.json`을 사용자 지정 폴더에 쓰고 C# export choke point가 `data/` 하위를 typed error로 거부하며, (ii) [0,1]→16-bit 규약 `clip(value,0,1)*65535 → rint → <u2`와 `source_domain=display_normalized`, `export_domain=uint16_display_encoding`, `domain_max=65535`, quantization 태그를 기록하고, (iii) 확정 양자화 바이트의 bit-exact artifact round-trip과 manifest의 input/calib/params/output hash를 검증하며, (iv) 등록 SAMPLE 왕복은 IO·렌더·왕복 sanity일 뿐 수치 golden/EV 도출·튜닝에 쓰지 않는다(QUARANTINE, #29; 정본 검증은 #33).

### Scenario 8 — 불변 가드: UI DSP 0 · 골든 무변경 · 도메인 무결성 (XDET-TC-135, REQ-XENH-GUARD-1)
- **Given** 탭·어댑터가 Enhancement 스테이지/조합을 구동하고,
- **When** 실행 후 코드 경로·의존 방향·쓰기 대상·골든 트리를 검사하면,
- **Then** (i) mse/window의 어떤 출력·진단·GSDF LUT도 UI/어댑터가 스스로 계산하지 않고 실제 골든(`process`·`build_gsdf_lut`·`run_pipeline`)에서 발생하며(C-09), (ii) [0,1] 표시 출력에 raw-DN을 통과시키거나 조작 디테일을 주입하지 않고(SWR-602 무복원·도메인 무결성), (iii) 등록 kind의 기본 캘리브레이션을 무단 대체하지 않으며(SWR-000-5), 스테이지를 UI가 스스로 정렬·조합하지 않고(C-11), (iv) 어떤 UI 동작도 `data/` 하위나 골든 fixture/CalibSet에 쓰지 않으며(C-20; 내보내기는 사용자 지정 폴더), (v) `modules/mse.py`·`modules/window.py`·`modules/denoise.py`·`common/`·`pipeline/` 하위 파일이 무변경(git diff 없음; C# engine/adapter raw export는 뷰어 지원 additive로 기존 `load_raw_frame`/XFrame/orchestrator 표면 무변경).

### Scenario — MSE/window와 GSDF/P-value 파생 연산 전수 실행

- **Given** selector별 MSE Params와 window Params가 있고,
- **When** MSE와 window를 실행해 GSDF/P-value diagnostics를 열면,
- **Then** 실제 `required_params`, 두 `process`, `build_gsdf_lut`, `remap_to_pvalue`가 engine에서 호출되고 golden-direct 결과와 동일해야 한다. UI에는 LUT/remap 산술이 없어야 한다.

## Edge Cases

- **mse 노이즈 결여는 FAIL·무단 대체 없음 (REQ-XENH-INPUT-3 / RUN-3)** — `XFrame.noise` α<=0(기본 `NoiseModel(0,0)` 포함) 프레임으로 mse를 개별/조합 구동하면 골든 `MseError`(mse.py:145-149)로 거부돼야 한다 — 통과로 침묵되거나 UI가 임의 (α,σ)를 합성하면 인수 실패(음성 대조: α=0 프레임 주입 시 실제 예외 발생 확인).
- **VOI 소스 전무는 FAIL (REQ-XENH-PARAM-2)** — `window_voi_override`·`window_voi_presets`+`window_region_code`·`window_voi_default` 셋 다 결여로 window를 구동하면 `WindowError`(window.py:211-215)로 거부돼야 한다(음성 대조: VOI 3소스 모두 제거 시 실제 거부 확인).
- **비-부분수열 조합은 FAIL (REQ-XENH-RUN-4)** — 역순 `("window","mse")`·미지·중복 스테이지 집합을 build에 넘기면 `PipelineOrderError`로 거부돼야 한다 — 통과로 침묵되면 안 된다.
- **도메인 혼동 렌더는 FAIL (REQ-XENH-VIEW-1)** — [0,1] 표시 출력을 raw-DN W/L로 렌더하거나 입력(raw-DN)과 출력([0,1])을 raw-DN 단위 단순 diff로 뒤섞으면 인수 실패 — 도메인 정합(분리 표시 또는 입력을 표시 도메인으로 렌더 후 비교)이어야 한다.
- **GSDF/진단 UI 자체 계산은 FAIL (REQ-XENH-VIEW-2/5, GUARD-1)** — 탭이 `history.extra` 대신 스스로 진단을 계산하거나 PS3.14 다항식/LUT를 UI에서 재구현하면 인수 실패 — LUT는 `build_gsdf_lut` 호출로만, 진단은 read-only로만 얻어야 한다(C-09/C-11).
- **`data/` 하위 저장은 FAIL (REQ-XENH-DATA-1, GUARD-1)** — 저장 경로가 `<project_root>/data` 하위로 해석되면 C# export choke point가 프레임 쓰기 전에 typed validation error로 거부해야 한다.
- **SAMPLE 실측의 수치 오용 (QUARANTINE, 이슈 #29)** — 등록 SAMPLE(에드로지) 열기→window→저장 sanity 결과를 정본 수치/EV 임계 도출·튜닝·적합에 쓰면 인수 실패 — sanity(유한·비퇴화·구조)만 허용, 정본 수치 검증은 #33 도착 후 별건.

## Definition of Done (체크리스트)

- [ ] 상주 폴더 브라우저(폴더트리+가상화 썸네일+형제 필름스트립+이전/다음)로 `load_raw_frame` 열기 + 파일 지정 시 부모 폴더 형제 목록 동시 표시 + 기본 소스 등록 실측 세트 (XDET-TC-128, INPUT-1)
- [ ] mse·window에 `make_synthetic_calibset(shape, OTHER)` placeholder 공급 + "미등록-kind 게이트 충족용(캘리브레이션 아님)" UI 표기 (XDET-TC-128, INPUT-2)
- [ ] mse 노이즈 결여/퇴화(α<=0) 시 골든 `MseError` 그대로 표면화 + 임의 (α,σ) 미합성 (XDET-TC-128, INPUT-3; 음성 대조 포함)
- [ ] mse 필수 키를 `required_params(params)` 셀렉터 매니페스트로 수집·강제 + method 전환 시 `mse_power`↔`mse_softclip_*` 세트 교체 + ⚠P 플래그 (XDET-TC-129, PARAM-1/3)
- [ ] window 필수 키를 `REQUIRED_PARAMS` 5키로 강제 + VOI 최소 1소스 요구(결여 시 `WindowError`) + `gsdf_jnd_grid_size` 선택 (XDET-TC-129, PARAM-2)
- [ ] 입력(raw-DN)·출력([0,1] 표시 도메인) 도메인 정합 렌더 + raw-DN 혼합 diff 미표시 (XDET-TC-130, VIEW-1)
- [ ] 엔진 진단 read-only 표시 — mse 11키 / window 8키(`history.extra`), UI 자체 계산 0 (XDET-TC-130, VIEW-2)
- [ ] SATURATION/SATURATION_BAND 표시 도메인 최대 핀 마스크 오버레이(무복원 식별) (XDET-TC-130, VIEW-3)
- [ ] DRC 전후 A/B = 서로 다른 Params로 골든 두 번 실행(UI DRC 자체 토글 계산 없음) (XDET-TC-131, VIEW-4)
- [ ] GSDF 곡선 = `build_gsdf_lut(pvalue_levels, lum_min, lum_max, grid_size)` 4위치 스칼라 호출(Params 오버로드 없음, window.process 선례) + `(jnd_index, display, max_dev)` 렌더, PS3.14 UI 재구현 없음 (XDET-TC-131, VIEW-5)
- [ ] 단일 스테이지(mse|window) 개별 `process` 구동 + 입력/출력/도메인정합 diff/진단 표시 (XDET-TC-132, RUN-1)
- [ ] 정렬 조합(`denoise→mse→window` 또는 `mse→window`) `run_pipeline` 단일 실행 + `validation_mode` `intermediates` 스테이지별 전/후 스크럽 (XDET-TC-132, RUN-2)
- [ ] mse 조합 시 (α,σ)>0 상류 `denoise`/사전적재 전제 + 결여 시 `MseError` 표면화 (XDET-TC-132, RUN-3)
- [ ] 비-부분수열 `PipelineOrderError` + 결여/불일치 CalibSet `CalibrationError` 거부, 무단 대체 없음(음성 대조 포함) (XDET-TC-133, RUN-4)
- [ ] frame artifact sidecar + run manifest 저장, 양자화 바이트 bit-exact round-trip, manifest hash 검증, C# export choke point의 `data/` 거부(C-20) (XDET-TC-134, DATA-1/2)
- [ ] [0,1]→16-bit 역양자화 규약 + 사이드카 도메인 태그(`domain=display_normalized`) 확정 + `load_raw_frame` 무손실 재적재 (XDET-TC-134, DATA-2)
- [ ] 등록 SAMPLE(에드로지) 열기→window→저장→재적재는 IO·렌더·왕복 sanity(유한·비퇴화)만, 수치 golden/EV 도출·튜닝 없음 (XDET-TC-134, DATA-3; QUARANTINE 이슈 #29)
- [ ] UI DSP 0 + 도메인 무결성(raw-DN 미통과) + 무단 캘리브레이션 대체 없음 + UI 자체 정렬·조합 없음 + `data/`·골든 fixture 미쓰기 (XDET-TC-135, GUARD-1)
- [ ] `modules/mse.py`·`modules/window.py`·`modules/denoise.py`·`common/`·`pipeline/` 무변경(git diff 없음); C# engine/adapter raw export는 additive로 기존 표면 무변경 (XDET-TC-135)
- [ ] `uv run pytest` 무회귀 green + `uv run lint-imports` green·불변

## 판정 원칙 (측정=판정 분리)

- **골든이 산출, UI는 표시.** 모든 mse/window 출력·진단·GSDF LUT·조합·거부는 골든(`process`·`build_gsdf_lut`·`run_pipeline`·`_calibration_gate`)에서 발생한다. 탭의 load-bearing 인수 기준은 골든 결과의 정확한 소비·표시·도메인 정합·무회귀·명시 거부이지 SAMPLE 절대 수치가 아니다(C-09/C-11).
- **도메인 무결성이 이 그룹의 핵심 판정.** Enhancement 출력은 정규화 [0,1] 표시 도메인이므로(mse `_DOMAIN_MAX=1.0` / window GSDF display), 입력(raw-DN)·출력([0,1]) 도메인 정합 렌더·저장 태그·SWR-602 무복원 핀이 반드시 관측 가능해야 한다.
- **양자화 규약은 확정 계약.** [0,1]→16-bit `clip*65535→rint`와 display encoding 도메인 태그는 foundation §3의 확정 artifact 계약이다. float 원본의 무손실과 양자화 산출물의 bit-exact round-trip을 혼동하지 않는다.
- **SAMPLE 실측 수치는 비정본(QUARANTINE).** 에드로지 SAMPLE 열기·구동은 sanity(유한·비퇴화·구조)만, 정본 수치/EV 검증은 정본 지침세트(#33) 도착 후 별건.
- **TC 넘버링은 중앙 스킴 인용.** XDET-TC-128~135는 8그룹 GUI 패밀리 스킴(그룹당 8슬롯·096 시작)의 그룹5 블록이며 심/탭 내부에 하드코딩하지 않는다(spec.md 확정 결정, foundation 중앙 레지스트리 확정).

### strict 사용자 입력·display artifact·증거 등급 (XDET-TC-135, REQ-XENH-DATA-2/3, REQ-XENH-GUARD-1, REQ-XENH-COVERAGE-4)

- **Given** 등록세트 밖의 strict frame, 유효 NoiseModel, MSE/window Params가 있을 때,
- **When** MSE/window를 실행하고 0~1 display artifact를 저장·재열기하면,
- **Then** direct-golden DTO와 domain을 보존하고 양자화 절대오차 `<=0.5/65535`를 만족하며 UI/report/manifest evidence를 `USER_SUPPLIED_UNVERIFIED`로 유지해야 한다.
- **Given** 승인 이력이 없거나 UI가 LUT/P-value를 재계산했을 때,
- **When** 완료 또는 정본 승격을 판정하면,
- **Then** 완료·승격을 거부하고 원본 engine 결과만 유지해야 한다.

## 요구사항-TC 추적

| 요구사항 | 중앙 TC |
|---|---|
| `REQ-XENH-TARGET-1` | 128~135 |
| `REQ-XENH-INPUT-{1..3}` | 128, 134 |
| `REQ-XENH-PARAM-{1..3}` | 129, 130 |
| `REQ-XENH-VIEW-{1..5}` | 131, 132 |
| `REQ-XENH-RUN-{1..4}` | 129, 130, 134 |
| `REQ-XENH-DATA-{1..3}` | 132, 133 |
| `REQ-XENH-GUARD-{1}` | 134, 135 |
| `REQ-XENH-COVERAGE-{1..4}` | 128~135 |

각 범위는 모든 개별 ID로 전개한다. 필수 증거 필드는 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따르며 누락·중복·orphan은 인수 실패다.

## v0.5.1 operation closure acceptance

- **Given** method/noise model과 window/GSDF/P-value Params가 있고,
- **When** selector가 `modules.mse.required_params`를 조회하고 사용자가 `modules.mse.process`, `modules.window.process`, `modules.window.build_gsdf_lut`, `modules.window.remap_to_pvalue`를 실행하면,
- **Then** 각 qualified EntryPoint의 typed frame/axis/series/result 또는 오류가 XDET-TC-128~135에 기록되고 WPF/adapter가 MSE·GSDF·remap 산술을 수행하지 않아야 한다.
