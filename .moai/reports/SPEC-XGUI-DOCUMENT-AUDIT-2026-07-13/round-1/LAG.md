# SPEC Review Report: SPEC-XGUI-LAG
Iteration: 1/5
Verdict: FAIL (one major C-09 sourcing gap; remainder is exceptionally well cross-verified)
Overall Score: 0.86

주의: 프롬프트로 전달된 저작자 추론 컨텍스트는 M1 Context Isolation에 따라 무시함. spec.md + 골든 소스만으로 감사.
acceptance.md / plan.md 는 아직 디렉터리에 없음(plan 단계 정상 — 전방 참조). audit-r1.md 만 산출.

## Must-Pass Results

- [PASS] MP-1 REQ 번호 일관성 — 그룹형 ID(XSEAM-002 미러). 각 그룹 내 순차·무결손·무중복:
  INPUT 1-4, VIEW 1-5, IRF 1-4, APPLY 1-5, METRIC 1-3, EXPORT 1-3, DATA 1-3 (spec.md:41-87). 갭/중복 없음.
- [PASS] MP-2 EARS 준수 — 5개 패턴에 정합. Ubiquitous(INPUT-1/3, VIEW-1, APPLY-2/4, METRIC-1, DATA-1/3),
  Event-Driven(INPUT-2, VIEW-2/3/4, IRF-1/4, APPLY-1, METRIC-2, EXPORT-1), Unwanted(INPUT-4, IRF-2/3, METRIC-3, EXPORT-2, DATA-2),
  State-Driven(APPLY-3), Optional(VIEW-5, APPLY-5, EXPORT-3). VIEW-5 만 Optional의 WHERE 절이 feature-presence가 아니라 사용자 의도("검토하려 하면")로 느슨 — minor.
- [PASS] MP-3 YAML frontmatter — id/version/status/created/updated/author/priority/issue_number/labels 전부 존재(spec.md:2-11).
  `created`/`updated`는 SPEC-XSEAM-002 미러 스키마(지시된 미러링). labels 배열. 타입 정합.
- [N/A] MP-4 언어중립 — 단일 프로젝트(XDET Python 골든) 범위. 16개 언어 다국어 툴링 아님.

## Category Scores (rubric-anchored)

| Dimension | Score | Band | Evidence |
|-----------|-------|------|----------|
| Clarity | 0.85 | 0.75~1.0 | 2단(build/apply) 구조·시퀀스 단위·IRF 필수성이 명료(spec.md:17,30-31). VIEW-3 곡선 출처 미지정만 흠 |
| Completeness | 0.95 | 1.0 | HISTORY/Env/EARS/Exclusions/결정필요 전부. Exclusions 8종 구체(spec.md:91-99) |
| Testability | 0.80 | 0.75 | 대부분 golden 오류형·수식으로 이진판정 가능. VIEW-3 "시간축 신호 곡선"은 golden 반환값에 없어 판정 불가 |
| Traceability | 0.90 | 0.75~1.0 | 거의 모든 REQ가 정확한 file:line + 오류형에 추적. VIEW-3만 golden 산출과 불일치 |

## 골든 대조 검증 결과 (전수)

정확히 일치 확인된 사실(지어내기·오류 없음):
- `irf_a`/`irf_b` 키 — calibset.py:82-84 (K_IRF_A="irf_a", K_IRF_B="irf_b") ✓
- `REQUIRED_PARAMS = ()` — modules/lag.py:63 ✓
- `LagCorrector.process(self, frame, calib, params)` 인스턴스 메서드 — lag.py:127 ✓
- `_load_irf` → `LagCalibError` (키 결여 시) — lag.py:82-97/70 ✓
- SATURATION 출력 보존 + 계산 I_hat로 상태 진행 — lag.py:149-161 ✓ (REQ-LAG-CORR-5)
- float64 병렬 검증 경로 — lag.py:170-177 ✓
- `compute_first_frame_lag` — metrics/lag.py:38; 필수 Params `lag_settle_frac`(:31,:75)·`lag_plateau_frac`(:30,:95),
  선택 `lag_dark_baseline`(:28,:67)·`lag_exposure_end_index`(:27,:87)·`lag_min_exposed_signal`(:29,:114) ✓ 전부 정확
- 반환 키 `first_frame_lag_pct/last_exposed_index/first_residual_index/dark_baseline` — lag.py:129-132 ✓
- `MetricReadError` (정착 tail 없음 / 플래토 없음) — lag.py:80-83/99-101 ✓
- `compute_ghost_cnr` = |mean_fg-mean_bg|/std_bg — lag.py:144/177 ✓ 수식 정확
- `fit_lag_irf(step_responses, *, m_terms, panel_id, resolution, valid_from, valid_until, ...)` — lag_irf.py:72 ✓
- `StepResponse(amplitude, residual)` — lag_irf.py:50 ✓
- `LagIRFCalibrationError` "single-exposure calibration is forbidden" — lag_irf.py:94-98 ✓ 문자열 정확
- rel-RMS 게이트(`rms_residual_tol`) — lag_irf.py:141-147 ✓; provenance fit-quality note — lag_irf.py:158-162 ✓
- `run_sequence(frames, definition, registry_factory, calib_map, params_map, *, ...)` — sequence.py:89 ✓ 시그니처 정확
- `FBTriggerError`/`NoOpFBTrigger`/`confirm()` — sequence.py:48/74/70 ✓
- `make_synthetic_calibset(_, LAG)` payload `{}` — synth_calibset.py:48 ✓ (lag엔 사용불가 주장 정확)
- `lag_factory` → `{"lag": LagCorrector().process}` — lag_seq.py:42-48 ✓
- `build_pipeline_registry` → `{name: module.process}` 단일 공유 인스턴스 — pipeline_panel.py:47-49 ✓
- `CANONICAL_ORDER` offset→gain→defect→lag — orchestrator.py:30-34 ✓; `CalibKind.LAG` 존재 — calibset.py:40 ✓
- `_CATEGORY_BY_FOLDER["GHOST"]="ghost_lag"` — ingest_edrogi.py:87 ✓; ingest는 LAG CalibSet 미생성 주장 정확
- `guard_output_path` — apps/gui/io_panel.py:27 ✓; `load_raw_frame` — common/io.py:35 ✓
- IRF_A=(0.030,0.020,0.010)/IRF_B=(0.50,0.80,0.90)/M=3 — lag_seq.py:26-28 ✓
- 저장 규약(float32→clip[0,65535]→np.rint→<u2 + .json {resolution,dtype}) — foundation §3 일치 ✓
- 제약 상속 C-09/C-11/C-20/QUARANTINE/SWR-000-2/SWR-000-5 정확 반영, foundation G-1~G-9와 정합 ✓

## Defects Found

D1. spec.md:52 (REQ-XGUI-LAG-VIEW-3) — **[MAJOR] C-09 곡선 출처 미지정 / 검증불가 약속.**
    요구: first_frame_lag_pct·검출 인덱스를 "시간축 신호 곡선(노출 플래토 → 잔상 감쇠)과 함께 표시".
    그러나 golden `compute_first_frame_lag`는 스칼라 4종만 반환하며(metrics/lag.py:126-141), **프레임별 신호 곡선(내부 `signals` 배열, lag.py:58)을 반환하지 않는다**. 따라서 이 곡선을 그리려면 UI가 프레임별 `robust_stats.robust_mean`을 스스로 계산해야 하는데, 이는 foundation G-2 "UI가 어떤 지표·처리 결과도 스스로 계산하지 않는다"(C-09)와 충돌하거나, 대안으로 존재하지 않는 golden 접근자를 전제한다. SPEC의 "결정 필요/확인 사항"(spec.md:101-108)도 이 출처 문제를 다루지 않는다 — 명세 공백. run 전 해소 필요.

D2. spec.md:52,54 (VIEW-3/VIEW-5) 파생 — **[MINOR] IRF 감쇠 곡선 h[n]=Σa_i·b_i^n 표시(VIEW-5)도 동일 계열 회색지대.**
    계수 표시·감쇠 모델 평가가 Exclusions(spec.md:92) "UI에서 IRF 계수 스스로 산출 금지"에 저촉되지 않는다는 점은 명세가 암시하나(모델 평가 ≠ 계수 산출), C-09 경계를 명시하면 더 안전. VIEW-3와 묶어 "표시용 파생량은 golden robust_stats/모델 평가로 한정, 판정 수치만 엔진 반환값"이라는 경계 문장을 추가 권고.

D3. spec.md:25 (HISTORY b) — **[MINOR] provenance 귀속 부정확.** `lag_calib`(lag_seq.py:51-72) 선례에 provenance `source="synthetic"/sample=true`라 기술했으나, 실제 `lag_calib`의 provenance는 `CalibProvenance(created_at="2026-07-09", source="synthetic")`로 **note가 빈 문자열 — "sample=true" 마커 없음**. "sample=true"는 에드로지 ingest SAMPLE 세트(`SAMPLE_PROVENANCE_NOTE`, ingest_edrogi.py:67)의 note 문자열이지 lag_calib 것이 아님. 두 출처 혼동.

D4. spec.md:86 (REQ-XGUI-LAG-DATA-2) — **[MINOR] "provenance sample=true" 표현.** 실제로는 boolean 필드가 아니라 `provenance.note` 내부 부분문자열("sample=true; plumbing-only; ...", ingest_edrogi.py:67). CalibProvenance 필드는 created_at/source/note 3종뿐(calibset.py:114-116) — `.sample` 속성 없음. 구현자가 boolean 필드로 오인할 소지. 단, 이 표현은 foundation G-5(foundation.md:32)에서 그대로 상속된 것이라 그룹 SPEC 단독 결함은 아님 — foundation과 동반 정정 권고.

D5. spec.md:19 — **[MINOR] 라인 귀속 부정확.** `calib_kind_for_stage("lag") -> CalibKind.LAG (orchestrator.py:152)`. 함수 `calib_kind_for_stage` 정의는 orchestrator.py:165. 152는 `_KIND_BY_STAGE`의 `"lag":"lag"` 배선 라인. 실질 주장(lag→LAG)은 참이고 152가 그 배선이므로 사실은 정확하나 심볼-라인 대응이 어긋남. StepResponse도 spec.md:19/58은 lag_irf.py:49로, foundation은 :50으로 표기 — 실제 class def는 :50(데코레이터 :49). 사소.

## Chain-of-Verification Pass

2차 재독 결과:
- REQ 전수 재확인: INPUT/VIEW/IRF/APPLY/METRIC/EXPORT/DATA 24개 요건 각각의 golden 인용을 개별 대조(스킴 아님). 모든 Params 키·오류형·수식·시그니처가 실제 소스와 문자 단위로 일치 — D1 외 사실 오류(지어낸 키/틀린 수식/틀린 상수) **없음**.
- 그룹간 일관성: foundation.md §2 그룹2·§3·§4·§5와 대조 — 저장/열기/시퀀스/리셋/placeholder IRF 서술 모두 정합. 상충 없음.
- 제약 위반 재점검: C-09(D1 제외 준수), C-11 단방향, C-20 guard_output_path, QUARANTINE 수치금지, SWR-000-2 순서, SWR-000-5 기본 IRF 금지 — 전부 정확 인코딩. Exclusions(spec.md:91-99)가 골든 무변경·IRF 재구현 금지·포화복원 금지·순서변경 금지·정본검증 금지·FB HW 금지를 구체적으로 차단.
- 신규 발견: 1차에서 D1을 포착. 초기에 놓칠 뻔한 지점 — "시간축 신호 곡선"이 표시 요구인데 golden 반환 스키마에 부재. 이것이 유일한 실질(major) 결함.

## Regression Check
해당 없음(iteration 1).

## Recommendation

이 SPEC은 골든 소스 대조 품질이 예외적으로 높다(Params 키·수식·오류형·시그니처 전수 정확, 지어내기 0건). FAIL 판정은 **오직 D1**(VIEW-3 C-09 곡선 출처 공백)에 기인하며, 아래를 반영하면 PASS 전환:

1. REQ-XGUI-LAG-VIEW-3(spec.md:52) 정정 — "시간축 신호 곡선"의 출처를 명시하라. 택1:
   (a) UI는 `compute_first_frame_lag` 반환 스칼라(first_frame_lag_pct·last_exposed_index·first_residual_index·dark_baseline)와 **프레임 이미지/뷰어 기존 표시**만 제시하고, 별도 프레임별 신호 곡선은 산출하지 않는다(가장 안전, C-09 무저촉); 또는
   (b) 신호 곡선을 표시하려면 그 프레임별 축약을 **golden `common.robust_stats.robust_mean` 호출로 한정**하고, 이것이 "UI DSP 0" 경계 안임을 EARS 본문에 명시(엔진 primitive 호출 = 소비, 재구현 아님)한다. 존재하지 않는 golden 접근자를 전제하지 말 것.
2. VIEW-5(spec.md:54)에도 동일 경계 문장 추가 — IRF 감쇠 곡선은 CalibSet 계수 `(a_i,b_i)`의 **모델 평가(표시)** 이며 계수 산출이 아님을 1행 명시(D2).
3. HISTORY(b)(spec.md:25)의 provenance 귀속 정정 — "sample=true"는 ingest_edrogi.py:67 SAMPLE note 마커이지 lag_calib 것이 아님. lag_calib 선례는 `source="synthetic"`(note 없음)로 기술(D3).
4. "provenance sample=true"(spec.md:86)를 "provenance.note에 'sample=true' 마커(ingest_edrogi.py:67); CalibProvenance는 note 문자열, boolean 필드 아님"으로 정밀화(D4). foundation.md:32 G-5와 동반 정정 권고.
5. 라인 인용 미세정정(D5): calib_kind_for_stage 함수는 orchestrator.py:165(배선은 :152), StepResponse는 lag_irf.py:50.

D1을 제외하면 실측[B] 차단 항목 없고, 그룹 고유 뷰어(시퀀스 스크러버 + IRF 감쇠 플롯 + lag/ghost 곡선)·2단 워크플로·QUARANTINE·저장/열기 규약이 모두 골든에 정확히 정박되어 있다.
