---
id: SPEC-XGUI-CALIB
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
labels: [xgui, gui-redesign, verification-gui, calibration, offset-gain-defect, golden-frozen]
---

# SPEC-XGUI-CALIB — Calibration(OC·GC·BPM) 그룹 검증 탭 (offset·gain·defect Build→Apply)

> 본 사양은 `../SPEC-XGUI-MASTER/baseline-control.md`의 G0와 `traceability-matrix.md`를 상속한다. 사용자 승인·기준선 동결·`implementation_authorized=true` 전에는 구현 입력으로 실행하지 않으며, 승인 뒤 규범 변경은 버전 상승과 재승인을 요구한다.

XDET 검증 GUI 재설계(이슈 #58)의 **그룹 1 — Calibration** 탭 명세다. 골든 WP1 3스테이지 `offset`(OC, dark 감산)·`gain`(GC, flat 정규화)·`defect`(BPM, 불량화소 보간)를 하나의 목적별 탭으로 묶어, 각 스테이지의 **구별되는 캘리브레이션 입력**(OFFSET `O_map` / GAIN `G_map` / DEFECT `class_map`)을 **Build**(캘리브레이션 생성)한 뒤 촬영 영상에 **Apply**(고정순서 조합 적용)하고 결과를 raw로 저장하는 워크플로를 규정한다. 공유 사실·불변 제약은 [SPEC-XGUI-MASTER](../SPEC-XGUI-MASTER/foundation.md)(foundation)에 있으며 본 문서는 이를 재기술하지 않고 **그룹 1 고유 사항만** 명세한다.

**문제(사용자 요구):** OC·GC·BPM은 각기 다른 캘리브레이션 소스(MasterDark / bright·flat / bad-pixel map)를 요구하며 조사조건(kV·mA·mAs)마다 flat이 달라진다. 사용자는 (a) 각 캘리브레이션을 조건별로 골라 Build하고, (b) Build된 캘리브레이션을 촬영영상에 개별/조합으로 Apply하여 스테이지별·조합 결과를 확인하고, (c) 결과를 벤더 포맷과 동일한 `<name>_result.raw`로 내보낼 수 있어야 한다. 검증 결과 **동결 Python 골든은 이 3스테이지를 이미 완전히 지원**한다 — `modules/{offset,gain,defect}.py::process`(단일 계약)와 `scripts/ingest_edrogi.py`의 CalibSet 빌더, `pipeline.orchestrator.run_pipeline`의 고정순서 조합이 그것이다. 실제 격차는 이 능력을 **목적별(Calibration 그룹) 탭 UI로 노출**하는 것뿐이며, DSP·조합·캘리브레이션 생성 로직을 GUI가 재구현하지 않는다.

- **근거(변경 없음, 소비만):** `modules/offset.py:85 process`(I1=clamp(I_raw−O,0), raw-sat 검출) · `modules/gain.py:87 process`(I2=clamp(I1·G,65535), 불량게인→DEFECT 핸드오프·over→SATURATION) · `modules/defect.py:282 process`(morphology 보간·INTERPOLATION 마킹) · `scripts/ingest_edrogi.py:278/296/321 build_{offset,gain,defect}_calibset` · `metrics/defect_map.py:83 build_defect_map`(dark+flat 스택→classify_defects+classify_morphology→`CalibKind.DEFECT`) · `metrics/defect_stats.py:57 classify_defects`(E2597 7분류) · `pipeline/orchestrator.py::run_pipeline`/`PipelineDefinition`/`CANONICAL_ORDER`(고정순서·부분수열)·`_calibration_gate`(부재/불일치 거부) · `apps/gui/app.py:90 CompareDisplay`(before/after/diff·마스크·probe·W/L·blink).
- **상속 원칙:** foundation §1의 불변 HARD 제약 G-1~G-9를 전부 상속한다 — 골든 FROZEN(호출만·수정 금지·Grep/Read 대조검증), C-09(UI DSP 0), C-11(단방향 소비), C-20(사용자 폴더만 내보내기), QUARANTINE(SAMPLE=sanity), SWR-000-2(고정 파이프라인 순서), SWR-000-5(무단 기본 캘리브레이션 대체 금지), IXdetEngine=run_pipeline 미러.
- **완료 정의(DoD):** (1) Build 하위탭이 OFFSET/GAIN/DEFECT CalibSet을 골든 빌더 경유로 생성·검증·등록 → (2) Apply가 `IXdetEngine.RunPipeline(PipelineRunRequest)`로 `offset→gain→defect` 부분수열을 구동 → (3) before/after/diff + mask + probe 표시 → (4) frame artifact, mask artifact, run manifest 저장과 hash/round-trip 검증 → (5) SAMPLE sanity 구동 → (6) UI/adapter DSP·조합·캘리브레이션 합성 및 Python `apps.gui` helper 직접 의존 0. 골든 무변경.
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.2.0 (2026-07-13)** — 중단 작업 복구 마무리. 구현 대상을 C# WPF `apps/xdet-console/`로 확정하고 Python `apps/gui/`는 참조 선례로 한정했다. 그룹별 결정·중앙 TC 레지스트리·plan/research를 확정했다. 골든 알고리즘은 변경하지 않는다.

- **v0.1.1 (2026-07-12)** — 라운드 1 적대적 교차검증(audit-r1.md, plan-auditor) 반영. 골든 소스 재대조(Grep/Read) 후 4개 결함 교정: **(D1, MAJOR)** `build_defect_map`(defect_map.py:112-120)은 `CalibSet`을 `validate()` **없이** 반환함을 확인 — "모든 빌더가 생성 직후 validate()" 오기를 삭제하고, SAMPLE 빌더 3종(`build_offset/gain/defect_calibset`, ingest_edrogi.py:292/317/342)만 자체 validate()하며 정본 스택 경로(`build_defect_map`)는 탭이 등록 전 명시적으로 `CalibSet.validate()`를 호출함을 Assumptions·BUILD-3·DoD(1)에 명시(비-DSP 스키마 확인, C-09 보존). **(D2, MINOR)** `_calibration_gate`/`run_pipeline`의 `domain` 인자와 CALDOM(SPEC-CALDOM-001) 교차도메인·kind·상호 domain/beam_quality 검사(orchestrator.py:178-280)를 게이트 서술과 APPLY-2/-4에 반영 — 이 그룹은 `domain=None`으로 구동하고 SAMPLE은 MEDICAL 상호일관. **(D3, MINOR)** BUILD-5의 `defect_min_frames` 게이트를 외부 BPM.raw 경로가 아니라 dark·flat 스택 경로(`classify_defects`, defect_stats.py:78-83)에 정확히 귀속. **(D4, MINOR)** `build_defect_map`의 keyword-only **필수** 신원 인자(panel_id·resolution·valid_from·valid_until, defect_map.py:83-94)를 시그니처·BUILD-3에 명시. GUARD-1은 정적 부재 검증으로 조임. acceptance.md 신규 작성(XDET-TC-096~101, 등록 edrogi SAMPLE sanity 연결). 골든 무변경.
- **v0.1.0 (2026-07-12)** — 초안 생성. GitHub 이슈 #58(GUI 재설계) 그룹 1 SPEC. foundation(SPEC-XGUI-MASTER) 참조, frontmatter/구조는 SPEC-XSEAM-002 미러링. **AUTHORITATIVE 소스로 검증한 그룹 1 사실**(Grep/Read): (a) `offset.REQUIRED_PARAMS=("raw_saturation_threshold",)`(offset.py:36), raw-sat는 감산 **전** 검출·SATURATION 누적(offset.py:97-113), `K_SIGMA_D` 공급 시 noise σ 초기화(offset.py:119-121). (b) `gain.REQUIRED_PARAMS=("gain_min","gain_max")`(gain.py:39); `[gain_min,gain_max]` 밖 게인은 **미적용**(원값 유지)+DEFECT 핸드오프(gain.py:96-112), 16-bit 초과는 SATURATION(gain.py:115); `anchor_gains` 존재 시 `NotImplementedError`(다중노출 [B] 이연, gain.py:53-60). (c) `defect.REQUIRED_PARAMS=("defect_cmax_pixels",)`(defect.py:54)만 필수; `defect_line_min`(기본 8)·`defect_line_max_width`(기본 1)은 선택(defect.py:291-294); C_max 초과 cluster는 `DefectMapRefused`(defect.py:107-130), 정상이웃 없으면 값 유지+INTERPOLATION **미설정**(defect.py:16-18/276-278). (d) BPM 생성 `build_defect_map`는 dark+flat **스택**을 요구(defect_map.py:83-106)하며 `classify_defects`의 7 임계 P급과 6× median noisy 고정 S급(defect_stats.py:29/98-111)에 의존 → SAMPLE은 단일 MasterDark/BPM만 있어 완전 생성 불가; SAMPLE BPM은 외부 `BPM.raw`를 `build_defect_calibset`(nonzero→SINGLE, ingest_edrogi.py:321-343)로 라벨. (e) SAMPLE 소스: `16bit cal` 폴더 → MasterDark(offset)/CalSet_19008(gain 단일점)/BPM(defect), `panel_id="SAMPLE-EDROGI-16BIT"`·`provenance sample=true`·domain=MEDICAL(ingest_edrogi.py:64-74). (f) 3스테이지 CalibKind = OFFSET/GAIN/DEFECT(foundation §2, `calib_kind_for_stage`). 확정 설계 결정: Build는 골든 CalibSet 빌더를 호출만, Apply는 `run_pipeline`을 고정순서로 구동만 — GUI는 순서·조합·캘리브레이션을 합성하지 않는다.

## Environment / Assumptions

- **본 SPEC은 T-스테이지가 아니다.** `modules/{offset,gain,defect}.py`·`metrics/{defect_map,defect_stats}.py`·`scripts/ingest_edrogi.py`의 CalibSet 빌더·`pipeline/orchestrator.py`는 동결 오라클이며 시그니처·수치·상수 변경이 없다. 본 SPEC은 그 위에 **Calibration 그룹 검증 탭 소비자**를 additive로 얹는다(SPEC-VIEWER-001/XSEAM-002 검증도구 계열 확장).
- **3스테이지의 구별되는 입력(검증됨).** offset은 `CalibSet(OFFSET)` `O_map`(+선택 `sigma_d`/`delta_O`), gain은 `CalibSet(GAIN)` 단일점 `G_map`, defect는 `CalibSet(DEFECT)` 정수 `class_map`을 각각 소비한다(foundation §2). `calib_kind_for_stage("offset"/"gain"/"defect")` = OFFSET/GAIN/DEFECT. UI/어댑터는 스테이지별로 이 구별 입력을 수집해 `calib_map`으로 전달한다.
- **CalibSet 생성 경로(검증됨).** 범용 golden builder는 `metrics.defect_map.build_defect_map(dark_frames, flat_frames, params, *, panel_id, resolution, valid_from, valid_until)`과 lag/noise/scatter builder다. `scripts.ingest_edrogi.build_offset_calibset`, `scripts.ingest_edrogi.build_gain_calibset`, `scripts.ingest_edrogi.build_defect_calibset`은 `SAMPLE_PANEL_ID`·고정 validity/domain/provenance를 쓰는 등록 edrogi 구조 sanity preset이다. 일반 사용자 OFFSET/GAIN/GEOMETRY CalibSet은 strict schema/hash/provenance import로 공급하며 C#이 범용 builder를 만들지 않는다.
- **validate() 소유권(검증됨, D1).** SAMPLE 빌더 3종(`build_offset/gain/defect_calibset`, ingest_edrogi.py:292/317/342)은 생성 직후 `CalibSet.validate()`를 스스로 호출한다. 그러나 정본 스택 빌더 `build_defect_map`은 `validate()` 없이 `CalibSet`을 그대로 반환한다(defect_map.py:112-120). 따라서 BUILD-3 스택 경로에서는 탭이 등록 전 `CalibSet.validate()`(panel_id·resolution·kind·유효기간 스키마 확인)를 **명시적으로** 호출해야 한다 — 이는 신원·스키마 검증일 뿐 DSP가 아니므로 C-09를 위배하지 않는다. 골든이 검증을 자동 수행한다고 오인하면 안 된다(지어내기 금지).
- **조사조건별 flat 선택.** gain의 flat은 조사조건(kV/mA/mAs)마다 다르다. `parse_acquisition_meta`(ingest_edrogi.py:129)가 파일명에서 kv/ma/mas/plate/frame_index를 파싱하되 이는 **표시·정렬·선택용 메타(usage="sample-plumbing")** 이며 알고리즘 파라미터가 아니다(QUARANTINE). Build 탭은 이 메타로 flat 세트를 조건별로 나열·선택한다.
- **고정순서 조합(검증됨).** Apply는 선택된 스테이지를 `CANONICAL_ORDER`의 부분수열 `offset→gain→defect`로만 조합한다. `PipelineDefinition(stages)`가 부분수열을 강제하며 위반 시 `PipelineOrderError`. 미체크 스테이지는 부분집합에서 제외될 뿐 순서가 재배열되지 않는다. GUI는 스테이지를 스스로 정렬하지 않는다(C-11).
- **캘리브레이션 진입 게이트(검증됨, D2).** 선택된 각 스테이지는 해상도·panel_id·kind 일치 CalibSet을 요구하며, 부재/불일치는 `_calibration_gate`(orchestrator.py:178-280)가 `CalibrationError`로 거부한다(SWR-000-5). CALDOM(SPEC-CALDOM-001) 서술자 계층은 추가로 (i) `run_pipeline`에 `domain` 컨텍스트가 주어질 때 CalibSet domain과의 교차도메인 방화벽, (ii) 스테이지 간 상호 domain/beam_quality 일관성을 강제한다(orchestrator.py:253-280). **이 그룹의 domain 취급(검증됨):** SAMPLE CalibSet은 domain=MEDICAL(ingest_edrogi.py:290/315/340)·beam_quality=None으로 스탬프되므로 스테이지 간 상호 domain 일관성은 항상 성립하고 beam_quality 검사는 스킵된다. 탭은 이 그룹을 `domain=None`으로 구동한다(교차도메인 컨텍스트 게이트 미적용 — 이는 CALDOM 인지 그룹 소관). 단, `domain=MEDICAL`을 전달해도 SAMPLE과 일치해 통과하고, `domain=NDT` 등 불일치를 전달하면 교차도메인 방화벽이 `CalibrationError`로 거부한다. GUI는 결여된 캘리브레이션을 기본값으로 대체하거나 합성하지 않는다.
- **표시 도메인.** 이 그룹의 3스테이지는 모두 **raw-DN 도메인**에서 동작한다(offset 감산·gain 곱·defect 보간 모두 원 DN 스케일). 그룹 5(mse/window)처럼 정규화 [0,1] 표시 도메인으로 전환하지 않으므로 저장 시 역스케일링 문제가 없다(단순 clip[0,65535]+rint→uint16).
- **누적 마스크(검증됨).** SATURATION은 offset의 raw-sat와 gain의 16-bit-clamp가 union으로 누적된다(offset.py:113 / gain.py:115). DEFECT는 gain의 불량게인 핸드오프와 defect map 라벨이 union된다(gain.py:112 / defect.py:307). INTERPOLATION은 defect가 실제 보간한 화소에만 설정된다(정상이웃 없으면 미설정, defect.py:340).
- **검증 모드 단일 패스.** 입력 `XFrame.validation_mode=True`면 `run_pipeline`이 스테이지별 출력을 `intermediates`로 부착한다(foundation §5) → 조합 1회로 offset/gain/defect 각 전·후를 추가 실행 없이 스크럽한다.
- **실측 데이터 가용성(SAMPLE·비정본, QUARANTINE 이슈 #29).** 등록 실측으로 **구동 가능 = offset(MasterDark→O_map)·gain(CalSet_19008→단일점 G_map)·defect(외부 BPM.raw→class_map)**. gain 다중노출 anchor는 `NotImplementedError`([B] 대기), defect 완전 morphology 생성은 dark/flat 스택 부재로 불가(#33 정본 대기). SAMPLE 구동은 **sanity(유한·비퇴화·구조 성립)** 확인일 뿐 수치 골든/EV 임계 도출·튜닝이 아니다.
- **환경.** Python은 `uv run`으로만 실행(`uv run pytest`, `uv run lint-imports`). 정확성·재현성이 목적이며 성능 최적화는 목적이 아니다(P2). 문서 언어 ko, 식별자/EARS 키워드/코드 심볼 en.

## Requirements (EARS)

### REQ-XGUI-CALIB-TARGET — 구현 대상 경계

- **REQ-XGUI-CALIB-TARGET-1 (Ubiquitous)** — 시스템은 `apps/xdet-console/` C# WPF 앱을 구현 대상으로 사용해야 하며, `apps/gui/`와 Python 테스트·패널은 계약 및 검증 선례로만 참조해야 한다. WPF는 Python 모듈을 직접 호출하지 않고 `IXdetEngine`/PythonNet seam을 경유해야 한다.

### REQ-XGUI-CALIB-BUILD — 캘리브레이션 생성(Build): OC·GC·BPM 소스 선택→CalibSet (SWR-101/201/301, ingest 빌더 소비)

- **REQ-XGUI-CALIB-BUILD-1 (Event-Driven)** — WHEN 사용자가 등록 edrogi SAMPLE preset의 MasterDark를 선택하면, THEN 탭은 `scripts.ingest_edrogi.build_offset_calibset`을 호출해 고정 SAMPLE `CalibSet(OFFSET)`을 생성·검증하고 `SAMPLE_SANITY`로 표시해야 한다. 외부 사용자 dark에는 이 helper를 사용할 수 없으며 범용 OFFSET은 import 검증 경로를 사용한다.
- **REQ-XGUI-CALIB-BUILD-2 (Event-Driven)** — WHEN 사용자가 등록 edrogi SAMPLE preset의 CalSet flat을 선택하면, THEN 탭은 `scripts.ingest_edrogi.build_gain_calibset`을 호출해 고정 SAMPLE `CalibSet(GAIN)`을 생성·검증하고 `SAMPLE_SANITY`로 표시해야 한다. 조사조건 메타는 표시·정렬에만 사용하고 외부 사용자 flat에는 이 helper를 사용하지 않는다.
- **REQ-XGUI-CALIB-BUILD-3 (Event-Driven)** — WHEN 사용자가 BPM 생성을 요청하고 dark·flat **스택**(각 `defect_min_frames` 이상)과 신원 필드(panel_id·resolution·valid_from·valid_until, keyword-only 필수)를 공급하면, THEN 탭은 `build_defect_map`(→`classify_defects` E2597 7분류 + `classify_morphology`)을 거쳐 `CalibSet(DEFECT)`(정수 `class_map`)을 생성한 뒤 — `build_defect_map`은 `validate()`를 자체 호출하지 않으므로(defect_map.py:112-120) — 탭이 등록 전 `CalibSet.validate()`를 명시적으로 호출·통과시켜 등록해야 한다(noisy 6× median은 고정 [S]이며 Param 아님; validate()는 스키마 확인일 뿐 DSP 아님 — C-09 보존).
- **REQ-XGUI-CALIB-BUILD-4 (Optional)** — WHERE 등록 edrogi SAMPLE preset의 `BPM.raw`를 선택하면, 탭은 `scripts.ingest_edrogi.build_defect_calibset`(nonzero→SINGLE)을 호출할 수 있어야 하며 `SAMPLE_SANITY` 전용이고 스택 기반 morphology builder의 대체가 아님을 표시해야 한다. 외부 BPM은 strict DEFECT CalibSet import 또는 범용 `build_defect_map` 입력으로만 사용한다.
- **REQ-XGUI-CALIB-BUILD-5 (Unwanted)** — IF gain 소스가 다중노출 anchor(`anchor_gains`)를 포함하거나(→`gain.process`의 `NotImplementedError`, gain.py:57-60), BUILD-3 정본 스택 경로의 dark·flat 스택 프레임 수가 `defect_min_frames` 미만이거나(→`classify_defects`의 `MetricReadError`, defect_stats.py:78-83 — 이 게이트는 스택 경로 전용이며 외부 BPM.raw SINGLE 경로(BUILD-4)에는 없음), 소스 프레임이 부재하면(→SAMPLE 빌더의 `CalibSourceMissingError`, ingest_edrogi.py:271-274), THEN 생성은 골든의 해당 명시적 오류로 거부되고 어떤 기본 캘리브레이션도 합성되지 않아야 한다(SWR-000-5).

### REQ-XGUI-CALIB-APPLY — 적용(Apply): 촬영영상 선택→OC/GC/BPM 고정순서 조합 (SWR-000-2, run_pipeline 미러)

- **REQ-XGUI-CALIB-APPLY-1 (Event-Driven)** — WHEN 사용자가 촬영영상을 폴더 또는 파일 리스트로 선택하면, THEN 탭은 상주 폴더 브라우저(foundation §4)로 부모 폴더의 형제 목록·썸네일·이전/다음을 함께 표시하고 선택 프레임을 `load_raw_frame`(headerless 16-bit + `.json` 사이드카)으로 적재해야 한다.
- **REQ-XGUI-CALIB-APPLY-2 (Event-Driven)** — WHEN 사용자가 OC/GC/BPM 부분집합과 각 `CalibSet`·`Params`를 준비하면, THEN WPF는 고정순서 `offset→gain→defect` 부분수열을 `IXdetEngine.RunPipeline(PipelineRunRequest)`에 단일 요청하고 `domain=None`을 전달해야 한다. Python adapter가 `PipelineDefinition`/`run_pipeline`에 위임하며 UI가 순서를 재구현하지 않는다.
- **REQ-XGUI-CALIB-APPLY-3 (State-Driven)** — WHILE 입력 `XFrame.validation_mode=True`인 조합 실행이 진행되는 동안, 탭은 그 단일 패스의 `intermediates`로부터 각 실행 스테이지의 전·후를 추가 실행 없이 스크럽 제공해야 한다.
- **REQ-XGUI-CALIB-APPLY-4 (Unwanted)** — IF 선택 부분집합이 `CANONICAL_ORDER` 부분수열이 아니거나(→`PipelineOrderError`), 선택 스테이지 중 하나라도 해상도·panel_id·kind 일치 `CalibSet`을 결여하거나(→`CalibrationError`), 스테이지 간 domain/beam_quality가 상호 불일치하거나 주어진 `domain` 컨텍스트가 CalibSet domain과 어긋나면(→CALDOM 교차도메인 `CalibrationError`, orchestrator.py:253-280), THEN 실행은 오케스트레이터의 명시적 오류로 프레임 처리 전에 거부되고 무단 기본값 대체가 없어야 한다(SWR-000-2 + SWR-000-5 + SPEC-CALDOM-001 보존).

### REQ-XGUI-CALIB-VIEW — 그룹 고유 뷰어: 이미지 before/after/diff + 누적 마스크 + probe (C-01~C-07)

- **REQ-XGUI-CALIB-VIEW-1 (Ubiquitous)** — 탭은 각 스테이지·조합 결과를 raw-DN 도메인 이미지의 before/after/diff로 표시해야 하며(그룹 7 NDT의 리포트·그룹 8 Metrics의 곡선 플롯과 달리 **이미지 처리 뷰**), 모든 수치는 골든 엔진 산출을 그대로 렌더링해야 한다(C-09, 자체 계산 0).
- **REQ-XGUI-CALIB-VIEW-2 (Ubiquitous)** — 탭은 DEFECT·INTERPOLATION·SATURATION 마스크 오버레이(토글·공유 불투명도)와 float32 정확값 픽셀 probe·W/L·blink를 제공해야 하며, offset raw-sat와 gain 16-bit-clamp가 누적된 SATURATION, gain 핸드오프와 map 라벨이 union된 DEFECT, defect가 실제 보간한 화소의 INTERPOLATION을 구별해 확인 가능해야 한다.
- **REQ-XGUI-CALIB-VIEW-3 (State-Driven)** — WHILE defect 결과를 표시하는 동안, 정상이웃 부재로 보간되지 않은 DEFECT 화소(INTERPOLATION 미설정, 값 유지)가 보간된 화소와 시각적으로 구별되어야 한다(SWR-602 무-조작 원칙 가시화).

### REQ-XGUI-CALIB-SAVE — 저장: `<name>_result.raw` + 사이드카 (C-20)

- **REQ-XGUI-CALIB-SAVE-1 (Event-Driven)** — WHEN 사용자가 결과 저장을 요청하면, THEN 탭은 `<name>_result.raw`, `xdet.frame-artifact/1.0` sidecar, `<name>_result_mask.raw`(`uint8` bitfield), `xdet.run-manifest/1.0` `<name>_run_manifest.json`을 저장해야 한다. Pixel과 mask 각각 bit-exact round-trip을 검증하고 manifest에 input/calib/params/output hash를 기록한다.
- **REQ-XGUI-CALIB-SAVE-2 (Unwanted)** — IF 저장 대상 경로가 `data/` 하위이면, THEN C# export choke point가 실행 전에 typed validation error로 거부해야 한다. WPF/adapter는 Python `guard_output_path`를 직접 호출하지 않는다(C-20).

### REQ-XGUI-CALIB-GUARD — 경계: DSP 0 · 조합/캘리브레이션 재구현 금지 (C-09/C-11)

- **REQ-XGUI-CALIB-GUARD-1 (Unwanted)** — IF C# UI 또는 어댑터가 offset/gain/defect 출력을 스스로 계산하거나, 스테이지를 스스로 정렬·조합하거나, 결여된 스테이지별 캘리브레이션(O_map/G_map/class_map)을 합성하거나, 등록 실측(SAMPLE) 구동 결과로 수치 golden/튜닝을 도출하면, THEN 이는 인수 실패다. 런타임 강제 기구가 아니라 **정적 부재로 검증**한다 — `common/`·`modules/`·`metrics/`·`pipeline/` 무변경(git diff 없음) + C# 어댑터에 DSP 산술·스테이지 정렬/조합·캘리브레이션 합성 코드 부재(DoD 6, XSEAM-002 Scenario 6 미러). 모든 DSP는 골든, 조합·순서 권한은 오케스트레이터, SAMPLE은 sanity 전용(QUARANTINE).

### REQ-XCAL-COVERAGE — 캘리브레이션 전수 실행

- **REQ-XCAL-COVERAGE-1 (Ubiquitous)** — Calibration 탭은 `metrics.defect_map.build_defect_map`, `classify_morphology`, `metrics.lag_irf.fit_lag_irf`, `metrics.noise_model.fit_noise_model`, `metrics.scatter_kernel.build_scatter_kernel`, `fit_scatter_kernel_from_samples`를 catalog FeatureId와 typed CALIBRATION_BUILD DTO로 노출해야 한다.
- **REQ-XCAL-COVERAGE-2 (Event-Driven)** — WHEN 사용자가 dark/flat stack, StepResponse series, DoseLevel series, thickness/kV 또는 primary/scatter sample을 공급하면 THEN engine은 해당 실제 builder를 호출하고 populated CalibSet·source hash·builder args·fit diagnostics를 반환해야 한다.
- **REQ-XCAL-COVERAGE-3 (Event-Driven)** — WHEN 사용자가 offset/gain/geometry CalibSet을 공급하면 THEN 탭은 `CalibSet.load/validate`로 schema·kind·resolution·panel/domain/validity/hash를 검증해 import해야 한다. 현재 골든에 없는 raw-to-map builder를 C#에서 만들지 않아야 한다.
- **REQ-XCAL-COVERAGE-4 (Event-Driven)** — WHEN 등록세트 밖 strict calibration input을 실행하면 THEN builder/import를 허용하고 결과를 승인 전 `USER_SUPPLIED_UNVERIFIED`로 기록해야 한다.
- **REQ-XCAL-COVERAGE-5 (Unwanted)** — IF builder 결과가 빈/placeholder payload이거나 UI가 CalibSet data를 합성하면 THEN apply와 export를 거부해야 한다.

## Exclusions (What NOT to Build)

- **골든 알고리즘 변경 없음** — `modules/{offset,gain,defect}.py`·`metrics/{defect_map,defect_stats}.py`·`scripts/ingest_edrogi.py` CalibSet 빌더·`pipeline/orchestrator.py`는 동결 오라클로 편집하지 않는다. 탭은 이들을 읽기-실행 전용으로 소비한다.
- **캘리브레이션·조합·DSP 재구현 없음** — dark 감산·flat 정규화·불량화소 보간·E2597 분류·morphology·고정순서 조합은 전부 골든에 남는다. GUI는 소스 선택·표시·저장만 한다.
- **다중노출 gain(anchor_gains) 없음** — 다중노출 piecewise-linear gain(SWR-202)은 골든에서 `NotImplementedError`로 이연([B], #33 대기)이며 본 탭도 단일점 `G_map`만 구동한다.
- **SAMPLE 스택 기반 BPM 완전 생성 없음** — 등록 실측은 단일 MasterDark/BPM만 있어 `build_defect_map`(dark/flat 스택 요구)의 완전 morphology 생성이 불가하다. SAMPLE BPM은 외부 `BPM.raw`→SINGLE 라벨 sanity 전용이며, 정본 morphology 생성은 정본 지침세트(#33) 도착 후 별건이다.
- **정본 수치 검증 없음(QUARANTINE)** — SAMPLE(에드로지) 구동은 sanity(유한·비퇴화·구조) 확인이며 수치 golden/EV 임계 도출·튜닝·적합에 쓰지 않는다(이슈 #29). panel_id=`SAMPLE-EDROGI-16BIT`·provenance sample=true 비정본성 유지.
- **표시 도메인 역스케일 없음** — 이 그룹은 raw-DN 도메인에서만 동작하므로 그룹 5(mse/window)의 정규화 [0,1]↔raw-DN 역스케일 문제를 다루지 않는다(foundation §6 미확인 항목은 그룹 5 소관).
- **다른 그룹 스테이지 없음** — 본 탭은 offset·gain·defect 3스테이지만 다룬다. lag/line_noise/saturation/geometry/denoise/mse/window/grid/virtual_grid 및 NDT/Metrics 지표 엔진은 각 그룹 SPEC 소관이다.
- **C++ 엔진 이식·성능 최적화·Gen 2 없음** — C++ 네이티브 엔진·마샬링 최적화·DL/ADR·배포는 범위 밖(SPEC-XSEAM 계열 승계).

## 확정 결정 (v0.5.1)

1. 등록 SAMPLE sanity는 offset→gain→defect 전체 조합까지 실행한다. 단, 유한성·형상·비퇴화·실행 성공만 확인하며 수치 골든으로 사용하지 않는다.
2. 스택 기반 BPM의 defect 임계값은 Calibration 탭 안의 전용 고급 하위패널에 배치하고, 외부 BPM 입력 경로에서는 숨긴다.
3. Apply fidelity는 최종 프레임뿐 아니라 validation mode의 offset/gain/defect 중간 프레임까지 스테이지별로 게이트한다.
4. 중앙 TC 레지스트리는 G1 블록 XDET-TC-096~103이며 전체 번호를 builder/import/apply/fidelity/evidence에 사용한다.

## v0.5.1 public operation closure

| Python EntryPoint | GUI 노출 | TC |
|---|---|---|
| `modules.offset.process` | Apply Offset action | 101~103 |
| `modules.gain.process` | Apply Gain action | 101~103 |
| `modules.defect.process` | Apply Defect action | 101~103 |
| `metrics.defect_map.build_defect_map` | Build Defect CalibSet action | 096~097 |
| `metrics.defect_map.classify_morphology` | defect builder diagnostic/sub-command | 097 |
| `metrics.defect_stats.classify_defects` | defect evidence diagnostic/action | 097 |
| `metrics.lag_irf.fit_lag_irf` | Build Lag CalibSet action | 098 |
| `metrics.noise_model.fit_noise_model` | Build Noise CalibSet action | 099 |
| `metrics.scatter_kernel.build_scatter_kernel` | Build Scatter CalibSet action | 100 |
| `metrics.scatter_kernel.fit_scatter_kernel_from_samples` | Fit Scatter CalibSet action | 100 |
| `scripts.ingest_edrogi.build_offset_calibset` | registered SAMPLE Offset preset | 096 |
| `scripts.ingest_edrogi.build_gain_calibset` | registered SAMPLE Gain preset | 096 |
| `scripts.ingest_edrogi.build_defect_calibset` | registered SAMPLE Defect preset | 096 |

각 행은 실제 qualified EntryPoint 호출 trace, typed 결과/오류, 최소 하나의 Contract 시험을 가져야 한다. offset/gain/geometry map builder는 golden에 없으므로 import schema 검증으로만 제공한다.
