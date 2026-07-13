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
labels: [xgui, gui-redesign, verification-gui, calibration, offset-gain-defect, golden-frozen, acceptance]
---

# SPEC-XGUI-CALIB — 인수 기준 (acceptance)

> 본 인수기준의 모든 EARS ID·중앙 TC·필수 증거 연결은 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따른다. `baseline-control.md`의 G0와 사용자 승인 전에는 이 체크리스트를 구현 완료 증거로 사용할 수 없으며 모든 TC는 `PLANNED` 상태를 유지한다.

> **구현 대상:** `apps/xdet-console/` C# WPF 앱. `apps/gui/`와 Python 테스트는 계약·검증 선례이며 구현 대상이 아니다.
Calibration 그룹(offset·gain·defect) 검증 탭의 E2E 워크플로 **열기(상주 폴더 브라우저) → Build/Import(CalibSet 생성·검증) → Apply(고정순서 조합) → 저장(`<name>_result.raw`) → 검증**을 Given-When-Then으로 규정한다. 모든 기준은 관측 가능해야 한다: 모든 공개 builder 호출·CalibSet `validate()` / `run_pipeline` 실제 구동 / `common.equivalence.diff_frames` delta 정확히 0(트랜스포트, ±1 LSB는 P2 범위) / `load_raw_frame` 왕복 / 명시적 typed 오류 / golden 파일 무변경. 각 시나리오는 **XDET-TC-096~103**에 귀속한다. 등록 실측(에드로지 SAMPLE) 구동은 **QUARANTINE(이슈 #29)** — sanity만 단언하고 수치 golden/EV 임계 도출·튜닝·적합은 하지 않는다. 공유 사실은 [SPEC-XGUI-MASTER](../SPEC-XGUI-MASTER/foundation.md), 상위 조합 선례는 [SPEC-XSEAM-002](../SPEC-XSEAM-002/acceptance.md)를 따른다.

**데이터 가용성 라벨(그룹 1):** offset(MasterDark→`O_map`)·gain(CalSet_19008→단일점 `G_map`)·defect(외부 `BPM.raw`→SINGLE `class_map`)는 **등록 실측 실행가능(SAMPLE sanity)**. gain 다중노출 anchor(`anchor_gains`)와 defect 정본 스택 morphology 생성(dark/flat 스택 요구)은 **#33 정본 지침세트 대기**(합성/placeholder 또는 골든 명시 오류로 표면화, 수치 튜닝 금지).

## Scenarios (Given-When-Then)

### Scenario 1 — Build: OC/GC/BPM CalibSet 생성 + validate() 소유권 (XDET-TC-096, REQ-XGUI-CALIB-BUILD-1~5)
- **Given** 등록 edrogi SAMPLE `16bit cal` 폴더(MasterDark / CalSet_19008 / BPM)와 저장소 `uv` 환경이 있고,
- **When** 사용자가 Build 하위탭에서 offset 소스(MasterDark)·gain 소스(조사조건별 CalSet_19008 flat)·defect 소스(외부 `BPM.raw`)를 각각 선택해 골든 빌더를 호출하면,
- **Then**
  - `scripts.ingest_edrogi.build_offset_calibset(MasterDark)`→고정 SAMPLE `CalibSet(OFFSET)` `O_map`,
  - `scripts.ingest_edrogi.build_gain_calibset(flat)`→고정 SAMPLE `CalibSet(GAIN)` `G_map = mean/clip(flat,1,None)`,
  - `scripts.ingest_edrogi.build_defect_calibset(BPM)`→고정 SAMPLE `CalibSet(DEFECT)` 정수 `class_map`
  가 각각 `kind`·`resolution`·`panel_id=SAMPLE-EDROGI-16BIT`·`domain=MEDICAL`·`provenance sample=true`와 함께 등록 목록에 표시되어야 한다.
  - **정본 스택 경로(D1 검증됨):** 대신 dark·flat 스택으로 `build_defect_map(dark_frames, flat_frames, params, *, panel_id, resolution, valid_from, valid_until)`을 쓰는 경우, 탭이 keyword-only 필수 신원 필드를 공급하고 — `build_defect_map`은 `validate()`를 자체 호출하지 않으므로(defect_map.py:112-120) — 반환 CalibSet에 **탭이 명시적으로** `CalibSet.validate()`를 호출·통과시킨 뒤 등록해야 한다.
  - 세 preset helper는 등록 edrogi에서만 enabled이고 항상 `SAMPLE_SANITY`다. 일반 사용자 OFFSET/GAIN/GEOMETRY CalibSet은 strict import 검증을 사용한다. GUI는 DSP 0(C-09)이며 SAMPLE 구동은 유한·비퇴화 sanity만 단언한다.

### Scenario 2 — Open(상주 폴더 브라우저) + 단일 스테이지 Apply + CompareDisplay (XDET-TC-097, REQ-XGUI-CALIB-APPLY-1/2 · VIEW-1/2)
- **Given** 등록 edrogi 촬영영상(headerless 16-bit `.raw` + `.json`({resolution,dtype}) 사이드카)과 등록된 `CalibSet(OFFSET)`이 있고,
- **When** 사용자가 입력을 연 뒤 OC만 켜고 WPF가 stages=["offset"], domain=None인 `PipelineRunRequest`를 `IXdetEngine.RunPipeline`에 전달하면,
- **Then** PythonNet adapter가 `PipelineDefinition`/`run_pipeline`에 위임하고, UI는 before/after/diff + SATURATION mask + probe + W/L + blink을 표시해야 한다. 출력 통계는 유한·비퇴화이고 모든 수치는 골든 산출이어야 한다(C-09/C-11).

### Scenario 3 — VIEW: 누적 마스크 구별 + defect 무보간 화소 가시화 (XDET-TC-098, REQ-XGUI-CALIB-VIEW-2/3)
- **Given** offset+gain+defect 조합 결과 XFrame(누적 마스크 스택 포함)이 표시되는 상태에서,
- **When** 사용자가 DEFECT/INTERPOLATION/SATURATION 마스크 오버레이를 토글하고 defect 결과를 스크럽하면,
- **Then**
  - SATURATION은 offset raw-sat(offset.py:113)와 gain 16-bit-clamp(gain.py:115)가 **union**으로 누적된 것으로,
  - DEFECT는 gain 불량게인 핸드오프(gain.py:112)와 defect map 라벨(defect.py:307)이 **union**된 것으로,
  - INTERPOLATION은 defect가 **실제 보간한** 화소에만 설정된 것으로
  각각 구별해 확인 가능해야 한다. 특히 정상이웃 부재로 보간되지 않은 DEFECT 화소(INTERPOLATION 미설정·값 유지, defect.py:338-340)가 보간된 화소와 **시각적으로 구별**되어야 한다(SWR-602 무-조작 원칙 가시화). 마스크 소스는 골든 XFrame mask stack이며 GUI는 마스크를 스스로 계산하지 않는다(C-09).

### Scenario 4 — 조합 Apply(부분수열) + 검증 모드 중간 프레임 스크럽 (XDET-TC-099, REQ-XGUI-CALIB-APPLY-2/3) — **load-bearing**
- **Given** offset/gain/defect가 각자 해상도·panel_id 일치 `CalibSet`·`Params`를 지니고 입력 XFrame이 `validation_mode=True`인 상태에서,
- **When** 사용자가 OC/GC/BPM을 켜고 WPF가 `IXdetEngine.RunPipeline`에 고정순서 stages와 typed calib/params를 **한 번** 전달하면,
- **Then** 어댑터가 그 부분수열에 대해 `run_pipeline`을 한 번 구동해 조합 출력을 내고, 그 단일 패스의 `XFrame.intermediates`로부터 각 실행 스테이지의 전·후를 **추가 실행 없이** 스크럽 제공해야 한다(미체크 스테이지는 순서 재배열 없이 스킵). 조합 최종 XFrame을 Python 골든 직접 `run_pipeline` 출력과 `common.equivalence.diff_frames`로 비교했을 때 `structurally_equal`가 True이고 `max_pixel_abs_diff`가 XDET-TC-021 허용오차 이내(이 그룹은 순수 소비 경로이므로 정확히 0/bit-동일 기대)여야 한다.

### Scenario 5 — Save: `<name>_result.raw` + 사이드카 + 왕복 + C-20 게이트 (XDET-TC-100, REQ-XGUI-CALIB-SAVE-1/2)
- **Given** 조합 결과 XFrame(raw-DN 도메인)과 사용자 지정 출력 폴더가 있고,
- **When** 사용자가 처리 결과 저장을 요청하면,
- **Then** 탭이 `xdet.frame-artifact/1.0` raw/sidecar, `uint8` mask bitfield, `xdet.run-manifest/1.0`을 사용자 폴더에 기록하고, pixel/mask 각각의 bit-exact round-trip과 input/calib/params/output hash를 검증해야 한다. `data/` 하위는 C# export choke point가 typed error로 거부한다.

### Scenario 6 — 거부·권한 가드 + 정적 부재 (XDET-TC-101, REQ-XGUI-CALIB-APPLY-4 · GUARD-1)
- **Given** 조합 진입점이 임의 스테이지 집합·`CalibSet` 맵·`domain` 컨텍스트를 받고 C# 어댑터·UI가 조합을 구동하는 상태에서,
- **When** (a) `CANONICAL_ORDER` 부분수열이 아닌 집합(예: 역순 `("gain","offset")`)을 요청하거나, (b) 선택 스테이지 중 하나의 `CalibSet`이 부재하거나 해상도·panel_id·kind가 불일치하거나, (c) `domain=NDT` 등 SAMPLE의 MEDICAL과 어긋나는 컨텍스트를 전달하거나, (d) 저장 경로를 `data/` 하위로 지정하거나, (e) C# 측 코드 경로·의존방향·쓰기대상을 검사하면,
- **Then**
  - (a)는 `PipelineDefinition.__post_init__`의 `PipelineOrderError`로,
  - (b)는 `_calibration_gate`의 `CalibrationError`로,
  - (c)는 CALDOM 교차도메인 방화벽의 `CalibrationError`(orchestrator.py:253-263)로 프레임 처리 **이전**에 거부되고 어떤 기본 캘리브레이션도 대체되지 않아야 하며(SWR-000-2/-5 + SPEC-CALDOM-001),
  - (d)는 C# export choke point가 typed validation error로 거부하고,
  - (e) 모든 스테이지 출력·조합이 실제 Python 골든에서 발생하고 C# 측에 DSP 산술·스테이지 정렬/조합·캘리브레이션 합성이 **없음**이 **정적으로** 확인(`common/`·`modules/`·`metrics/`·`pipeline/` 무변경(git diff 없음))되어야 한다. SAMPLE 구동 결과는 정본 수치/EV 도출·튜닝에 쓰지 않는다(QUARANTINE).

- **Then** 오류형·누락 필드·feature/stage가 typed error로 표시되고 결과·artifact·최근 성공 상태가 변경되지 않아야 한다.

### Scenario 7 — 공개 calibration builder 전수 도달성 (XDET-TC-102, REQ-XCAL-COVERAGE-1~3)

- **Given** defect stack, step-response series, dose series, thickness/kV 또는 primary/scatter sample과 각 builder의 필수 metadata가 준비돼 있을 때,
- **When** 사용자가 defect map/morphology, lag IRF, noise model, parametric scatter, sample-fit scatter를 각각 실행하면,
- **Then** catalog의 실제 6개 builder EntryPoint가 호출되고 populated CalibSet·source hash·builder args·fit diagnostics가 반환되며 `validate()` 뒤 해당 처리 stage가 소비할 수 있어야 한다.

### Scenario 8 — strict import·사용자 입력·증거 등급 (XDET-TC-103, REQ-XGUI-CALIB-TARGET-1, REQ-XCAL-COVERAGE-4/5)

- **Given** 등록세트 밖의 사용자 CalibSet/input-set이 schema·kind·resolution·panel·domain·validity·hash를 만족할 때,
- **When** import 후 apply와 저장을 실행하면,
- **Then** 등록 fixture 부재로 차단하지 않고 결과와 manifest를 `USER_SUPPLIED_UNVERIFIED`로 표시해야 한다.
- **Given** payload가 비었거나 schema/hash가 맞지 않거나 UI/C#이 map을 합성했을 때,
- **When** apply 또는 export를 요청하면,
- **Then** `CALIBRATION_INVALID`로 거부하고 silent default·증거 승격·artifact 생성을 모두 금지해야 한다.

### Scenario — 전체 calibration builder와 import 도달성 (XDET-TC-096~103)

- **Given** defect dark/flat, Lag StepResponse, Noise DoseLevel, scatter thickness/kV와 primary/scatter sample, 외부 offset/gain/geometry CalibSet이 있고,
- **When** 사용자가 각각 build 또는 import를 실행하면,
- **Then** 6개 실제 builder EntryPoint 또는 `CalibSet.load/validate`가 호출되고 populated payload·source hash·fit diagnostics가 표시되며, 결과를 해당 처리 stage에 적용해 golden-direct와 동일해야 한다. 빈 placeholder, C# 합성 map, 미검증 kind/resolution/panel/domain은 거부돼야 한다.

## Edge Cases

- **비-부분수열 조합은 FAIL (APPLY-4)** — 역순·미지·중복 스테이지 집합을 조합 진입점에 넘기면 `PipelineOrderError`로 거부돼야 한다(음성 대조: 역순 `("gain","offset")` 주입 시 실제 예외 발생 확인, 통과로 침묵 금지).
- **결여/불일치 CalibSet은 FAIL·무단 대체 없음 (APPLY-4)** — 선택 스테이지의 `CalibSet`이 없거나 해상도·panel_id·kind 불일치이면 `CalibrationError`로 프레임 처리 전에 거부되고 기본값이 대체되면 안 된다(SWR-000-5; 음성 대조: 특정 스테이지 CalibSet 제거 시 실제 거부 확인).
- **교차도메인 오용은 FAIL (APPLY-4, D2)** — SAMPLE은 domain=MEDICAL로 스탬프되므로 `domain=NDT` 컨텍스트를 전달하면 CALDOM 교차도메인 방화벽이 `CalibrationError`를 던져야 한다(음성 대조: NDT 컨텍스트 주입 시 실제 거부; `domain=None`/`MEDICAL`은 통과).
- **`build_defect_map` validate 누락 함정 (BUILD-3, D1)** — 정본 스택 경로에서 탭이 `CalibSet.validate()`를 생략하면 신원(panel_id/resolution/kind/유효기간)이 검증되지 않은 CalibSet이 등록될 수 있다. BUILD-3은 탭의 명시적 `validate()`를 요구하며, 이를 골든 자동 수행으로 오인하면 안 된다(SAMPLE 빌더 3종만 자체 validate).
- **`data/` 저장은 FAIL (SAVE-2)** — 결과를 골든 fixture 트리(`data/`)에 쓰려는 시도는 C# export choke point가 거부해야 한다.
- **gain 다중노출 / defect 스택 부족은 골든 명시 오류로 표면화 (BUILD-5)** — `anchor_gains` 포함 gain 소스는 `NotImplementedError`, 정본 스택 경로의 dark·flat 프레임 수 < `defect_min_frames`는 `classify_defects`의 `MetricReadError`(스택 경로 전용, 외부 BPM SINGLE 경로엔 없음), 소스 부재는 `CalibSourceMissingError`로 거부돼야 한다 — GUI가 합성으로 우회하면 안 된다(SWR-000-5).
- **SAMPLE 조합 수치 오용은 FAIL (QUARANTINE, 이슈 #29)** — 등록 SAMPLE 조합 구동 결과를 정본 수치/EV 임계 도출·튜닝·적합에 사용하면 인수 실패 — sanity(유한·비퇴화·구조)만 허용, 정본 수치 검증은 정본 지침세트(#33) 도착 후 별건.
- **저장 왕복의 라운딩 경계 (SAVE-1)** — float32 → `rint` → uint16 변환은 일반적으로 무손실이 아니나, raw-DN 정수 격자에 놓인 결과값은 왕복 시 정확 일치해야 한다(표시 정규화 [0,1] 도메인의 역스케일은 이 그룹 범위 밖 — 그룹 5 Enhancement 소관).

## Definition of Done (체크리스트)

- [ ] Build 하위탭이 offset(MasterDark)·gain(CalSet_19008)·defect(외부 BPM) 소스에서 골든 빌더 경유로 `CalibSet(OFFSET/GAIN/DEFECT)`를 생성·등록 — SAMPLE 빌더는 자체 `validate()`, 정본 스택 경로 `build_defect_map`은 탭이 신원 필드 공급 + 명시적 `CalibSet.validate()`(XDET-TC-096, BUILD-1~4, D1/D4)
- [ ] Build reject: `anchor_gains`→`NotImplementedError`, 스택 프레임 수 < `defect_min_frames`→`MetricReadError`(스택 경로 전용), 소스 부재→`CalibSourceMissingError`, 무단 기본값 대체 없음 (XDET-TC-096, BUILD-5, D3)
- [ ] 상주 폴더 브라우저(부모 폴더 형제 목록 + 가상화 썸네일 + 이전/다음)로 열기 + `load_raw_frame` 적재 + 단일 스테이지 `run_pipeline`(`domain=None`) 구동 + `CompareDisplay` before/after/diff·마스크·probe·W/L·blink 표시(수치는 골든 산출) (XDET-TC-097, APPLY-1/2, VIEW-1/2)
- [ ] 누적 마스크 구별(SATURATION union / DEFECT union / INTERPOLATION 실보간 화소) + 무보간 DEFECT 화소 시각 구별(SWR-602 가시화) (XDET-TC-098, VIEW-2/3)
- [ ] 고정순서 부분수열 `("offset","gain","defect")` 단일 `run_pipeline` 조합 + `validation_mode` `intermediates`로 추가 실행 없이 스테이지별 전/후 스크럽 (XDET-TC-099, APPLY-2/3)
- [ ] 조합 fidelity: 조합 최종 XFrame vs 골든 직접 `run_pipeline`을 `diff_frames`로 `structurally_equal` True + `max_pixel_abs_diff` 정확히 0(±1 LSB는 P2 예약) (XDET-TC-099, APPLY-2)
- [ ] 저장: frame artifact + mask artifact + run manifest, pixel/mask bit-exact round-trip 및 hash 일치 (XDET-TC-100, SAVE-1)
- [ ] C-20 게이트: C# export choke point가 `data/` 하위를 typed error로 거부하고 사용자 지정 폴더만 허용 (XDET-TC-100, SAVE-2)
- [ ] 거부 가드: 비-부분수열 `PipelineOrderError` + 결여/불일치 CalibSet `CalibrationError` + 교차도메인(domain=NDT vs MEDICAL) `CalibrationError`, 무단 대체 없음(음성 대조 포함) (XDET-TC-101, APPLY-4, D2)
- [ ] 정적 부재: C# 어댑터에 DSP 산술·스테이지 정렬/조합·캘리브레이션 합성 코드 부재 + `common/`·`modules/`·`metrics/`·`pipeline/` 무변경(git diff 없음) (XDET-TC-101, GUARD-1)
- [ ] `uv run pytest` 무회귀 green + `uv run lint-imports` green·불변 (골든 FROZEN 무변경)
- [ ] 등록 edrogi SAMPLE 구동은 sanity(유한·비퇴화·구조)만 단언, 수치 golden/EV 도출·튜닝 없음(QUARANTINE, 이슈 #29). gain 다중노출·defect 정본 스택 morphology는 #33 대기로 라벨
- [ ] 골든 알고리즘(`modules/`·`metrics/`·`pipeline/`·`common/`) 무변경 — 탭은 읽기-실행 전용 소비

## 판정 원칙 (측정=판정 분리)

- 조합 fidelity 허용오차(XDET-TC-021: 정수 bit-동일 / float ±1 LSB)는 CLAUDE.md T10 동일성 프레임에서 인용하며 탭에 하드코딩하지 않는다. 이 그룹은 순수 소비 경로이므로 관측 delta는 정확히 0(bit-동일) 기대다.
- 조합/순서 권한은 `PipelineDefinition`(오케스트레이터), 캘리브레이션 admission은 `_calibration_gate`, DSP는 골든 모듈에 있으며 GUI/어댑터는 판정하지 않고 결과만 표시한다(측정=판정 분리; C-09/C-11).
- **validate() 소유권(D1):** SAMPLE 빌더는 자체 `validate()`, 정본 스택 `build_defect_map`은 탭이 명시적 `validate()`. 이는 신원·스키마 검증(비-DSP)이므로 C-09를 위배하지 않는다.
- SAMPLE 실측 수치는 비정본(QUARANTINE) — 인수의 load-bearing 기준은 골든 대비 **동일성(delta 0)**·**명시 거부**·**왕복 성립**·**무회귀**이지 SAMPLE 절대 수치가 아니다.

## TC 배정

- MASTER 중앙 레지스트리의 Calibration 블록은 `XDET-TC-096~103`이다.
- 본 acceptance는 `XDET-TC-096~103` 전체를 사용한다. builder/import/apply/fidelity/evidence의 세부 대응은 spec의 public operation closure와 중앙 TestSpec을 따른다.
- 알고리즘 core TC와 GUI-E2E TC는 서로 다른 증거 계층으로 관리한다.

## 요구사항-TC 추적

| 요구사항 | 중앙 TC |
|---|---|
| `REQ-XGUI-CALIB-TARGET-{1}` | 096~103 |
| `REQ-XGUI-CALIB-BUILD-{1..5}` | 096, 102 |
| `REQ-XGUI-CALIB-APPLY-{1..4}` | 097, 099, 101, 103 |
| `REQ-XGUI-CALIB-VIEW-{1..3}` | 097, 098 |
| `REQ-XGUI-CALIB-SAVE-{1..2}` | 100, 103 |
| `REQ-XGUI-CALIB-GUARD-1` | 101, 103 |
| `REQ-XCAL-COVERAGE-{1..5}` | 102, 103 |

각 범위는 모든 개별 ID로 전개한다. 필수 증거 필드는 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따르며 누락·중복·orphan은 인수 실패다.

## v0.5.1 operation closure acceptance

- **Given** dark/flat/step-response/dose/scatter input-set과 import 대상 CalibSet이 준비되고,
- **When** 사용자가 `modules.offset.process`, `modules.gain.process`, `modules.defect.process`, `metrics.defect_map.build_defect_map`, `metrics.defect_map.classify_morphology`, `metrics.defect_stats.classify_defects`, `metrics.lag_irf.fit_lag_irf`, `metrics.noise_model.fit_noise_model`, `metrics.scatter_kernel.build_scatter_kernel`, `metrics.scatter_kernel.fit_scatter_kernel_from_samples`에 대응하는 action 또는 등록 preset 전용 `scripts.ingest_edrogi.build_offset_calibset`, `scripts.ingest_edrogi.build_gain_calibset`, `scripts.ingest_edrogi.build_defect_calibset`을 실행하면,
- **Then** 각 qualified EntryPoint가 실제 호출되고 typed 결과 또는 typed 오류가 표시되며 builder 결과는 `CalibSet.validate()`·hash·provenance를 통과한 뒤에만 Apply에 사용할 수 있어야 한다. 각 EntryPoint는 XDET-TC-096~103 중 하나의 자동화 test name에 연결되어야 한다.
