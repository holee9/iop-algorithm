# SPEC 감사 리포트: SPEC-XGUI-METRICS
라운드: 1/5
판정: FAIL (수정 요망 — 차단성 아님, 그러나 run 착수 전 교정 필요)
Reasoning context ignored per M1 Context Isolation. 감사는 spec.md + 골든 소스 + foundation.md만 근거로 수행.

## 대조검증 요약 (골든 소스 Grep/Read)

SPEC이 인용한 골든 `file:line` 사실은 **거의 전부 정확**하다. 적대적 재검증 결과 다음이 라인 단위로 일치:

- `compute_mtf(frame, params, *, calibset_id=None, direction="vertical")` mtf.py:142 ✓ / `estimate_edge_angle` :48 ✓ / `mtf_value_at` :212 ✓ / MTF Params 5키 mtf.py:28-32, require :167-171 ✓ / 각도경계 warning :182-187 ✓ / 스칼라 `mtf_at_nyquist`·`edge_angle_deg`·`nyquist_lpmm` :199-205 ✓
- `compute_nps(frames: list[XFrame], ...)` nps.py:83, `if not frames` :101 ✓ / `detect_line_noise` :152 ✓ / NPS 6키 nps.py:28-33, require :103-108 ✓ / `line_noise_sig_factor` :34 ✓ / `axial_1d_nps` :123 ✓ / `mean_signal`·`n_roi` :145-146 ✓
- `compute_dqe(frequencies_lpmm, mtf, nnps, params, ...)` dqe.py:31 ✓ / shape 강제 :57-58 ✓ / DQE 3키 :26-28, require :60-62 ✓ / `fluence=q*ka` :63 ✓ / NNPS≤floor→NaN :65-68 ✓ / `invalid_indices` :82 ✓ / `dqe_value_at` :96 ✓
- `MetricResult` result.py:41 / `MetricCondition` :22 / `MetricReadError` :60 / `require_param` :73 / "측정만·판정 안 함" :10-12 / "기본값 대체 없음" :66,89-91 ✓
- `classify_defects(dark_frames, flat_frames, params, *, calibset_id=None, truth_map=None)` defect_stats.py:57 / `DefectClass` IntEnum :40 ✓ / `build_defect_map` defect_map.py:83 → CalibKind.DEFECT :117 ✓
- GUI: `metrics_panel.plot_mtf` :65 / `recompute_mtf_for_roi` :77 / 배열동일성 선례 :5-9 ✓ / `MetricsTab` app.py:571-706, pitch_spin 0.14 :603, `_params` 5키 :669-675, 상류소비 :647-654, ROI 왕복 :688-706 ✓ / `guard_output_path` export.py:32/56 ✓
- frontmatter는 SPEC-XSEAM-002(id/version/status/created/updated/author/priority/issue_number/labels)와 필드 완전 미러 ✓
- EARS: 전 요구가 Event-Driven(WHEN/THEN)·Ubiquitous·Unwanted(IF/THEN)·Optional(WHERE) 키워드 준수 ✓
- Exclusions 7항 구체적 ✓

지어낸 Params 키·존재하지 않는 시그니처·틀린 수식은 **발견되지 않았다**. 이 점은 강점이다.

그러나 아래 결함이 남는다 — 특히 **네 번째 지표(defect-stats)와 DQE 합성**에서 나머지 3개 지표 대비 취급이 불완전하다.

## 우선순위 결함 목록

### D1 [MAJOR] DQE "완전 지원" 주장이 자체 §결정필요3와 모순 — 공통축 재샘플이 C-09를 침해할 수 있음
- 위치: spec.md:19 / L31 DoD(1) / L38 HISTORY(b) / L85 REQ-XMETRIC-COMPUTE-2 / L129 §결정필요3
- 문제: L19·문제진술은 "동결된 골든 지표 엔진은 이 능력을 이미 완전히 지원한다"고 단언하나, DQE는 `compute_dqe`가 `freq/mtf/nnps` **shape 일치를 강제**(dqe.py:57-58)하는데 MTF 축(rfftfreq d=1/oversample → oversample·Nyquist까지)과 NPS 축(Nyquist까지)은 범위·간격이 **근본적으로 다르다**. 골든에는 두 실측 축을 정렬하는 헬퍼가 **존재하지 않는다**(Grep 확인). 골든 수용시험 `tests/metrics/test_nps_dqe.py:84`조차 실제 MTF를 쓰지 않고 `mtf_ideal = np.ones_like(freqs)`로 NPS 축 위에서 회피한다 — 즉 **실측 MTF∘실측 NPS 합성 선례가 골든에 전무**하다.
- 모순: REQ-XMETRIC-COMPUTE-2(L85)는 "공통축 정렬은 지표 값을 새로 계산하는 것이 아니라 … 정합"이라 단정하나, `np.interp`로 MTF를 NPS 주파수에 리샘플하면 **엔진이 내지 않은 주파수의 MTF 값을 GUI가 산출**하게 된다. 이는 C-09("실제 엔진 결과만 표시", REQ-XMETRIC-COMPUTE-1/GUARD-1)와 정면 충돌한다. SPEC은 §결정필요3(L129)에서 이 소재를 "미확정"으로 남기면서 동시에 DoD(1)에서 "정확한 엔진 진입점으로 위임 호출"을 약속한다 — 그런 진입점은 없다.
- 요구 조치: (a) L19/문제진술의 "완전 지원"을 "MTF/NPS/defect는 완전 지원, DQE 합성은 축정렬 미해결"로 정정. (b) §결정필요3을 run 착수 전 **차단 결정**으로 승격하고, 재샘플이 C-09 위반이 아님을 성립시키는 경계(예: 정렬을 골든 additive 헬퍼로 두어 "엔진 산출"로 만들 것인지)를 명시. (c) DoD(1)에서 DQE는 "실측이 아닌 합성/#33"임을 재확인하되, 합성에서도 축정렬이 필요함을 DoD에 반영.

### D2 [MAJOR] defect-stats의 정확한 Params 키가 REQ-XMETRIC-PARAM-1에 누락 (SPEC 자체 기준 위반)
- 위치: spec.md:79 REQ-XMETRIC-PARAM-1 (vs L31 DoD(1)/L73 INPUT-1/L98 DATA-3)
- 문제: PARAM-1은 "탭은 각 지표에 대해 골든이 요구하는 정확한 Params 키만 공급해야 한다"고 규정한 뒤 MTF(5키)·NPS(6키)·DQE(3키)는 완전 열거하나, **defect-통계 키는 열거하지 않는다**. 그러나 defect-통계는 INPUT-1·COMPUTE-1·DATA-3·DoD(1)에서 1급 지표로 범위에 든다. 골든 `classify_defects`는 7키를 강제한다: `defect_min_frames`(:78), `defect_over_value`, `defect_under_value`, `defect_dead_gain_frac`, `defect_nonuniform_frac`, `defect_lag_frac`, `defect_unstable_frac`(defect_stats.py:31-37, require :98-103). HISTORY(c) L43도 "P_MIN_FRAMES + 모듈 [P] 임계"로만 뭉개고 정확 키를 안 준다.
- 영향: DoD(1)은 defect-통계를 "정확한 Params 키로 위임 호출"하라 하나 그 키가 SPEC 어디에도 확정되지 않아 **검증 불가**. 나머지 3지표와 커버리지 불일치.
- 요구 조치: PARAM-1에 defect-통계 7키를 골든과 동일하게 열거하고, `NOISY_MEDIAN_MULTIPLIER=6.0`은 E2597-22 [S] 상수로 Param 아님(defect_stats.py:27-29)을 명시.

### D3 [MODERATE] defect-stats 뷰어 특성이 미정의·상충 (그룹 고유 뷰 누락)
- 위치: spec.md:90 REQ-XMETRIC-VIEW-1 / L60 Environment
- 문제: VIEW-1은 그룹 8의 뷰를 "주파수축(lp/mm) 곡선 플롯 + 스칼라"로 규정하고 MTF/NPS/DQE 판독만 열거한다. 그러나 `classify_defects`는 **주파수축도 곡선도 없는** `class_map`(2D 이미지)+`counts`+`fractions`+`miss_rate`(defect_stats.py:145-149)를 낸다. defect-통계의 자연스러운 뷰(E2597 클래스 히스토그램 + 공간 class_map)는 "주파수축 곡선" 프레이밍과 상충하며 SPEC에 미기술이다.
- 영향: 4개 지표 중 하나의 그룹 고유 뷰가 요구에서 빠져 run 단계 해석이 갈린다.
- 요구 조치: VIEW-1에 defect-통계 뷰(클래스 히스토그램/카운트/분율 + 선택적 class_map 표시, `miss_rate`는 truth_map 있을 때만)를 별도 명시하고, "주파수축 곡선"은 MTF/NPS/DQE에 한정됨을 문구로 분리.

### D4 [MINOR] 존재하지 않는 동반 문서로의 끊긴 링크
- 위치: spec.md:32 — `[plan.md](./plan.md)` · `[acceptance.md](./acceptance.md)`
- 문제: 디렉터리에는 spec.md만 존재(plan.md·acceptance.md 부재). 형제 SPEC-XSEAM-002는 둘 다 보유. SPEC이 산출물로 링크한 문서가 없다.
- 요구 조치: 링크를 제거하거나 run 착수 전 두 문서를 생성.

### D5 [MINOR] REQ-XMETRIC-DATA-3의 classify_defects 입력 표현 부정확
- 위치: spec.md:98 — "등록 BPM/dark/flat SAMPLE 스택이 가용하면 classify_defects를 … 구동"
- 문제: `classify_defects`는 `dark_frames`+`flat_frames`(+선택 `truth_map`)를 받는다(defect_stats.py:57). **BPM은 입력 스택이 아니라** dark/flat로부터 산출되는 DEFECT CalibSet(K_CLASS_MAP, foundation §2 그룹1). BPM을 classify_defects의 입력 스택처럼 서술한 것은 부정확(다만 BPM을 `truth_map` 진리맵으로 쓴다면 성립).
- 요구 조치: "dark+flat 스택(선택적으로 BPM을 truth_map으로)"으로 정정.

## Chain-of-Verification Pass
2차 재검토에서 확인/추가:
- 모든 골든 인용 라인 재대조 — MTF/NPS/DQE/result/defect_stats/defect_map/metrics_panel/export/app.py 전부 재확인, 허위 인용 없음.
- REQ 번호: 카테고리별(INPUT/PARAM/COMPUTE/VIEW/DATA/EXPORT/GUARD) 하위번호 연속, 그룹 내 누락·중복 없음(형제 SPEC 규약 준수) — 단일 REQ-001…N 스킴 아님은 프로젝트 관례로 수용.
- 신규 발견 결함: D2·D3(defect-stats가 PARAM/VIEW에서 나머지 3지표 대비 과소기술)은 1차에서 놓칠 뻔한 **교차-지표 커버리지 비대칭**으로, 2차 재독에서 확정. D1의 골든 헬퍼 부재는 `test_nps_dqe.py:84` `mtf_ideal=np.ones_like` 회피를 직접 확인하여 입증.
- 제약 위반 재점검: C-09/C-11/C-20/QUARANTINE/G-1~G-9 — SPEC은 대체로 충실(내보내기 choke point, SAMPLE sanity 라벨, 골든 무변경, run_pipeline 미사용 모두 정확). 유일한 실질 위반 위험은 **D1의 DQE 재샘플 대 C-09**.

## 권고
run 착수 전 D1·D2·D3 교정 필수(검증가능성·커버리지). D4·D5는 문구 정정. D1은 §결정필요3을 차단 결정으로 올리고 C-09 경계를 확정하기 전에는 DQE 관련 REQ를 "합성/#33 + 축정렬 미해결"로 명시 표기할 것. 골든 무변경 원칙과 사실 정확성은 우수하므로, 결함은 전부 SPEC 문서 측 보강으로 해소 가능(골든 수정 불필요).
