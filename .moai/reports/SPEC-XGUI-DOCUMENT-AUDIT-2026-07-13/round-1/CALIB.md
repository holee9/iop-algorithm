# SPEC-XGUI-CALIB 적대적 교차검증 — Round 1/5

Verdict: **FAIL** (major 1 + minor 3). D1(골든-사실 오기)만 필수 수정, 나머지는 정확도 향상 권장.
Auditor: plan-auditor. 대조검증 방식: 골든 소스 Grep/Read 직접 대조(G-1). 저자 추론 컨텍스트 미참조.

## 검증 완료(대조 통과) 사실 — 지어내기 없음 확인

| SPEC 주장 | 골든 대조 | 판정 |
|---|---|---|
| `offset.REQUIRED_PARAMS=("raw_saturation_threshold",)` :36 | offset.py:36 | ✓ |
| offset raw-sat 감산 **전** 검출·SATURATION 누적 :97-113 | offset.py:97-99/111-113 | ✓ |
| `K_SIGMA_D`(sigma_d) 공급 시 noise σ 초기화 :119-121 | offset.py:29/119-120 | ✓ |
| offset 선택 입력 `delta_O` | offset.py:30 `K_DELTA_O="delta_O"` :67-71 | ✓ |
| `gain.REQUIRED_PARAMS=("gain_min","gain_max")` :39 | gain.py:39 | ✓ |
| gain 범위밖 미적용+DEFECT 핸드오프, over→SATURATION | gain.py:96/112/115 | ✓ |
| `anchor_gains`→`NotImplementedError`(다중노출 [B]) | gain.py:31/57-60 | ✓ |
| `G_map=mean/clip(flat,1,None)` 단일점 | ingest_edrogi.py:305-306 (정확 일치) | ✓ |
| `defect.REQUIRED_PARAMS=("defect_cmax_pixels",)` :54 | defect.py:47/54 | ✓ |
| defect_line_min 기본 8·defect_line_max_width 기본 1 (선택) | defect.py:292/294 | ✓ |
| C_max 초과→`DefectMapRefused`; 정상이웃 없으면 INTERPOLATION 미설정 | defect.py:77/126, :338-340 | ✓ |
| `classify_defects` E2597 7분류 + 6×median noisy 고정 [S] | defect_stats.py:40-50/29/107 | ✓ |
| 7 [P] 임계 param 명 (min_frames/over/under/dead_gain_frac/nonuniform_frac/lag_frac/unstable_frac) | defect_stats.py:31-37 | ✓ |
| `build_offset/gain/defect_calibset`(빌더 3종) | ingest_edrogi.py:278/296/321 | ✓ |
| `build_defect_calibset` nonzero→SINGLE 라벨 | ingest_edrogi.py:331 | ✓ |
| `parse_acquisition_meta`(표시·정렬용 메타) | ingest_edrogi.py:129 | ✓ |
| SAMPLE panel_id=`SAMPLE-EDROGI-16BIT`·domain=MEDICAL·sample=true | ingest_edrogi.py:64/74 | ✓ |
| `CANONICAL_ORDER`/`PipelineDefinition`(부분수열 강제)/`PipelineOrderError` | orchestrator.py:30/93/105-116 | ✓ |
| `_calibration_gate`→`CalibrationError` | orchestrator.py:84/178 | ✓ |
| validation_mode→`intermediates` 부착(단일패스) | orchestrator.py:334-341 | ✓ |
| `guard_output_path` 단일 choke point(C-20) | apps/gui/io_panel.py:27 (ANCHOR) | ✓ |
| `CompareDisplay`(before/after/diff·mask·probe·W/L·blink) | apps/gui/app.py:90 | ✓ |
| SAVE-1 사이드카 `{"resolution":[rows,cols],"dtype":"uint16"}` | common/io.py:10-14 (load_raw_frame 스키마 정확 일치, 왕복 가능) | ✓ |
| frontmatter 필드 SPEC-XSEAM-002 미러 | XSEAM-002 spec.md:1-11 (id/version/status/created/updated/author/priority/issue_number/labels 동일) | ✓ |
| EARS 패턴 준수 | BUILD-1~5/APPLY-1~4/VIEW-1~3/SAVE-1~2/GUARD-1 전부 Event/State/Optional/Unwanted/Ubiquitous 적격, REQ 번호 그룹내 결번·중복 없음 | ✓ |

불변 제약 상속(G-1~G-9) 정합: C-09/C-11/C-20/QUARANTINE/SWR-000-2/SWR-000-5/IXdetEngine=run_pipeline — foundation.md:28-36과 일치. 위반 없음.

## 우선순위 결함 목록

### D1 [MAJOR] `build_defect_map`는 `validate()`를 호출하지 않음 — 골든-사실 오기(G-1 위반)
- **위치:** spec.md:32 "모든 빌더는 생성 직후 `CalibSet.validate()`로 panel_id·resolution·kind·유효기간을 검증한다" + REQ-XGUI-CALIB-BUILD-3 "`build_defect_map`(…)을 거쳐 …을 생성·**검증**·등록해야 한다".
- **대조 사실:** `metrics/defect_map.py:112-120` — `build_defect_map`은 `CalibSet(...)`를 **`.validate()` 없이 그대로 return** 한다. `validate()`를 호출하는 빌더는 ingest_edrogi의 SAMPLE 3종(`build_offset/gain/defect_calibset` :292/317/342)뿐이다. 즉 "**모든** 빌더가 validate()" 는 거짓.
- **영향:** BUILD-3 스택 경로(정본 morphology)에서 검증이 골든에서 자동 수행된다고 오인 → run 단계에서 검증 누락 또는 잘못된 계약 구현 유발. G-1(지어내기 금지·Grep/Read 대조검증) 직접 위반.
- **수정:** (a) 문장을 "SAMPLE 빌더(build_offset/gain/defect_calibset)는 생성 직후 validate()를 호출하며, `build_defect_map`은 validate()를 호출하지 않으므로 탭이 등록 전 명시적으로 `CalibSet.validate()`를 호출해야 한다"로 교정, (b) BUILD-3의 "검증"을 탭 책임(비-DSP, C-09 위배 아님)으로 명시.

### D2 [MINOR] 캘리브레이션 진입 게이트 축소 기술 — kind·교차도메인(domain/beam_quality) 누락
- **위치:** spec.md:35 및 REQ-XGUI-CALIB-APPLY-4 — 게이트를 "해상도·panel_id 일치"로만 기술.
- **대조 사실:** `_calibration_gate`(orchestrator.py:178-280, SPEC-CALDOM-001 교차도메인 게이트)는 kind + (인자 `domain` 지정 시) domain/beam_quality 일치도 강제한다(test_calibdom_gate.py:73/110-111 NDT↔MEDICAL 불일치 raise; `domain=None`이면 교차도메인 미검사 test:154). APPLY-2의 run_pipeline 구성 서술에 `domain` 파라미터 언급이 없다.
- **영향:** SAMPLE 빌더가 domain=MEDICAL로 스탬프하므로, 탭이 run_pipeline에 domain을 넘기는지/None으로 두는지에 따라 게이트 거동이 달라짐. 검증불가 약속 위험.
- **수정:** APPLY-2/APPLY-4에 kind + `domain` 취급(예: 이 그룹은 domain=None으로 교차도메인 게이트를 미적용, 또는 MEDICAL 일관 전달)을 명시. foundation G-7과도 동기화 권장.

### D3 [MINOR] BUILD-5 "BPM 스택 수가 defect_min_frames 미만" 용어 부정확 — 경로 혼동
- **위치:** REQ-XGUI-CALIB-BUILD-5.
- **대조 사실:** min_frames 게이트는 `build_defect_map`→`classify_defects`(defect_stats.py:78-83, dark+flat **스택**)에만 존재. 외부 BPM.raw 경로(BUILD-4 `build_defect_calibset`)는 min_frames 검사가 전혀 없다(단일 파일 nonzero 라벨). "BPM 스택"이라는 표현이 dark/flat 스택 경로를 BPM 경로처럼 오도.
- **수정:** "dark·flat 스택(각 defect_min_frames 미만) → MetricReadError"로 경로를 BUILD-3 스택 경로에 명확히 귀속.

### D4 [MINOR] `build_defect_map` 시그니처 축약 — 필수 키워드 인자 누락
- **위치:** spec.md:32 "`build_defect_map(dark_stack, flat_stack, params)`".
- **대조 사실:** 실제 시그니처(defect_map.py:83-94)는 keyword-only **필수** 인자 `panel_id, resolution, valid_from, valid_until`를 요구(+ 선택 created_at/source). SAMPLE 빌더와 달리 provenance sample 스탬프 없음(정본 경로).
- **영향:** BUILD-3 구현 시 탭이 이 CalibSet 신원 필드를 공급해야 함이 명세에서 빠져 호출 실패 가능.
- **수정:** BUILD-3에 탭이 panel_id·resolution·유효기간을 공급한다는 점 명시.

## 관찰(비차단)
- GUARD-1(Unwanted)의 "이는 거부되어야 한다"는 런타임 강제 기구가 없음(SAVE-2 choke point/APPLY-4 orchestrator 오류와 달리). 단 DoD(6) "C# 어댑터의 DSP·조합·캘리브레이션 합성 **부재**"로 정적 부재검사 가능 → 검증가능성 확보됨. 표현을 "정적 부재로 검증"으로 조이면 명확.
- HISTORY(d) "classify_defects의 7 임계"는 7 param(min_frames 포함, noisy는 고정 6×) ↔ 7 분류 클래스(over/under/noisy/unstable/lag/dead/nonuniform)를 느슨히 병기. 결정필요 §2의 param 7종 열거는 정확하므로 내부 정합성은 유지.

## 그룹간 일관성
frontmatter·구조 XSEAM-002 미러 정합. 배제절이 lag/line_noise/saturation/geometry/denoise/mse/window/grid/virtual_grid·NDT·Metrics를 타 그룹 소관으로 정확히 분리 → 그룹 경계 충돌 없음. 저장 도메인(raw-DN, 역스케일 없음)이 그룹5(mse/window) 정규화 도메인과 명시적으로 구분됨 — 일관.

## 라운드 2 재검증 대상
D1 문장 교정(필수), D2~D4 정확도 반영 여부.
