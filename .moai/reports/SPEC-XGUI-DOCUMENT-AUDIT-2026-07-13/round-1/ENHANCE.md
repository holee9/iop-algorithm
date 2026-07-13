# SPEC 감사 리포트: SPEC-XGUI-ENHANCE
라운드: 1/5
판정: **CONDITIONAL PASS** (골든 대조 무결점 · 문서/완결성 결함 5건 — 지어낸 Params·수식·제약위반 0건)
M1 고지: 저작자 추론 컨텍스트는 M1 Context Isolation에 따라 무시하고 spec.md + 골든 소스만 대조검증함.

## 대조검증 요약 (AUTHORITATIVE 소스 = modules/mse.py, modules/window.py, pipeline/orchestrator.py, foundation.md, io.py, io_panel.py, export.py, ingest_edrogi.py)

**골든 사실 대조 — 전건 VERIFIED (지어내기 0):**
- `mse.required_params`는 함수(mse.py:97), `_REQUIRED_COMMON` 6키 순서·이름 정확(mse.py:79-86): `mse_levels, mse_gamma, mse_noise_beta, mse_drc_gamma, mse_norm_plow, mse_norm_phigh` ✓
- `_required_keys`: power_law→`mse_power`, soft_clip→`mse_softclip_gain, mse_softclip_knee`(mse.py:89-94) ✓ / 선택 `mse_drc_bmid, mse_drc_low_levels`(mse.py:69-70) ✓
- `_resolve_noise` α<=0/퇴화 → `MseError`(mse.py:134-150), 기본값 대체 금지 ✓ / `_DOMAIN_MAX=1.0`(mse.py:115) SATURATION 핀(mse.py:309-314) ✓
- mse 진단 11키(`gamma_mean,drc_gamma,drc_low_levels,drc_compression_rate,b_mid,norm_low,norm_high` + `method,noise_beta,resolved_alpha,resolved_sigma`) = 골든 diagnostics(mse.py:316-324) + extra(mse.py:361-367) 정확 ✓
- `window.REQUIRED_PARAMS` 5키 순서·이름 정확(window.py:64-70): `gsdf_lum_min, gsdf_lum_max, window_pvalue_levels, window_collim_rel_threshold, window_direct_fence_k` ✓
- VOI at-least-one(`window_voi_override`|`window_voi_presets`+`window_region_code`|`window_voi_default`) 결여→`WindowError`(window.py:211-215) ✓ / `gsdf_jnd_grid_size` 선택 ✓
- window 진단 8키(`voi_low,voi_high,override,voi_source,anatomy_fraction` + `gsdf_max_dev,gsdf_lum_min,gsdf_lum_max`) = diagnostics(window.py:292-299) + extra(window.py:339-344) 정확 ✓
- `build_gsdf_lut`(window.py:133) → (jnd_index, display, max_dev) 반환, GSDF 다항식(window.py:79-89) ✓ / window 출력 display-normalized(window.py:168/283), SATURATION→`lut_display[-1]`(window.py:289-290) ✓
- `CANONICAL_ORDER` tail `denoise→mse→window→post`(orchestrator.py:67/75/76/77), post 등록모듈 없음 ✓ / `_KIND_BY_STAGE["denoise"]="noise"`(orchestrator.py:157) → denoise가 (α,σ) 공급자 주장 정합 ✓
- `calib_kind_for_stage` 공개, mse/window 미등록→`CalibKind.OTHER`(orchestrator.py:165-175) ✓ / `load_raw_frame`(io.py:35) 존재·`save_raw_frame` 부재 → 신설 주장 정합 ✓
- `make_synthetic_calibset`(synth_calibset.py:24) ✓ / `guard_output_path`(io_panel.py:27) ✓ / `denoise.process`(denoise.py:616) ✓
- foundation.md 존재, G-1~G-9 정의(foundation.md:28-36), §6 역양자화 미해결→그룹5 확정 명시(foundation.md:180) → REQ-XENH-DATA-2의 "foundation §6 그룹5 확정" 주장 정합 ✓
- 제약 인코딩(C-09/C-11/C-20/SWR-602/SWR-000-2/SWR-000-5) 전부 정확, 그룹 고유 뷰어 특성([0,1] 표시도메인 렌더·GSDF 곡선·SATURATION 오버레이·도메인정합 diff) 누락 없음 ✓

**MP 결과:** MP-1(REQ 넘버링, 그룹내 순차·무결) PASS · MP-2(EARS 라벨-내용 정합) PASS · MP-3(frontmatter, XSEAM-002 미러 충실) PASS · MP-4(언어중립) N/A(단일 프로젝트 SPEC).

## 우선순위 결함 목록

### D1 (MAJOR) — plan.md·acceptance.md 링크 존재하나 파일 부재 → 인수기준/TC ID 미정의
- spec.md:24 가 `[plan.md](./plan.md)` · `[acceptance.md](./acceptance.md)` 를 링크하나 두 파일 모두 부재(디렉터리에 spec.md만 존재).
- 결정필요 #5(spec.md:103)가 "구체 TC ID 확정"을 **본 그룹 acceptance.md에서** 하도록 이연 → 현재 SPEC에 구체 인수기준·XDET-TC ID가 0건. DoD(spec.md:23)의 (a)~(f)가 검증가능 TC로 바인딩되지 않음(검증불가 약속).
- 조치: 라운드 진행과 병행해 acceptance.md(XDET-TC-096+ 블록 실배정)·plan.md를 산출하거나, 미산출 시 spec.md:24 링크를 "예정"으로 표기. XSEAM-002는 acceptance.md+plan.md 동반(미러 대상과 불일치).

### D2 (MINOR) — HISTORY EARS 개수 오기 (19 vs 20)
- spec.md:28 "6개 요구 그룹 ... EARS **20개**". 실제 카운트 = INPUT 3 + PARAM 3 + VIEW 5 + RUN 4 + DATA 3 + GUARD 1 = **19개**.
- 조치: "20개"→"19개" 교정, 또는 누락 의도된 20번째 요구가 있으면 추가.

### D3 (MINOR) — REQ-XENH-VIEW-5 "동일 Params로 호출" 시그니처 부정합
- spec.md:65 는 `window.build_gsdf_lut`을 "동일 **Params**로 호출"이라 기술하나, 골든 시그니처는 `build_gsdf_lut(pvalue_levels, lum_min, lum_max, grid_size)`(window.py:133-138) — **4개 위치 스칼라**이며 `Params` 인자 오버로드가 없다(window.process가 params에서 pmax/lum_min/lum_max/grid_size를 추출해 호출, window.py:310-315).
- 조치: "동일 Params로 호출" → "window 실행과 동일 Params 값(pvalue_levels/lum_min/lum_max/gsdf_jnd_grid_size)을 추출해 `build_gsdf_lut(...)` 호출"로 정밀화. 구현자가 없는 Params-오버로드를 찾는 오해 방지.

### D4 (MINOR) — guard_output_path 파일:라인 인용이 정의부 아닌 사용부를 가리킴
- spec.md:21 "`apps.gui.io_panel.guard_output_path`(**export.py:32/56**, C-20 choke point)". 모듈 경로는 정확하나 정의는 io_panel.py:27이고 export.py:32/56은 import·호출부다(정의부 아님). foundation.md G-4도 export.py:3-7/56로 유사 인용.
- 조치: "(io_panel.py:27 정의; export.py:56 호출)"로 인용 정정.

### D5 (MINOR) — GUARD-1 상속 원칙 범위 불일치 (G-1~G-8 vs 상속선언 G-1~G-9)
- spec.md:22 상속선언은 G-1~G-9(9개, G-9=탭=그룹별) 열거. spec.md:82 REQ-XENH-GUARD-1 종결부는 "foundation §1 **G-1~G-8** 위반"으로 G-9 제외.
- 의도적(G-9는 거부대상 위반이 아닌 구조원칙)일 수 있으나 교차참조 범위가 상충. 조치: "G-1~G-8(구조원칙 G-9 제외)"로 명시하거나 근거 1줄 추가.

## Chain-of-Verification (2차 재검)
- mse/window Params 키·순서·라인 재확인(1차 통과 재검): _REQUIRED_COMMON 6키, _required_keys 분기, REQUIRED_PARAMS 5키, VOI 3소스, 진단 dict 전키 — 재검 결과 지어낸 키/오기 라인 **추가 결함 0**.
- 수식 재검: mse power-law `gamma*sign(c)*|c|^p`(mse.py:172)·noise-gate `c^2/(c^2+beta*sigma^2)`(mse.py:189-192)·정규화 clip(mse.py:307)·GSDF `display=(lum-lum_min)/(lum_max-lum_min)`(window.py:168) — SPEC은 수식을 재기술하지 않고 소스 위임(재구현 없음, 골든FROZEN 준수). 틀린 수식 **0**.
- 제약 재검: REQ-XENH-DATA-2 `*65535` 스케일은 [0,1]→16bit용으로 ingest 선례(raw-DN, `*65535` 없음)와 스케일 의미가 다르나 **"가정 기본값"+결정필요#1로 정직 라벨** → 지어낸 정본 아님(QUARANTINE/정직표기 준수). 재검 결과 은닉된 제약위반 **0**.
- 그룹간 불일치 재검: "입력=raw-DN vs 출력=[0,1]" 도메인 분리가 뷰어(VIEW-1)·저장(DATA-1/2)·진단(VIEW-2)·가드(GUARD-1 iii)에 일관 → 그룹내 모순 **0**. 유일 불일치는 D2(카운트)·D5(G범위) 문서결함.

## 권고
1. **D1**: acceptance.md(XDET-TC-096+ 실배정)·plan.md 산출 — 미러 대상 XSEAM-002와 동반 3파일 구성 맞춤. 인수기준 바인딩 전까지 DoD는 검증불가.
2. **D2~D5**: 문서 교정(카운트 19, VIEW-5 시그니처 정밀화, guard 인용 정정, GUARD-1 G범위 명시). 골든 재대조 불필요 — 모두 텍스트 편집.
3. 골든 계약 사실(Params 키·진단·에러·순서·도메인)은 전건 정확하므로 **run 착수를 차단하는 골든 정합 결함 없음**. D1(인수기준 부재)만 해소되면 PASS.
