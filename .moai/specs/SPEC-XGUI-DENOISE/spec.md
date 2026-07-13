---
id: SPEC-XGUI-DENOISE
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
labels: [xgui, gui-redesign, verification-gui, denoise, vst, bm3d, golden-frozen]
---

# SPEC-XGUI-DENOISE — Denoise (VST+BM3D) 알고리즘 그룹 GUI 검증 탭 (그룹 4)

> 본 사양은 `../SPEC-XGUI-MASTER/baseline-control.md`의 G0와 `traceability-matrix.md`를 상속한다. 사용자 승인·기준선 동결·`implementation_authorized=true` 전에는 구현 입력으로 실행하지 않으며, 승인 뒤 규범 변경은 버전 상승과 재승인을 요구한다.

XDET 검증 GUI 재설계(이슈 #58, 탭 = 알고리즘 그룹별 G-9)의 **그룹 4 — Denoise (WP5: VST+BM3D)** 검증 탭 명세다. 동결(FROZEN) Python 골든 `modules/denoise.py`(SWR-701~706)를 **호출만** 하여 노이즈 감소 전/후와 VST 왕복 무편향 근거를 검증한다. 공유 사실(불변 HARD 제약 G-1~G-9, 저장/열기 규약, 파이프라인 조합 사실)은 [SPEC-XGUI-MASTER/foundation.md](../SPEC-XGUI-MASTER/foundation.md)에 있으며 본 문서는 이를 **참조**하고 재기술하지 않는다.

- **AUTHORITATIVE 대조 원칙(G-1):** 아래 모든 process 시그니처·CalibKind·Params 키·오류형은 골든 소스에서 Grep/Read로 검증했다. v0.2.0의 설계 결정은 문서 하단 확정 결정에 기록한다.
- **선례 미러링:** frontmatter/구조는 [SPEC-XSEAM-002](../SPEC-XSEAM-002/spec.md)를 미러링. 뷰어 계보 = [SPEC-VIEWER-001](../SPEC-VIEWER-001/spec.md) REQ-VIEW-RUN-1(단일 모듈 `ProcessModule.process`)/RUN-2(부분·전체 `run_pipeline`) → C# 심(SPEC-XSEAM-002 REQ-XSEAM-CONTRACT-6 `run_pipeline` 미러) → 본 그룹 탭.
- **완료 정의(DoD):** (1) 입력 + populated NOISE CalibSet 조달 → (2) engine `AlgorithmCatalogManifest`의 selector-dependent required params로 동적 폼 구성 → (3) `IXdetEngine.RunPipeline(PipelineRunRequest)` 단일 stage 실행 → (4) 같은 seam으로 정렬 조합 실행 및 populated NOISE CalibSet 주입 → (5) dedicated `IXdetEngine` metric DTO로 NPS/SNR 산출 → (6) frame/mask artifact + run manifest 저장·hash/round-trip 검증 → (7) Python `apps.gui` helper 직접 의존 0, 골든 FROZEN/C-09/C-11/C-20/QUARANTINE 통과.
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.2.0 (2026-07-13)** — 중단 작업 복구 마무리. 구현 대상을 C# WPF `apps/xdet-console/`로 확정하고 Python `apps/gui/`는 참조 선례로 한정했다. 그룹별 결정·중앙 TC 레지스트리·plan/research를 확정했다. 골든 알고리즘은 변경하지 않는다.

- **v0.1.1 (2026-07-12)** — 라운드 1 교차검증 후속(audit-r1.md, VERDICT PASS·minor 2건 반영). **D1(NOISE CalibSet 조달 생산자 확정):** 골든 재대조 결과 (α,σ)의 **유일 정본 생산자는 `metrics.noise_model.fit_noise_model`**(noise_model.py:73-77 `@MX:ANCHOR "sole (alpha, sigma) producer"`, ≥2 선량 요구 noise_model.py:99)이며 `make_synthetic_calibset(NOISE)`는 빈 페이로드(synth_calibset.py:48)임을 확정. 선언 스칼라 (α,σ)를 담는 "채워진" NOISE CalibSet은 **공개 스키마 API**(`common.calibset.CalibSet` + 공개 상수 `K_NOISE_ALPHA="alpha"`/`K_NOISE_SIGMA="sigma"` calibset.py:90-92)로 **스칼라 2개를 패키징**하는 것으로, 신호처리 0(C-09 위반 아님)·공개 API 호출만(G-1 골든 무변경). 저작 계층 확정 = 정본 실측형 경로는 골든 `fit_noise_model`(합성 ≥2 선량 스택), 선언-스칼라 직접형은 GUI 어댑터/테스트 픽스처의 얇은 스키마-패키징(새 골든 생산자 신설 없음). INPUT-2/-3·GUARD-2·GUARD-4·「확정 결정」 2 갱신. **D2(NPS 단일프레임 규약 확정):** `compute_nps(frames: list[XFrame])`(nps.py:83)의 앙상블 평균은 **각 프레임의 중앙영역 반겹침 256² ROI 타일링**(`_central_rois` nps.py:53-80) 기반이므로, 단일 denoise 출력 `compute_nps([frame], params)`가 유효한 다-ROI 앙상블을 산출(다중프레임 스택 불요) — 단, 균일 flat 입력이며 중앙영역(`nps_central_frac`×축) ≥ ROI(256)여야 함. `compute_snr(frame, roi, params)`(ndt.py:129)는 단일프레임+명시 ROI. VIEW-3 갱신. 골든 무변경.
- **v0.1.0 (2026-07-12)** — 초안 생성. 이슈 #58(GUI 재설계). SPEC-XGUI-MASTER foundation 그룹 4 참조. 6개 REQ 그룹(INPUT/PARAM/APPLY/VIEW/IO/GUARD). 저작 시 **AUTHORITATIVE 소스로 검증한 사실**: (a) `modules/denoise.py::process(frame, calib, params)->XFrame`(denoise.py:616) 단일 계약, **비상태형**(lag과 대비). (b) 스테이지 `denoise`는 `CANONICAL_ORDER`(orchestrator.py:67)에서 `… → virtual_grid → denoise → mse → window → post`; `_KIND_BY_STAGE["denoise"]="noise"`(orchestrator.py:157) → `calib_kind_for_stage("denoise")` = `CalibKind.NOISE`(orchestrator.py:165-175). (c) CalibSet 페이로드 = `NOISE_PAYLOAD_KEYS=("alpha","sigma")`(calibset.py:90-92); `_resolve_noise(calib)`(denoise.py:129-148)가 `calib.data["alpha"]`/`["sigma"]`를 소비하고 부재/퇴화(alpha<=0, sigma<0, 비유한, 키 결여) 시 `DenoiseError`로 거부 — XFrame 기본 `NoiseModel(0,0)`은 폴백으로 **절대 사용 안 함**(SWR-000-5). (d) Params 키는 **method 셀렉터 의존 함수** `required_params(params)`(denoise.py:92-114)로 노출(SPEC-ERGO-001) — 정적 상수 아님. (e) **`common/synth_calibset.py::make_synthetic_calibset`(synth_calibset.py:24)는 빈 페이로드** → NOISE kind로 만들어도 `_resolve_noise`가 하드 실패하므로 denoise 탭은 조합 시 빈 합성 OTHER/NOISE placeholder를 쓸 수 없고 **채워진 NOISE CalibSet을 calib_map으로 주입**해야 함(pipeline_panel.py:118 "substitution when absent, not always"). (f) 실측 가용성: 그룹 4 = **합성 전용 / #33 대기**(foundation §2 group 4) — 등록 edrogi SAMPLE에 NOISE CalibSet 부재(OFFSET/GAIN/DEFECT만). (g) 저장은 `<name>_result.raw`(16-bit headerless, foundation §3) — 현행 `apps/gui/export.py`(npz+json)와 포맷 상이. (h) 열기·쓰기 가드·로더 = VIEWER-001 인프라(`common/io.load_raw_frame` io.py:35, `apps/gui/io_panel.guard_output_path` io_panel.py:27) 재사용. 확정 설계 결정: **VST 왕복 무편향의 1급 bias-vs-λ 곡선은 denoiser-우회 경로가 필요한데 공개 골든 표면은 `process`(GAT→denoise→역변환 전체)만 노출** → 무편향 확인은 엔진 위임 통계(DC/평균 보존)+골든 기록 진단(clamp_rate)으로 범위 한정, denoiser-우회 진단은 tests/(XDET-TC-011) 소관 유지(「확정 결정」 1).

## Environment / Assumptions

- **본 SPEC은 T-스테이지가 아니다.** `CANONICAL_ORDER` 변경·`process(...)->XFrame` 시그니처 변경·신규 `CalibKind`·`_KIND_BY_STAGE` 변경이 전혀 없다. VIEWER-001/XSEAM 검증 도구 계열의 **GUI 탭 additive** 확장이며, 골든 4계층(`modules`/`metrics`/`common`/`pipeline`)은 불변 오라클로 호출만 한다(G-1).
- **foundation 상속.** 불변 HARD 제약 G-1~G-9, 저장 규약(§3 `<name>_result.raw`), 열기 규약(§4 상주 폴더 브라우저), 파이프라인 조합 사실(§5), CalibSet 게이트 사실(`_calibration_gate` orchestrator.py:178-280)을 [SPEC-XGUI-MASTER/foundation.md](../SPEC-XGUI-MASTER/foundation.md)에서 상속하며 본 문서에서 재기술하지 않는다.
- **검증된 골든 사실(그룹 4 고유).** `modules/denoise.py`: 3단 파이프라인 = GAT 순변환(SWR-702, `_gat_forward` denoise.py:154, radicand<0은 0으로 clamp) → 변환영역 denoise(BM3D 2단 hard-threshold+Wiener `_bm3d` denoise.py:413 / NLM 대안 `_nlm` denoise.py:517, Haar 3D) → **정확 무편향 역변환 LUT**(SWR-703, Makitalo-Foi 2011, `_build_inverse_lut` denoise.py:176 / `_gat_inverse` denoise.py:239). **점근/대수 역변환((f/2)² 계열)은 금지**(SWR-703, CLAUDE.md; 코드에 해당 경로 부재, denoise.py:194 명시).
- **입력의 이중성.** denoise는 **입력 프레임**(노이즈 있는 XFrame)과 **NOISE CalibSet**(α,σ) 둘을 필요로 한다. 다른 스테이지가 검출 CalibSet(offset=O_map, gain=G_map, defect=class_map)을 갖듯 denoise는 `CalibKind.NOISE`의 (α,σ)를 갖는다(orchestrator.py:157, calibset.py:86-92). (α,σ)의 **유일 정본 생산자**는 오프라인 빌더 `metrics/noise_model.py::fit_noise_model(dose_levels, ...)->CalibSet(NOISE)`(noise_model.py:78, `@MX:ANCHOR "sole (alpha, sigma) producer"` noise_model.py:73-77) — 다중 선량 flat 스택(**≥2 선량**, noise_model.py:99-103)의 var=α·mean+σ² 회귀. 빌더는 `metrics→common` 일방이며 denoise 모듈은 metrics를 import하지 않는다.
- **NOISE CalibSet 조달 계층·생산자 확정(D1 해소).** "채워진 NOISE CalibSet"의 생산 경로는 정확히 둘이며 어느 것도 골든을 신설·변경하지 않는다. (1) **정본 실측형(1차)** = 골든 `fit_noise_model`에 **합성 ≥2 선량 Poisson-Gaussian flat 스택**을 입력해 (α,σ)를 회귀 산출(호출만, G-1). (2) **선언-스칼라 직접형(테스트/데모용)** = 선언된 (α,σ) 스칼라 2개를 **공개 스키마 API**(`common.calibset.CalibSet` 데이터클래스 + 공개 상수 `K_NOISE_ALPHA="alpha"`/`K_NOISE_SIGMA="sigma"`, calibset.py:90-92)로 `data={K_NOISE_ALPHA: α, K_NOISE_SIGMA: σ}` 패키징. 이 패키징은 **신호처리가 0**이므로 C-09를 위반하지 않고, **공개 API 호출만**이므로 G-1(골든 무변경)을 만족한다 — 즉 새 골든 생산자 함수를 신설하지 않는다. 저작 계층: (2)는 GUI 어댑터(apps/gui) 또는 테스트 픽스처의 얇은 스키마-패키징 단계이며(`common/synth_calibset.py`가 배포성 때문에 `common/`에 사는 선례와 달리, 여기서는 **새 common 헬퍼를 신설하지 않고** 기존 공개 `CalibSet`/키 상수만 사용), 정본 수치가 필요한 실측형 경로는 항상 (1) `fit_noise_model`을 쓴다. **빈 `make_synthetic_calibset(NOISE)`(빈 페이로드 synth_calibset.py:42-51)는 (α,σ) 결여로 `_resolve_noise` 하드 실패하므로 denoise 조달에 사용 금지**(INPUT-3).
- **부작용·하류 소비.** `process`는 해결된 (α,σ)를 출력 `XFrame.noise`에 기록한다(denoise.py:653) — T6 `mse` SWR-803 노이즈 게이팅이 소비(REQ-DENOISE-CONTRACT-2, foundation §2 group 5). 진단 스칼라 {method, k_s, clamp_rate, resolved_alpha, resolved_sigma}는 `HistoryEntry.extra`에 기록(denoise.py:659-665). 마스크 가중(SWR-706): DEFECT|INTERPOLATION|SATURATION|SATURATION_BAND은 블록매칭 통계에서 제외; SATURATION/SATURATION_BAND 픽셀 **값은 불변 보존**(복원 금지, SWR-602, denoise.py:610-612). 마스크 플래그는 세우거나 지우지 않음.
- **실측 데이터 가용성(SAMPLE·비정본, QUARANTINE 이슈 #29).** 그룹 4는 **합성 전용 또는 #33(정본 지침세트) 대기**다. 등록 edrogi SAMPLE에는 NOISE CalibSet이 없다(offset/gain/defect만 존재, foundation §2 group 1). QUARANTINE은 SAMPLE 수치에서 (α,σ) 적합/도출을 금지하므로 SAMPLE nps_flat 프레임으로 실 NOISE CalibSet을 **정본으로** 만들 수 없다. 따라서 SAMPLE 적용은 최대 **plumbing sanity 스모크**(합성/선언 (α,σ)를 담은 채워진 NOISE CalibSet을 실 3072² flat 프레임에 적용 → 유한·비퇴화·오류무발생 확인)일 뿐 수치 골든 주장이 아니다. 정본 수치 검증은 #33 선량 사다리로 `fit_noise_model` 후 별건이다.
- **빈 합성 CalibSet 함정(그룹 4 고유).** `make_synthetic_calibset(resolution, CalibKind.NOISE)`(synth_calibset.py:42-51)는 페이로드가 **비어 있다** → `_resolve_noise`가 키 결여로 하드 실패(denoise.py:136-140). 그러므로 denoise 탭·조합 경로는 다른 그룹처럼 빈 합성 placeholder를 쓸 수 없고 **채워진 NOISE CalibSet을 명시적으로 주입**해야 한다(REQ-VIEW-CORE-3 "부재 시 대체"의 예외 케이스).
- **조합·심 계약.** denoise 단일/조합 실행은 모두 `IXdetEngine.RunPipeline(PipelineRunRequest)`를 통과하고 PythonNet adapter가 오케스트레이터에 위임한다. Python `apps.gui` helper는 실행 경계가 아니다. `mse`가 포함되면 denoise의 (α,σ)>0 handoff를 보존한다.
- **뷰어 도메인.** denoise 출력은 raw-DN 도메인 그대로다(그룹 5 mse/window의 정규화 [0,1] 표시 도메인과 대비, foundation §2 group 5) — 저장 시 float→uint16 역스케일이 불필요한 단순 clip/rint 경로(foundation §3).
- **환경.** Python은 `uv run`으로만 실행(`uv run pytest`, `uv run lint-imports`). 정확성·재현성이 목적이며 성능 최적화는 목적이 아니다(P1, 속도 최적화 금지). 한글 출력은 `PYTHONIOENCODING=utf-8`.

## Requirements (EARS)

### REQ-XGUI-DENOISE-TARGET — 구현 대상 경계

- **REQ-XGUI-DENOISE-TARGET-1 (Ubiquitous)** — 시스템은 `apps/xdet-console/` C# WPF 앱을 구현 대상으로 사용해야 하며, `apps/gui/`와 Python 테스트·패널은 계약 및 검증 선례로만 참조해야 한다. WPF는 Python 모듈을 직접 호출하지 않고 `IXdetEngine`/PythonNet seam을 경유해야 한다.

### REQ-XGUI-DENOISE-INPUT — 입력세트: 프레임 + NOISE CalibSet 조달 (C-21, REQ-VIEW-CORE-1/-3, SWR-701)

- **REQ-XGUI-DENOISE-INPUT-1 (Event-Driven)** — WHEN 사용자가 입력 프레임을 선택하면, THEN 탭은 상주 폴더 브라우저(foundation §4 — 폴더 트리 + 가상화 썸네일 + 형제 필름스트립 + 이전/다음)로 `common.io.load_raw_frame(raw_path, meta_path)`(io.py:35)를 호출해 headerless 16-bit raw + `.json`({resolution, dtype}) 사이드카를 float32 XFrame으로 적재해야 하며, 파일을 지정해도 부모 폴더의 형제 목록을 함께 표시해야 한다.
- **REQ-XGUI-DENOISE-INPUT-2 (Event-Driven)** — WHEN denoise 스테이지를 적용하려면, THEN 탭은 그 스테이지 고유의 **NOISE CalibSet**((α,σ) 페이로드, `NOISE_PAYLOAD_KEYS=("alpha","sigma")`)을 조달해야 하며, 조달 경로는 정확히 (a) **정본형** — 골든 `metrics.noise_model.fit_noise_model`로 다중 선량 flat 스택(**≥2 선량**, noise_model.py:99-103)에서 (α,σ)를 회귀 산출(유일 정본 생산자, noise_model.py:73-77), 또는 (b) **선언-스칼라형** — 선언된 (α,σ)를 **공개 스키마 API**(`common.calibset.CalibSet` + 공개 상수 `K_NOISE_ALPHA`/`K_NOISE_SIGMA`)로 `data={"alpha":α,"sigma":σ}` 패키징한 **채워진** NOISE CalibSet 중 하나여야 한다. (b)는 신호처리 0의 스키마-패키징이므로 C-09 위반이 아니고 공개 API 호출만이므로 G-1 골든 무변경이며, 새 골든 생산자를 신설하지 않는다. **빈 `make_synthetic_calibset(NOISE)`는 (α,σ) 결여로 사용 금지**(INPUT-3).
- **REQ-XGUI-DENOISE-INPUT-3 (Unwanted)** — IF denoise 스테이지가 (α,σ) 페이로드가 없는 CalibSet(빈 합성 placeholder 포함)이나 퇴화 모델(α≤0, σ<0, 비유한)로 구동되면, THEN 실행은 골든의 명시 오류 `DenoiseError`로 거부되어야 하고 어떤 기본 노이즈 모델(XFrame 기본 `NoiseModel(0,0)` 포함)도 대체되지 않아야 한다(SWR-000-5, denoise.py:136-147; 탭은 이 오류를 스스로 우회·억제하지 않고 그대로 표면화).

### REQ-XGUI-DENOISE-PARAM — method 셀렉터 + 동적 required_params 폼 (SPEC-ERGO-001, SWR-704/705)

- **REQ-XGUI-DENOISE-PARAM-1 (Event-Driven)** — WHEN 사용자가 `denoise_method`를 변경하면, THEN WPF는 versioned `AlgorithmCatalogManifest`의 selector-dependent required params를 사용해 폼을 재구성해야 한다. PythonNet adapter가 골든 `required_params(params)`와 manifest 일치를 검증하며 불일치는 실행 차단이다.
- **REQ-XGUI-DENOISE-PARAM-2 (Ubiquitous)** — 탭은 method 무관 공통 필수 키 `denoise_strength_ks`([T]) · `denoise_inv_lut_lambda_max`([P]) · `denoise_inv_lut_nodes`([P]) · `denoise_inv_lut_gh_nodes`([P])를 수집해야 하며(denoise.py:106), method=`"bm3d"`이면 추가로 `denoise_bm3d_block`·`denoise_bm3d_step`·`denoise_bm3d_max_match`·`denoise_bm3d_search_window`·`denoise_bm3d_lambda3d`·`denoise_bm3d_kaiser_beta`([L], Dabov 2007)·`denoise_bm3d_match_tau_hard`·`denoise_bm3d_match_tau_wiener`([T])를(denoise.py:107-111), method=`"nlm"`이면 추가로 `denoise_nlm_h`·`denoise_nlm_patch`·`denoise_nlm_window`([P])를(denoise.py:112-113) 수집해야 한다.
- **REQ-XGUI-DENOISE-PARAM-3 (Unwanted)** — IF 선택된 method의 필수 Params 키 중 하나라도 결여되거나(BM3D `block`/`max_match`가 2의 거듭제곱이 아니면 포함), THEN 실행은 골든의 명시 오류 `DenoiseError`로 거부되어야 하고 탭은 결여 키/제약을 그대로 표시해야 한다(denoise.py:117-123/432-440; 탭이 기본값을 임의 대입하지 않음 — HARD 파라미터 외부화 정책).

### REQ-XGUI-DENOISE-APPLY — build/apply 워크플로: 단일 스테이지 → 조합 (REQ-VIEW-RUN-1/-2, REQ-XSEAM-CONTRACT-6/COMPOSE-1~2)

- **REQ-XGUI-DENOISE-APPLY-1 (Event-Driven)** — WHEN 사용자가 denoise를 단일 적용하면, THEN WPF는 stages=["denoise"]인 `PipelineRunRequest`를 `IXdetEngine.RunPipeline`에 전달하고 엔진 결과의 before/after/mask/diag만 표시해야 한다.
- **REQ-XGUI-DENOISE-APPLY-2 (Event-Driven)** — WHEN 사용자가 denoise 포함 조합을 적용하면, THEN WPF는 정렬 stages, typed params/calib map을 같은 `IXdetEngine.RunPipeline`에 한 번 전달하고 `PipelineRunResult.intermediates`를 표시해야 한다. denoise에는 populated NOISE CalibSet을 명시 주입한다.
- **REQ-XGUI-DENOISE-APPLY-3 (Unwanted)** — IF 탭 또는 어댑터가 GAT/BM3D/역변환 등 어떤 처리 결과를 스스로 계산하거나, 스테이지를 스스로 정렬·조합하거나, 결여된 NOISE CalibSet을 합성(빈 placeholder 대입)하면, THEN 이는 거부되어야 한다(모든 DSP는 골든에 — C-09; 조합/순서 권한은 Python 오케스트레이터에 — C-11; SWR-000-2/-5).

### REQ-XGUI-DENOISE-VIEW — 그룹 고유 뷰어: 노이즈 텍스처 + 무편향 근거 (C-01/C-09, SWR-702/703/706)

- **REQ-XGUI-DENOISE-VIEW-1 (Event-Driven)** — WHEN denoise 적용이 완료되면, THEN 탭은 before/after/diff/W-L와 mask overlay를 표시하고 블록매칭 제외 vs 값 보존 의미를 구분해야 한다. 픽셀 histogram은 engine result DTO가 제공할 때만 표시하며 UI가 bin/count를 계산하지 않는다(C-09).
- **REQ-XGUI-DENOISE-VIEW-2 (Event-Driven)** — WHEN denoise 적용이 완료되면, THEN 탭은 골든이 **기록한** 진단값 — 출력 `XFrame.noise`의 해결 (α,σ)(denoise.py:653) 및 `HistoryEntry.extra`의 {method, k_s, clamp_rate, resolved_alpha, resolved_sigma}(denoise.py:659-665) — 을 표시해야 한다(이는 엔진 기록값의 표시이지 UI 계산이 아님 — C-09). 이 (α,σ)가 하류 mse(T6 SWR-803)로 넘어가는 handoff임을 함께 표기한다.
- **REQ-XGUI-DENOISE-VIEW-3 (Event-Driven)** — WHEN 사용자가 정량을 요청하면, THEN WPF는 dedicated `IXdetEngine` NPS/SNR request DTO를 사용하고 반환 `MetricResultEnvelope`만 표시해야 한다. PythonNet adapter가 균일 flat 전/후를 각각 `compute_nps([frame], params)`와 `compute_snr`에 위임한다. UI/adapter의 NPS/SNR/DC 계산은 금지한다(C-09).
- **NPS 단일프레임 앙상블 규약(주, D2 확정).** `compute_nps`의 "스택"은 `list[XFrame]`이나 실 앙상블 단위는 프레임이 아니라 **각 프레임 중앙영역의 반겹침 256² ROI**다. 따라서 (i) NPS/NNPS 뷰는 **균일 flat** 노이즈 텍스처(합성 Poisson-Gaussian flat 또는 SAMPLE `nps` flat)에 대해서만 의미가 있고, (ii) 구조/엣지가 있는 임의 영상에는 적용하지 않으며(비-균일 → 지표 무의미), (iii) 중앙영역이 256보다 작은 소형 입력은 `MetricReadError`(nps.py:68-72)로 거부된다 — 탭은 이 오류를 그대로 표면화한다.

### REQ-XGUI-DENOISE-IO — 열기/저장 규약: 폴더 브라우저 + `<name>_result.raw` (C-20, foundation §3/§4)

- **REQ-XGUI-DENOISE-IO-1 (Event-Driven)** — WHEN 사용자가 결과를 저장하면, THEN 탭은 `xdet.frame-artifact/1.0` raw/sidecar, `uint8` mask raw, `xdet.run-manifest/1.0`을 기록하고 pixel/mask bit-exact round-trip과 input/calib/params/output hash를 검증해야 한다.
- **REQ-XGUI-DENOISE-IO-2 (Unwanted)** — IF 저장 경로가 `<project_root>/data` 하위이면, THEN C# export choke point가 실행 전에 typed validation error로 거부해야 한다. Python `guard_output_path` 직접 호출은 금지한다(C-20).

### REQ-XGUI-DENOISE-GUARD — 불변 게이트 + 데이터 가용성 (G-1~G-8, QUARANTINE, SWR-000-2/-5)

- **REQ-XGUI-DENOISE-GUARD-1 (Ubiquitous)** — 탭은 `modules/denoise.py`를 포함한 골든 4계층을 동결 오라클로 **호출만** 해야 하며(G-1), 시그니처·수치·상수·`CANONICAL_ORDER`·`_KIND_BY_STAGE`를 변경하지 않고, 코어를 단방향 소비하며(C-11, `apps/gui`→코어 일방, import-linter forbidden 계약 + 위반 카나리 유지), 어떤 지표·DSP도 스스로 계산하지 않는다(C-09).
- **REQ-XGUI-DENOISE-GUARD-2 (State-Driven)** — WHILE 정본 NOISE CalibSet(#33 정본 지침세트의 선량 사다리 적합 결과)이 부재하는 동안, 탭은 (a) 합성 ≥2 선량 Poisson-Gaussian 스택→`fit_noise_model` 산출 NOISE CalibSet, 또는 (b) 선언 (α,σ)를 공개 스키마 API로 패키징한 채워진 NOISE CalibSet을 1차 검증 경로로 사용하고, 등록 edrogi SAMPLE 프레임(균일 `nps` flat)에 대해서는 **sanity 스모크**(유한·비퇴화·오류무발생)로만 구동해야 한다 — SAMPLE 수치에서 (α,σ) 적합/EV 임계/튜닝 도출은 금지한다(QUARANTINE 이슈 #29, G-5).
- **REQ-XGUI-DENOISE-GUARD-3 (Unwanted)** — IF SAMPLE(에드로지) 또는 벤더 `_result` 프레임에서 산출된 어떤 값이 정본 골든/기대 기준으로 승격되거나, 그 수치가 EV 임계·보정 상수·모듈 Params 기본값으로 설정되면, THEN 이는 거부되어야 한다(비정본 `panel_id="SAMPLE-EDROGI-16BIT"`/provenance `sample=true`; 수치 출처 가드 REQ-REALDATA-VALIDATE-4 정신 승계).
- **REQ-XGUI-DENOISE-GUARD-4 (Unwanted)** — IF 탭·어댑터가 (α,σ)를 얻기 위해 골든에 새 공개 생산자 함수를 신설하거나, denoise 사설 헬퍼(`_gat_forward`/`_gat_inverse`/`_bm3d`)를 호출하거나, `fit_noise_model` 회귀를 UI에서 재구현하면, THEN 이는 거부되어야 한다 — (α,σ)의 유일 정본 산출은 골든 `fit_noise_model`(호출만)이고, 선언-스칼라 CalibSet은 오직 **공개** `common.calibset.CalibSet`+공개 상수 `K_NOISE_ALPHA`/`K_NOISE_SIGMA`로 스칼라를 패키징하는 것(신호처리 0 → C-09 안전, 공개 API 호출만 → G-1 골든 무변경)에 한한다(D1 확정 계약).

### REQ-XDENOISE-COVERAGE — selector별 전체 실행

- **REQ-XDENOISE-COVERAGE-1 (State-Driven)** — WHILE denoise method/selector가 바뀌면 engine은 실제 `modules.denoise.required_params(params)`를 호출해 BM3D 또는 NLM 필수 키 집합을 갱신해야 한다.
- **REQ-XDENOISE-COVERAGE-2 (Event-Driven)** — WHEN 각 selector의 필수 Params와 populated NOISE CalibSet이 제공되면 THEN 실제 `modules.denoise.process`를 실행하고 XFrame/noise/history/mask와 engine diagnostics를 반환해야 한다.
- **REQ-XDENOISE-COVERAGE-3 (Event-Driven)** — WHEN DoseLevel series가 제공되면 THEN Calibration service의 실제 `metrics.noise_model.fit_noise_model`로 NOISE CalibSet을 생성하고 같은 탭에서 소비할 수 있어야 한다.
- **REQ-XDENOISE-COVERAGE-4 (Event-Driven)** — WHEN strict 사용자 input/NOISE CalibSet이 제공되면 THEN 등록 정본 부재로 기능을 막지 않고 실행 결과를 `USER_SUPPLIED_UNVERIFIED`로 기록해야 한다.

## Exclusions (What NOT to Build)

- **골든 모델 변경 없음** — `modules/denoise.py`(GAT/BM3D/NLM/exact-inverse-LUT)·`metrics/noise_model.py`·`pipeline/orchestrator.py`·`common/*`는 동결 오라클로 편집하지 않는다. 탭은 이들을 읽기-실행 전용으로 소비한다(G-1, C-09/C-11).
- **denoiser-우회 무편향 진단(bias-vs-λ)의 골든 신설 없음** — VST 왕복 무편향의 1급 bias-vs-λ 곡선은 denoiser를 우회한 GAT→exact-inverse 경로가 필요하나 공개 골든 표면은 `process`(전체 경로)만 노출한다. 탭은 이를 위해 골든에 공개 진단 진입점을 신설하거나 사설 헬퍼(`_gat_forward`/`_gat_inverse`)를 호출하지 않는다 — 그 검증은 tests/(XDET-TC-011, 합성 Poisson-Gaussian) 소관이다(「확정 결정」 1).
- **점근/대수 역 Anscombe 없음** — 탭은 정확 무편향 역변환(SWR-703)만 소비한다. 점근 역((f/2)² 계열)은 골든에도 GUI에도 존재하지 않는다(CLAUDE.md 금지).
- **UI에서의 DSP·조합 재구현 없음** — GAT/BM3D/Wiener/역변환·스테이지 정렬·조합 결정은 골든/오케스트레이터에 남는다. 탭은 표시·조달·요청만 한다(C-09/C-11).
- **정본 수치 검증 없음(QUARANTINE)** — SAMPLE 실측 구동은 sanity(유한·비퇴화·구조) 확인이며 수치 골든/EV 도출·튜닝에 쓰지 않는다(이슈 #29). 정본 수치 검증은 #33 도착 후 별건이다.
- **신규 파이프라인 스테이지·CalibKind 없음** — 본 SPEC은 `denoise` 스테이지·`CalibKind.NOISE`를 신설하지 않는다(이미 SPEC-DENOISE-001에서 존재). GUI 탭 additive만이다.
- **별도 그룹 저장 스키마 없음** — 그룹 전용 최소 sidecar를 만들지 않고 foundation의 frame artifact/mask/run manifest 공통 스키마를 그대로 사용한다.

## 확정 결정 (v0.5.1)

1. denoiser-bypass bias-vs-λ 곡선은 공개 golden 표면이 없으므로 GUI 범위에서 제외한다. 무편향 관측은 엔진 통계와 기록 진단으로 한정한다.
2. NOISE CalibSet은 `fit_noise_model` 정본 경로 또는 명시 alpha/sigma의 test/demo DTO 패키징으로 조달한다. 빈 synthetic NOISE CalibSet은 금지한다.
3. NPS와 SNR은 metrics engine을 호출하고 UI는 반환값만 표시한다.
4. 중앙 TC 레지스트리는 G4 블록 XDET-TC-120~127 전체를 사용한다.

## v0.5.1 public operation closure

| Python EntryPoint | GUI 노출 | TC |
|---|---|---|
| `modules.denoise.required_params` | method selector 기반 ParamSchema | 120, 124~127 |
| `modules.denoise.process` | denoise action(BM3D/NLM 포함) | 121~127 |
| `metrics.noise_model.fit_noise_model` | Noise model build action | 122 |
| `metrics.nps.compute_nps` | NPS validation action | 123 |
| `metrics.ndt.compute_snr` | SNR validation action | 123 |

selector 변경 뒤 required key set과 UI 입력 schema가 다르면 실행 전 실패하며 adapter/UI가 기본값을 보충하지 않는다.
