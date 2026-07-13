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
priority: medium
issue_number: 58
labels: [xgui, gui-redesign, verification-gui, grid, virtual-grid, scatter, sks, golden-frozen]
---

# SPEC-XGUI-GRID — Grid/Virtual-Grid 알고리즘 그룹 GUI 검증 탭 (그룹 6)

> 본 사양은 `../SPEC-XGUI-MASTER/baseline-control.md`의 G0와 `traceability-matrix.md`를 상속한다. 사용자 승인·기준선 동결·`implementation_authorized=true` 전에는 구현 입력으로 실행하지 않으며, 승인 뒤 규범 변경은 버전 상승과 재승인을 요구한다.

XDET 검증 GUI 재설계(이슈 #58)의 **그룹 6 — Grid/VGrid(WP8+WP9)** 검증 탭 SPEC이다. 두 동결(FROZEN) 골든 모듈 `modules/grid.py`(격자선 억제, T7/WP8)와 `modules/virtual_grid.py`(SKS 가상 그리드, T8/WP9)를 **호출만** 하여, 스테이지별 구별 입력을 수집하고 개별/조합 적용 결과를 검증한다. 공유 사실 출처는 [SPEC-XGUI-MASTER/foundation.md](../SPEC-XGUI-MASTER/foundation.md)(이하 foundation)이며, frontmatter/구조는 [SPEC-XSEAM-002](../SPEC-XSEAM-002/spec.md)를 미러링한다. 본 SPEC은 foundation의 불변 HARD 제약(G-1~G-9)과 파이프라인 조합 사실을 재기술하지 않고 상속·참조한다.

**AUTHORITATIVE 원칙:** 아래 모든 process 시그니처·Params 키·CalibKind·데이터 가용성은 동결 골든 소스에서 Grep/Read로 대조검증했다(「골든 대조 근거표」). 미확인 항목은 명시적으로 "[미확인]"으로 표기한다. 지어내기(fabrication) 금지.

**문제(사용자 요구):** 격자선 억제와 가상 그리드는 각기 **구별되는 입력·표시 도메인**을 갖는다. grid은 관측 스펙트럼 피크를 직접 탐색(명목 grid 주파수 금지, SWR-1001)하므로 **주파수 도메인 뷰어**(FFT/PSD + 1D notch 전달함수)가 핵심이고, virtual_grid은 SKS 산란 추정·차감이므로 **공간 도메인 산란맵 뷰어** + ⚠P 특허 플래그가 핵심이다. 두 스테이지는 취득 컨텍스트상 상호 배타(물리 grid 有 → grid / grid-less → virtual_grid, virtual_grid.py:7-9)이나 `CANONICAL_ORDER`상으로는 grid → virtual_grid 순의 부분수열로 나란히 존재한다. 이 탭은 각 스테이지를 개별 확인한 뒤 하류 조합(grid→denoise, virtual_grid→denoise→mse 등)까지 골든 오케스트레이터를 거쳐 검증한다.

**엔진 중립성(G-8):** WPF는 `IXdetEngine.RunPipeline(PipelineRunRequest)`만 호출하고 PythonNet adapter가 `pipeline.orchestrator.run_pipeline`에 위임한다. 조합/DSP 권한은 골든에 남고 Python `apps.gui` helper는 실행 경계가 아니다.

- 근거(변경 없음, 소비만): `modules/grid.py::process`(grid.py:409) · `modules/grid.py::analyze`(grid.py:243, 순수·GridAnalysis) · `modules/grid.py::notch_gain_1d`(grid.py:327, 순수 1D notch 전달함수 |H(f)|) · `modules/virtual_grid.py::process`(virtual_grid.py:302) · `modules/virtual_grid.py::estimate_scatter`(virtual_grid.py:202, 순수 S_hat) · `pipeline/orchestrator.py::run_pipeline`·`PipelineDefinition`·`CANONICAL_ORDER`·`calib_kind_for_stage`(orchestrator.py:165)·`_calibration_gate` · `common/synth_calibset.py::make_synthetic_calibset`(synth_calibset.py:24) · `metrics/scatter_kernel.py::build_scatter_kernel`(scatter_kernel.py:144)·`fit_scatter_kernel_from_samples`(:213) · `common/io.py::load_raw_frame` · `apps/gui/io_panel.py::guard_output_path`(io_panel.py:27) · `common/xframe.py`(XFrame, `validation_mode`→`intermediates`)
- 상속 원칙: **읽기-실행 전용**(C-20/G-4), **지표·DSP 자체 계산 0**(C-09/G-2: UI/어댑터는 스스로 계산하지 않고 실제 엔진 결과만 표시), **단방향 소비**(C-11/G-3). 조합/순서 권한은 오케스트레이터에 남는다(SWR-000-2/G-6, SWR-000-5/G-7).
- 완료 정의(DoD): (1) grid/virtual_grid를 typed `IXdetEngine.RunPipeline`로 구동하고 엔진 진단만 표시 → (2) populated SCATTER CalibSet과 Params 검증 → (3) 정렬 조합과 intermediates를 단일 실행으로 표시 → (4) frame/mask artifact + run manifest 저장과 hash/round-trip/C-20 검증 → (5) data capability 라벨 정확성. 골든 무변경.
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.2.0 (2026-07-13)** — 중단 작업 복구 마무리. 구현 대상을 C# WPF `apps/xdet-console/`로 확정하고 Python `apps/gui/`는 참조 선례로 한정했다. 그룹별 결정·중앙 TC 레지스트리·plan/research를 확정했다. 골든 알고리즘은 변경하지 않는다.

- **v0.1.1 (2026-07-12)** — 라운드 1 교차검증(audit-r1.md, Verdict PASS, must-pass 4/4) minor 결함 3건 반영. **D1(섹션 넘버링 일관화)**: 형제 SPEC 편집 흔적으로 남은 `## 3.`/`## 9.` 번호 제거 → 무번호 헤딩으로 통일(house style), 내부 §3/§3.1/§3.2/§9 상호참조를 「Params 키 목록」·「골든 대조 근거표」 명칭 참조로 갱신(foundation §-참조는 외부 문서 지시이므로 불변). **D2(dangling 참조 해소)**: DoD(1)이 위임하던 인수 기준 문서 `acceptance.md` 신규 작성 + DoD의 `§인수` 표기를 정규 링크로 정리. **D3(배타성 과대표현 교정)**: grid+virtual_grid 결합을 "비권장/상호 배타"로 과대표현하던 서술을, 골든 오케스트레이터가 grid→virtual_grid 순서를 "저비율 물리 그리드의 잔여 산란"을 커버하는 **정당한 결합**으로 명시 문서화한 근거(orchestrator.py:49-56)를 병기하여 "배타=통상 취득 기본값 / 결합=저비율 그리드 정당 예외(양립)"로 재특징화(Environment·결정사항 3). 골든 무변경, EARS 16개·근거표 20개 사실 불변.
- **v0.1.0 (2026-07-12)** — 초안 생성. GitHub 이슈 #58(GUI 재설계) 그룹 6. foundation(SPEC-XGUI-MASTER) 상속, 구조는 SPEC-XSEAM-002 미러링. 6개 요구 그룹(INPUT/BUILD/APPLY/VIEW/EXPORT/GUARD) EARS. 저작 시 **AUTHORITATIVE 소스로 대조검증한 사실**: (a) `modules/grid.py` REQUIRED_PARAMS = 정확히 8키 `("grid_pitch_mm","grid_search_band_lo_lpmm","grid_peak_significance_db","grid_direction_margin_db","grid_harmonic_max_order","grid_notch_fwhm_mult","grid_moire_lowfreq_cutoff_lpmm","grid_moire_atten_cap")`(grid.py:83-92); 선택 키 `grid_meta_mounted`/`grid_meta_nominal_lpmm`(비교 경고 전용, 탐색 입력 금지 SWR-1001)·`grid_bg_window_bins`는 REQUIRED 아님(grid.py:72-76). (b) `modules/virtual_grid.py` REQUIRED_PARAMS = 정확히 5키 `("vgrid_sks_iterations","vgrid_downsample_levels","vgrid_grid_ratio_w","vgrid_lowsignal_threshold","vgrid_lowsignal_softness")`(virtual_grid.py:82-88). (c) grid은 `CalibSet(OTHER)`만 소비(진입 게이트용, 검출 캘리 없음, grid.py:36-37; `calib_kind_for_stage("grid")`→OTHER, orchestrator.py:165-174의 `_KIND_BY_STAGE`에 grid 부재). virtual_grid은 `CalibSet(SCATTER)`의 **dual-Gaussian payload**(`scatter_amp`[2]/`scatter_sigma`[2], SPR<1) 필수(`_resolve_kernel` virtual_grid.py:111-151, `_KIND_BY_STAGE["virtual_grid"]="scatter"` orchestrator.py:158-161). (d) **핵심 함정 검증됨:** `make_synthetic_calibset(shape, SCATTER)`(synth_calibset.py:24-52)는 **빈 data payload** CalibSet을 만들어 진입 게이트(kind==scatter)는 통과시키나, virtual_grid의 `_resolve_kernel`이 `scatter_amp`/`scatter_sigma` 부재로 **VirtualGridError**를 던진다(SWR-000-5 기본 커널 대체 금지). 따라서 virtual_grid 탭은 **populated SCATTER 커널**(`metrics/scatter_kernel.py::build_scatter_kernel`→CalibKind.SCATTER, scatter_kernel.py:144, 또는 fixture-populated)을 공급해야 한다 — mse의 상류 노이즈 하드 실패(foundation 그룹 5)와 동형. (e) grid 미검출 시 수치 동일 통과(grid.py:434-446), virtual_grid 비음수 클램프(virtual_grid.py:283-287)·저신호 tanh 감쇠(virtual_grid.py:229-240)·마스크 사전충전(virtual_grid.py:246-257). (f) 두 모듈 출력은 **raw-DN 도메인**(with_pixel로 frame.pixel.dtype 유지, grid.py:455/virtual_grid.py:339) — 그룹 5(mse/window 정규화 [0,1])와 달리 16-bit 라운드트립이 청결. (g) SAMPLE 에드로지 폴더(16bit cal/아크릴/최소선량선형/GHOST/nps, ingest_edrogi.py)에 **grid·scatter 세트 부재** → 그룹 6은 전(全) 스테이지 **합성 전용/#33 대기**(SAMPLE 실측 미구동). 확정 설계 결정: DSP·조합·캘리 합성 권한은 골든에 남기고 탭은 미러 DTO 전달·표시만(C-09/C-11/G-8). ⚠P(SKS US 11,911,202) 특허 대조는 릴리스 게이트 몫으로 P1 범위 밖, 커널 provenance는 이력에 기록(virtual_grid.py:42-49/352-356).

## Environment / Assumptions

- **본 SPEC은 T-스테이지가 아니다.** `CANONICAL_ORDER` 스테이지 추가·`process(...)->XFrame` 시그니처 변경·신규 CalibKind·`_KIND_BY_STAGE` 변경이 전혀 없다. `modules/grid.py`·`modules/virtual_grid.py`·오케스트레이터 표면은 불변이며, 본 SPEC은 그 위에 **그룹 6 검증 탭 소비자**를 additive로 얹는다(SPEC-VIEWER-001·SPEC-XSEAM 검증 도구 계열의 그룹별 재편).
- **grid ↔ virtual_grid: 통상 배타, 저비율 그리드에서는 정당한 결합(취득 컨텍스트).** grid은 물리 그리드가 **있는** 검출기의 주기적 격자선 변조를 제거하고, virtual_grid은 그리드가 **없는** 검출기의 산란(veiling glare)을 SKS로 추정·차감한다(virtual_grid.py:6-9). **통상 취득**에서 한 프레임은 둘 중 하나만 적용된다. 다만 골든 오케스트레이터는 grid → virtual_grid 순서를 **저비율 물리 그리드의 잔여 산란**(residual scatter of a low-ratio physical grid)을 커버하는 정당한 결합 시나리오로 명시 문서화하며(orchestrator.py:49-56), `CANONICAL_ORDER`가 그 부분수열을 허용한다. 즉 배타는 통상 취득의 기본값이고 결합은 저비율 물리 그리드의 정당한 예외이며(양립), 두 사실은 모순이 아니다. 탭은 두 스테이지를 개별 제공하되 조합 검증은 각 스테이지의 **하류**(grid→denoise 또는 virtual_grid→denoise→mse) 정합에 초점을 두고, grid+virtual_grid 동시 결합은 저비율 그리드 예외로 라벨링한다.
- **grid 입력 = CalibSet(OTHER) placeholder + Params(8) + 격자선 팬텀.** grid은 검출기 캘리브레이션을 소비하지 않는다. 진입 게이트만 `make_synthetic_calibset(shape, CalibKind.OTHER)`(빈 payload로 충분)로 만족시키고, 실제 억제 로직은 8개 REQUIRED Params(「Params 키 목록」 grid)와 입력 스펙트럼에서 파생한다. 입력 프레임은 격자 밀도 3부류(30~85 lines/cm)의 **합성 격자선 팬텀**(XDET-TC-015/016) 또는 정본 지침세트(#33 대기).
- **virtual_grid 입력 = populated CalibSet(SCATTER) + Params(5) + 산란 팬텀.** virtual_grid은 dual-Gaussian 산란 커널(`scatter_amp`/`scatter_sigma`, 각 2원소, SPR<1)을 **CalibSet(SCATTER)에서만** 취한다(단일 출처, 기본 커널 대체 금지 SWR-000-5, virtual_grid.py:111-151). **빈 payload 합성 CalibSet은 진입 게이트는 통과하나 `_resolve_kernel`에서 VirtualGridError로 하드 실패**하므로, 탭은 `metrics/scatter_kernel.py::build_scatter_kernel`(→CalibKind.SCATTER) 또는 fixture로 payload를 채운 SCATTER 커널을 공급해야 한다. 입력 프레임은 grid-less **합성 산란 팬텀**(veiling glare 주입) 또는 #33 대기.
- **열기 = 상주 폴더 브라우저(foundation §4).** 폴더 트리 + 가상화 썸네일 + 형제 필름스트립 + 이전/다음. 파일 지정 시에도 부모 폴더 형제 목록 유지. 로더는 `load_raw_frame(raw_path, meta_path)`(headerless 16-bit + `{resolution,dtype}` 사이드카, uint16→float32 무손실). 기본 소스는 등록 실측 세트이나 그룹 6은 실측 grid/scatter 부재로 합성 팬텀을 명시 라벨과 함께 로드(합성 목업 사용자탭 금지는 실측 세트 존재 시 규칙이며, #33 대기 스테이지의 엔진 검증용 합성은 명시 라벨로 허용 — foundation §2 그룹 6/§6).
- **저장 = frame artifact + mask + run manifest(foundation §3).** grid/virtual_grid 출력은 raw-DN 도메인이다. sidecar는 `xdet.frame-artifact/1.0` 전체 필드를 기록하고 pixel/mask bit-exact round-trip을 검증한다. `xdet.run-manifest/1.0`은 input/calib/params/output hash를 연결하며 C# export choke point가 `data/` 하위를 거부한다.
- **검증 모드 단일 패스 중간 프레임(검증됨).** 입력 `XFrame.validation_mode=True`면 조합 실행 한 번으로 `result.intermediates[i]`에 i번째 스테이지 출력이 부착되어(orchestrator, SPEC-XSEAM-002 spec.md:38) grid/virtual_grid 각각의 전/후를 추가 실행 없이 스크럽 가능.
- **데이터 가용성 = 그룹 전(全) 스테이지 합성 전용/#33 대기.** SAMPLE 에드로지 등록 세트에는 격자선·산란 정본이 없다(16bit cal/아크릴/최소선량선형/GHOST/nps만 존재). 따라서 그룹 1(offset/gain/defect SAMPLE sanity 실행가능)과 달리 그룹 6은 **SAMPLE 실측 미구동**이며, 합성 팬텀으로 엔진 자체(검출·notch·SKS 수렴)를 검증한다. 정본 수치 검증은 #33 지침세트 도착 후 별건(QUARANTINE, G-5).
- **⚠P 특허 플래그(virtual_grid).** SKS 정식화는 능동 특허(US 11,911,202 등)에 걸린다(virtual_grid.py:42-49). SW는 특허 판단을 하지 않고 커널 provenance를 이력에 기록(`sks_patent_flag`/`kernel_provenance`, virtual_grid.py:352-356); 대조·게이팅은 릴리스 게이트로 P1 범위 밖.
- **환경.** Python은 `uv run`으로만 실행(`uv run pytest`, `uv run lint-imports`). 정확성·재현성이 목적이며 성능·마샬링 최적화는 목적이 아니다.

## 정확한 Params 키 목록 (골든 검증)

골든 소스의 `REQUIRED_PARAMS` 매니페스트(SPEC-ERGO-001)에서 정확히 대조한 키 목록이다. 키 이름만 계약이며 값(등급 [B]/[T]/[P])은 Params/CalibSet 외부화(하드코딩 금지). 탭은 이 키들을 수집·전달하되 값의 의미·기본을 스스로 정하지 않는다(C-09).

### `grid` 스테이지 — REQUIRED 8키 (grid.py:83-92) + 선택 3키

| Params 키 | 상수 | 역할 (골든) | 등급 |
|---|---|---|---|
| `grid_pitch_mm` | P_PITCH | 패널 pitch(mm); f_N=1/(2·pitch), f_s=1/pitch **파생** | [ungraded] |
| `grid_search_band_lo_lpmm` | P_SEARCH_LO | 탐색 밴드 하단(≈0.3 lp/mm) | [ungraded] |
| `grid_peak_significance_db` | P_DTH_DB | 피크 유의성 임계 D_th(국소 배경 대비) | [T] |
| `grid_direction_margin_db` | P_DIR_MARGIN_DB | 행/열 방향 결정 마진 | [T] |
| `grid_harmonic_max_order` | P_HARMONIC_MAX | folded-harmonic 최대 차수 | [T] |
| `grid_notch_fwhm_mult` | P_NOTCH_FWHM_MULT | notch 대역폭 = 피크 FWHM × mult | [T] |
| `grid_moire_lowfreq_cutoff_lpmm` | P_MOIRE_CUTOFF | 저주파 접힘 컷오프(≈0.5 lp/mm) | [ungraded] |
| `grid_moire_atten_cap` | P_MOIRE_ATTEN_CAP | moire 밴드 이하 감쇠 캡 | [T] |
| `grid_bg_window_bins` (선택) | P_BG_WINDOW_BINS | 국소 배경 rolling-median 폭(기본 11) | [T] |
| `grid_meta_mounted` (선택) | P_META_MOUNTED | 취득 메타: 그리드 장착 여부 — **비교 경고 전용, 탐색 입력 금지** | — |
| `grid_meta_nominal_lpmm` (선택) | P_META_NOMINAL | 명목 밀도 — **비교 전용, SWR-1001 탐색 금지** | — |

- CalibKind: **OTHER**(검출 캘리 없음; 진입 게이트만). 누락 REQUIRED 시 `GridError`(grid.py:98-106).

### `virtual_grid` 스테이지 — REQUIRED 5키 (virtual_grid.py:82-88)

| Params 키 | 상수 | 역할 (골든) | 등급 |
|---|---|---|---|
| `vgrid_sks_iterations` | P_ITERATIONS | SKS 고정점 반복수(2~3) | [T] |
| `vgrid_downsample_levels` | P_DOWNSAMPLE_LEVELS | `reduce_once` 반복(3 → x8) | [T] |
| `vgrid_grid_ratio_w` | P_GRID_RATIO_W | grid-ratio 변환 가중(사용자 3:1~12:1 등가, **캘리 아님**) | [T]/[P] |
| `vgrid_lowsignal_threshold` | P_LOWSIGNAL_THRESHOLD | 저신호 감쇠 중점(tanh) | [T] |
| `vgrid_lowsignal_softness` | P_LOWSIGNAL_SOFTNESS | 감쇠 전이 폭 | [T] |

- CalibKind: **SCATTER** payload `scatter_amp`[2]/`scatter_sigma`[2] (SPR<1) 필수(`_resolve_kernel`, 단일 출처 SWR-000-5). 누락 REQUIRED 시 `VirtualGridError`(virtual_grid.py:97-105); 커널 부재·퇴화 시도 `VirtualGridError`(virtual_grid.py:111-151).

## Requirements (EARS)

### REQ-XGUI-GRID-TARGET — 구현 대상 경계

- **REQ-XGUI-GRID-TARGET-1 (Ubiquitous)** — 시스템은 `apps/xdet-console/` C# WPF 앱을 구현 대상으로 사용해야 하며, `apps/gui/`와 Python 테스트·패널은 계약 및 검증 선례로만 참조해야 한다. WPF는 Python 모듈을 직접 호출하지 않고 `IXdetEngine`/PythonNet seam을 경유해야 한다.

### REQ-XGUI-GRID-INPUT — 입력세트 선택: 상주 폴더 브라우저 + 스테이지별 구별 입력 (C-11, foundation §4, SWR-000-5)

- **REQ-XGUI-GRID-INPUT-1 (Ubiquitous)** — 그룹 6 탭은 입력 프레임을 **상주 폴더 브라우저**(폴더 트리 + 가상화 썸네일 그리드 + 형제 필름스트립 + 이전/다음)로 선택할 수 있어야 하며, 사용자가 단일 파일을 지정해도 그 부모 폴더의 형제 목록을 함께 표시하고, `common.io.load_raw_frame`(headerless 16-bit + `{resolution,dtype}` 사이드카)로 XFrame을 무손실 적재해야 한다.
- **REQ-XGUI-GRID-INPUT-2 (Event-Driven)** — WHEN 사용자가 `grid` 스테이지를 선택하면, THEN 탭은 진입 게이트용 `CalibSet(OTHER)` placeholder(`make_synthetic_calibset(shape, CalibKind.OTHER)`)와 8개 REQUIRED Params(「Params 키 목록」 grid)를 그 스테이지의 구별 입력으로 수집해야 하며, grid은 검출기 캘리브레이션을 소비하지 않음(검출 캘리 없음)을 UI에 명시해야 한다.
- **REQ-XGUI-GRID-INPUT-3 (Event-Driven)** — WHEN 사용자가 `virtual_grid` 스테이지를 선택하면, THEN 탭은 **populated** `CalibSet(SCATTER)`(dual-Gaussian `scatter_amp`[2]/`scatter_sigma`[2], SPR<1; `build_scatter_kernel` 또는 fixture 유래)와 5개 REQUIRED Params(「Params 키 목록」 virtual_grid)를 수집해야 하며, 빈 payload SCATTER CalibSet은 진입 게이트는 통과하나 스테이지가 `VirtualGridError`로 거부함(SWR-000-5, 기본 커널 대체 금지)을 사전 경고로 표시해야 한다.

### REQ-XGUI-GRID-BUILD — 캘리브레이션·파라미터 조립 (C-09, SWR-000-5)

- **REQ-XGUI-GRID-BUILD-1 (Ubiquitous)** — 탭이 조립하는 스테이지별 `CalibSet`·`Params`는 골든이 요구하는 정확한 계약을 만족해야 한다 — grid은 「Params 키 목록」 grid의 8키(누락 시 `GridError`, grid.py:98-106), virtual_grid은 「Params 키 목록」 virtual_grid의 5키(누락 시 `VirtualGridError`, virtual_grid.py:97-105)이며, 선택 키(grid의 `grid_meta_*`/`grid_bg_window_bins`)는 기본값을 가지므로 미공급을 허용해야 한다.
- **REQ-XGUI-GRID-BUILD-2 (Unwanted)** — IF 탭이 결여된 SCATTER 커널을 스스로 합성하거나(빈 payload를 임의 계수로 채움), grid 탐색에 명목 grid 주파수(`grid_meta_nominal_lpmm`)를 주입하려 하면, THEN 이는 거부되어야 한다(커널은 CalibSet(SCATTER) 단일 출처 SWR-000-5; 메타데이터는 비교 경고 전용이고 피크 탐색 입력 금지 SWR-1001, grid.py:73-76/389-406).

### REQ-XGUI-GRID-APPLY — build/apply 워크플로: 개별 → 부분수열 조합 → 검증 모드 (SWR-000-2, SPEC-XSEAM-002 CONTRACT-6/COMPOSE-1~3 미러)

- **REQ-XGUI-GRID-APPLY-1 (Event-Driven)** — WHEN 사용자가 단일 스테이지(`grid` 또는 `virtual_grid`)를 적용하면, THEN WPF는 단일 stage `PipelineRunRequest`를 `IXdetEngine.RunPipeline`에 전달하고 입력/출력/diff/이력 진단을 표시해야 한다. 모든 수치는 엔진 DTO 산출이어야 한다(C-09/C-11).
- **REQ-XGUI-GRID-APPLY-2 (Event-Driven)** — WHEN 사용자가 그룹 6 스테이지를 포함한 정렬된 부분수열(예: `("grid",)`·`("virtual_grid",)`·`("grid","denoise")`·`("virtual_grid","denoise","mse")`)을 선택하면, THEN 탭은 그 정렬된 부분수열에 대한 단일 심 파이프라인 실행을 요청하고 조합 출력과 각 스테이지의 전/후를 함께 표시해야 하며, 스테이지 순서·조합 결정은 C# 측이 아니라 `PipelineDefinition`(오케스트레이터)이 강제해야 한다(SWR-000-2, C-11).
- **REQ-XGUI-GRID-APPLY-3 (Event-Driven)** — WHEN 조합 실행이 검증 모드(`XFrame.validation_mode=True`)로 요청되면, THEN 심은 실행된 모든 스테이지의 중간 프레임(`XFrame.intermediates`)을 그 단일 패스에서 반환하고, 탭은 추가 실행을 발행하지 않고 grid/virtual_grid 각 스테이지의 전/후를 스크럽할 수 있어야 한다(SPEC-XSEAM-002 REQ-XSEAM-COMPOSE-3 미러).

### REQ-XGUI-GRID-VIEW — 그룹 고유 뷰어 특성: 주파수 도메인(grid) vs 공간 산란맵(virtual_grid)

- **REQ-XGUI-GRID-VIEW-1 (Event-Driven)** — WHEN `grid` 스테이지 결과가 표시되면, THEN 탭은 **주파수 도메인 뷰어**를 제공해야 한다 — 축별 관측 PSD 스펙트럼(`analyze`/`common.fft_psd` 유래), 검출 피크 마커(`Peak.freq_lpmm`/`significance_db`/`fwhm_lpmm`), 격자-직교 축의 1D Gaussian notch 전달함수 `|H(f)|`(`notch_gain_1d`, grid.py:327 순수 프록시), 방향 지시자(`vertical`/`horizontal`/`none`), 이력 진단(`peak_freq_lpmm`/`peak_significance_db`/`notch_bandwidth_lpmm`/`direction_energy_ratio_db`/`n_peaks`). 모든 값은 엔진 산출이어야 한다(C-09).
- **REQ-XGUI-GRID-VIEW-2 (Event-Driven)** — WHEN `grid` 스테이지가 유의 피크를 검출하지 못하거나 방향이 모호하면(`GridAnalysis.detected=False`), THEN 탭은 **수치 동일 통과(passthrough)** 상태를 명시하고(이력 `grid_detected=false`/`grid_undetected=true`, grid.py:434-446) 어떤 픽셀 변경도 없었음을 표시해야 하며; 저주파 접힘으로 감쇠가 캡핑되면(`moire_atten_capped=true`) 그리드 교체 권고 경고를 표시해야 한다(SWR-1004, grid.py:475-479).
- **REQ-XGUI-GRID-VIEW-3 (Event-Driven)** — WHEN `virtual_grid` 스테이지 결과가 표시되면, THEN 탭은 **공간 도메인 산란맵 뷰어**를 제공해야 한다 — SKS 산란 추정 `S_hat`(전-해상도, `estimate_scatter` 유래) + 차감 전/후 이미지, 스칼라 진단(`scatter_fraction`/`lowsignal_attenuated_fraction`/`nonneg_clamp_count`, virtual_grid.py:345-351), SKS 반복수·다운샘플 레벨(x8=3레벨)·적용 grid-ratio 가중, 그리고 ⚠P **특허 플래그 배너**(`sks_patent_flag`/`kernel_provenance`, virtual_grid.py:352-356). 포화 픽셀 "복원"은 없음(단조 하향 차감은 복원이 아님, SWR-602)을 명시해야 한다.

### REQ-XGUI-GRID-EXPORT — 결과 저장: `<name>_result.raw` + 사이드카, C-20 게이트 (foundation §3, G-4)

- **REQ-XGUI-GRID-EXPORT-1 (Event-Driven)** — WHEN 사용자가 결과를 저장하면, THEN 탭은 raw-DN 결과를 `xdet.frame-artifact/1.0` raw/sidecar, mask가 있으면 `uint8` mask raw, 그리고 `xdet.run-manifest/1.0`으로 기록해야 한다. Pixel/mask round-trip과 input/calib/params/output hash를 검증한다.
- **REQ-XGUI-GRID-EXPORT-2 (Unwanted)** — IF 저장 대상 경로가 `<project_root>/data` 하위이면, THEN C# export choke point가 실행 전에 typed validation error로 거부해야 한다. WPF/adapter는 Python `guard_output_path`를 직접 호출하지 않는다(C-20/G-4).

### REQ-XGUI-GRID-GUARD — 골든 FROZEN·DSP 0·QUARANTINE 가드 (C-09/C-11/G-1/G-5)

- **REQ-XGUI-GRID-GUARD-1 (Unwanted)** — IF 탭 또는 어댑터가 grid의 피크 탐색·notch, virtual_grid의 SKS 추정·차감을 스스로 계산하거나(엔진 우회), 스테이지를 스스로 정렬·조합하거나, 골든 시그니처·수치·상수를 변경하려 하면, THEN 이는 거부되어야 한다(DSP는 골든에, 조합 권한은 오케스트레이터에, 골든 읽기 전용 — C-09/C-11/G-1).
- **REQ-XGUI-GRID-GUARD-2 (Ubiquitous)** — 그룹 6 SAMPLE·합성 팬텀 구동은 **sanity(유한·비퇴화·구조 성립: 스펙트럼 존재·피크 검출 가부·SKS 수렴·비음수)** 확인일 뿐이어야 하며, 어떤 수치 golden 도출·EV 임계 튜닝·커널 적합에도 사용되어서는 안 된다(QUARANTINE/G-5). 정본 수치 검증은 정본 지침세트(이슈 #33) 도착 후 별건이다.
- **REQ-XGUI-GRID-GUARD-3 (Ubiquitous)** — 탭은 그룹 6 전(全) 스테이지의 데이터 가용성을 **합성 전용/#33 대기**로 라벨해야 하며, SAMPLE 에드로지 등록 세트에 격자선·산란 정본이 없어 SAMPLE 실측 구동이 불가함을 명시해야 한다(그룹 1 offset/gain/defect의 SAMPLE sanity 실행가능과 대비).
- **REQ-XGUI-GRID-GUARD-4 (Ubiquitous)** — virtual_grid 결과 표시·저장 시 탭은 ⚠P SKS 특허 플래그(`sks_patent_flag`)와 커널 provenance를 보존·표시해야 하며(릴리스 게이트 추적성), SW가 특허 판단을 하지 않음을 명시해야 한다(virtual_grid.py:42-49, P1 범위 밖).

### REQ-XGRID-COVERAGE — physical/virtual grid 전수 실행

- **REQ-XGRID-COVERAGE-1 (Event-Driven)** — WHEN physical grid를 실행하면 THEN engine은 실제 `modules.grid.analyze`, `notch_gain_1d`, `process`를 호출하고 GridAnalysis와 notch-response series, output XFrame을 typed result로 반환해야 한다.
- **REQ-XGRID-COVERAGE-2 (Event-Driven)** — WHEN virtual grid를 실행하면 THEN engine은 실제 `modules.virtual_grid.estimate_scatter`와 `process`를 호출하고 scatter estimate diagnostics와 output XFrame을 반환해야 한다.
- **REQ-XGRID-COVERAGE-3 (Event-Driven)** — WHEN scatter calibration을 생성하면 THEN parametric 경로는 `metrics.scatter_kernel.build_scatter_kernel`, sample-fit 경로는 `fit_scatter_kernel_from_samples`를 호출하고 동일 populated SCATTER schema를 반환해야 한다.
- **REQ-XGRID-COVERAGE-4 (Event-Driven)** — WHEN strict 사용자 frame/SCATTER calibration source가 제공되면 THEN 등록 정본 부재로 실행을 막지 않고 `USER_SUPPLIED_UNVERIFIED`로 기록해야 한다.
- **REQ-XGRID-COVERAGE-5 (Unwanted)** — IF UI가 FFT peak, notch gain, scatter estimate 또는 kernel fit을 계산하면 THEN 인수 실패해야 한다.

## Exclusions (What NOT to Build)

- **골든 모델 변경 없음** — `modules/grid.py`·`modules/virtual_grid.py`·`pipeline/orchestrator.py`·`common/`·`metrics/`는 동결 오라클로 편집하지 않는다. 탭은 이들을 읽기 전용으로 소비한다(호출만). grid의 피크 탐색·notch·moire 캡, virtual_grid의 SKS 반복·산란 커널·저신호 감쇠·비음수 클램프 로직을 UI에서 재구현하지 않는다.
- **명목 grid 주파수 기반 처리 없음** — grid 탐색은 관측 스펙트럼 피크만 사용한다(SWR-1001). `grid_meta_mounted`/`grid_meta_nominal_lpmm` 메타데이터를 피크 위치 탐색 입력으로 주입하지 않는다(비교 경고 표시 전용, grid.py:389-406).
- **SCATTER 커널 합성·기본값 대체 없음** — virtual_grid 커널은 CalibSet(SCATTER) 단일 출처다. 탭은 결여·퇴화 커널을 임의 계수로 채우지 않으며, 빈 payload 합성 CalibSet의 하드 실패(`VirtualGridError`)를 버그가 아닌 정상 거부로 표면화한다(SWR-000-5).
- **포화 "복원" 없음** — virtual_grid의 단조 하향 산란 차감은 포화 픽셀의 클리핑된 정보를 재구성하지 않는다(SWR-602). 탭은 "복원" UI를 제공하지 않는다.
- **⚠P 특허 대조·게이팅 없음** — SKS 특허(US 11,911,202) 대조·릴리스 게이팅은 P1 SW 범위 밖이다. 탭은 특허 플래그·provenance를 표시·기록만 하고 판단하지 않는다.
- **정본 수치 검증 없음(QUARANTINE)** — 합성 팬텀 구동은 sanity 확인이며 수치 golden/EV 임계 도출·튜닝·적합에 쓰지 않는다. 정본 수치 검증은 이슈 #33 지침세트 도착 후 별건이다.
- **DSP·조합·CalibKind 신설 없음** — 조합은 기존 `CANONICAL_ORDER`(grid → virtual_grid → …)·기존 CalibKind(OTHER/SCATTER)로만 이뤄진다. 신규 스테이지·kind를 신설하지 않는다.
- **C++ 엔진 이식·성능 최적화 없음** — 네이티브 조합 커널이나 3072² 프레임 마샬링 최적화는 범위 밖(SPEC-XSEAM Stage 2/P2 승계).
- **시퀀스(시간축) 뷰어 없음** — 그룹 6은 단일 프레임 스테이지다. 다중 프레임 시퀀스(그룹 2 lag의 `run_sequence`)는 이 탭의 범위가 아니다.

## 확정 결정 (v0.5.1)

1. Virtual Grid의 기본 kernel 생성 경로는 골든 `build_scatter_kernel`이다.
2. builder 입력은 advanced panel에 노출하고 8 cm/100 kV는 알려진 시험 preset으로만 제공한다. 알고리즘 기본값으로 하드코딩하지 않는다.
3. Grid 주파수 뷰에는 folded-harmonic marker를 표시한다.
4. grid→virtual_grid 조합은 저-ratio residual scatter 확인 목적일 때 허용하며 stage sequence와 목적을 명시한다.
5. 중앙 TC 레지스트리는 G6 블록 XDET-TC-136~143 전체를 사용한다.

## 골든 대조 근거표 (AUTHORITATIVE)

모든 사실을 동결 골든 소스 `file:line`으로 Grep/Read 대조검증했다. 지어내기 금지 원칙의 추적 근거다.

| 사실 | 근거 (file:line) |
|---|---|
| grid `process(frame, calib, params) -> XFrame` 단일 계약 | modules/grid.py:409 |
| grid 관측 스펙트럼 피크 직접 탐색(aliasing 전제, 명목 주파수 금지) | modules/grid.py:4-11 (docstring), SWR-1001 |
| grid 1D Gaussian notch(격자-직교 축, 2D 등방 금지) | modules/grid.py:295-386 (`_gaussian_notch_gain`/`_apply_notch`) |
| grid 저주파 접힘 감쇠 캡 + 경고 | modules/grid.py:315-324/475-479 (moire cap) |
| grid 미검출 시 수치 동일 통과 | modules/grid.py:434-446 |
| grid REQUIRED_PARAMS 8키 | modules/grid.py:83-92 |
| grid 선택 키(meta/bg_window, 비교 전용) | modules/grid.py:72-76/389-406 |
| grid CalibKind=OTHER(검출 캘리 없음) | modules/grid.py:36-37; orchestrator.py:165-174 (grid ∉ `_KIND_BY_STAGE`) |
| grid 순수 분석/전달함수 프록시(뷰어 소스) | modules/grid.py:243 (`analyze`), :327 (`notch_gain_1d`), Peak :109, GridAnalysis :118 |
| grid 이력 진단 필드 | modules/grid.py:426-479 |
| virtual_grid `process(...)` 단일 계약 | modules/virtual_grid.py:302 |
| virtual_grid SKS 다운샘플 반복(x8=3레벨, pyramid) | modules/virtual_grid.py:170-223 (`_downsample`/`estimate_scatter`) |
| virtual_grid CalibSet(SCATTER) dual-Gaussian 단일 출처, 기본 대체 금지 | modules/virtual_grid.py:111-151 (`_resolve_kernel`), SWR-000-5 |
| virtual_grid REQUIRED_PARAMS 5키 | modules/virtual_grid.py:82-88 |
| virtual_grid 저신호 tanh 감쇠 + 비음수 클램프 | modules/virtual_grid.py:229-240/283-287 |
| virtual_grid 마스크 사전충전(추정 오염 방지) | modules/virtual_grid.py:92-94/246-257 |
| virtual_grid 포화 "복원" 없음(단조 하향 차감) | modules/virtual_grid.py:40, SWR-602 |
| virtual_grid ⚠P 특허 플래그·provenance | modules/virtual_grid.py:42-49/352-356 (US 11,911,202) |
| virtual_grid CalibKind=SCATTER(kind-vs-stage 강제) | pipeline/orchestrator.py:158-161 (`_KIND_BY_STAGE["virtual_grid"]="scatter"`) |
| `calib_kind_for_stage` 공개 접근자 | pipeline/orchestrator.py:165 |
| 합성 CalibSet 팩토리(빈 payload) — grid OTHER엔 충분, vgrid SCATTER엔 불충분 | common/synth_calibset.py:24-52 |
| populated SCATTER 커널 빌더 | metrics/scatter_kernel.py:144 (`build_scatter_kernel`), :213 (`fit_scatter_kernel_from_samples`), :74 (Error) |
| C-20 단일 choke point(`data/` 하위 쓰기 거부) | apps/gui/io_panel.py:27 (`guard_output_path`) |
| 열기 로더(headerless 16-bit + 사이드카) | common/io.py (`load_raw_frame`) |
| SAMPLE 에드로지 폴더에 grid/scatter 정본 부재 → 합성 전용/#33 대기 | foundation §2 그룹 6, scripts/ingest_edrogi.py |

## v0.5.1 public operation closure

| Python EntryPoint | GUI 노출 | TC |
|---|---|---|
| `modules.grid.analyze` | Grid analysis action/diagnostic | 136 |
| `modules.grid.notch_gain_1d` | Notch response action/series | 137 |
| `modules.grid.process` | Grid removal action | 137~138 |
| `modules.virtual_grid.estimate_scatter` | Scatter estimate action/preview | 139 |
| `modules.virtual_grid.process` | Virtual-grid action | 139~140 |
| `metrics.scatter_kernel.build_scatter_kernel` | parametric kernel builder | 141 |
| `metrics.scatter_kernel.fit_scatter_kernel_from_samples` | sample-fit kernel builder | 142 |

TC-143은 조합·오류·user-input/evidence를 검증한다. 각 derived 결과도 실제 Python call trace와 golden-direct fidelity를 가져야 한다.
