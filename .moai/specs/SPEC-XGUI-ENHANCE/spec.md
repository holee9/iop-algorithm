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

# SPEC-XGUI-ENHANCE — Enhancement 그룹(MSE/DRC + 자동윈도우/GSDF) 검증 GUI 탭

> 본 사양은 `../SPEC-XGUI-MASTER/baseline-control.md`의 G0와 `traceability-matrix.md`를 상속한다. 사용자 승인·기준선 동결·`implementation_authorized=true` 전에는 구현 입력으로 실행하지 않으며, 승인 뒤 규범 변경은 버전 상승과 재승인을 요구한다.

XDET 검증 GUI 재설계(이슈 #58)의 **알고리즘 그룹 5 — Enhancement** 탭 명세다. 공유 사실은 [SPEC-XGUI-MASTER/foundation.md](../SPEC-XGUI-MASTER/foundation.md)(단일 사실 출처)를 상속하며, 본 문서는 그 사실을 재기술하지 않고 이 그룹 고유의 요구만 EARS로 인코딩한다. frontmatter/구조는 [SPEC-XSEAM-002](../SPEC-XSEAM-002/spec.md)를 미러링한다.

**대상 골든(FROZEN, 호출만):** `modules/mse.py`(SWR-801~805, WP6 — Laplacian L=7 다중스케일 강조 + power-law/soft-clip band 변조 + noise-gate + DRC + percentile linear-cutoff 정규화) · `modules/window.py`(SWR-901~903, WP7 — 조사야 인식→직접선 분리→VOI 3단계 + DICOM PS3.14 GSDF LUT). 두 스테이지는 `CANONICAL_ORDER`의 표시 후처리 tail(denoise→**mse→window**→post)이며, GUI는 이들을 **읽기-실행 전용**으로만 소비한다.

**문제(사용자 요구):** Enhancement는 XDET 파이프라인의 최종 표시 산출 단계로, 출력이 **검출기 raw-DN이 아니라 정규화 0~1 표시 도메인**이라는 점에서 다른 그룹과 근본적으로 다르다(mse `_DOMAIN_MAX=1.0`, mse.py:107-115/309-314; window GSDF display, window.py:168/283-290). 따라서 (a) 입력(raw-DN)과 출력([0,1])을 각기 올바른 도메인으로 렌더하는 표시 매핑, (b) DRC/대비 압축 효과와 GSDF 표시 특성의 검증, (c) mse가 상류 노이즈 모델 (α,σ)>0을 HARD로 요구하는 조합 제약(mse.py:134-149, SWR-000-5)의 표면화가 이 탭의 핵심이다. 조합 실행 능력 자체는 골든 오케스트레이터에 이미 있으므로(SPEC-XSEAM-002), 본 탭은 그것을 **소비**만 하고 DSP·조합 권한을 UI에 두지 않는다.

- **근거(변경 없음, 소비만):** `modules/mse.py::process`(mse.py:328) · `modules/mse.py::required_params`(mse.py:97-105, 셀렉터 의존 매니페스트) · `modules/mse.py::build`—없음(순수함수형 process) · `modules/window.py::process`(window.py:303) · `modules/window.py::REQUIRED_PARAMS`(window.py:64-70) · `modules/window.py::build_gsdf_lut`(window.py:133, PS3.14 LUT + 자기점검, 순수 골든 함수) · `pipeline.orchestrator.run_pipeline`/`PipelineDefinition`/`calib_kind_for_stage`(mse·window → `CalibKind.OTHER`, 미등록 kind) · `common.io.load_raw_frame`(io.py:35) · C# engine/adapter C-20 guard (Python `apps.gui.io_panel.guard_output_path` 선례)(io_panel.py:27 정의; export.py:32 import·:56 호출, C-20 choke point) · `common.synth_calibset.make_synthetic_calibset`(OTHER placeholder).
- **상속 원칙(foundation §1 G-1~G-9):** 골든 FROZEN(호출만·수정 금지·Grep/Read 대조·지어내기 금지, G-1) / UI DSP 0(C-09, G-2) / 단방향 소비(C-11, G-3) / 내보내기는 사용자 지정 폴더만(C-20, G-4) / QUARANTINE(등록 실측 sanity만, G-5) / 고정 파이프라인 순서(SWR-000-2, G-6) / 무단 기본 캘리브레이션 대체 금지(SWR-000-5, G-7) / 심 IXdetEngine = run_pipeline 미러(CONTRACT-6, G-8) / 탭=알고리즘 그룹별(G-9).
- **완료 정의(DoD):** (a) 개별 스테이지(mse·window)를 골든 process로 구동·입력/출력/진단 표시 → (b) mse 필수 Params가 `required_params` 셀렉터 매니페스트로 강제되고 method 전환 시 키 세트 갱신 → (c) window 필수 Params가 `REQUIRED_PARAMS`로 강제되고 VOI 소스(override/presets/default) 최소 1개 검증 → (d) [0,1] 표시 도메인과 raw-DN 입력을 도메인 정합 렌더 + 엔진 진단(history.extra)만 read-only 표시 → (e) denoise→mse→window 정렬 부분집합을 `run_pipeline` 단일 실행으로 조합·스테이지별 전/후 스크럽 + mse noise 결여 시 MseError 표면화 → (f) `<name>_result.raw`(16-bit)+사이드카 저장이 C-20 게이트를 통과하고 표시 도메인 태그를 기록. 골든 무변경, 정본 수치 검증은 #33 대기.
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.2.0 (2026-07-13)** — 중단 작업 복구 마무리. 구현 대상을 C# WPF `apps/xdet-console/`로 확정하고 Python `apps/gui/`는 참조 선례로 한정했다. 그룹별 결정·중앙 TC 레지스트리·plan/research를 확정했다. 골든 알고리즘은 변경하지 않는다.

- **v0.1.1 (2026-07-12)** — 라운드 1 교차검증(audit-r1.md, CONDITIONAL PASS — 골든 대조 무결점) 문서 결함 5건 교정 + 3파일 완결. **D1(MAJOR)**: `acceptance.md`(Given-When-Then 8시나리오, XDET-TC-128~135 실배정)·`plan.md` 신규 산출 — DoD (a)~(f)를 검증가능 TC에 바인딩(spec.md:24 링크 실체화, XSEAM-002 미러 3파일 정합). **D2**: HISTORY EARS 개수 오기 교정(20→19, INPUT 3+PARAM 3+VIEW 5+RUN 4+DATA 3+GUARD 1). **D3**: REQ-XENH-VIEW-5 `build_gsdf_lut` 호출 정밀화 — Params 오버로드 없는 4개 위치 스칼라 시그니처(window.py:133-138)를 `window.process`(window.py:310-315) 선례대로 추출해 호출로 정정. **D4**: `guard_output_path` 인용 정정(정의부 io_panel.py:27 / 사용부 export.py:32·56 분리). **D5**: REQ-XENH-GUARD-1 G범위 명시(G-1~G-8 위반; 구조원칙 G-9 의도적 제외). 골든 재대조 결과 지어낸 Params 키·수식·제약위반 **추가 결함 0**(D2~D5는 텍스트 편집).
- **v0.1.0 (2026-07-12)** — 초안 생성. GitHub 이슈 #58(C# GUI 재설계) 8개 알고리즘 그룹 SPEC 중 그룹 5(Enhancement). foundation.md(SPEC-XGUI-MASTER) 공유 사실 상속. 6개 요구 그룹(INPUT/PARAM/VIEW/RUN/DATA/GUARD) EARS 19개(INPUT 3 + PARAM 3 + VIEW 5 + RUN 4 + DATA 3 + GUARD 1). 저작 시 **AUTHORITATIVE 소스로 대조검증한 사실**: (a) `mse.required_params(params)`(mse.py:97-105)는 **함수**로 method 셀렉터 의존 — 공통 `_REQUIRED_COMMON=(mse_levels, mse_gamma, mse_noise_beta, mse_drc_gamma, mse_norm_plow, mse_norm_phigh)`(mse.py:79-86), `mse_method="power_law"`(기본) 추가 `mse_power`, `mse_method="soft_clip"`(⚠P) 추가 `(mse_softclip_gain, mse_softclip_knee)`(mse.py:89-94), 선택 `mse_drc_bmid`/`mse_drc_low_levels`(mse.py:69-70). (b) `window.REQUIRED_PARAMS`(window.py:64-70)는 **고정 튜플** `(gsdf_lum_min, gsdf_lum_max, window_pvalue_levels, window_collim_rel_threshold, window_direct_fence_k)` — VOI 선택(`window_voi_override` | `window_voi_presets`+`window_region_code` | `window_voi_default`)과 `gsdf_jnd_grid_size`는 at-least-one/기본값 의미로 선택(window.py:59-63). (c) mse 출력은 raw-DN이 아니라 정규화 [0,1] — SATURATION/SATURATION_BAND 픽셀은 `_DOMAIN_MAX=1.0`에 핀(mse.py:309-314), raw-DN 통과 없음(SWR-602 무복원). (d) mse는 `_resolve_noise(frame)`(mse.py:134-149)로 `XFrame.noise`의 (α,σ)를 소비하며 α<=0/퇴화 시 **MseError**로 하드 실패 — 기본값 대체 금지(SWR-000-5); 상류 T5 denoise가 (α,σ)를 기록해야 함(SPEC-XSEAM-002 spec.md:41). (e) window 출력은 GSDF display-normalized 0~1(window.py:168/283), SATURATION 픽셀은 `lut_display[-1]`에 핀(window.py:289-290). (f) `common/io.py`에 raw 쓰기 함수 부재(load_raw_frame만, io.py:35), 기존 `export.py::export_frame`은 npz+JSON로 요구 포맷과 다름 → `<name>_result.raw` writer는 신설(foundation §3). (g) mse·window는 `calib_kind_for_stage` 미등록 → `CalibKind.OTHER` placeholder로 게이트 통과(foundation §5). 확정 설계: DSP·조합 권한은 골든에 남기고 UI는 표시·수집만; [0,1] 표시 도메인의 16-bit 저장 역양자화 규약은 본 SPEC이 확정(foundation §6 미해결 항목).

## Environment / Assumptions

- **본 SPEC은 T-스테이지가 아니다.** `CANONICAL_ORDER` 스테이지 추가·`process(...)->XFrame` 시그니처 변경·신규 `CalibKind`·`_KIND_BY_STAGE` 변경이 전혀 없다. `modules/mse.py`·`modules/window.py`·`common`·`pipeline`은 동결 오라클이며, 본 SPEC은 그 위에 **GUI 검증 소비자**(탭)를 additive로 얹는다(SPEC-VIEWER-001·SPEC-XSEAM-002 검증 도구 계열의 확장).
- **표시 후처리 tail.** mse·window는 `CANONICAL_ORDER`의 마지막 두 실 스테이지(denoise→mse→window→post)이며, window 이후 실 스테이지가 없다(`post`는 예약 tail·등록 모듈 없음). 따라서 Enhancement 그룹 탭은 **파이프라인의 종단 표시 산출**을 검증한다.
- **출력 도메인(검증됨).** 두 스테이지 출력 모두 정규화 [0,1] 표시 도메인이다 — mse는 percentile [p_low, p_high] linear-cutoff 정규화(SWR-805, mse.py:296-307) 후 SATURATION 픽셀을 `_DOMAIN_MAX=1.0`에 핀(mse.py:309-314); window는 P-value→GSDF LUT display 값(window.py:280-283)으로 SATURATION 픽셀을 `lut_display[-1]`(display max)에 핀(window.py:289-290). **어느 경로도 raw-DN을 통과시키지 않는다**(주입 시 [0,1] 이미지의 하류 통계 파괴, SWR-602).
- **mse 노이즈 하드 의존(검증됨).** mse는 입력 `XFrame.noise`의 (α,σ)를 소비하며(mse.py:134-149), 기본 `NoiseModel(0,0)` 또는 α<=0은 `MseError`로 거부한다(SWR-000-5, 기본값 대체 금지). 개별 mse 검증은 (i) α>0 노이즈가 주입된 합성 프레임 또는 (ii) 상류 `denoise` 조합 산출 프레임을 요구한다. window는 노이즈 의존이 없다.
- **CalibSet 형태(검증됨).** mse·window는 `calib_kind_for_stage`에 미등록이므로 `CalibKind.OTHER`이고, 진입 게이트는 `CalibSet(OTHER)` placeholder(`make_synthetic_calibset(shape, OTHER)`)로 만족된다(foundation §5). 이는 **등록 kind의 기본값 무단 대체가 아니다** — OTHER는 검출 캘리브레이션이 없는 스테이지의 정당한 placeholder다. 실제 캘리브레이션 데이터를 합성하지 않는다.
- **Params 매니페스트(검증됨).** mse 필수 키는 셀렉터 의존 함수 `required_params(params)`(mse.py:97-105)로만 질의하고, window 필수 키는 고정 튜플 `REQUIRED_PARAMS`(window.py:64-70)로 강제한다. UI는 키 **이름**만 골든에서 도출하고 수치 기본값을 지어내지 않는다(SPEC-ERGO-001 REQUIRED_PARAMS 매니페스트 계약).
- **조합은 골든에 이미 있다.** denoise→mse→window 같은 정렬 부분집합의 조합 실행은 `run_pipeline`+`PipelineDefinition`이 이미 지원한다. 순서/조합 권한(SWR-000-2)과 캘리브레이션 게이트(SWR-000-5)는 오케스트레이터가 강제하며, 탭은 미러 DTO만 전달한다(C-11). C# 심은 이 진입점을 `IXdetEngine`으로 미러한다(SPEC-XSEAM-002 CONTRACT-6).
- **검증 모드 단일 패스.** 입력 `XFrame.validation_mode=True`면 `run_pipeline`이 스테이지별 출력을 `intermediates`로 부착 → 조합 1회 실행으로 denoise/mse/window 각 전·후를 추가 실행 없이 스크럽한다(foundation §5).
- **저장 규약.** C# engine/adapter가 `<name>_result.raw` + JSON sidecar와 선택 mask raw를 기록한다. `common/io.py`는 load 선례로만 소비하며 writer를 추가하지 않는다. 쓰기 전 C-20 경계에서 `data/` 하위를 거부한다.
- **열기 규약(상속).** 상주 폴더 브라우저(폴더트리+가상화 썸네일+형제 필름스트립+이전/다음). 파일 지정 시에도 부모 폴더 형제 목록을 함께 표시. 기본 소스는 등록 실측 세트(에드로지 SAMPLE / 향후 #33)이며 합성 목업 사용자탭을 기본으로 두지 않는다(foundation §4).
- **실측 데이터 가용성(SAMPLE·비정본, QUARANTINE 이슈 #29).** Enhancement 그룹에는 등록 실측으로 **직접 구동 가능한 스테이지가 없다**(offset/gain/defect는 그룹 1). mse·window는 정본 데이터 가용성이 "합성 전용 / #33 대기"다(foundation §2 그룹 5). 실질 검증은 α>0 주입 합성 프레임 또는 denoise 선행 조합으로만 이뤄지며, 정본 수치 검증(EV 임계·튜닝)은 정본 지침세트(#33) 도착 후 별건이다.
- **환경.** Python은 `uv run`으로만 실행(`uv run pytest`, `uv run lint-imports`), WPF/engine contract는 현재 솔루션과 동일한 .NET 9를 사용한다. 정확성·재현성이 목적이며 알고리즘/수치 최적화는 범위가 아니다.

## Requirements (EARS)

### REQ-XENH-TARGET — 구현 대상 경계

- **REQ-XENH-TARGET-1 (Ubiquitous)** — 시스템은 `apps/xdet-console/` C# WPF 앱을 구현 대상으로 사용해야 하며, `apps/gui/`와 Python 테스트·패널은 계약 및 검증 선례로만 참조해야 한다. WPF는 Python 모듈을 직접 호출하지 않고 `IXdetEngine`/PythonNet seam을 경유해야 한다.

### REQ-XENH-INPUT — 입력세트: 프레임 선택 + CalibSet(OTHER) placeholder + mse 노이즈 하드 의존 (C-11/SWR-000-5)

- **REQ-XENH-INPUT-1 (Event-Driven)** — WHEN 사용자가 Enhancement 탭에서 입력 프레임을 선택하면, THEN 탭은 상주 폴더 브라우저로 `load_raw_frame`(io.py:35, headerless 16-bit + `.json` `{resolution,dtype}` 사이드카)을 통해 프레임을 로드하고, 파일을 지정해도 그 부모 폴더의 형제 목록(필름스트립+이전/다음)을 함께 표시해야 하며, 기본 소스는 등록 실측 세트(에드로지 SAMPLE / #33)여야 한다(합성 목업 사용자탭을 기본으로 두지 않음).
- **REQ-XENH-INPUT-2 (Ubiquitous)** — mse·window 스테이지는 `calib_kind_for_stage`에 미등록(`CalibKind.OTHER`)이므로 탭은 각 스테이지에 `make_synthetic_calibset(shape, OTHER)` placeholder를 공급해 진입 게이트를 통과시키되, 그 placeholder가 캘리브레이션 데이터가 아니라 미등록-kind 게이트 충족용임을 UI에 표시해야 한다(등록 kind의 기본값 무단 대체가 아님, SWR-000-5).
- **REQ-XENH-INPUT-3 (Unwanted)** — IF mse 개별 실행의 입력 프레임이 노이즈 모델을 결여하거나 퇴화(`XFrame.noise` α<=0)면, THEN 실행은 골든 모듈 자신의 `MseError`(mse.py:134-149)로 거부되어야 하고, 탭은 그 오류를 그대로 표면화하며 임의 기본 노이즈 (α,σ)를 합성하지 않아야 한다(기본값 대체 금지, SWR-000-5 — 조합 검증은 REQ-XENH-RUN-3의 denoise 선행 경로 사용).

### REQ-XENH-PARAM — Params 키: 셀렉터 의존 매니페스트를 골든에서만 도출 (SPEC-ERGO-001, C-09)

- **REQ-XENH-PARAM-1 (Ubiquitous)** — mse 실행 시 탭은 필수 Params 키를 골든 `mse.required_params(params)`(mse.py:97-105)가 반환하는 매니페스트로만 수집·강제해야 한다 — 공통 `(mse_levels, mse_gamma, mse_noise_beta, mse_drc_gamma, mse_norm_plow, mse_norm_phigh)`; `mse_method="power_law"`(기본) 추가 `mse_power`; `mse_method="soft_clip"`(⚠P) 추가 `(mse_softclip_gain, mse_softclip_knee)`; 선택 `(mse_drc_bmid, mse_drc_low_levels)`. 키 이름은 골든에서 도출하고 수치 기본값을 UI가 지어내지 않는다.
- **REQ-XENH-PARAM-2 (Ubiquitous)** — window 실행 시 탭은 필수 Params 키를 골든 `window.REQUIRED_PARAMS`(window.py:64-70) `(gsdf_lum_min, gsdf_lum_max, window_pvalue_levels, window_collim_rel_threshold, window_direct_fence_k)`로 강제하고, VOI 소스는 `window_voi_override` | (`window_voi_presets`+`window_region_code`) | `window_voi_default` 중 **최소 하나**를 요구(결여 시 골든 `WindowError` 표면화, window.py:211-215)하며, `gsdf_jnd_grid_size`는 선택으로 다뤄야 한다.
- **REQ-XENH-PARAM-3 (Where)** — WHERE `mse_method` 셀렉터가 UI에 노출되면, THEN 탭은 method 변경 시 `required_params`를 재질의해 입력 필드를 갱신해야 하며(`power_law`↔`soft_clip` 전환 시 `mse_power` vs `mse_softclip_*` 세트 교체), `soft_clip` 경로에는 특허 검토 플래그(⚠P, REQ-POST-MSE-5)를 표기해야 한다.

### REQ-XENH-VIEW — 그룹 고유 뷰어: [0,1] 표시 도메인 + DRC/GSDF 표시 매핑 (C-09, SWR-602)

- **REQ-XENH-VIEW-1 (Ubiquitous)** — Enhancement 출력은 raw-DN이 아니라 정규화 [0,1] 표시 도메인이므로, 탭 뷰어는 입력(raw-DN, W/L 렌더)과 출력([0,1] 표시 도메인)을 **각기 올바른 도메인**으로 렌더해야 하며, 두 도메인을 뒤섞은 단순 `(after - before)` diff를 raw-DN 단위로 표시하지 않아야 한다(도메인 정합 비교 — 입력을 표시 도메인으로 렌더한 뒤 비교하거나 각 도메인을 분리 표시). 표시 도메인 스트레치는 렌더 변환일 뿐 엔진 재실행이 아니다.
- **REQ-XENH-VIEW-2 (Event-Driven)** — WHEN 실행이 완료되면, THEN 탭은 엔진이 `history.extra`에 기록한 진단만 읽어 표시해야 한다(C-09, 스스로 계산 금지) — mse: `gamma_mean, drc_gamma, drc_low_levels, drc_compression_rate, b_mid, norm_low, norm_high, method, noise_beta, resolved_alpha, resolved_sigma`(mse.py:316-324/356-367); window: `voi_low, voi_high, override, voi_source, anatomy_fraction, gsdf_max_dev, gsdf_lum_min, gsdf_lum_max`(window.py:292-299/339-344).
- **REQ-XENH-VIEW-3 (State-Driven)** — WHILE SATURATION/SATURATION_BAND 픽셀이 표시 도메인 최대(mse `1.0` / window `lut_display[-1]`)에 핀되어 있으면, THEN 탭은 그 마스크 오버레이(SATURATION/SATURATION_BAND)를 제공해 핀된 픽셀이 조작 디테일이 아니라 무복원 핀(SWR-602)임을 사용자가 식별할 수 있어야 한다.
- **REQ-XENH-VIEW-4 (Where)** — WHERE 사용자가 DRC/대비 전후 비교를 요청하면, THEN 탭은 동일 입력에 대해 서로 다른 Params(예: `mse_drc_gamma`=1 vs <1)로 골든 엔진을 **두 번 실행**해 두 엔진 출력을 나란히 비교할 수 있어야 하며, 두 결과 모두 골든 산출이어야 한다(UI가 DRC를 스스로 끄고/켜 계산하지 않음 — C-09).
- **REQ-XENH-VIEW-5 (Where)** — WHERE window GSDF 표시 매핑 곡선을 표시하면, THEN 탭은 골든 `window.build_gsdf_lut`(window.py:133-138)를 window 실행과 **동일 Params 값**을 추출해 호출(read-execute 소비)해야 한다 — 이 함수는 `Params` 오버로드가 없는 4개 위치 스칼라 시그니처 `build_gsdf_lut(pvalue_levels, lum_min, lum_max, grid_size)`이므로, `window.process`(window.py:310-315) 선례와 동일하게 `window_pvalue_levels`→`pvalue_levels`, `gsdf_lum_min`→`lum_min`, `gsdf_lum_max`→`lum_max`, `gsdf_jnd_grid_size`(기본 4096)→`grid_size`로 추출해 전달하고 반환된 `(jnd_index, display, max_dev)`로 P-value→정규화 display/JND-index 곡선과 `max_dev`를 렌더한다. DICOM PS3.14 다항식(window.py:79-89)을 UI에서 재구현하지 않아야 한다(C-09/C-11 — LUT는 골든이 계산, UI는 호출만).

### REQ-XENH-RUN — build/apply 워크플로: 개별 → 조합 부분집합 → 검증 모드 중간 프레임 (SPEC-VIEWER-001 RUN-1/2 소비, C-11)

- **REQ-XENH-RUN-1 (Event-Driven)** — WHEN 사용자가 단일 스테이지(mse 또는 window)를 선택하고 apply하면, THEN WPF는 `IXdetEngine.RunPipeline(PipelineRunRequest)`에 단일 stage와 typed Params/OTHER placeholder를 전달하고 입력/출력/diff(도메인 정합)/진단을 표시해야 한다. 모든 DSP는 골든에서 실행되며 `apps.gui` helper를 실행 경계로 사용하지 않는다.
- **REQ-XENH-RUN-2 (Event-Driven)** — WHEN 사용자가 이 그룹의 정렬된 조합(예: `("denoise","mse","window")` 또는 `("mse","window")`)을 부분집합으로 선택하고 build하면, THEN 탭은 `IXdetEngine.RunPipeline(PipelineRunRequest)` **단일 실행**으로 구동하고, 조합 출력과 `PipelineRunResult.intermediates`를 표시해야 한다. 순서/조합 권한은 Python 오케스트레이터에 남는다(C-11).
- **REQ-XENH-RUN-3 (State-Driven)** — WHILE 조합에 mse가 포함되면, THEN 탭은 (α,σ)>0 노이즈 모델이 상류 `denoise` 또는 α>0 사전적재로 확보됨을 전제로 조합을 구성해야 하고, 결여 시 실패를 mse 모듈 자신의 명시 오류(MseError)로 표면화해야 한다(조합 버그가 아님; SPEC-XSEAM-002 spec.md:41 — mse-window 인접이라 denoise가 노이즈 공급자).
- **REQ-XENH-RUN-4 (Unwanted)** — IF 요청된 조합 부분집합이 `CANONICAL_ORDER`의 부분수열이 아니거나(→ `PipelineOrderError`) 선택 스테이지 중 하나라도 해상도·panel_id 일치 CalibSet(또는 OTHER placeholder)을 결여하면(→ `CalibrationError`), THEN 그 실행은 오케스트레이터의 명시 오류로 거부되고 어떤 기본 캘리브레이션도 대체되지 않아야 한다(SWR-000-2 + SWR-000-5).

### REQ-XENH-DATA — 저장/열기 + 표시 도메인 16-bit 규약 + edrogi 가용성 (C-20, QUARANTINE)

- **REQ-XENH-DATA-1 (Event-Driven)** — WHEN 사용자가 결과 저장을 요청하면, THEN 탭은 `<name>_result.raw`, `xdet.frame-artifact/1.0` sidecar, 그리고 `xdet.run-manifest/1.0` `<name>_run_manifest.json`을 **사용자 지정 폴더에만** 써야 한다. C# export choke point는 `data/` 하위를 typed validation error로 거부하며 WPF/adapter는 Python `guard_output_path`를 직접 호출하지 않는다(C-20).
- **REQ-XENH-DATA-2 (Ubiquitous)** — Enhancement 출력은 [0,1] display-normalized 도메인이므로, 저장 규약은 `clip(value,0,1) * 65535 → rint → <u2`로 **확정**한다. sidecar는 `source_domain: display_normalized`, `export_domain: uint16_display_encoding`, `domain_max: 65535`, `quantization: clip[0,1]*65535,rint`, byte_order/resolution/dtype를 포함한다. 이는 원래 float의 무손실 보존이 아니라 **확정 양자화 산출물의 bit-exact artifact round-trip**이며 raw-DN 검출기 프레임으로 해석할 수 없다. run manifest는 input/calib/params/output hash와 실행 이력을 기록한다.
- **REQ-XENH-DATA-3 (Unwanted)** — IF Enhancement 스테이지/조합을 등록 실측(에드로지 SAMPLE)으로 구동하면, THEN 그것은 sanity(유한·비퇴화·구조 성립) 확인일 뿐이어야 하며 — 이 그룹에 등록 실측 직접 구동 스테이지는 없고(offset/gain/defect는 그룹 1) mse·window 데이터 가용성은 "합성 전용 / #33 대기"이므로 — 수치 golden/EV 임계 도출·튜닝·적합에 쓰지 않아야 한다(비정본, 이슈 #29). 정본 수치 검증은 #33 도착 후 별건이다.

### REQ-XENH-GUARD — 불변 가드: UI DSP 0 · 골든 무변경 · 도메인 무결성 (C-09/C-11/C-20, SWR-602/SWR-000-5)

- **REQ-XENH-GUARD-1 (Unwanted)** — IF UI 또는 어댑터가 (i) mse/window의 출력·진단·GSDF LUT를 스스로 계산하거나, (ii) 골든을 수정하거나, (iii) [0,1] 출력에 raw-DN을 통과시키거나, (iv) 기본 캘리브레이션을 무단 대체하거나, (v) 스테이지를 스스로 정렬·조합하거나, (vi) `data/` 하위로 내보내거나, (vii) Python `apps.gui` helper를 직접 호출하면, THEN 이는 거부되어야 한다(G-1~G-8/C-09/C-11/C-20).

### REQ-XENH-COVERAGE — MSE/window 공개 연산 전수 귀속

- **REQ-XENH-COVERAGE-1 (State-Driven)** — WHILE MSE selector가 바뀌면 engine은 실제 `modules.mse.required_params(params)`를 호출해 필수 key를 갱신해야 한다.
- **REQ-XENH-COVERAGE-2 (Event-Driven)** — WHEN MSE 또는 window를 실행하면 THEN 실제 `modules.mse.process` 또는 `modules.window.process`가 호출돼야 한다.
- **REQ-XENH-COVERAGE-3 (Ubiquitous)** — window 결과 DTO는 부모 실행의 DERIVED 산출로 실제 `modules.window.build_gsdf_lut`의 axis/series와 `modules.window.remap_to_pvalue`의 P-value 결과/metadata를 운반해야 하며 UI가 LUT/remap을 재계산하지 않아야 한다.
- **REQ-XENH-COVERAGE-4 (Event-Driven)** — WHEN strict 사용자 Frame/Params/CalibSet이 제공되면 THEN 등록 정본 부재와 무관하게 실행하고 `USER_SUPPLIED_UNVERIFIED`로 기록해야 한다.

## Exclusions (What NOT to Build)

- **골든 모델 변경 없음** — `modules/mse.py`·`modules/window.py`·`modules/denoise.py`·`common/`·`pipeline/`은 동결 오라클로 편집하지 않는다. 탭은 이들을 읽기-실행 전용으로 소비한다(REQ-XENH-GUARD-1).
- **알고리즘 재구현 없음** — Laplacian 다중스케일 강조·power-law/soft-clip 변조·noise-gate·DRC·percentile 정규화(mse), 조사야/직접선 분리·VOI·PS3.14 GSDF(window)의 어떤 부분도 UI에서 재구현하지 않는다. GSDF LUT 곡선 표시조차 골든 `build_gsdf_lut` 호출로만 얻는다(REQ-XENH-VIEW-5).
- **noise 모델 합성/튜닝 없음** — mse가 요구하는 (α,σ)는 상류 denoise(그룹 4) 또는 사전적재로만 공급하며, 탭은 노이즈 모델을 적합·튜닝·기본값 주입하지 않는다. denoise 파라미터 튜닝은 그룹 4(SPEC-XGUI-DENOISE, 예정) 범위다.
- **신규 스테이지·CalibKind 없음** — 조합은 기존 `CANONICAL_ORDER`·기존 CalibKind로만 이뤄진다. mse·window의 `CalibKind.OTHER`를 새 kind로 승격하지 않는다.
- **정본 수치 검증 없음(QUARANTINE)** — SAMPLE 실측 구동은 sanity 확인이며 EV 임계 도출·튜닝·적합에 쓰지 않는다(이슈 #29). 정본 수치 조합/EV 검증은 정본 지침세트(#33) 도착 후 별건이다.
- **C++ 엔진 이식·동일성 프레임 없음** — 조합 fidelity·±1 LSB envelope 소진은 P2 C++ 재계산(SPEC-XSEAM Stage 2, XDET-TC-020/021) 몫이며 본 SPEC 범위 밖이다.
- **성능·마샬링 최적화 없음** — 3072² 프레임의 스테이지별 중간 프레임 마샬링·스루풋 최적화는 범위 밖이다(정확성·표시 정합 증명이 목적).
- **Gen 2·배포 없음** — DL/ADR, 웹 서버·다중 사용자·배포는 범위 밖.

## 확정 결정 (v0.5.1)

1. Enhancement 결과 raw는 uint16 display-normalized 산출물이며 sidecar에 `domain=display_normalized`와 양자화 규약을 기록한다.
2. 원본 raw는 결과와 혼동하지 않도록 별도의 pre-stage artifact로만 저장한다.
3. MSE 단독 실행은 명시 noise model이 있을 때만 허용하고, 그렇지 않으면 denoise 조합을 요구한다.
4. DRC A/B는 선택 기능이다. 핵심 MSE/window 검증을 차단하지 않는다.
5. GSDF 곡선은 공개 golden `build_gsdf_lut` 호출 결과만 사용한다.
6. 중앙 TC 레지스트리는 G5 블록 XDET-TC-128~135이다.

## v0.5.1 public operation closure

| Python EntryPoint | GUI 노출 | TC |
|---|---|---|
| `modules.mse.required_params` | method selector 기반 ParamSchema | 128 |
| `modules.mse.process` | MSE action | 129~130 |
| `modules.window.process` | Window action | 131~132 |
| `modules.window.build_gsdf_lut` | GSDF LUT action/sub-command | 133 |
| `modules.window.remap_to_pvalue` | P-value remap action/sub-command | 134 |

모든 반환 axis/series/frame은 engine DTO를 표시하며 GSDF나 remap 수학을 WPF에서 재구현하지 않는다.
