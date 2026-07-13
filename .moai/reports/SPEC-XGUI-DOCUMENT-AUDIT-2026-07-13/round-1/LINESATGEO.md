# SPEC Review Report: SPEC-XGUI-LINESATGEO

Iteration: 1/5
Verdict: **FAIL** (defects found — see D1~D5; must-pass firewall all PASS, but MAJOR C-09-tension viewer promise)
Overall Score: 0.82

M1 준수: 저자 reasoning context는 무시했다. spec.md + 골든 소스(modules/line_noise.py, saturation.py, geometry.py, pipeline/orchestrator.py, common/xframe.py, common/synth_calibset.py, common/io.py) + foundation.md + SPEC-XSEAM-002 frontmatter만 대조검증했다.

## Must-Pass Results

- **[PASS] MP-1 REQ 번호 일관성** — 서브그룹별 순차, 결번/중복 없음: INPUT-1~4, PARAMS-1~3, VIEW-1~4, RUN-1~4, DATA-1~2, GUARD-1~3 (spec.md:50-86). 형제 SPEC(SPEC-XSEAM-002 `REQ-XSEAM-COMPOSE-N`) 관례를 미러.
- **[PASS] MP-2 EARS 준수** — 전 요구가 5개 패턴 중 하나에 정합: Ubiquitous(INPUT-1/3, PARAMS-1/3, VIEW-1, DATA-1), Event-Driven WHEN/THEN(INPUT-2/4, RUN-1~4), State-Driven WHILE(VIEW-2/3/4), Optional WHERE(PARAMS-2, DATA-2), Unwanted IF/THEN(GUARD-1~3). 비공식어("적절","합리적") 없음.
- **[PASS] MP-3 YAML frontmatter** — id/version/status/created/updated/author/priority/issue_number/labels (spec.md:2-10). SPEC-XSEAM-002(spec.md:2-10)·SPEC-XGUI-MASTER를 정확히 미러. (일반 rubric의 `created_at` 대신 프로젝트 표준 `created` 사용 — 지배 관례가 형제 SPEC이므로 PASS.)
- **[N/A] MP-4 언어 중립성** — 단일언어(Python 골든) 프로젝트 범위. 16개 다국어 툴링 아님 → 자동 통과.

## Category Scores (rubric-anchored)

| Dimension | Score | Band | Evidence |
|-----------|-------|------|----------|
| Clarity | 0.75 | 0.75 | 대부분 단일해석. VIEW-3/VIEW-4의 "곡선/벡터장" 산출 출처(provenance) 미명시로 C-09-safe 여부가 해석에 좌우됨(spec.md:67-68). |
| Completeness | 0.90 | 1.0-band 근접 | HISTORY/Environment/Requirements/Exclusions/결정필요 존재, frontmatter 완전. plan.md·acceptance.md 미존재(spec.md:23)로 감점. |
| Testability | 0.80 | 0.75~1.0 | diff==0·active=false 등 이진판정 가능. 단 VIEW-4 "보정 곡선"은 골든 미노출로 판정 대상 산출물이 불명확. |
| Traceability | 0.85 | 0.75 | 모든 Params/CalibSet 키가 골든과 1:1 검증됨. acceptance.md 부재로 AC 역추적 미확인. |

## 골든 대조검증 결과 (사실 정확성 — 전부 통과)

모든 인용 키·상수·수식·라인번호를 골든에서 재확인했다. **지어낸 키 0건.**

- line_noise: `process`@198, `K_REFERENCE="reference_region"`@44, `REQUIRED_PARAMS=(profile_window,highpass_cutoff,contam_k)`@54, `_EXCLUDE=DEFECT|INTERPOLATION|SATURATION`@57, `out[protect]=img[protect]`@221, no-ref=행+열 고역통과(@128-130), ref=행중앙값+k*MAD(@153-180) — **전부 일치**.
- saturation: `process`@61, `REQUIRED_PARAMS=()`@53, `P_BAND_WIDTH="saturation_band_width"`@48 기본 2@58, `band=dilated & ~sat`@80-81, 별개 비트 `SATURATION_BAND=8`(xframe.py:72), 픽셀 무변경@85-87 — **일치**.
- geometry: `process`@178, `distortion_coeffs_x/y`@52-53, `calibration_residual`@54(항상 필수, 부재 ValueError@186-190), `REQUIRED_PARAMS=(activation_residual_px,poly_degree)`@65, spline/inverse 기본 3/8@67-68, 계수는 활성일 때만 읽음@214-215, `residual<activate` 항등+`active="false"`@193-206, 경계밖 DEFECT@161-162 — **일치**.
- 배선: `_KIND_BY_STAGE` line_noise만@153, saturation/geometry 미배선→OTHER(`calib_kind_for_stage`@165-175) — **일치**.
- CANONICAL_ORDER 연속 line_noise→saturation→geometry(orchestrator.py:35-37) — **일치**.
- synth: `make_synthetic_calibset(resolution,kind)` data={} 빈 payload(synth_calibset.py:24-52) → geometry 불충분(ValueError) 논증 타당 — **일치**.
- validation_mode/intermediates(xframe.py:161/163, orchestrator.py:334-341), load_raw_frame(io.py:35), guard_output_path(apps/gui/io_panel.py) — **전부 존재 확인**.
- MaskFlag(DEFECT=1/SATURATION=2/INTERPOLATION=4/SATURATION_BAND=8), 오류형 PipelineOrderError/CalibrationError(foundation G-6/G-7) — **일치**.

## Defects Found

**D1. spec.md:65-68 — VIEW-4(및 VIEW-3) 뷰어 특성이 동결 골든 인터페이스로 공급 불가능 + C-09 위반 유발 — Severity: MAJOR**
REQ-XGUI-LSG-VIEW-4는 "행/열 프로파일 보정 곡선"을, VIEW-3은 "왜곡 변위장(벡터장/격자 워프)"을 표시하라고 요구한다. 그러나 골든은:
- `line_noise.process`의 HistoryEntry.extra에 **스칼라 `row_corr_max`/`col_corr_max`만** 노출(line_noise.py:133-134). 행/열 보정 배열(`row_corr`,`col_corr`)은 반환하지 않는다.
- `geometry.process`의 extra는 `active`/`poly_degree`/`calibration_residual`만(geometry.py:239-243). 변위장 `e_row`/`e_col`은 반환하지 않는다.

C-09(G-2, UI DSP 0, HARD)는 UI 재계산을 금지하는데, "보정 곡선"의 자연스러운 구현(median_filter+FFT 재계산)은 즉시 C-09 위반이다. SPEC은 이 산출물의 **C-09-safe 출처를 명시하지 않아** 위반을 유발한다. before/after 주변합(marginal mean)으로 유도 가능하나(diff2d[r,c]=row_corr[r]+col_corr[c]), 이는 SPEC이 명시하지 않은 표시-계층 집계다.
권고: (a) 산출 출처를 "before/after 주변차 유도(표시 집계, 알고리즘 재계산 아님)"로 명시하거나, (b) 골든 diag 확장(row_corr/col_corr, e_row/e_col 노출)을 별건 스코프로 분리하거나, (c) C-09-safe 산출(결합 diff 히트맵 + diag 스칼라)로 요구를 축소.

**D2. spec.md:15 vs spec.md:82 — G-제약 상속 개수 불일치 — Severity: MINOR**
서론은 "불변 HARD 제약(G-1~G-9) 상속"이라 하나 GUARD 절 헤더는 "foundation G-1~G-8 상속"이라 한다. foundation.md:28-36은 G-1~G-9(9개)를 정의하며 G-9(탭=목적별)는 이 탭 SPEC의 전제다. G-9 상속 여부/인코딩 위치를 명확화.

**D3. spec.md:67 — geometry 경계밖 DEFECT 오버레이의 식별 가능성 미명시 — Severity: MINOR**
VIEW-3은 "경계 밖 채움 픽셀의 DEFECT 플래그 오버레이"를 요구하나, 골든은 경계밖 채움을 **공유 DEFECT 비트**에 병합(geometry.py:162; 전용 boundary-fill 플래그 없음). 상류 DEFECT와 구분하려면 geometry 전/후 DEFECT 마스크 diff가 필요하다. SPEC이 이 출처를 명시해야 오해(전용 비트 존재 가정)를 막는다.

**D4. spec.md:75,106 — saturation/geometry 저장의 "무손실 왕복" 주장이 마스크 산출을 누락 — Severity: MINOR**
RUN-4는 `<name>_result.raw`(픽셀) + 최소 `{resolution,dtype}` JSON으로 저장하며 "무손실 왕복"을 주장한다. 그러나 saturation의 유일한 산출은 `SATURATION_BAND` 마스크이고 픽셀은 입력과 bit-동일(saturation.py:87)이므로, 저장된 `.raw`는 이 스테이지 산출을 **전혀 담지 못한다**. 결정필요 #4에서 개방과제로 표기했으나 요구문의 "무손실" 주장은 마스크 보유 스테이지엔 거짓이다. 마스크 직렬화 규약을 확정하거나 "무손실"을 픽셀 도메인으로 한정.

**D5. spec.md:23 — 참조된 plan.md·acceptance.md 부재 — Severity: MINOR**
`[plan.md](./plan.md)`·`[acceptance.md](./acceptance.md)`를 링크하나 SPEC 디렉터리에는 spec.md만 존재한다. 이번 라운드에서 AC 역추적을 교차검증할 수 없다(plan 후속 하위단계에서 생성 예정으로 추정).

## Chain-of-Verification Pass

2차 재독 결과:
- REQ 번호를 끝까지 순차 재확인(결번/중복 0) — OK.
- 12개 Params/CalibSet 키를 골든 소스 각각에서 개별 Grep/Read 재확인 — 지어냄 0건 확정.
- 뷰어 특성(VIEW-1~4)을 골든 반환 표면과 대조하던 중 **D1 신규 발견**: 1차에서 "마스크는 노출됨(VIEW-2 OK)"까지만 보고 넘어갈 뻔했으나, line_noise/geometry의 반환 diag를 정독하니 곡선/변위장은 미노출임을 확인. C-09 HARD 제약과의 충돌이 최대 가치 결함.
- Exclusions(spec.md:90-97) 대조: line 91 "기하 역변환장/리샘플 UI 재구현 금지"가 VIEW-3 변위장 요구와 표면상 긴장 → 다만 변위장은 사용자 주입 입력모델 표시로 해석 가능하여 D1로 통합(별도 모순 아님).
- 그룹간 일치: foundation 그룹3 표(foundation.md:71-73)와 spec HISTORY(c~e) 키·등급([T]/[B]) 일치 확인.

## Recommendation (run 착수 전 수정 권고, 우선순위순)

1. **D1(MAJOR) 우선 해소** — VIEW-3/VIEW-4에 산출 출처 문장을 추가: "행/열 보정 곡선·변위장은 골든이 반환하는 before/after 프레임(및 diag 스칼라 `row_corr_max`/`col_corr_max`)에서 표시-계층 집계로 유도하며, UI는 median_filter/FFT/역변환장을 재계산하지 않는다(C-09)". 또는 골든 diag 확장을 별건 SPEC으로 명시 분리.
2. **D2** — spec.md:82 헤더를 서론(G-1~G-9)과 정합시키거나 G-9 미상속 근거를 명시.
3. **D3** — VIEW-3에 "경계밖 DEFECT는 geometry 전/후 DEFECT 마스크 diff로 식별(전용 비트 없음)" 문구 추가.
4. **D4** — RUN-4의 "무손실 왕복"을 픽셀 도메인으로 한정하고, 마스크 사이드카 직렬화 규약(결정필요 #4)을 이 SPEC에서 확정할지 그룹 공통으로 위임할지 결정.
5. **D5** — acceptance.md 생성 후 AC↔REQ 역추적을 라운드 2에서 재검.
