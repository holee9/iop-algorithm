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
priority: medium
issue_number: 58
labels: [xgui, gui-redesign, verification-gui, line-noise, saturation, geometry, golden-frozen]
---

# SPEC-XGUI-LINESATGEO — Line/Sat/Geo 알고리즘 그룹 GUI 검증 탭 (WP3+WP4)

> 본 사양은 `../SPEC-XGUI-MASTER/baseline-control.md`의 G0와 `traceability-matrix.md`를 상속한다. 사용자 승인·기준선 동결·`implementation_authorized=true` 전에는 구현 입력으로 실행하지 않으며, 승인 뒤 규범 변경은 버전 상승과 재승인을 요구한다.

XDET 검증 GUI 재설계(이슈 #58)의 **그룹 3 — Line noise / Saturation / Geometry** 검증 탭이다. [SPEC-XGUI-MASTER](../SPEC-XGUI-MASTER/spec.md)(공유 팩트시트·foundation)의 불변 HARD 제약(G-1~G-9)과 저장/열기 규약을 **상속**하며 재기술하지 않는다. frontmatter·문서 구조는 [SPEC-XSEAM-002](../SPEC-XSEAM-002/spec.md)를 미러링한다.

**대상 골든 모듈(FROZEN, 호출만):** `modules/line_noise.py::process`(line_noise.py:198) · `modules/saturation.py::process`(saturation.py:61) · `modules/geometry.py::process`(geometry.py:178). 세 스테이지는 `CANONICAL_ORDER`에서 **연속**(`… → lag → line_noise → saturation → geometry → grid → …`, orchestrator.py:35-37)하므로 이 그룹은 **정렬된 유효 부분수열**을 이룬다 — 개별 스테이지 검증 후 `("line_noise","saturation","geometry")` 조합을 단일 심 패스로 검증할 수 있다.

**문제(사용자 요구):** 세 스테이지는 저마다 **구별되는 입력**을 갖는다 — line_noise는 CalibSet(LINE_NOISE)의 선택적 `reference_region` 유무로 경로가 갈리고, saturation은 상류에서 누적된 SATURATION 마스크만 소비(CalibSet payload 불요)하며, geometry는 CalibSet(OTHER)의 다항 왜곡 모델(`distortion_coeffs_x/y` + `calibration_residual`)을 요구한다. 이 탭은 각 스테이지의 구별 입력을 스테이지별로 수집해 골든 엔진을 거쳐 개별 구동·표시하고(C-09: UI는 DSP 0), 개별 확인 뒤 정렬된 조합을 검증한다. **모든 사실은 동결 골든 소스로 Grep/Read 대조검증**했으며 지어내기는 없다(G-1).

**Python 선례:** [SPEC-VIEWER-001](../SPEC-VIEWER-001/spec.md) REQ-VIEW-RUN-1(단일 스테이지 `process` 직접 실행)·REQ-VIEW-RUN-2(부분/전체 `run_pipeline`)를 이 그룹 세 스테이지에 특화한다. 조합 심 경로는 [SPEC-XSEAM-002](../SPEC-XSEAM-002/spec.md) REQ-XSEAM-CONTRACT-6(`run_pipeline` 미러) 계약을 따른다.

- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.2.0 (2026-07-13)** — 중단 작업 복구 마무리. 구현 대상을 C# WPF `apps/xdet-console/`로 확정하고 Python `apps/gui/`는 참조 선례로 한정했다. 그룹별 결정·중앙 TC 레지스트리·plan/research를 확정했다. 골든 알고리즘은 변경하지 않는다.

- **v0.1.1 (2026-07-12)** — plan-audit 라운드 1(FAIL 0.82) 반영 수정 (D1~D5). 저작 reasoning은 무시하고 골든 소스로 재대조하여 교정:
  - **D1(MAJOR) 해소 — VIEW-3/VIEW-4 산출 출처를 엔진 결과 DTO로 한정.** 골든은 `line_noise` diag에 **스칼라 `row_corr_max`/`col_corr_max`만**(line_noise.py:133-134; reference 경로는 `contaminated_rows`/`ref_mad`, line_noise.py:177-178), `geometry` diag에 **`active`/`poly_degree`/`calibration_residual`만**(활성 geometry.py:239-243; 항등 geometry.py:199-203)을 노출하고, 행/열 보정 배열(`row_corr`/`col_corr`, line_noise.py:128-129)·역변위장(`e_row`/`e_col`, geometry.py:217)은 **반환하지 않는다**. 따라서 기본 UI는 before/after/diff·mask·diag 스칼라만 표시한다. 보정 곡선·변위장/격자 워프는 향후 골든/엔진 결과 DTO가 해당 배열을 명시적으로 제공할 때만 활성화하며, UI/어댑터가 주변차·좌표매핑으로 새 수치 배열을 만들지 않는다(G-2/C-09).
  - **D2 해소 — G-제약 상속 개수 정합.** GUARD 헤더를 서론(G-1~G-9)과 일치시키고, **G-9(탭=알고리즘 그룹, foundation.md:36)** 는 이 탭(Line/Sat/Geo 그룹) 자체의 구성 전제임을 명시.
  - **D3 해소 — geometry 경계밖 DEFECT 식별 출처 명시.** 경계밖 채움은 전용 비트 없이 **공유 `MaskFlag.DEFECT`** 에 병합(geometry.py:162)되므로, geometry **전/후 DEFECT 마스크 diff**로 식별(상류 DEFECT와 구분). VIEW-3에 인코딩.
  - **D4 해소 — RUN-4 '무손실 왕복'을 픽셀 도메인으로 한정.** saturation의 유일 산출인 `SATURATION_BAND` 마스크는 픽셀이 입력과 bit-동일(saturation.py:83-87)이라 `<name>_result.raw`가 스테이지 산출을 담지 못함을 명시; 마스크 사이드카 직렬화 규약은 v0.2.0 확정 결정 4로 이연.
  - **D5 해소 — [acceptance.md](./acceptance.md) 신규 작성.** E2E(열기→build/apply→저장 `_result.raw`→재적재 왕복) Given-When-Then + edge case 수록, 시험 블록 **XDET-TC-112~119**(SPEC-XGUI-ENHANCE 결정 #5의 중앙 레지스터 제안에서 그룹 3=112~119 슬롯에 정렬; SPEC-XGUI-MASTER 중앙 레지스트리에서 확정). AC↔REQ 역추적이 라운드 2에서 가능. plan.md는 후속 하위단계에서 생성(XSEAM-002 미러 전방참조).
  - 골든 무변경(G-1). 세 `process`의 시그니처·상수·반환 표면 불변.
- **v0.1.0 (2026-07-12)** — 초안 생성. GitHub 이슈 #58(GUI 재설계). SPEC-XGUI-MASTER foundation 상속. 저작 시 **AUTHORITATIVE 골든 소스로 대조검증한 사실**:
  - **(a) line_noise 경로 선택(검증됨, line_noise.py:183-220).** `_has_reference(calib, shape)`가 CalibSet(LINE_NOISE)의 `K_REFERENCE="reference_region"`(line_noise.py:44) 키 유무·비어있지 않음으로 경로를 **결정적**으로 선택. **부재 시 → REQ-LNSG-LINE-1(P1 우선순위, SWR-503) 행/열 고역통과 프로파일 감산**(no-reference), **존재 시 → REQ-LNSG-LINE-2(Optional, SWR-501/502) 레퍼런스 행-중앙값 감산 + k*MAD 오염 제외**. reference 없이도 SWR-503 대안 경로가 동작하므로 **P1 기본 경로는 reference-absent**다.
  - **(b) line_noise 마스크 제외·SAT 보호(검증됨, line_noise.py:57/207-221).** 강건 프로파일 통계는 `_EXCLUDE = DEFECT|INTERPOLATION|SATURATION`(line_noise.py:57) 픽셀을 제외. 추가로 SATURATION 플래그 픽셀은 감산 후 원값 복원(`out[protect]=img[protect]`, line_noise.py:221)되어 클램프값(65535)이 T5까지 무손상 생존(SWR-602 무복원과 정합). 노이즈 모델(α,σ)은 재추정 안 함(REQ-LNSG-LINE-3).
  - **(c) line_noise Params(검증됨, line_noise.py:47-54).** `REQUIRED_PARAMS = ("line_noise_profile_window","line_noise_highpass_cutoff","line_noise_contam_k")`. window/cutoff은 항상 필수, contam_k는 reference 경로에서 필수(세 개 모두 raise-on-missing 접근자로 소비). 전부 [T] 등급(튜닝).
  - **(d) saturation 무변경·no-op(검증됨, saturation.py:61-101).** `process`는 누적 SATURATION 마스크(`MaskFlag.SATURATION=2`, xframe.py:66)만 소비 → 코어를 `dilate_mask`로 팽창해 코어를 뺀 버퍼밴드(`band = dilated & ~sat`, saturation.py:80-81)를 **별개 비트 `SATURATION_BAND=8`**(xframe.py:72)로 표시. **픽셀 값 무변경·INTERPOLATION 무설정**(SAT-3, saturation.py:85). SATURATION 마스크가 없으면 band가 비어 사실상 **no-op**. 별개 비트 사용으로 재실행 시 밴드가 재성장하지 않음(멱등). `REQUIRED_PARAMS = ()`(saturation.py:53); `P_BAND_WIDTH="saturation_band_width"`(saturation.py:48)는 선택(모듈 기본값 2, saturation.py:58). **복원 분기 없음 — 단일 결정적 경로**(SWR-602 [HARD]).
  - **(e) geometry 활성/항등(검증됨, geometry.py:178-245).** CalibSet(OTHER) payload `distortion_coeffs_x/y`(geometry.py:52-53)+`calibration_residual`(geometry.py:54)를 소비. **`calibration_residual`은 활성 판정을 위해 항상 필수**(부재 시 ValueError, geometry.py:186-190); `distortion_coeffs_x/y`는 **활성일 때만** 읽음(geometry.py:214-215). `residual < geometry_activation_residual_px`이면 **항등 통과**(입력 무변경 + `active=false` 이력 기록, geometry.py:193-206), 이상이면 고정점 역변환장 계산 후 스플라인 리샘플·마스크 동일 워프(경계 밖 픽셀은 DEFECT 플래그, geometry.py:161-162). `REQUIRED_PARAMS = ("geometry_activation_residual_px","geometry_poly_degree")`(geometry.py:65); `geometry_spline_order`/`geometry_inverse_iters`는 선택(모듈 기본 3/8).
  - **(f) CalibKind 배선(검증됨, orchestrator.py:148-175).** `_KIND_BY_STAGE`에 `line_noise → "line_noise"`(LINE_NOISE)만 배선; **saturation·geometry는 미배선 → `calib_kind_for_stage`가 `CalibKind.OTHER` 반환**(orchestrator.py:175). 진입 게이트는 OTHER placeholder로 만족.
  - **(g) 합성 placeholder의 payload 공백(검증됨·설계 함의, synth_calibset.py:42-52).** `make_synthetic_calibset(resolution, kind)`는 `data={}` **빈 payload**를 반환 → 스키마만 유효(진입 게이트 통과용). **line_noise(reference 부재 no-ref 경로)·saturation(payload 불요)에는 충분**하나 **geometry에는 불충분** — `calibration_residual` 부재로 `geometry.process`가 ValueError를 던짐. 따라서 geometry 서브탭은 **populated 합성 왜곡 모델**(빈 placeholder 아님)을 공급해야 한다. 이는 조합 버그가 아니라 geometry 자신의 명시 오류(SPEC-XSEAM-002 spec.md:41 mse의 노이즈 부재 하드실패와 동형).
  - **(h) 데이터 가용성(검증됨, foundation §2 그룹 3 / ingest_edrogi.py).** 세 스테이지 전부 **합성 전용 / #33 대기**. 등록 edrogi SAMPLE에는 line 레퍼런스·포화 유발 과노출·왜곡 캘리가 없다. 확정 설계: 이 탭의 정본 수치 검증 경로는 **합성 주입**(banding/포화 코어/기하 왜곡)이며 edrogi는 프레임 소스 sanity 전용(QUARANTINE, 튜닝/적합 금지).

## Environment / Assumptions

- **본 SPEC은 T-스테이지가 아니다.** `CANONICAL_ORDER` 스테이지 추가·`process(...)->XFrame` 시그니처 변경·신규 CalibKind·`_KIND_BY_STAGE` 변경이 전혀 없다. 세 골든 모듈(line_noise/saturation/geometry)과 오케스트레이터 표면은 불변이며, 본 SPEC은 그 위에 **검증 GUI 소비자**를 additive로 얹는다(SPEC-VIEWER-001·SPEC-XSEAM-002 검증 도구 계열의 그룹 특화).
- **골든 FROZEN(G-1 상속).** 세 `process` 함수·상수·시그니처는 읽기-실행 전용으로만 소비한다. 위 HISTORY의 모든 사실은 `file:line` 대조로 검증했으며, run 단계 구현자도 값을 지어내지 않고 소스로 재확인한다.
- **스테이지별 구별 입력(검증됨).** `calib_kind_for_stage("line_noise")=LINE_NOISE`, `calib_kind_for_stage("saturation")=OTHER`, `calib_kind_for_stage("geometry")=OTHER`(orchestrator.py:175). UI/어댑터는 스테이지별로 그 구별 입력을 수집해 `calib_map`/`params_map`으로 전달할 뿐, 스스로 CalibSet을 합성하거나 스테이지를 정렬·조합하지 않는다(조합/순서 권한은 Python 오케스트레이터, C-11).
- **합성 CalibSet의 payload 한계(검증됨, synth_calibset.py:42-48).** `make_synthetic_calibset`은 빈 payload → line_noise·saturation은 이대로 구동, **geometry는 populated 왜곡 모델 필요**. geometry 검증은 (i) 활성 경로: `distortion_coeffs_x/y`+`calibration_residual >= geometry_activation_residual_px` 주입, (ii) 항등 경로: `calibration_residual < geometry_activation_residual_px` 주입 — 두 경로 모두 명시적으로 시험한다.
- **조합 시 상류 마스크 전제(검증됨).** saturation은 SATURATION 마스크가 있어야 밴드를 표시(없으면 no-op); line_noise의 SAT 보호(line_noise.py:212-221)·마스크 제외도 상류 마스크에 의존한다. 그룹 조합 검증은 입력 프레임이 이미 누적 SATURATION/DEFECT/INTERPOLATION 마스크를 지녔다고 가정한다(합성 주입 또는 offset/gain/defect 프리픽스 실행 결과). 마스크가 없는 합성 프레임에서는 saturation이 no-op임을 명시적으로 확인한다.
- **표시 도메인(검증됨).** 세 스테이지의 출력은 모두 **raw-DN 도메인**이다 — line_noise는 감산 후 raw-DN, saturation은 픽셀 무변경 raw-DN, geometry는 리샘플된 raw-DN(또는 항등). 그룹 5(mse/window, 정규화 [0,1] 표시 도메인, mse.py:107-115)와 달리 **역스케일 없이 16-bit `.raw` 왕복이 직접 성립**한다(저장 규약이 단순).
- **표시 경계(C-09, 검증됨 — D1 근거).** 골든의 현재 반환 표면은 before/after `XFrame`과 `HistoryEntry.extra`의 스칼라 diag다. 행/열 보정 배열과 역변위장은 반환되지 않는다. 이들은 현재 공개 알고리즘/결과가 아니므로 별도 FeatureId·control을 만들지 않는다. GUI는 실제 반환된 before/after/diff·mask·diag를 모두 표시하며 존재하지 않는 값을 가짜 기능으로 만들거나 UI 계산으로 생성하지 않는다.
- **데이터 가용성(검증됨, QUARANTINE 이슈 #29 / #33 대기).** 등록 edrogi SAMPLE(비정본)은 **프레임 소스 sanity**(유한·비퇴화·구조 성립)로만 사용 — 수치 golden/튜닝/적합 금지. 정본 수치 검증(EV 임계 대조)은 정본 지침세트(이슈 #33) 도착 후 별건이다.
- **환경.** Python은 `uv run`으로만 실행(`uv run pytest`, `uv run lint-imports`). 정확성·재현성이 목적이며 성능 최적화는 목적이 아니다(P2).

## Requirements (EARS)

### REQ-XGUI-LSG-TARGET — 구현 대상 경계

- **REQ-XGUI-LSG-TARGET-1 (Ubiquitous)** — 시스템은 `apps/xdet-console/` C# WPF 앱을 구현 대상으로 사용해야 하며, `apps/gui/`와 Python 테스트·패널은 계약 및 검증 선례로만 참조해야 한다. WPF는 Python 모듈을 직접 호출하지 않고 `IXdetEngine`/PythonNet seam을 경유해야 한다.

### REQ-XGUI-LSG-INPUT — 입력세트: 프레임 소스 + 스테이지별 구별 CalibSet

- **REQ-XGUI-LSG-INPUT-1 (Ubiquitous)** — 이 탭은 프레임 소스를 **상주 폴더 브라우저**(foundation §4: 폴더 트리 + 가상화 썸네일 그리드 + 형제 필름스트립 + 이전/다음)로 선택해야 하며, 파일을 지정해도 그 부모 폴더의 형제 목록을 컨텍스트로 함께 표시해야 한다. 기본 소스는 등록 실측 세트(edrogi SAMPLE / 향후 #33) 또는 합성 주입 프레임이며, 로더는 `common/io.py::load_raw_frame`(io.py:35, headerless 16-bit + `.json` 사이드카)을 사용해야 한다(합성 목업 사용자 탭 금지).
- **REQ-XGUI-LSG-INPUT-2 (Event-Driven)** — WHEN 사용자가 `line_noise` 스테이지를 검증하려 하면, THEN UI는 `CalibKind.LINE_NOISE` CalibSet을 스테이지 입력으로 수집해야 하며, 그 payload의 선택적 `reference_region` bool 마스크 **유무로 경로를 결정**(부재 → SWR-503 no-reference P1 경로, 존재 → SWR-501/502 reference 경로)함을 표시해야 한다 — 경로 선택은 `line_noise.process`가 수행하고 UI는 스스로 판정하지 않는다(C-09).
- **REQ-XGUI-LSG-INPUT-3 (Ubiquitous)** — `saturation` 스테이지 입력은 CalibSet payload를 요구하지 않으므로(`REQUIRED_PARAMS=()`, 마스크만 소비), UI는 `CalibKind.OTHER` placeholder CalibSet(`make_synthetic_calibset(resolution, CalibKind.OTHER)`)로 진입 게이트를 만족시키고, 밴드 표시에 필요한 SATURATION 마스크는 입력 프레임(상류 누적 또는 합성 주입)에서 온다는 것을 UI가 표시해야 한다.
- **REQ-XGUI-LSG-INPUT-4 (Event-Driven)** — WHEN 사용자가 `geometry` 스테이지를 검증하려 하면, THEN UI는 `CalibKind.OTHER` CalibSet에 **populated 왜곡 모델**(`distortion_coeffs_x`, `distortion_coeffs_y`, `calibration_residual`)을 수집해야 하며, 빈 payload placeholder는 `geometry.process`의 `calibration_residual` 부재 ValueError를 유발하므로 거부되어야 한다(활성/항등 판정을 위해 `calibration_residual`은 항상 필수).

### REQ-XGUI-LSG-PARAMS — 정확한 Params 키 (골든 REQUIRED_PARAMS 대조)

- **REQ-XGUI-LSG-PARAMS-1 (Ubiquitous)** — `line_noise` 스테이지 실행 시 UI는 `Params`에 `line_noise_profile_window`·`line_noise_highpass_cutoff`·`line_noise_contam_k`(line_noise.py:54 `REQUIRED_PARAMS`)를 제공해야 한다. window/cutoff은 항상, contam_k는 reference 경로에서 필수이며, 값 부재 시 골든이 던지는 `ValueError`("missing required parameter")를 UI가 은폐하지 않고 표면화해야 한다.
- **REQ-XGUI-LSG-PARAMS-2 (Optional)** — WHERE `saturation` 밴드 폭을 조정하는 기능을 제공하면, UI는 선택적 `saturation_band_width`(saturation.py:48, 모듈 기본 2)를 `Params`로 전달해야 하며, 미제공 시 모듈 기본값이 사용됨을 표시해야 한다(`REQUIRED_PARAMS=()`이므로 강제 키 없음).
- **REQ-XGUI-LSG-PARAMS-3 (Ubiquitous)** — `geometry` 스테이지 실행 시 UI는 `Params`에 `geometry_activation_residual_px`·`geometry_poly_degree`(geometry.py:65 `REQUIRED_PARAMS`)를 제공해야 하며, 선택적 `geometry_spline_order`·`geometry_inverse_iters`(모듈 기본 3/8)는 override로만 노출해야 한다.

### REQ-XGUI-LSG-VIEW — 이 그룹 고유의 뷰어 특성

- **REQ-XGUI-LSG-VIEW-1 (Ubiquitous)** — 이 탭은 세 스테이지 모두 **before/after/diff 이미지 + 마스크 오버레이 + 픽셀 probe(float32 정확값) + W/L**를 공통 제공해야 하며, 표시하는 모든 수치·처리 결과는 골든 엔진 산출이어야 한다(C-09, UI는 DSP 0). 세 스테이지 출력은 전부 raw-DN 도메인이므로 정규화 역스케일이 필요 없다(그룹 5와의 차이).
- **REQ-XGUI-LSG-VIEW-2 (State-Driven)** — WHILE `saturation` 결과를 표시하는 동안, UI는 `SATURATION`(코어) 마스크와 `SATURATION_BAND`(버퍼 밴드, 별개 비트) 오버레이를 **구분**해 표시해야 하며, 포화 픽셀 값이 변경되지 않았음을 diff가 0으로 확인해야 한다 — 포화 "복원"은 금지된다(SWR-602 [HARD]).
- **REQ-XGUI-LSG-VIEW-3 (State-Driven)** — WHILE `geometry`가 활성인 동안, UI는 before/after/diff, diag(`active`, `poly_degree`, `calibration_residual`) 및 geometry 전/후 `DEFECT` mask diff를 표시해야 한다. 엔진이 반환하지 않는 변위장/격자 워프 control은 만들지 않고 UI는 `_invert_field`나 좌표장을 재계산하지 않는다. WHILE 비활성인 동안 diff=0과 `active=false`를 표시한다.
- **REQ-XGUI-LSG-VIEW-4 (State-Driven)** — WHILE `line_noise` 결과를 표시하는 동안, UI는 before/after/diff, 실제 diag와 강건 통계 제외 mask 오버레이를 표시해야 한다. 엔진이 반환하지 않는 행/열 보정 곡선 control은 만들지 않고 UI는 주변차나 correction array를 재계산하지 않는다. SATURATION 픽셀의 diff=0도 표시한다.

### REQ-XGUI-LSG-RUN — build/apply 워크플로 (개별 → 조합 → 검증 모드)

- **REQ-XGUI-LSG-RUN-1 (Event-Driven)** — WHEN 사용자가 단일 스테이지(line_noise | saturation | geometry)를 선택하고 그 스테이지 고유의 CalibSet과 Params를 공급하면, THEN WPF는 `IXdetEngine.RunPipeline(PipelineRunRequest)`에 단일 stage를 전달해 **개별 구동**하고 입력/출력/diff/mask/diag를 표시해야 한다. `apps.gui` helper는 실행 경계로 사용할 수 없다.
- **REQ-XGUI-LSG-RUN-2 (Event-Driven)** — WHEN 사용자가 이 그룹의 정렬된 부분집합(예: `("line_noise","saturation","geometry")` — `CANONICAL_ORDER`의 유효 부분수열)을 선택하고 각 스테이지가 고유 CalibSet·Params를 지니면, THEN UI는 단일 심 파이프라인 실행(`run_pipeline`, SPEC-XSEAM-002 REQ-XSEAM-CONTRACT-6 진입점)을 요청하고 조합 출력과 각 스테이지 전/후를 함께 표시해야 한다 — 스테이지 정렬·조합은 `PipelineDefinition`(오케스트레이터)이 강제하고 UI가 재구현하지 않는다.
- **REQ-XGUI-LSG-RUN-3 (Event-Driven)** — WHEN 조합/부분집합 실행이 검증 모드(입력 `XFrame.validation_mode=True`)로 요청되면, THEN 심은 실행된 모든 스테이지의 중간 프레임(`XFrame.intermediates`)을 그 **단일 패스**에서 반환하고, UI는 추가 실행 없이 각 스테이지 전/후를 스크럽할 수 있어야 한다(orchestrator.py `validation_mode`→`intermediates` 소비).
- **REQ-XGUI-LSG-RUN-4 (Event-Driven)** — WHEN 사용자가 스테이지 결과를 저장하면, THEN UI는 `<name>_result.raw`, `xdet.frame-artifact/1.0` sidecar, mask가 있으면 `<name>_result_mask.raw`(`uint8` bitfield), 그리고 `xdet.run-manifest/1.0`을 사용자 지정 폴더에 저장해야 한다. sidecar는 resolution/dtype/byte_order/source_domain/export_domain/domain_max/quantization/mask를 포함하고 pixel과 mask 각각의 bit-exact round-trip을 검증한다. manifest는 input/calib/params/output hash를 포함한다. C# export choke point는 실행 전 `data/` 하위를 typed error로 거부한다.

### REQ-XGUI-LSG-DATA — 등록 edrogi 적용 가능성 (합성 vs #33)

- **REQ-XGUI-LSG-DATA-1 (Ubiquitous)** — line_noise·saturation·geometry는 전부 **합성 전용 / #33 대기**이므로, 이 탭의 정본 수치 검증 경로는 합성 주입 프레임(행/열 banding, 포화 코어, 다항 기하 왜곡)과 합성 CalibSet(line_noise reference/geometry 왜곡 모델)을 사용해야 한다.
- **REQ-XGUI-LSG-DATA-2 (Optional)** — WHERE 사용자가 등록 edrogi SAMPLE 프레임을 이 탭에 로드하면, UI는 그것을 **프레임 소스 sanity**(유한·비퇴화·구조 성립) 확인용으로만 사용해야 하고 수치 golden 도출·튜닝·적합에 쓰지 않아야 하며(QUARANTINE, 이슈 #29), 정본 수치 검증은 정본 지침세트(이슈 #33) 도착 후 별건임을 표시해야 한다.

### REQ-XGUI-LSG-GUARD — 불변 HARD 거부 가드 (foundation G-1~G-9 상속; G-9 탭=알고리즘 그룹은 이 탭 자체의 구성 전제)

- **REQ-XGUI-LSG-GUARD-1 (Unwanted)** — IF UI 또는 어댑터가 세 스테이지 중 어느 출력이든 스스로 계산하거나(C-09 위반), 스테이지를 스스로 정렬·조합하거나(C-11 위반), 결여된 스테이지별 CalibSet을 무단으로 합성·기본값 대체하면(SWR-000-5 위반), THEN 이는 거부되어야 한다 — 모든 DSP는 골든 엔진에, 조합/순서 권한은 Python 오케스트레이터에 남는다.
- **REQ-XGUI-LSG-GUARD-2 (Unwanted)** — IF 요청된 부분집합이 `CANONICAL_ORDER`의 부분수열이 아니거나(→ `PipelineOrderError`) 선택 스테이지가 해상도·panel_id·kind 일치 CalibSet을 결여하면(→ `CalibrationError`), THEN 실행은 오케스트레이터의 명시적 오류로 거부되고 어떤 기본 캘리브레이션도 대체되지 않아야 한다(SWR-000-2 + SWR-000-5 보존).
- **REQ-XGUI-LSG-GUARD-3 (Unwanted)** — IF 저장 경로가 `data/` 하위를 가리키면, THEN C# export choke point가 실행 전에 typed validation error로 거부해야 한다(C-20). WPF/adapter는 Python `guard_output_path`를 직접 호출하지 않는다.

### REQ-XGUI-LSG-COVERAGE — 세 처리 알고리즘 도달성

- **REQ-XGUI-LSG-COVERAGE-1 (Ubiquitous)** — `proc.line-noise`, `proc.saturation`, `proc.geometry`는 각각 고유 FeatureId·Params/CalibSet manifest·RunPipeline request·ViewModel action·TC 112/113/114를 가져야 한다.
- **REQ-XGUI-LSG-COVERAGE-2 (Event-Driven)** — WHEN strict 사용자 Frame/CalibSet/Params가 제공되면 THEN 등록 데이터 부재와 무관하게 각 알고리즘과 정렬 조합을 실행하고 결과를 `USER_SUPPLIED_UNVERIFIED`로 기록해야 한다.

## Exclusions (What NOT to Build)

- **골든 모델 변경 없음** — `modules/line_noise.py`·`modules/saturation.py`·`modules/geometry.py`·`pipeline/`·`common/`·`metrics/`는 동결 오라클로 편집하지 않는다. 세 `process`의 시그니처·상수·경로 선택 로직·`REQUIRED_PARAMS`를 변경하지 않으며 읽기 전용으로 소비한다(REQ-XGUI-LSG-GUARD-1).
- **UI측 DSP·조합 재구현 없음** — line_noise 경로 선택, 포화 밴드 팽창, 기하 역변환장/리샘플을 UI가 재구현하지 않는다. 경로 선택은 `line_noise._has_reference`, 활성 판정은 `geometry.process`의 residual 비교가 수행한다.
- **포화 복원 없음(SWR-602 [HARD])** — saturation 탭은 포화 픽셀을 외삽·재구성하지 않는다. 밴드 표시만 하고 픽셀 값은 무변경으로 확인한다.
- **명목 grid/왜곡 파라미터 지어내기 없음** — geometry 왜곡 모델·line_noise 파라미터를 실측 대신 임의값으로 하드코딩하지 않는다. 합성 검증은 명시적 합성 주입값을, 정본은 #33/실측 CalibSet을 사용한다.
- **신규 파이프라인 스테이지·CalibKind 없음** — 조합은 기존 `CANONICAL_ORDER`(line_noise/saturation/geometry)·기존 CalibKind(LINE_NOISE/OTHER)로만 이뤄진다.
- **정본 수치 검증 없음(QUARANTINE)** — edrogi SAMPLE 구동은 sanity 확인이며 EV 임계 도출·튜닝·적합에 쓰지 않는다(이슈 #29). 정본 수치 검증은 #33 도착 후 별건이다.
- **그룹 5 정규화 도메인 역스케일 없음** — 이 그룹은 raw-DN 도메인만 다룬다. 정규화 [0,1] 표시 도메인의 16-bit 역스케일(mse/window)은 그룹 5(Enhancement) SPEC 몫이다.
- **C++ 엔진 이식·성능 최적화 없음** — 트랜스포트 정확성·조합 정합성 증명이 목적이며, C++/C ABI 네이티브 엔진과 마샬링 최적화는 XSEAM Stage 2(P2) 범위 밖이다.

## 확정 결정 (v0.5.1)

1. Geometry 합성 기준은 `tests/modules/phantoms/linesat.py`의 기존 fixture preset을 사용한다. UI가 임의 coefficient scale을 알고리즘 기본값으로 만들지 않는다.
2. Line-noise reference-region 경로는 advanced 옵션이고 no-reference 경로가 기본 흐름이다.
3. 실제 실행의 mask는 Calibration 출력에서 우선 전달하며 synthetic mask injection은 시험 전용으로 한정한다.
4. mask가 존재하는 결과는 공통 `<name>_result_mask.raw` uint8 파일과 flag map sidecar로 저장한다.
5. 중앙 TC 레지스트리는 G3 블록 XDET-TC-112~119이다.

## v0.5.1 public operation closure

| Python EntryPoint | GUI 노출 | TC |
|---|---|---|
| `modules.line_noise.process` | Line-noise action(reference/no-reference) | 112, 115~119 |
| `modules.saturation.process` | Saturation action | 113, 115~119 |
| `modules.geometry.process` | Geometry action | 114~119 |

세 행의 actual XFrame/history/mask/diag만 표시한다. golden이 반환하지 않는 curve/vector를 별도 기능으로 만들지 않는다.
