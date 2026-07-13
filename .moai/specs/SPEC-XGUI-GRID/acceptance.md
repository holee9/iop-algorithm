---
id: SPEC-XGUI-GRID
version: 0.5.1
status: planned
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-12
updated: 2026-07-13
author: drake.lee
issue_number: 58
labels: [xgui, acceptance, grid, virtual-grid, wpf]
---

# SPEC-XGUI-GRID 인수 기준 (Acceptance) — Grid/Virtual-Grid 검증 탭 (그룹 6)

> 본 인수기준의 모든 EARS ID·중앙 TC·필수 증거 연결은 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따른다. `baseline-control.md`의 G0와 사용자 승인 전에는 이 체크리스트를 구현 완료 증거로 사용할 수 없으며 모든 TC는 `PLANNED` 상태를 유지한다.

> **구현 대상:** `apps/xdet-console/` C# WPF 앱. `apps/gui/`와 Python 테스트는 계약·검증 선례이며 구현 대상이 아니다.
[spec.md](./spec.md)의 그룹 6 검증 탭에 대한 인수 기준이다. 핵심 E2E 흐름은 **열기(상주 폴더 브라우저) → build(CalibSet·Params 조립) → apply(심/오케스트레이터 경유 구동) → 저장(`<name>_result.raw` + `.json`) → 검증(재적재 라운드트립·엔진 진단)** 이다. 모든 시나리오는 [SPEC-XGUI-MASTER/foundation.md](../SPEC-XGUI-MASTER/foundation.md)의 불변 HARD 제약과 spec.md의 EARS 요구를 상속한다.

## 인수 원칙 (Acceptance Principles)

- **엔진 산출만(C-09/G-2).** 모든 표시·저장 수치는 골든 엔진(`modules/grid.py`·`modules/virtual_grid.py`, `pipeline.orchestrator.run_pipeline`, 또는 심 미러 `IXdetEngine`)의 결과다. 탭·어댑터는 피크 탐색·notch·SKS 추정·차감을 스스로 계산하지 않는다.
- **골든 FROZEN(G-1).** 인수 시나리오는 골든을 **호출만** 하며, 어떤 시나리오도 `modules/`·`pipeline/`·`common/`·`metrics/` 소스를 수정하지 않는다. 인용된 계약(process 시그니처·Params 키·CalibKind·진단 필드)은 동결 소스 `file:line`으로 대조검증됐다(spec.md 「골든 대조 근거표」).
- **QUARANTINE(G-5).** 등록 실측(SAMPLE 에드로지) 구동은 **sanity(유한·비퇴화·구조 성립)** 확인일 뿐이며, 어떤 수치 golden·EV 임계·커널 적합에도 쓰지 않는다. 그룹 6은 격자선·산란 정본 부재로 **알고리즘 고유 검증은 합성 팬텀 전용**이며 정본 수치 검증은 이슈 #33 도착 후 별건이다.
- **저장 포맷(foundation §3).** 저장은 `xdet.frame-artifact/1.0` raw/sidecar + 선택 `uint8` mask raw + `xdet.run-manifest/1.0`이다. Pixel/mask bit-exact round-trip과 hash를 검증하며 C# export choke point가 `data/` 하위를 거부한다(C-20).
- **실행 증거(no vacuous pass).** 각 Then은 "예외 미발생"이 아니라 **실제 실행 증거**(출력 shape/dtype, 유한·비퇴화 통계, 특정 이력 진단 필드 값, 재적재 라운드트립 동일성)를 단언한다.
- **실행 환경.** 모든 명령은 `uv run`(예: `uv run pytest`, `uv run lint-imports`); 한글 출력은 `PYTHONIOENCODING=utf-8`.

## E2E 시나리오 (Given-When-Then)

### 시나리오 1 — grid 스테이지 E2E: 합성 격자선 팬텀 (REQ-INPUT-1/2, BUILD-1, APPLY-1, VIEW-1, EXPORT-1) — 합성 전용

근거: XDET-TC-015/016 (격자 밀도 3부류, 30~85 lines/cm) 판정 엔진. 실측 격자선 팬텀 부재 → 합성/#33.

- **Given** 격자 밀도 3부류 중 하나(예: f_grid < f_N)의 **합성 격자선 팬텀** 프레임과 진입 게이트용 `make_synthetic_calibset(shape, CalibKind.OTHER)`(빈 payload로 충분) placeholder, 그리고 8개 REQUIRED grid Params(`grid_pitch_mm`, `grid_search_band_lo_lpmm`, `grid_peak_significance_db`, `grid_direction_margin_db`, `grid_harmonic_max_order`, `grid_notch_fwhm_mult`, `grid_moire_lowfreq_cutoff_lpmm`, `grid_moire_atten_cap`)가 조립되어 있다.
- **When** 사용자가 팬텀 프레임을 열고 WPF가 stages=["grid"]인 `PipelineRunRequest`를 `IXdetEngine.RunPipeline`에 전달한다.
- **Then** 탭은 (a) 축별 관측 PSD 스펙트럼과 검출 피크 마커(`peak_freq_lpmm`)·1D notch 전달함수 `|H(f)|`(`notch_gain_1d`)·방향 지시자를 표시하고, (b) 이력 진단 `grid_detected="true"`·`peak_freq_lpmm`·`notch_bandwidth_lpmm`·`direction_energy_ratio_db`가 부착되며(grid.py:428/468-472), (c) 출력 프레임은 입력과 동일 shape·dtype(raw-DN 유지)이고 유한·비퇴화이며, 모든 수치는 엔진 산출이다(C-09). 저장 시 `<name>_grid_result.raw` + `.json`이 사용자 지정 폴더에 기록된다.

### 시나리오 2 — virtual_grid 스테이지 E2E: populated SCATTER 커널 (REQ-INPUT-3, BUILD-1, APPLY-1, VIEW-3, EXPORT-1) — 합성 전용

근거: XDET-TC-017 (GDS-scatter 팬텀, SKS 산란 추정·차감). 실측 산란 세트 부재 → 합성/#33.

- **Given** grid-less **합성 산란 팬텀**(veiling glare 주입) 프레임과, `metrics.scatter_kernel.build_scatter_kernel(thickness_proxy_cm, kv, *, panel_id, resolution, valid_from, valid_until, spr_per_cm, spr_max, sigma_narrow_px, sigma_wide_px, wide_fraction, thickness_sigma_gain_per_cm, kv_sigma_ref)`(scatter_kernel.py:144)로 생성한 **populated** `CalibSet(SCATTER)`(dual-Gaussian `scatter_amp`[2]/`scatter_sigma`[2], SPR<1), 그리고 5개 REQUIRED virtual_grid Params(`vgrid_sks_iterations`, `vgrid_downsample_levels`, `vgrid_grid_ratio_w`, `vgrid_lowsignal_threshold`, `vgrid_lowsignal_softness`)가 조립되어 있다.
- **When** 사용자가 팬텀 프레임을 열고 WPF가 stages=["virtual_grid"]인 `PipelineRunRequest`를 `IXdetEngine.RunPipeline`에 전달한다.
- **Then** 탭은 (a) 전-해상도 SKS 산란 추정 `S_hat` 공간 산란맵 + 차감 전/후 이미지를 표시하고, (b) 스칼라 진단 `scatter_fraction`∈(0,1)·`lowsignal_attenuated_fraction`·`nonneg_clamp_count`(virtual_grid.py:295-297/349-351)를 표시하며, (c) 출력은 **전 픽셀 비음수**(clamp 적용, 음수 X선 신호 불가)·유한이고 raw-DN shape/dtype를 유지하며, (d) ⚠P 특허 플래그 배너 `sks_patent_flag="US11911202-clearance-deferred"`와 `kernel_provenance`(= `calibset_id`)가 표시·보존된다(virtual_grid.py:354-355). 저장 시 `<name>_vgrid_result.raw` + `.json`이 기록된다.

### 시나리오 3 — 등록 edrogi 실측 PLUMBING sanity (REQ-INPUT-1, APPLY-1, GUARD-2/3) — 실측 sanity만 (QUARANTINE)

그룹 6에는 격자선·산란 정본 세트가 없으므로, 이 시나리오는 **알고리즘 수치 검증이 아니라 열기→적용→저장 배관(plumbing)의 실측 구동 sanity**다. 등록 edrogi 실행가능 프레임(예: `nps_flat`·`acrylic_step`, 실측 3072² 16-bit)을 실제 골든 스테이지에 통과시켜 배관이 성립함만 확인한다. **비권위(non-authoritative), 수치 golden/튜닝 금지.**

- **Given** `scripts/ingest_edrogi.py`가 인식하는 등록 SAMPLE 프레임(`_CATEGORY_BY_FOLDER` = `GHOST`/`nps`/`아크릴`; panel_id=`SAMPLE-EDROGI-16BIT`) 중 하나. 이 세트에는 물리 안티스캐터 그리드가 없다.
- **When** 사용자가 상주 폴더 브라우저로 그 실측 프레임을 열고 `grid` 스테이지를 적용한다(진입 게이트 `CalibSet(OTHER)` placeholder + 8 Params).
- **Then** (a) 출력은 유한·비퇴화이고 입력과 동일 shape/dtype(raw-DN)이며, (b) 이 프레임엔 주기적 격자 변조가 없으므로 grid이 유의 피크를 검출하지 못해 **수치 동일 통과**(`grid_detected="false"`, `grid_undetected="true"`, grid.py:437-438)로 픽셀 무변경이 표시되고, (c) 저장→재적재가 라운드트립 일치한다(시나리오 7). 탭은 이 구동이 **sanity 배관 확인**이며 정본 수치 검증이 아님을 명시하고(그룹 6 전 스테이지 합성 전용/#33 라벨), 어떤 EV 임계·커널 적합에도 이 수치를 쓰지 않는다.

### 시나리오 4 — 하류 부분수열 조합 + 검증 모드 중간 프레임 (REQ-APPLY-2/3, VIEW-1/3) — 합성 전용

- **Given** 정렬된 부분수열 프리셋(예: `("grid","denoise")` 또는 `("virtual_grid","denoise","mse")`)과 각 스테이지의 구별 입력(grid=OTHER placeholder+8 Params; virtual_grid=populated SCATTER+5 Params; 하류 denoise/mse는 각자 계약 CalibSet). 입력 `XFrame.validation_mode=True`.
- **When** 사용자가 그 부분수열을 **단일 심 파이프라인 실행**으로 요청한다.
- **Then** (a) 스테이지 순서·조합은 `PipelineDefinition`(오케스트레이터)이 강제하며(C# 측 아님, SWR-000-2), (b) 실행된 모든 스테이지의 중간 프레임이 그 **단일 패스**에서 `XFrame.intermediates[i]`로 반환되어(SPEC-XSEAM-002 REQ-XSEAM-COMPOSE-3 미러) 탭이 추가 실행 없이 grid/virtual_grid 각 전/후를 스크럽하고, (c) 조합 출력·각 중간 프레임이 유한·비퇴화다. grid+virtual_grid 동시 결합은 **저비율 물리 그리드 예외**로 라벨링된다(통상 취득은 배타, orchestrator.py:49-56 정당 결합 근거).

### 시나리오 5 — 빈 payload SCATTER 하드 실패 (음성 대조, REQ-INPUT-3, BUILD-2, GUARD-1) — 정상 거부

`build_scatter_kernel`로 채우지 않은 **빈 payload** SCATTER CalibSet의 하드 실패가 **버그가 아닌 정상 거부**임을 표면화한다(SWR-000-5).

- **Given** `make_synthetic_calibset(shape, CalibKind.SCATTER)`(빈 payload `data={}`)와 5 REQUIRED Params.
- **When** 사용자가 `virtual_grid` 스테이지를 적용한다.
- **Then** 진입 게이트(kind==scatter)는 통과하나 `_resolve_kernel`이 `scatter_amp`/`scatter_sigma` 부재로 **`VirtualGridError`**를 던지고(virtual_grid.py:111-151), 탭은 이를 "기본 커널 대체 금지에 의한 정상 거부"로 표면화하며 populated 커널(`build_scatter_kernel` 또는 fixture) 공급을 사전 경고로 안내한다. 탭은 결여·퇴화 커널을 임의 계수로 **채우지 않는다**.

### 시나리오 6 — C-20 내보내기 가드 (REQ-EXPORT-2, GUARD, 항상 실행) — 실측 불요

- **Given** 저장 대상 경로가 `<project_root>/data` 하위로 해석되는 결과 프레임.
- **When** 사용자가 저장을 시도한다.
- **Then** C# export choke point가 실행 전에 typed validation error로 거부하고 사용자 지정 폴더만 허용한다.

### 시나리오 7 — 저장→재적재 라운드트립 (REQ-EXPORT-1) — 합성/실측 공통

- **Given** 시나리오 1~4의 임의 raw-DN 결과 프레임 `result`.
- **When** 사용자가 사용자 지정 폴더에 `<name>_result.raw` + `.json`으로 저장한 뒤 `load_raw_frame`으로 재적재한다.
- **Then** (a) sidecar는 `xdet.frame-artifact/1.0` 전체 필드를 포함하고, (b) 재적재 pixel/mask가 확정 양자화/bitfield와 bit-exact이며, (c) run manifest의 input/calib/params/output hash가 산출물과 일치한다.

### 시나리오 8 — grid 명목 주파수 주입 금지 + 미검출/moire 캡 (음성 대조, REQ-BUILD-2, VIEW-2) — 합성 전용

- **Given** 취득 메타 `grid_meta_mounted`/`grid_meta_nominal_lpmm`(선택 키, 비교 경고 전용)와 합성 격자선 팬텀.
- **When** 사용자가 grid을 적용한다.
- **Then** (a) 피크 탐색은 **관측 스펙트럼만** 사용하며 명목 주파수는 탐색 입력이 아니다(SWR-1001; 메타는 검출-메타 불일치 경고 표시 전용, grid.py:389-406), (b) 저주파 접힘으로 감쇠가 캡되면 `moire_atten_capped="true"`(grid.py:472) + 그리드 교체 권고 경고가 표시되고, (c) 유의 피크 미검출 시 `grid_detected="false"`로 수치 동일 통과가 표시된다. 탭·어댑터가 명목 주파수를 탐색에 주입하려 하면 거부된다.

### Scenario — physical/virtual grid 공개 연산 전수 실행 (XDET-TC-136~143)

- **Given** physical grid frame/Params와 virtual-grid frame/populated SCATTER CalibSet, 두 scatter builder source가 있고,
- **When** analyze/process/estimate와 parametric/sample-fit build를 실행하면,
- **Then** 실제 7개 공개 EntryPoint가 engine에서 호출되고 GridAnalysis/notch series/scatter estimate/XFrame/CalibSet이 golden-direct와 동일해야 한다. UI FFT·notch·scatter·fit 계산은 0건이어야 한다.

## Edge Cases

- **포화 "복원" 없음(SWR-602).** virtual_grid의 단조 하향 산란 차감은 포화 픽셀의 클리핑 정보를 재구성하지 않는다. 탭은 "복원" UI를 제공하지 않으며, 마스크(DEFECT/SATURATION/SATURATION_BAND/INTERPOLATION) 사전충전은 추정 오염 방지용일 뿐이다(virtual_grid.py:35-40).
- **비음수 클램프 경계.** 산란 차감이 음수를 유발하는 저신호 영역은 0으로 클램프되고 `nonneg_clamp_count`로 계수된다; 저신호 tanh 감쇠로 노이즈 부스트를 억제한다.
- **미검출 통과 불변성.** grid 미검출 시 출력은 입력과 **비트/값 동일**(픽셀 무변경)이어야 하며, notch가 전혀 적용되지 않는다.
- **⚠P 플래그 지속성.** virtual_grid 결과의 표시·저장·조합 어느 경로에서도 `sks_patent_flag`·`kernel_provenance`가 소실되지 않아야 한다(릴리스 게이트 추적성). SW는 특허 판단을 하지 않는다.
- **빈 SCATTER = 정상 거부.** 시나리오 5의 `VirtualGridError`는 실패 UI가 아니라 계약 위반의 정상 표면화다.
- **data/ 가드 우회 불가.** 어떤 저장 경로도 C# export choke point를 우회할 수 없다.

## 품질 게이트 / Definition of Done

- [ ] **DoD-1 (grid E2E)** — 시나리오 1: 합성 격자선 팬텀을 열기→OTHER placeholder+8 Params build→apply→PSD/피크/notch/방향/미검출 표시→저장. (REQ-INPUT-1/2, BUILD-1, APPLY-1, VIEW-1/2, EXPORT-1)
- [ ] **DoD-2 (virtual_grid E2E)** — 시나리오 2: 합성 산란 팬텀을 열기→populated SCATTER 커널+5 Params build→apply→S_hat 산란맵/scatter_fraction/비음수/⚠P 배너 표시→저장. (REQ-INPUT-3, BUILD-1, APPLY-1, VIEW-3, EXPORT-1, GUARD-4)
- [ ] **DoD-3 (실측 sanity)** — 시나리오 3: 등록 edrogi 실측 프레임 열기→grid 적용→유한·비퇴화·미검출 통과 구조 sanity→저장(QUARANTINE, 비권위). (REQ-INPUT-1, APPLY-1, GUARD-2/3)
- [ ] **DoD-4 (조합·검증 모드)** — 시나리오 4: 정렬 부분수열 단일 심 실행 + `intermediates` 전/후 스크럽. (REQ-APPLY-2/3)
- [ ] **DoD-5 (음성 대조)** — 시나리오 5·8: 빈 SCATTER `VirtualGridError` 정상 거부, 명목 주파수 주입 금지. (REQ-BUILD-2, GUARD-1)
- [ ] **DoD-6 (내보내기 가드·라운드트립)** — 시나리오 6·7: `data/` 하위 typed 거부, frame/mask artifact 재적재 bit-exact, run manifest hash 일치. (REQ-EXPORT-1/2)
- [ ] **DoD-7 (골든 무변경 게이트)** — 인수 실행 전후 `modules/grid.py`·`modules/virtual_grid.py`·`pipeline/`·`common/`·`metrics/` diff 없음(호출만); `uv run lint-imports` 0 위반; `uv run pytest` 그룹 6 관련 케이스 통과.
- [ ] **DoD-8 (데이터 가용성 라벨)** — 그룹 6 전 스테이지가 UI에서 **합성 전용/#33 대기**로 정확히 라벨되고, SAMPLE 세트에 격자선·산란 정본 부재가 명시된다(그룹 1 SAMPLE sanity 실행가능과 대비). (REQ-GUARD-3)

## TC 할당 (확정 — SPEC-XGUI-MASTER 중앙 레지스트리)

XGUI 가족(이슈 #58)의 GUI-E2E 탭 테스트 TC 맵은 SPEC-XGUI-ENHANCE 결정 #5가 제안한 **중앙 스킴**(그룹당 8슬롯, 096부터: g1 Calib 096–103 · g2 Lag 104–111 · g3 Line/Sat/Geo 112–119 · g4 Denoise 120–127 · g5 Enhancement 128–135 · **g6 Grid/VGrid 136–143** · g7 NDT 144–151 · g8 Metrics 152–159)을 따른다. 최종 비준은 SPEC-XGUI-MASTER foundation(중앙 레지스터) 몫이며, MASTER가 `docs/XDET_TestSpec_v1.0.md`와 대조해야 한다. 이 GUI-전용 블록은 골든 Gen1 TC(000~021)와 목적이 다르며 비충돌이다.

| 제안 TC (g6 = 136–143) | 시나리오 | 성격 |
|---|---|---|
| XDET-TC-136 | 시나리오 1 grid E2E | 합성 전용 |
| XDET-TC-137 | 시나리오 2 virtual_grid E2E | 합성 전용 |
| XDET-TC-138 | 시나리오 3 실측 plumbing sanity | 실측 sanity(QUARANTINE) |
| XDET-TC-139 | 시나리오 4 조합·검증 모드 | 합성 전용 |
| XDET-TC-140 | 시나리오 5·8 음성 대조 | 합성 전용 |
| XDET-TC-141 | 시나리오 6·7 내보내기 가드·라운드트립 | 항상 실행 |
| XDET-TC-142 | sample-fit scatter kernel과 golden-direct fidelity | 합성 또는 strict 사용자 입력 |
| XDET-TC-143 | 조합·typed 오류·availability/evidence/export | 항상 실행 |

- 알고리즘 자체(격자 검출·notch·SKS 수렴)의 수치 검증은 Gen1 **XDET-TC-015/016**(grid 밀도 3부류)·**XDET-TC-017**(virtual_grid CNR)이 담당하며, 위 GUI-E2E 블록은 그 위의 **열기→apply→저장 E2E 배관**을 검증한다(중복 아님). 골든 TC 참조는 유효하게 유지되고 136–143은 GUI-전용 관심사만 담는다.
- GUI-E2E 테스트 소스는 Gen1 캡스톤 rglob 충돌 방지를 위해 `000`~`021` 문자열을 포함하지 않는다(VIEWER 선례).

## 요구사항-TC 추적

| 요구사항 | 중앙 TC |
|---|---|
| `REQ-XGUI-GRID-TARGET-1` | 136~143 |
| `REQ-XGUI-GRID-INPUT-{1..3}` | 136, 138, 142 |
| `REQ-XGUI-GRID-BUILD-{1..2}` | 140, 141 |
| `REQ-XGUI-GRID-APPLY-{1..3}` | 137~139 |
| `REQ-XGUI-GRID-VIEW-{1..3}` | 136~139 |
| `REQ-XGUI-GRID-EXPORT-{1..2}` | 142 |
| `REQ-XGUI-GRID-GUARD-{1..4}` | 139, 142, 143 |
| `REQ-XGRID-COVERAGE-{1..5}` | 136~143 |

각 범위는 모든 개별 ID로 전개한다. 필수 증거 필드는 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따르며 누락·중복·orphan은 인수 실패다.

## v0.5.1 operation closure acceptance

- **Given** grid frame/Params와 parametric 또는 sample-fit scatter 입력이 있고,
- **When** 사용자가 `modules.grid.analyze`, `modules.grid.notch_gain_1d`, `modules.grid.process`, `modules.virtual_grid.estimate_scatter`, `modules.virtual_grid.process`, `metrics.scatter_kernel.build_scatter_kernel`, `metrics.scatter_kernel.fit_scatter_kernel_from_samples`를 실행하면,
- **Then** 각 qualified EntryPoint의 call trace와 typed diagnostic/frame/CalibSet/error가 XDET-TC-136~143에 연결되고 UI가 peak/notch/scatter 값을 다시 계산하지 않아야 한다.
