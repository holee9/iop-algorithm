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
labels: [xgui, gui-redesign, verification-gui, denoise, vst, bm3d, golden-frozen, acceptance]
---

# SPEC-XGUI-DENOISE — 인수 기준 (acceptance)

> 본 인수기준의 모든 EARS ID·중앙 TC·필수 증거 연결은 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따른다. `baseline-control.md`의 G0와 사용자 승인 전에는 이 체크리스트를 구현 완료 증거로 사용할 수 없으며 모든 TC는 `PLANNED` 상태를 유지한다.

> **구현 대상:** `apps/xdet-console/` C# WPF 앱. `apps/gui/`와 Python 테스트는 계약·검증 선례이며 구현 대상이 아니다.
Denoise(WP5: VST+BM3D) 검증 탭(그룹 4)의 **E2E Given-When-Then**: 열기(상주 폴더 브라우저) → NOISE CalibSet 조달 + method/Params 폼 → build/apply(단일 스테이지 → 조합) → 저감/무편향 정량 위임 → 저장 `<name>_result.raw` → 왕복 재적재·골든 무변경 검증. 모든 기준은 **관측 가능**(파일 적재/저장 성공·왕복 픽셀 일치 / 골든 엔진 산출 수치 표시 / 명시 오류로 거부 / `git diff` 무변경 / import-linter green)해야 한다. 공유 사실(불변 HARD 제약 G-1~G-9, 저장 §3·열기 §4 규약, 조합 §5)은 [SPEC-XGUI-MASTER/foundation.md](../SPEC-XGUI-MASTER/foundation.md) 상속이며 재기술하지 않는다.

- **골든 대조 원칙(G-1):** 아래 인용된 함수·CalibKind·Params 키·오류형은 모두 골든 소스 Grep/Read로 검증됨. 지어내기 없음.
- **데이터 정책:** 그룹 4 = **합성 전용 또는 #33 대기**(foundation §2 group 4 — SAMPLE에 NOISE CalibSet 부재). 1차 검증 경로는 **합성 Poisson-Gaussian flat + 조달된 NOISE CalibSet**. 등록 edrogi 실측 연결은 **`nps`(nps_flat) 실 flat 프레임에 대한 plumbing sanity 스모크 1건**에 한하며, 그 (α,σ)는 합성/선언(SAMPLE 적합 아님) — **QUARANTINE(이슈 #29)**: sanity(유한·비퇴화·구조)만 단언, 수치 골든 주장 없음.
- **TC 배정:** `XDET-TC-120~127`은 SPEC-XGUI-MASTER 중앙 레지스트리의 G4 확정 블록이다.

## Scenarios (Given-When-Then)

### Scenario 1 — 열기: 상주 폴더 브라우저 + raw 적재 (XDET-TC-120, REQ-XGUI-DENOISE-INPUT-1) — foundation §4
- **Given** 상주 폴더 브라우저(폴더 트리 + 가상화 썸네일 + 형제 필름스트립 + 이전/다음)와, headerless 16-bit raw + `.json`({resolution, dtype}) 사이드카(합성 Poisson-Gaussian flat 또는 SAMPLE `nps` flat)가 있고,
- **When** 사용자가 입력 프레임을 선택하거나(또는 파일을 직접 지정하거나),
- **Then** 탭은 `common.io.load_raw_frame(raw_path, meta_path)`(io.py:35)로 uint16→float32 무손실 업캐스트해 XFrame으로 적재하고, **파일을 지정해도 부모 폴더의 형제 목록**(필름스트립/썸네일)을 함께 표시해야 한다(단독 파일 열기가 아니라 컨텍스트 유지).

### Scenario 2 — NOISE CalibSet 조달 + method 셀렉터 동적 Params 폼 (XDET-TC-120, REQ-XGUI-DENOISE-INPUT-2 / PARAM-1 / PARAM-2)
- **Given** 적재된 프레임이 있고, NOISE CalibSet 조달 경로가 (a) 골든 `metrics.noise_model.fit_noise_model`에 **합성 ≥2 선량 Poisson-Gaussian flat 스택**을 입력(유일 정본 생산자, noise_model.py:73-77/99-103) 또는 (b) 선언 (α,σ)를 **공개 스키마 API**(`common.calibset.CalibSet` + 공개 상수 `K_NOISE_ALPHA`/`K_NOISE_SIGMA`, calibset.py:90-92)로 `data={"alpha":α,"sigma":σ}` 패키징 중 하나로 주어지면,
- **When** 사용자가 `denoise_method` 셀렉터(기본 `"bm3d"`, 대안 `"nlm"`)를 설정하면,
- **Then** 탭은 골든 함수 `required_params(params)`(denoise.py:92)를 호출해 **그 method가 요구하는 정확한 Params 키 집합**으로 폼을 동적 구성해야 하며(정적 키 표 하드코딩 금지), 공통 키 `denoise_strength_ks`·`denoise_inv_lut_lambda_max`·`denoise_inv_lut_nodes`·`denoise_inv_lut_gh_nodes`에 더해 bm3d이면 `denoise_bm3d_{block,step,max_match,search_window,lambda3d,kaiser_beta,match_tau_hard,match_tau_wiener}`, nlm이면 `denoise_nlm_{h,patch,window}`를 노출해야 한다. (b) 경로의 CalibSet 패키징은 **신호처리 0**(C-09 안전)·**공개 API 호출만**(G-1 무변경)이어야 한다.

### Scenario 3 — build/apply 단일 스테이지 + 그룹 고유 뷰어 (XDET-TC-121, REQ-XGUI-DENOISE-APPLY-1 / VIEW-1 / VIEW-2) — VIEWER RUN-1 미러 — **load-bearing**
- **Given** 적재 프레임 + 채워진 NOISE CalibSet + method별 완전한 Params가 있고,
- **When** 사용자가 denoise를 **단일 스테이지**로 적용하면,
- **Then** 탭은 `IXdetEngine.RunPipeline(PipelineRunRequest)`에 `Stages=("denoise",)`와 채워진 NOISE CalibSet/Params를 전달해 실제 `modules.denoise.process`가 낸 입력/출력 XFrame 쌍을 받고, (i) 노이즈 텍스처 **before/after + diff + W/L**, (ii) 마스크 오버레이를 **블록매칭 제외(SWR-706) vs 값 보존(SATURATION/SATURATION_BAND, SWR-602)** 로 구분 표기, (iii) 골든이 **기록한** 진단 — 출력 `XFrame.noise`의 해결 (α,σ)(denoise.py:653) 및 `HistoryEntry.extra`의 {method, k_s, clamp_rate, resolved_alpha, resolved_sigma}(denoise.py:659-665) — 를 표시해야 한다. WPF/adapter는 `apps.gui.module_panel`을 호출하지 않고 모든 수치는 골든 엔진 산출(C-09)이어야 한다.

### Scenario 4 — build/apply 정렬된 부분집합/전체 조합 (XDET-TC-121, REQ-XGUI-DENOISE-APPLY-2) — VIEWER RUN-2 미러
- **Given** denoise가 정렬된 부분집합/전체에 포함되고(예: 하류 `mse`가 α>0을 요구 → denoise 선행 공급, foundation §5), 각 스테이지가 고유 CalibSet·Params를 지니면,
- **When** 사용자가 그 정렬된 부분집합(또는 전체 = `tuple(s for s in CANONICAL_ORDER if s != "post")`)을 적용하면,
- **Then** 탭은 generic `IXdetEngine.RunPipeline(PipelineRunRequest)`로 단일 패스 실행해 조합 출력과 각 스테이지 전/후를 표시하되, **denoise 스테이지에는 채워진 NOISE CalibSet을 `CalibMap`에 주입**해야 한다. PythonNet은 `{stage: module.process}` bare 콜러블 레지스트리로 골든 `run_pipeline`을 직접 호출하며 `apps.gui.pipeline_panel` helper를 호출하지 않아야 한다. 조합/순서 권한은 Python 오케스트레이터에 남는다.

### Scenario 5 — 저감/무편향 정량 metrics 위임 (XDET-TC-122, REQ-XGUI-DENOISE-VIEW-3) — D2 확정
- **Given** 균일 flat 저감 전/후 XFrame 쌍이 있고,
- **When** 사용자가 노이즈 저감/무편향 정량을 요청하면,
- **Then** 탭은 NPS/NNPS와 SNR을 `IXdetEngine`의 metric 전용 request/result를 통해 각각 골든 `metrics.nps.compute_nps`와 `metrics.ndt.compute_snr`에 위임해 산출·표시해야 하며(GUI 자체 지표 계산 0 — C-09), VST 왕복 무편향의 근거로 flat DC/평균이 엔진 통계로 보존됨을 함께 제시해야 한다. adapter가 호출한 공개 entry point는 run manifest에 기록한다. **denoiser-우회 bias-vs-λ 곡선은 범위 밖**이다.

### Scenario 6 — 저장: `<name>_result.raw` + C-20 게이트 (XDET-TC-122, REQ-XGUI-DENOISE-IO-1 / IO-2) — foundation §3
- **Given** denoise 출력 XFrame(raw-DN 도메인)이 있고,
- **When** 사용자가 **사용자 지정 폴더**에 저장하면,
- **Then** 탭은 `<name>_result.raw`, `xdet.frame-artifact/1.0` sidecar, mask가 있으면 `<name>_result_mask.raw`, 별도 `xdet.run-manifest/1.0`을 써야 한다. sidecar는 source/export domain과 quantization을, manifest는 input/Params/CalibSet/artifact hash를 포함한다. Pixel/mask artifact round-trip과 run reproducibility는 별도로 판정한다. **IF** 저장 경로가 `<project_root>/data` 하위이면 **THEN** C# export choke point가 typed `DATA_WRITE_REJECTED`로 거부해야 한다.

### Scenario 7 — 검증: 왕복 재적재 + 골든 무변경 + 단방향 소비 (XDET-TC-122, REQ-XGUI-DENOISE-GUARD-1 / GUARD-4)
- **Given** 저장된 `<name>_result.raw` + `.json`이 있고,
- **When** `common.io.load_raw_frame`로 재적재하고 코드 경로·의존 방향·쓰기 대상을 검사하면,
- **Then** (i) 재적재 프레임 픽셀이 저장 직전 uint16 양자화 결과와 `artifact round-trip` 일치하고 hash가 유효하며, (ii) 동일 input/Params/CalibSet 재실행의 `run reproducibility`가 별도 판정되고, (iii) `common/`·`modules/`·`metrics/`·`pipeline/` 하위 파일이 무변경이며, (iv) 탭에 어떤 DSP 산술·스테이지 정렬·CalibSet 합성도 없고(C-09/C-11), (v) core→GUI 역의존과 adapter→Python GUI helper 의존이 없어야 한다.

### Scenario 8 — SAMPLE nps_flat plumbing sanity 스모크 (XDET-TC-123, REQ-XGUI-DENOISE-GUARD-2 / GUARD-3) — 실측 연결(QUARANTINE)
- **Given** 등록 edrogi `nps`(nps_flat) 실 3072² flat 프레임(비정본 `panel_id="SAMPLE-EDROGI-16BIT"`, `sample=true`)과, **합성/선언** (α,σ)를 담은 채워진 NOISE CalibSet(SAMPLE에서 적합한 것이 아님)이 주어지면,
- **When** 그 실 flat에 denoise를 적용하면,
- **Then** 실행은 **유한·비퇴화·오류무발생**의 plumbing sanity로만 성립하고, `compute_nps([frame], params)`가 구조적으로 유효한 NPS(ROI 앙상블)를 산출하며, **SAMPLE 수치에서 (α,σ) 적합·EV 임계·보정 상수·Params 기본값을 도출하지 않아야** 한다(QUARANTINE 이슈 #29, G-5). 실 프레임만 실측이고 (α,σ)는 합성/선언임을 명시한다.

- **Then** 유한·비퇴화·shape/dtype 성립만 보고하고 알고리즘 품질 임계나 `GOLDEN_APPROVED`를 주장하지 않아야 한다.

### Scenario 9 — BM3D/NLM selector와 required Params 완전성 (XDET-TC-124, REQ-XGUI-DENOISE-PARAM-1~3, REQ-XDENOISE-COVERAGE-1/2)

- **Given** populated NOISE CalibSet과 BM3D 및 NLM 각각의 유효 Params가 있을 때,
- **When** selector를 바꾸고 각 방법을 실행하면,
- **Then** 실제 `modules.denoise.required_params(params)` 결과와 입력 폼 key 집합이 동일하고, 각 실행이 `modules.denoise.process`를 정확히 한 번 호출해 direct-golden과 bit-identical XFrame/noise/history/mask를 반환해야 한다.

### Scenario 10 — NOISE builder→소비→조합 (XDET-TC-125, REQ-XGUI-DENOISE-INPUT-2, REQ-XGUI-DENOISE-APPLY-2, REQ-XDENOISE-COVERAGE-3)

- **Given** dose-level series와 denoise를 포함한 canonical 부분수열이 있을 때,
- **When** `fit_noise_model`로 populated NOISE CalibSet을 만들고 denoise 단일 실행과 조합 실행에 사용하면,
- **Then** 동일 CalibSet hash가 builder result, stage input, run manifest에 보존되고 조합은 오케스트레이터 한 번의 호출로 intermediates를 반환해야 한다.

### Scenario 11 — 퇴화 NOISE·누락 Params·UI DSP 거부 (XDET-TC-126, REQ-XGUI-DENOISE-INPUT-3, REQ-XGUI-DENOISE-APPLY-3, REQ-XGUI-DENOISE-GUARD-1~4)

- **Given** 빈/퇴화 NOISE, selector 필수 Params 누락, 또는 UI/adapter의 GAT/BM3D/역변환 재구현 중 하나가 존재할 때,
- **When** 실행을 요청하면,
- **Then** 원본 `DenoiseError` 또는 typed validation error를 보존해 거부하고 기본 NoiseModel·placeholder·silent retry·result commit을 모두 금지해야 한다.

### Scenario 12 — strict 사용자 입력·artifact·증거 (XDET-TC-127, REQ-XGUI-DENOISE-TARGET-1, REQ-XGUI-DENOISE-IO-1/2, REQ-XDENOISE-COVERAGE-4)

- **Given** 등록세트 밖의 strict frame/input-set과 populated NOISE CalibSet이 있을 때,
- **When** BM3D 또는 NLM을 실행하고 저장·재열기·재현성 검증을 수행하면,
- **Then** 실행을 허용하되 `USER_SUPPLIED_UNVERIFIED`를 UI/report/manifest에 보존하고 raw/domain encoding·hash·C-20·양자화 허용오차가 평가 방법서와 일치해야 한다.

### Scenario — BM3D/NLM selector 전수 실행 (XDET-TC-120~127)

- **Given** 각 method의 `required_params`를 만족하는 Params와 populated NOISE CalibSet이 있고,
- **When** BM3D와 NLM을 각각 실행하면,
- **Then** form의 required key 집합이 골든 반환과 동일하고 실제 `modules.denoise.process` 결과가 golden-direct와 동일해야 한다. key/NOISE 결여는 명시 거부되며 strict 사용자 입력은 `USER_SUPPLIED_UNVERIFIED`로 실행돼야 한다.

## Edge Cases

- **빈/퇴화 NOISE CalibSet은 FAIL·폴백 없음 (REQ-XGUI-DENOISE-INPUT-3, SWR-000-5)** — (α,σ) 페이로드가 없는 CalibSet(빈 `make_synthetic_calibset(NOISE)` synth_calibset.py:42-51 포함)이나 퇴화 모델(α≤0, σ<0, 비유한)로 구동하면 `_resolve_noise`(denoise.py:129-148)가 `DenoiseError`로 하드 거부하고, XFrame 기본 `NoiseModel(0,0)`을 포함한 **어떤 기본 노이즈 모델도 대체되지 않아야** 한다 — 탭은 이 오류를 스스로 우회·억제하지 않고 그대로 표면화(음성 대조: 빈 NOISE placeholder 주입 시 실제 예외 확인).
- **method 필수 Params 결여/비-2거듭제곱은 FAIL (REQ-XGUI-DENOISE-PARAM-3)** — 선택 method의 필수 키가 하나라도 결여되거나 BM3D `block`/`max_match`가 2의 거듭제곱이 아니면 `DenoiseError`(denoise.py:117-123/432-440)로 거부되고, 탭은 결여 키/제약을 그대로 표시하며 **기본값을 임의 대입하지 않아야** 한다(HARD 파라미터 외부화).
- **UI에서의 DSP·조합 재구현은 FAIL (REQ-XGUI-DENOISE-APPLY-3, C-09/C-11)** — 탭/어댑터가 GAT/BM3D/역변환을 스스로 계산하거나, 스테이지를 스스로 정렬·조합하거나, 결여 NOISE CalibSet을 합성(빈 placeholder 대입)하면 인수 실패 — 모든 DSP는 골든, 조합/순서는 오케스트레이터.
- **골든 신설·사설 헬퍼 호출은 FAIL (REQ-XGUI-DENOISE-GUARD-4)** — (α,σ)를 얻기 위해 골든에 새 공개 생산자를 신설하거나 `_gat_forward`/`_gat_inverse`/`_bm3d` 사설 헬퍼를 호출하거나 `fit_noise_model` 회귀를 UI에서 재구현하면 인수 실패 — 정본 산출은 골든 `fit_noise_model`(호출만), 선언-스칼라는 공개 `CalibSet`+공개 키 상수 패키징만.
- **`data/` 쓰기는 FAIL (REQ-XGUI-DENOISE-IO-2, C-20)** — 저장 경로가 `<project_root>/data` 하위로 해석되면 `DataWriteRejectedError`로 거부돼야 한다(음성 대조: `data/` 하위 경로 지정 시 실제 거부 확인) — 골든 fixture/CalibSet 보호.
- **비-균일/소형 입력 NPS는 명시 오류 (REQ-XGUI-DENOISE-VIEW-3, D2)** — 중앙영역이 ROI(256)보다 작은 입력은 `compute_nps`가 `MetricReadError`(nps.py:68-72)로 거부하고 탭이 그대로 표면화한다. NPS/NNPS 뷰는 **균일 flat**에 대해서만 의미가 있으며 구조/엣지 영상에는 적용하지 않는다.
- **점근 역 Anscombe 부재 (SWR-703)** — 탭은 정확 무편향 역변환(SWR-703)만 소비한다. 점근 역((f/2)² 계열)은 골든에도 GUI에도 존재하지 않아야 한다(CLAUDE.md 금지; 음성 대조: 코드에 해당 경로 부재 확인, denoise.py:194).
- **SAMPLE 수치 오용은 FAIL (QUARANTINE, 이슈 #29)** — 등록 SAMPLE(에드로지) 구동 결과를 정본 수치/EV 임계 도출·튜닝·적합에 사용하면 인수 실패 — sanity(유한·비퇴화·구조)만 허용, 정본 수치 검증은 정본 지침세트(#33) 도착 후 별건.

## Definition of Done (체크리스트)

- [ ] 열기·NOISE CalibSet 조달·골든 `required_params(params)` 기반 동적 Params 폼 (XDET-TC-120, INPUT/PARAM)
- [ ] 단일·조합 apply는 generic `IXdetEngine.RunPipeline(PipelineRunRequest)` 사용, Python GUI helper 호출 0, 채워진 NOISE CalibSet 주입 (XDET-TC-121, APPLY/VIEW)
- [ ] NPS/NNPS/SNR은 `IXdetEngine` metric 전용 DTO로 골든에 위임하고 flat DC/평균 보존 표시 (XDET-TC-122, VIEW-3)
- [ ] `_result.raw` + `xdet.frame-artifact/1.0` sidecar/run manifest/hash, C-20 typed 거부, artifact round-trip과 run reproducibility 분리 (XDET-TC-122, IO/GUARD)
- [ ] SAMPLE `nps` flat plumbing sanity는 유한·비퇴화만 단언하고 SAMPLE 수치 golden/EV/튜닝 도출 없음 (XDET-TC-123, GUARD-2/3)
- [ ] 빈/퇴화 NOISE CalibSet → `DenoiseError`, 기본 노이즈 모델 무대체(음성 대조) (INPUT-3, SWR-000-5)
- [ ] denoiser-우회 bias-vs-λ 곡선·골든 사설 헬퍼 호출·`fit_noise_model` UI 재구현 부재 (GUARD-4, 「확정 결정」 1)
- [ ] 신규 파이프라인 스테이지·CalibKind 신설 없음(denoise/NOISE는 SPEC-DENOISE-001 기존) — GUI 탭 additive만
- [ ] `uv run pytest` 무회귀 green + `uv run lint-imports` green·불변

## 판정 원칙 (측정=판정 분리)

- **골든이 산출, GUI는 표시.** 모든 DSP(GAT/BM3D/NLM/exact-inverse-LUT)와 지표(NPS/NNPS/SNR)는 골든 엔진이 산출하고 탭은 표시·조달·요청만 한다(C-09). (α,σ) 진단은 골든이 **기록**한 값(`XFrame.noise`/`HistoryEntry.extra`)의 표시이지 UI 계산이 아니다.
- **조합/순서는 오케스트레이터, 캘리브레이션 admission은 게이트.** 스테이지 정렬·조합은 `PipelineDefinition`(orchestrator), 부재/불일치 CalibSet 거부는 `_calibration_gate`이며, 탭·C# 심은 이를 판정하지 않고 결과만 표시·전파한다(C-11, CONTRACT-6).
- **(α,σ) 생산자 단일성.** (α,σ)의 유일 정본 산출은 골든 `fit_noise_model`(≥2 선량)이며, 선언-스칼라 CalibSet은 공개 스키마 API 패키징(신호처리 0)에 한한다 — 새 골든 생산자 신설·사설 헬퍼 호출 금지(D1 확정).
- **SAMPLE 실측은 비정본(QUARANTINE).** denoise 인수의 load-bearing 기준은 합성 검증 경로의 **명시 거부**·**왕복 무결성**·**골든 무변경**·**무회귀**이지 SAMPLE 절대 수치가 아니다. SAMPLE 실 flat 구동은 plumbing sanity(유한·비퇴화·구조)만 단언한다.
- **TC 추적:** GUI-E2E `XDET-TC-120~127`과 core 알고리즘 TC는 서로 다른 증거 계층으로 관리한다.

## 요구사항-TC 추적

| 요구사항 | 중앙 TC |
|---|---|
| `REQ-XGUI-DENOISE-TARGET-{1}` | 120~127 |
| `REQ-XGUI-DENOISE-INPUT-{1..3}` | 120, 125, 126 |
| `REQ-XGUI-DENOISE-PARAM-{1..3}` | 120, 124, 126 |
| `REQ-XGUI-DENOISE-APPLY-{1..3}` | 121, 125, 126 |
| `REQ-XGUI-DENOISE-VIEW-{1..3}` | 121, 122, 124 |
| `REQ-XGUI-DENOISE-IO-{1..2}` | 122, 127 |
| `REQ-XGUI-DENOISE-GUARD-{1..4}` | 122, 123, 126, 127 |
| `REQ-XDENOISE-COVERAGE-{1..4}` | 124~127 |

각 범위는 모든 개별 ID로 전개한다. 필수 증거 필드는 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따르며 누락·중복·orphan은 인수 실패다.

## v0.5.1 operation closure acceptance

- **Given** method별 Params, NOISE CalibSet, single frame 또는 validation stack이 있고,
- **When** selector가 `modules.denoise.required_params`를 조회하고 사용자가 `modules.denoise.process`, `metrics.noise_model.fit_noise_model`, `metrics.nps.compute_nps`, `metrics.ndt.compute_snr` action을 실행하면,
- **Then** runtime required-key set과 입력 control이 일치하고 각 qualified EntryPoint의 typed result/error와 golden-direct fidelity가 XDET-TC-120~127에 남아야 한다. BM3D/NLM별 누락 Params는 silent default 없이 거부해야 한다.
