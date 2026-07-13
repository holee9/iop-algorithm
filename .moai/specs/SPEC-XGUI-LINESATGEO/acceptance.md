---
id: SPEC-XGUI-LINESATGEO
version: 0.5.1
status: planned
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-12
updated: 2026-07-13
author: drake.lee
issue_number: 58
labels: [xgui, acceptance, line-noise, saturation, geometry, wpf]
---

# SPEC-XGUI-LINESATGEO — 인수 기준 (Acceptance Criteria)

> 본 인수기준의 모든 EARS ID·중앙 TC·필수 증거 연결은 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따른다. `baseline-control.md`의 G0와 사용자 승인 전에는 이 체크리스트를 구현 완료 증거로 사용할 수 없으며 모든 TC는 `PLANNED` 상태를 유지한다.

> **구현 대상:** `apps/xdet-console/` C# WPF 앱. `apps/gui/`와 Python 테스트는 계약·검증 선례이며 구현 대상이 아니다.
[SPEC-XGUI-LINESATGEO/spec.md](./spec.md) 그룹 3(Line noise / Saturation / Geometry, WP3+WP4) 검증 탭의 인수 기준이다. 모든 시나리오는 **E2E 흐름 — 열기(resident folder browser + `common/io.load_raw_frame`) → build/apply(골든 엔진 경유) → 저장(`<name>_result.raw` + `.json`) → 재적재 검증**을 축으로 하며, 표시·저장·거부의 관측 가능한 이진 판정을 정의한다. 저작 시 모든 골든 사실은 `file:line`으로 대조검증했다(G-1, 지어내기 금지).

- **시험 블록:** `XDET-TC-112~119` — SPEC-XGUI-MASTER 중앙 레지스트리의 G3 확정 블록.
- **테스트 위치·실행:** WPF ViewModel/engine seam은 `apps/xdet-console/tests/`의 xUnit 및 필요 시 Windows UI Automation으로, Python 알고리즘 회귀는 `tests/`에서 검증한다. 실행은 `dotnet test apps/xdet-console/Xdet.sln`, `uv run pytest`, `uv run lint-imports`이며 한글 출력은 `PYTHONIOENCODING=utf-8`로 고정한다.
- **실행 증거 원칙(L#1):** 각 시나리오는 "예외 미발생"이 아니라 **실제 실행 증거**(XFrame shape/dtype, 비퇴화 통계, diff 불리언, 오버레이 비트 카운트, 재적재 픽셀 동일성, 명시 오류형)를 단언한다.

## 전제 / 픽스처

- **합성 정본 경로(DATA-1).** 세 스테이지 전부 합성 전용 / #33 대기이므로 정본 수치 검증은 합성 주입으로 구성한다:
  - `LN_FRAME` — 행/열 banding이 주입된 raw-DN 프레임(known 행/열 오프셋), 일부 픽셀에 상류 `MaskFlag.SATURATION`(=2) 마스크.
  - `SAT_FRAME` — `MaskFlag.SATURATION` 코어가 주입된 raw-DN 프레임(포화 클램프값 65535).
  - `GEO_FRAME` — 다항 왜곡을 되돌릴 격자 팬텀 프레임.
  - `LN_CALIB` — `make_synthetic_calibset(shape, CalibKind.LINE_NOISE)`(빈 payload → no-reference SWR-503 경로). reference 경로 시나리오(XDET-TC-113)는 payload에 `reference_region` bool 마스크를 주입.
  - `SAT_CALIB` — `make_synthetic_calibset(shape, CalibKind.OTHER)`(빈 placeholder, 게이트 통과용; 밴드 표시는 프레임 마스크에서).
  - `GEO_CALIB` — `CalibKind.OTHER`에 **populated 왜곡 모델**(`distortion_coeffs_x`,`distortion_coeffs_y` = (degree+1)² 계수 행렬, `calibration_residual`) 주입. 활성 프리셋(`calibration_residual >= geometry_activation_residual_px`)·항등 프리셋(`< ...`) 두 종.
- **등록 실측 프레임 소스(DATA-2, QUARANTINE).** `images/에드로지16BIT/`의 SAMPLE 프레임은 **프레임 소스 sanity 전용** — 이 그룹 세 스테이지는 실측 CalibSet이 없다(#33 대기). edrogi 프레임은 finite·비퇴화 확인용으로만 로드하며 수치 golden/튜닝/적합에 쓰지 않는다(`panel_id="SAMPLE-EDROGI-16BIT"`, `sample=true`). realdata 부재 시 `@pytest.mark.realdata`로 정상 skip.
- **저장 writer.** 저장은 C# engine/adapter raw export를 사용하고 C-20 경계에서 `data/` 하위를 거부한다. 재적재 검증은 engine seam을 통해 Python `common.io.load_raw_frame` 계약을 소비한다.

---

## 인수 시나리오 (Given-When-Then)

### XDET-TC-112 — line_noise 개별 구동 (no-reference SWR-503 P1 경로)

- 커버: REQ-XGUI-LSG-INPUT-1/INPUT-2, PARAMS-1, VIEW-1/VIEW-4, RUN-1

```
GIVEN 상주 폴더 브라우저에서 LN_FRAME(행/열 banding + 상류 SATURATION 마스크)을 load_raw_frame로 로드하고,
      LN_CALIB(빈 LINE_NOISE payload → reference_region 부재)과
      Params(line_noise_profile_window, line_noise_highpass_cutoff, line_noise_contam_k)를 공급한다
WHEN  WPF가 `IXdetEngine.RunPipeline(PipelineRunRequest)`에 stages=["line_noise"]와 typed Params/CalibSet을 전달한다
THEN  출력 XFrame이 반환되고(shape == 입력 shape, pixel dtype 보존),
 AND  경로가 no-reference(SWR-503)임을 diag가 확인한다(HistoryEntry.extra["path"] == "no_reference", diag 키 = row_corr_max/col_corr_max, line_noise.py:131-135)
 AND  before/after/diff 이미지와 엔진 diag의 row_corr_max/col_corr_max를 표시한다. 보정 곡선은 엔진 결과 DTO가 명시적으로 제공할 때만 표시하며 UI가 marginal 또는 `_highpass_correction`을 재계산하지 않는다(C-09)
 AND  강건 통계 제외 마스크(DEFECT|INTERPOLATION|SATURATION, line_noise.py:57) 오버레이가 표시된다
 AND  상류 SATURATION 픽셀은 before/after diff == 0 (원값 복원 out[protect]=img[protect], line_noise.py:221; SWR-602 정합)
 AND  노이즈 모델(alpha, sigma)이 입력과 동일하다(재추정 없음, REQ-LNSG-LINE-3)
```

### XDET-TC-113 — line_noise reference 경로 (SWR-501/502, 합성 reference_region)

- 커버: REQ-XGUI-LSG-INPUT-2(존재 분기), PARAMS-1(contam_k)

```
GIVEN LN_FRAME과, payload에 비어있지 않은 reference_region bool 마스크(frame.shape 일치)를 주입한 LINE_NOISE CalibSet,
      그리고 line_noise_contam_k 포함 Params를 공급한다
WHEN  line_noise를 골든 엔진으로 구동한다
THEN  경로 선택이 골든에서 수행되어 diag["path"] == "reference" 이고 diag 키 = contaminated_rows/ref_mad (line_noise.py:175-179)
 AND  UI는 경로를 스스로 판정하지 않는다(_has_reference가 결정, line_noise.py:183-195; C-09)
 AND  before/after/diff와 엔진 diag의 contaminated_rows/ref_mad를 표시한다. 행 주파수 곡선은 엔진 결과 DTO가 제공할 때만 표시한다(C-09)
```

### XDET-TC-114 — saturation 개별 구동 (밴드/코어 구분, 포화 무복원)

- 커버: REQ-XGUI-LSG-INPUT-3, PARAMS-2(WHERE), VIEW-2, RUN-1

```
GIVEN SAT_FRAME(SATURATION 코어 주입)과 SAT_CALIB(빈 OTHER placeholder)을 공급한다
WHEN  saturation을 골든 엔진으로 구동한다
THEN  출력 XFrame에서 SATURATION_BAND(=8) 비트가 코어 팽창 경계에만 설정되고(band = dilated & ~sat, saturation.py:80-81), SATURATION(=2) 코어와 겹치지 않는다
 AND  UI가 SATURATION(코어)와 SATURATION_BAND(버퍼) 오버레이를 별개 비트로 구분 표시한다
 AND  모든 픽셀의 before/after diff == 0 (픽셀 무변경, saturation.py:83-87; SWR-602 "복원" 금지)
 AND  재실행(멱등) 시 밴드 픽셀 카운트가 증가하지 않는다(별개 비트 사용, 코어만 팽창 소스)
 AND  [WHERE] saturation_band_width가 Params로 제공되면 밴드 폭이 그 값을 따르고, 미제공이면 모듈 기본값 2(saturation.py:58)가 사용됨을 표시한다(REQUIRED_PARAMS=(), 강제 키 없음)
```

### XDET-TC-115 — geometry 활성/항등 두 경로 (변위장·경계 DEFECT·항등)

- 커버: REQ-XGUI-LSG-INPUT-4, PARAMS-3, VIEW-3

```
GIVEN GEO_FRAME과 GEO_CALIB(활성 프리셋: calibration_residual >= geometry_activation_residual_px, populated distortion_coeffs_x/y),
      Params(geometry_activation_residual_px, geometry_poly_degree)를 공급한다
WHEN  geometry를 골든 엔진으로 구동한다
THEN  활성 경로가 실행되어 diag["active"] == "true" (geometry.py:239-243)이고 리샘플된 raw-DN 출력이 반환된다
 AND  before/after/diff 및 엔진 diag를 표시한다. 변위장/격자 워프는 엔진 결과 DTO가 좌표장을 제공할 때만 표시하며 UI가 `_invert_field`/e_row/e_col 또는 좌표장을 재계산하지 않는다(C-09)
 AND  경계 밖 채움 픽셀은 geometry 전/후 DEFECT 마스크 diff로 식별되어 오버레이된다(전용 비트 없음, 공유 MaskFlag.DEFECT 병합, geometry.py:162)
GIVEN 동일 프레임과 항등 프리셋(calibration_residual < geometry_activation_residual_px)
WHEN  geometry를 구동한다
THEN  항등 통과되어 diff == 0 이고 diag["active"] == "false" 마커(geometry.py:199-206)가 기록된다
```

### XDET-TC-116 — 정렬된 조합 (line_noise→saturation→geometry) 단일 심 + 중간 프레임

- 커버: REQ-XGUI-LSG-RUN-2, RUN-3

```
GIVEN CANONICAL_ORDER의 유효 부분수열 ("line_noise","saturation","geometry")과
      각 스테이지 고유 CalibSet(LN_CALIB / SAT_CALIB / 활성 GEO_CALIB)·Params,
      그리고 누적 SATURATION/DEFECT 마스크를 지닌 입력 프레임(합성 주입)
WHEN  WPF가 `IXdetEngine.RunPipeline(PipelineRunRequest)`에 stages, params_map, calib_map을 담아 단일 호출한다
      (calib_map은 geometry populated 왜곡 모델을 포함하도록 override — 빈 placeholder는 ValueError 유발)
THEN  단일 패스로 조합 출력이 반환되고, 스테이지 정렬·조합은 PipelineDefinition(오케스트레이터)이 강제한다(UI 재구현 없음, C-11)
 AND  입력 XFrame.validation_mode=True 로 실행되어 result.intermediates가 실행된 각 스테이지 출력을 담고(orchestrator.py:334-341), 추가 실행 없이 각 스테이지 전/후를 스크럽할 수 있다(len(intermediates) == len(stages))
 AND  `PipelineRunResult.intermediates`의 각 `StageFrameResult`가 추가 엔진 실행 없이 표시된다
```

### XDET-TC-117 — 저장 왕복 (`<name>_result.raw` + `.json` → 재적재 픽셀 동일)

- 커버: REQ-XGUI-LSG-RUN-4, GUARD-3

```
GIVEN 어느 스테이지의 출력 XFrame과 사용자 지정(비-data/) 저장 폴더
WHEN  C# engine/adapter의 C-20 choke point가 경로를 검증한 뒤 `<name>_result.raw`, `<name>_result.json`, 마스크가 있으면 `<name>_result_mask.raw`, 그리고 `<name>_run_manifest.json`을 쓴다
THEN  sidecar는 `schema_version: xdet.frame-artifact/1.0`, resolution, dtype, byte_order, source_domain, export_domain, domain_max, quantization, mask 정보를 포함한다
AND  `load_raw_frame`로 재적재한 픽셀이 저장 직전 `clip[0,65535]`·`rint`·`uint16` 변환과 bit-동일하고, 재적재한 mask도 저장 직전 `uint8` bitfield와 bit-동일하다
 AND  saturation 결과의 SATURATION_BAND 비트가 `_result_mask.raw` 왕복 후에도 보존된다
 AND  run manifest는 `xdet.run-manifest/1.0` 공통 필드와 input/calib/params/output hash를 포함해 산출물을 추적한다
 AND  [GUARD-3] 저장 경로가 data/ 하위를 가리키면 C# 어댑터가 실행 전에 typed validation error로 거부한다(내보내기는 사용자 지정 폴더만)
```

### XDET-TC-118 — 불변 HARD 거부 가드

- 커버: REQ-XGUI-LSG-GUARD-1/GUARD-2, INPUT-4(거부), PARAMS-1(표면화)

```
GIVEN 이 그룹의 스테이지들
WHEN  CANONICAL_ORDER 부분수열이 아닌 순서(예: ("geometry","line_noise"))로 조합을 요청한다
THEN  PipelineDefinition.__post_init__이 PipelineOrderError로 거부한다(어떤 기본 캘리브레이션도 대체되지 않음, SWR-000-2)
WHEN  선택 스테이지가 해상도·panel_id·kind 일치 CalibSet을 결여한다
THEN  _calibration_gate가 CalibrationError로 거부한다(무단 기본값 대체 없음, SWR-000-5)
WHEN  geometry에 빈 payload placeholder(calibration_residual 부재)를 공급한다
THEN  geometry.process가 ValueError를 던지고(geometry.py:186-190) UI가 이를 은폐하지 않고 표면화한다
WHEN  line_noise에 필수 Params(window/cutoff, reference 경로의 contam_k)를 결여한다
THEN  골든이 던지는 ValueError("missing required parameter")를 UI가 표면화한다(은폐 금지, PARAMS-1)
 AND  UI/어댑터는 어떤 스테이지 출력도 스스로 계산하지 않고(C-09), 스테이지를 스스로 정렬·조합하지 않으며(C-11), 결여 CalibSet을 무단 합성하지 않는다(SWR-000-5) — 모든 DSP는 골든에, 조합/순서 권한은 오케스트레이터에 남는다
```

### XDET-TC-119 — 등록 edrogi 프레임-소스 sanity (QUARANTINE) + 합성 정본 경로

- 커버: REQ-XGUI-LSG-DATA-1, DATA-2(WHERE)

```
GIVEN 합성 정본 경로(LN_FRAME/SAT_FRAME/GEO_FRAME + 합성 CalibSet)
WHEN  세 스테이지를 각각 구동한다
THEN  정본 수치 검증은 합성 주입 known 값(banding/포화 코어/기하 왜곡)에 대해 이뤄진다(DATA-1)
 AND  [WHERE] 사용자가 등록 edrogi SAMPLE 프레임을 이 탭에 로드하면,
      UI는 그것을 프레임 소스 sanity(유한·비퇴화·구조 성립) 확인용으로만 사용하고 수치 golden 도출·튜닝·적합에 쓰지 않으며(QUARANTINE, 이슈 #29),
      정본 수치 검증은 정본 지침세트(이슈 #33) 도착 후 별건임을 표시한다
 AND  realdata 부재 시 해당 시나리오는 @pytest.mark.realdata로 정상 skip한다(합성 경로는 always-run)
```

---

### Scenario — line/saturation/geometry 전수 도달성

- **Given** 세 stage 각각의 strict Frame/CalibSet/Params와 조합 입력이 있고,
- **When** 독립 실행과 canonical ordered 조합을 수행하면,
- **Then** 실제 `modules.line_noise.process`, `modules.saturation.process`, `modules.geometry.process`가 `IXdetEngine`을 통해 호출되고 golden-direct와 동일한 XFrame/mask/history가 표시되어야 한다. 엔진이 반환하지 않는 correction curve/vector control과 UI 계산은 없어야 한다.

## Edge Cases

- **마스크 없는 saturation 입력** — 입력 프레임에 SATURATION 마스크가 없으면 band가 비어 사실상 no-op(SATURATION_BAND 카운트 0); UI는 "밴드 없음"을 표시하고 픽셀 diff == 0.
- **line_noise reference 전부 오염** — reference 경로에서 모든 참조행이 오염(contaminated)이면 골든이 인접행 보간/0 대체로 처리(line_noise.py:146-149); UI는 contaminated_rows 값을 그대로 표시(자체 보정 없음).
- **geometry degree 불일치** — `distortion_coeffs_x/y` 형상이 (degree+1)²와 다르면 골든이 ValueError(geometry.py:171-174); UI 표면화.
- **저장 정규화 도메인 혼동 금지** — 이 그룹은 raw-DN만 다룬다. 정규화 [0,1] 표시 도메인의 16-bit 역스케일(mse/window)은 그룹 5 몫이며 이 탭 저장 경로에 개입하지 않는다.
- **조합 시 상류 마스크 부재** — 합성 프레임에 누적 SATURATION/DEFECT 마스크가 없으면 saturation no-op·line_noise SAT 보호 무동작을 명시적으로 확인(조합 검증은 마스크 준비를 전제).
- **C-20 우회 시도** — data/ 심볼릭/상대경로 우회도 C# export choke point에서 거부됨을 확인한다.

---

## 품질 게이트 (Quality Gate)

- [ ] `dotnet test apps/xdet-console/Xdet.sln`과 `uv run pytest`·`uv run lint-imports`가 통과한다(XDET-TC-112~119).
- [ ] `uv run lint-imports` 통과 — 어댑터/GUI가 `modules`/`metrics`/`pipeline` 계층을 위반 소비하지 않음(읽기-실행 전용, C-11).
- [ ] 골든 무변경(G-1): `modules/line_noise.py`·`modules/saturation.py`·`modules/geometry.py`·`pipeline/`·`common/` diff 없음(writer는 C# engine/adapter에 두고 Python `common/`은 불변).
- [ ] C-09: 표시되는 모든 곡선·벡터장·수치가 엔진 결과 DTO에 존재하며 UI DSP 재계산 0(XDET-TC-112/XDET-TC-115 단언).
- [ ] C-20: C# export choke point가 data/ 경로를 거부한다(XDET-TC-117); WPF/adapter는 Python GUI helper 또는 `guard_output_path`를 직접 호출하지 않는다.
- [ ] 실행 경계: `apps.gui.module_panel.run_module` 및 `apps.gui.pipeline_panel.run_partial_pipeline` 의존 0건이며 모든 실행이 `IXdetEngine` typed DTO를 통과한다.
- [ ] QUARANTINE: edrogi SAMPLE는 sanity-only, EV 임계/튜닝/적합 미도출(XDET-TC-119).

## Definition of Done

- [ ] REQ-XGUI-LSG-INPUT/PARAMS/VIEW/RUN/DATA/GUARD 전 요구가 최소 1개 시나리오로 커버(아래 추적 매트릭스).
- [ ] Optional(WHERE) 요구(PARAMS-2, DATA-2) 각각에 "WHERE … 제공되면 …" 조건 AC 존재(XDET-TC-114, XDET-TC-119).
- [ ] Unwanted(IF…THEN) 요구(GUARD-1~3)가 결정적 거부(명시 오류형/거부)로 판정(XDET-TC-117/XDET-TC-118).
- [ ] E2E 왕복(열기→build/apply→저장→재적재)이 픽셀과 mask bitfield 각각에 대해 bit-동일하고 run manifest hash가 산출물을 추적한다(XDET-TC-117).
- [ ] 조합 검증이 단일 심 실행 + validation_mode intermediates로 성립(XDET-TC-116).
- [ ] 모든 AC가 실제 실행 증거(shape/dtype·diff·비트 카운트·오류형)를 단언(공허 통과 없음).

---

## AC ↔ REQ 추적 매트릭스

| REQ | 패턴 | 시나리오 |
|---|---|---|
| INPUT-1 | Ubiquitous | XDET-TC-112(열기·load_raw_frame), 전 시나리오 공통 |
| INPUT-2 | Event-Driven | XDET-TC-112(no-reference), XDET-TC-113(reference) |
| INPUT-3 | Ubiquitous | XDET-TC-114 |
| INPUT-4 | Event-Driven | XDET-TC-115(populated), XDET-TC-118(빈 payload 거부) |
| PARAMS-1 | Ubiquitous | XDET-TC-112, XDET-TC-118(결측 표면화) |
| PARAMS-2 | Optional (WHERE) | XDET-TC-114(WHERE band width) |
| PARAMS-3 | Ubiquitous | XDET-TC-115 |
| VIEW-1 | Ubiquitous | XDET-TC-112, XDET-TC-114, XDET-TC-115 |
| VIEW-2 | State-Driven | XDET-TC-114 |
| VIEW-3 | State-Driven | XDET-TC-115 |
| VIEW-4 | State-Driven | XDET-TC-112 |
| RUN-1 | Event-Driven | XDET-TC-112, XDET-TC-114, XDET-TC-115 |
| RUN-2 | Event-Driven | XDET-TC-116 |
| RUN-3 | Event-Driven | XDET-TC-116 |
| RUN-4 | Event-Driven | XDET-TC-117 |
| DATA-1 | Ubiquitous | XDET-TC-119(합성 정본), XDET-TC-112~116 |
| DATA-2 | Optional (WHERE) | XDET-TC-119(WHERE edrogi) |
| GUARD-1 | Unwanted | XDET-TC-118 |
| GUARD-2 | Unwanted | XDET-TC-118 |
| GUARD-3 | Unwanted | XDET-TC-117 |

### 사용자 제공 입력과 증거 보존 (XDET-TC-119, REQ-XGUI-LSG-DATA-2, REQ-XGUI-LSG-GUARD-3)

- **Given** 등록세트 밖의 strict frame/reference/geometry CalibSet과 action별 Params가 있을 때,
- **When** line-noise, saturation, geometry를 개별 및 canonical 조합으로 실행하면,
- **Then** 실제 EntryPoint 결과를 표시·저장하되 UI/report/manifest의 evidence를 `USER_SUPPLIED_UNVERIFIED`로 유지해야 한다.
- **Given** 승인 이력이 없을 때,
- **When** SAMPLE 또는 사용자 입력 결과를 정본으로 승격하려 하면,
- **Then** 승격을 거부하고 기존 evidence와 artifact를 변경하지 않아야 한다.

## 요구사항-TC 추적

| 요구사항 | 중앙 TC |
|---|---|
| `REQ-XGUI-LSG-TARGET-1` | 112~119 |
| `REQ-XGUI-LSG-INPUT-{1..4}` | 112~114, 118 |
| `REQ-XGUI-LSG-PARAMS-{1..3}` | 112~114, 118 |
| `REQ-XGUI-LSG-VIEW-{1..4}` | 112~115 |
| `REQ-XGUI-LSG-RUN-{1..4}` | 112~116, 118 |
| `REQ-XGUI-LSG-DATA-{1..2}` | 117, 119 |
| `REQ-XGUI-LSG-GUARD-{1..3}` | 116, 118, 119 |
| `REQ-XGUI-LSG-COVERAGE-{1..2}` | 112~119 |

각 범위는 모든 개별 ID로 전개한다. 필수 증거 필드는 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따르며 누락·중복·orphan은 인수 실패다.

## v0.5.1 operation closure acceptance

- **Given** 각 stage에 유효한 Frame/CalibSet/Params와 reference/no-reference 선택이 있고,
- **When** 사용자가 `modules.line_noise.process`, `modules.saturation.process`, `modules.geometry.process`를 각각 또는 canonical 조합으로 실행하면,
- **Then** 세 qualified EntryPoint의 call trace, 실제 XFrame/history/scalar diag, `uint8` mask, typed 오류가 XDET-TC-112~119에 기록되고 존재하지 않는 curve/vector를 UI가 계산하지 않아야 한다.
