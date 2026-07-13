---
id: SPEC-XGUI-LAG
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
labels: [xgui, gui-redesign, verification-gui, lag, afterglow, sequence, irf, golden-frozen]
---

# SPEC-XGUI-LAG — Lag(잔상 보정) 그룹 GUI 검증 탭 (WP2, 시퀀스 뷰어 + IRF 피팅)

> 본 사양은 `../SPEC-XGUI-MASTER/baseline-control.md`의 G0와 `traceability-matrix.md`를 상속한다. 사용자 승인·기준선 동결·`implementation_authorized=true` 전에는 구현 입력으로 실행하지 않으며, 승인 뒤 규범 변경은 버전 상승과 재승인을 요구한다.

XDET 검증 GUI 재설계(이슈 #58)의 **알고리즘 그룹 2 — Lag(잔상 보정)** 탭 명세다. 공유 사실은 [SPEC-XGUI-MASTER/foundation.md](../SPEC-XGUI-MASTER/foundation.md)에 있으며 본 SPEC은 그 팩트를 재기술하지 않고 **그룹 2 고유의 입력세트·Params·뷰어 특성·build/apply 워크플로·데이터 가용성**만 명세한다. frontmatter/구조는 [SPEC-XSEAM-002](../SPEC-XSEAM-002/spec.md)를 미러링한다.

**이 그룹이 다른 모든 그룹과 근본적으로 다른 점:** lag는 **P1에서 유일하게 상태를 프레임 간에 나르는 처리 모듈**(SWR-000-7 명시 허용 예외, `modules/lag.py:10-14`)이다. 따라서 검증 대상은 단일 프레임 in/out이 아니라 **연속 캡처 시퀀스**(시간축)이며, 골든은 단일 프레임 `run_pipeline` 반복이 아니라 시퀀스당 하나의 상태형 `LagCorrector`를 쓰는 `pipeline/sequence.py::run_sequence`(sequence.py:89)로 이를 구동한다. 부수적으로 lag는 **CalibSet(LAG)의 IRF 계수 `(a_i, b_i)`로 완전히 결정**되며(모듈은 `[T]/[P]` 튜닝 상수를 전혀 노출하지 않음 — `modules/lag.py:60-63`, `REQUIRED_PARAMS = ()`), 그 IRF를 **다중 노출 step-response에서 적합하는 오프라인 도구** `metrics/lag_irf.py::fit_lag_irf`(lag_irf.py:72)가 별도로 존재한다. 그래서 이 탭은 다른 그룹의 "모듈 실행 탭"과 달리 **(A) IRF build 서브워크플로 + (B) 시퀀스 apply 서브워크플로**의 2단 구조를 갖는다.

- 근거(변경 없음, 소비만): `modules/lag.py::LagCorrector.process(frame, calib, params) -> XFrame`(상태형 인스턴스 메서드, lag.py:127) · `pipeline/sequence.py::run_sequence`(시퀀스당 1개 `LagCorrector`, FB 트리거 핸드셰이크, sequence.py:89) · `metrics/lag.py::compute_first_frame_lag`(lag.py:38) / `compute_ghost_cnr`(lag.py:144) · `metrics/lag_irf.py::fit_lag_irf`(lag_irf.py:72) + `StepResponse`(lag_irf.py:50) · `common/calibset.py`의 `K_IRF_A="irf_a"`/`K_IRF_B="irf_b"`(calibset.py:82-84, `CalibKind.LAG`) · `pipeline/orchestrator.calib_kind_for_stage("lag") -> CalibKind.LAG`(함수 정의 orchestrator.py:165; `_KIND_BY_STAGE` 배선 `"lag":"lag"` orchestrator.py:152).
- 상속 원칙: SPEC-XGUI-MASTER §1 불변 HARD 제약 G-1~G-9 전수 상속(골든 FROZEN 호출만 / C-09 UI DSP 0 / C-11 단방향 소비 / C-20 사용자 폴더 export / QUARANTINE / SWR-000-2 순서 / SWR-000-5 기본값 대체 금지 / 시임 = `run_pipeline` 미러 / 탭=그룹별). 조합/순서/상태 리셋 권한은 **Python 오케스트레이터와 `run_sequence`에 남는다** — C#/UI는 스테이지를 스스로 정렬·조합하거나 lag 상태를 스스로 진행시키지 않는다.
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.2.0 (2026-07-13)** — 중단 작업 복구 마무리. 구현 대상을 C# WPF `apps/xdet-console/`로 확정하고 Python `apps/gui/`는 참조 선례로 한정했다. 그룹별 결정·중앙 TC 레지스트리·plan/research를 확정했다. 골든 알고리즘은 변경하지 않는다.

- **v0.1.1 (2026-07-12)** — 라운드 1 교차검증(audit-r1.md, verdict FAIL@0.86) 반영. 골든 소스 재대조로 5개 결함 교정: **(D1, MAJOR)** REQ-XGUI-LAG-VIEW-3의 "시간축 신호 곡선" 출처 공백 해소 — `compute_first_frame_lag`는 스칼라 4종만 반환하고 프레임별 `signals`(metrics/lag.py:58)를 반환하지 않음을 확인, VIEW-3을 **엔진 반환 스칼라 전용 판정**으로 한정하고, 표시용 시간축 곡선은 신설 REQ-XGUI-LAG-VIEW-6에서 골든 primitive `common.robust_stats.robust_mean`(엔진 `_frame_signal`이 쓰는 동일 호출, metrics/lag.py:34-35 / common/robust_stats.py:22) 소비로만 한정(C-09 "UI DSP 0" 경계 명시). **(D2, MINOR)** VIEW-5에 감쇠 곡선 = 알려진 계수의 모델 평가(표시)이지 계수 산출·적합이 아님(적합은 `fit_lag_irf` 골든)을 명시. **(D3, MINOR)** HISTORY provenance 귀속 정정 — `lag_calib` 선례는 `CalibProvenance(created_at="2026-07-09", source="synthetic")`(note 미설정, lag_seq.py:71)이며, `sample=true`는 ingest SAMPLE의 `provenance.note`(ingest_edrogi.py:67)로 별개 출처. **(D4, MINOR)** REQ-XGUI-LAG-DATA-2 정밀화 — `sample=true`는 boolean 필드가 아니라 `provenance.note` 부분문자열, `CalibProvenance`는 `created_at`/`source`/`note` 3필드뿐(calibset.py:114-116). **(D5, MINOR)** 라인 인용 정정 — `calib_kind_for_stage` 함수 정의 orchestrator.py:165(배선 :152), `StepResponse` class def lag_irf.py:50.
- **v0.1.0 (2026-07-12)** — 초안 생성. GitHub 이슈 #58(GUI 재설계). SPEC-XGUI-MASTER foundation 그룹 2. 저작 시 **AUTHORITATIVE 소스로 대조검증한 사실**: (a) `LagCorrector.process`는 `process(self, frame, calib, params)` **인스턴스 메서드**(bare 콜러블이 아님)이며 `default_registry()`가 lag에 대해 반환하는 것은 `LagCorrector()` **인스턴스**다 — `run_pipeline`용 레지스트리는 `build_pipeline_registry()`(pipeline_panel.py:47-49)가 `{name: module.process}`로 어댑트하나, 이는 **단일 공유 인스턴스의 `.process`를 바인딩**하므로 상태가 호출 간에 누적된다. 시퀀스 정확성은 반드시 `run_sequence`의 `registry_factory`(매 시퀀스 fresh `{"lag": LagCorrector().process}` — lag_seq.py:42-48 `lag_factory` 선례)로 얻는다. (b) lag 스테이지는 **populated IRF CalibSet(LAG)** 필수: `LagCorrector.process`가 `_load_irf`(lag.py:82-97)로 `irf_a`/`irf_b` 키를 요구하며 결여 시 `LagCalibError`(lag.py:70). **`make_synthetic_calibset(shape, CalibKind.LAG)`는 payload `{}`(빈 딕트, synth_calibset.py:48)를 반환하므로 lag에는 그대로 쓸 수 없다** — 다른 그룹의 빈 placeholder 통과 패턴과 갈리는 지점. IRF 값이 실린 CalibSet은 `fit_lag_irf`(정본 후보) 또는 명시적 비정본 placeholder(lag_seq.py:51-72 `lag_calib` 선례, provenance = `CalibProvenance(created_at="2026-07-09", source="synthetic")` — `note` 미설정, lag_seq.py:71)로만 얻는다. **주의**: 등록 에드로지 SAMPLE의 비정본 마커 `sample=true`는 ingest 산출물의 `provenance.note`(`SAMPLE_PROVENANCE_NOTE`, ingest_edrogi.py:67)이지 `lag_calib`의 것이 아니다 — 두 출처(합성 placeholder IRF vs 등록 SAMPLE 맵)를 혼동하지 않는다. (c) `REQUIRED_PARAMS = ()`(lag.py:63) — lag 모듈은 튜닝 Params가 없다; Params는 이력 해시용으로만 통과(lag.py:130-133). **Params 키를 요구하는 것은 지표 엔진**(`metrics/lag.py`)이지 모듈이 아니다. (d) 등록 GHOST 폴더는 `_CATEGORY_BY_FOLDER["GHOST"]="ghost_lag"`(ingest_edrogi.py:87) 원시 프레임일 뿐 **ingest가 LAG CalibSet을 만들지 않는다**(ingest는 offset/gain/defect 맵만 생성) — 등록 실측 lag 구동은 원시 시퀀스 + 비정본 placeholder IRF에 한함(정본 IRF #33 대기). (e) SATURATION 픽셀은 출력값 보존하되 내부 재귀는 계산된 `I_hat`으로 진행(lag.py:149-161, SWR-602 정신/REQ-LAG-CORR-5). (f) `run_sequence`는 FB(forward-bias) 트리거 핸드셰이크 소유 — `confirm()`이 falsy면 `FBTriggerError`(sequence.py:48), 기본 `NoOpFBTrigger`. 확정 설계 결정: IRF build(다중 노출 step-response → `fit_lag_irf`)와 시퀀스 apply(`run_sequence`)를 한 탭의 2개 서브패널로 분리하고, UI/어댑터는 IRF 계수를 스스로 산출하지 않으며(피팅은 `fit_lag_irf` 골든), lag 상태를 스스로 진행시키지 않는다(재귀는 `LagCorrector`).

## Environment / Assumptions

- **본 SPEC은 T-스테이지가 아니다.** `modules/lag.py`·`pipeline/sequence.py`·`metrics/lag.py`·`metrics/lag_irf.py`·`common/calibset.py`(LAG 페이로드)·`pipeline/orchestrator.py`(순서/게이트/`calib_kind_for_stage`)는 동결 오라클로 편집하지 않는다. 본 SPEC은 그 위에 **읽기-실행 전용 검증 탭**을 additive로 얹는다(SPEC-VIEWER-001 → SPEC-XGUI-MASTER 계보).
- **시퀀스가 검증 단위다(그룹 고유).** 다른 그룹은 단일 프레임 before/after가 기본이지만, lag는 `frames: Sequence[XFrame]`(sequence.py:90) 전체가 하나의 입력이다. 프레임 k의 최종 상태가 프레임 k+1을 시드하며(REQ-LAG-STATE-5), 새 시퀀스는 fresh `LagCorrector` = 시퀀스 간 리셋(REQ-LAG-STATE-4; `LagCorrector` 도크스트링 lag.py:100-108). 별도 리셋 프로토콜 메서드는 없다.
- **lag는 populated IRF CalibSet(LAG) 없이 구동 불가.** `LagCorrector.process`가 `_load_irf(calib)`로 `irf_a`/`irf_b`를 요구; 결여 시 `LagCalibError`(무단 기본 IRF 대체 금지, SWR-000-5, lag.py:70-75). 따라서 이 탭은 스테이지 실행 전에 **유효한 IRF CalibSet**을 반드시 확보한다 — 출처는 (i) `fit_lag_irf` 산출물, (ii) 디스크의 측정 CalibSet(LAG)(정본, #33 대기), (iii) 명시적 비정본 placeholder IRF(합성/sanity 전용). 빈 `make_synthetic_calibset(_, LAG)`는 이 탭에서 사용 금지.
- **모듈은 튜닝 Params가 없다.** `modules/lag.py`의 `REQUIRED_PARAMS = ()`(lag.py:63). lag 스테이지 Params는 이력 해시 결정성용으로만 통과된다(lag.py:130-133). **Params 키를 요구하는 것은 지표 엔진**(아래 REQ-XGUI-LAG-METRIC): `metrics/lag.py`의 `compute_first_frame_lag`가 `lag_settle_frac`·`lag_plateau_frac`(`require_param`, 필수), `lag_dark_baseline`·`lag_exposure_end_index`·`lag_min_exposed_signal`(선택)를 소비(lag.py:27-31, :75/:95/:114). `compute_ghost_cnr`는 Params를 메타데이터 통과로만 사용(lag.py:144-191).
- **실측 데이터 가용성(SAMPLE·비정본, QUARANTINE 이슈 #29).** 등록 실측(에드로지 SAMPLE)에서 lag 관련 자산은 `GHOST` 폴더(`ghost_lag` 카테고리, ingest_edrogi.py:87) **원시 프레임뿐**이며, ingest는 이 폴더로 **LAG CalibSet을 만들지 않는다**(offset/gain/defect 맵만 생성, foundation §2 그룹 1). 그러므로 등록 GHOST 시퀀스에 lag 보정을 걸려면 **비정본 placeholder IRF**(clearly-labeled: `lag_calib` 선례처럼 `provenance.source="synthetic"`, lag_seq.py:71)가 필요하고, 그 결과는 **sanity(유한·비퇴화·구조 성립) 확인일 뿐 수치 골든/EV 임계 도출·튜닝·적합에 쓰지 않는다**(등록 GHOST **원시 프레임** 자체의 비정본 마커 `sample=true`는 그 프레임 ingest 산출물의 `provenance.note`(ingest_edrogi.py:67)이며, placeholder IRF CalibSet의 provenance와는 별개다). 정본 IRF와 정밀 첫프레임 lag/ghost CNR 판정은 정본 지침세트(이슈 #33) 도착 후 별건이다.
- **합성 검증 경로.** 실측 도착 전 엔진/탭 자체 검증은 합성 데이터로 한다: 알려진 IRF `(a_i, b_i)`로 forward-lag 오염 시퀀스를 만들고(matched-IRF 전제, tests/modules/phantoms/lag_seq.py 선례), 동일 IRF 보정이 이를 역전함을 확인. IRF build 서브워크플로도 **합성 다중 노출 step-response에서 알려진 IRF를 회복**함으로써 검증한다(REQ-LAG-IRF-3, `fit_lag_irf`의 rel-RMS 게이트 lag_irf.py:141).
- **조합/순서/상태 권한은 골든에 남는다.** 고정 정준 순서(SWR-000-2)와 캘리브레이션 진입 게이트(SWR-000-5)는 `PipelineDefinition.__post_init__`와 `_calibration_gate`가, 시퀀스 상태 수명과 리셋은 `run_sequence`의 fresh-registry 규약이, IRF 재귀는 `LagCorrector`의 SWR-402 재귀가 강제한다. UI/어댑터는 이들을 스스로 재구현하지 않는다.
- **저장/열기 규약(foundation §3·§4 상속).** 저장 = 프레임별 `xdet.frame-artifact/1.0` + 선택 mask + 시퀀스 수준 `xdet.run-manifest/1.0`; C# export choke point가 `data/` 하위를 거부한다. 열기는 형제 시퀀스 로딩이 1급 시나리오다.
- **환경.** Python은 `uv run`으로만 실행(`uv run pytest`, `uv run lint-imports`). 정확성·재현성이 목적이며 성능/마샬링 최적화는 목적이 아니다.

## Requirements (EARS)

### REQ-XGUI-LAG-TARGET — 구현 대상 경계

- **REQ-XGUI-LAG-TARGET-1 (Ubiquitous)** — 시스템은 `apps/xdet-console/` C# WPF 앱을 구현 대상으로 사용해야 하며, `apps/gui/`와 Python 테스트·패널은 계약 및 검증 선례로만 참조해야 한다. WPF는 Python 모듈을 직접 호출하지 않고 `IXdetEngine`/PythonNet seam을 경유해야 한다.

### REQ-XGUI-LAG-INPUT — 입력세트: 프레임 시퀀스 + IRF CalibSet 선택 (G-1/G-5, SWR-000-5)

- **REQ-XGUI-LAG-INPUT-1 (Ubiquitous)** — 탭은 lag 검증의 입력으로 **정렬된 프레임 시퀀스**(`list[XFrame]`, 캡처 순서)와 **하나의 CalibSet(LAG)**을 요구해야 하며, 시퀀스는 `common/io.py::load_raw_frame`(headerless 16-bit + `.json` 사이드카)로 적재된 형제 프레임 집합으로 구성해야 한다(단일 프레임 in/out이 아님).
- **REQ-XGUI-LAG-INPUT-2 (Event-Driven)** — WHEN 사용자가 폴더 브라우저에서 한 프레임을 지정하면, THEN 탭은 그 부모 폴더의 형제 프레임을 프레임 인덱스 순으로 정렬한 **시퀀스 후보**로 함께 표시해 사용자가 시퀀스 경계(시작/끝 프레임)를 선택할 수 있어야 한다(foundation §4 형제 컨텍스트 유지의 시퀀스 확장).
- **REQ-XGUI-LAG-INPUT-3 (Ubiquitous)** — 탭은 IRF CalibSet(LAG)의 출처를 세 가지 중 하나로 명시적으로 선택하게 해야 한다: (a) 이 탭의 IRF build 서브워크플로가 산출한 `fit_lag_irf` 결과, (b) 디스크에서 적재한 측정 CalibSet(LAG)(정본, #33 대기), (c) 명시적 **비정본 placeholder IRF**(합성/sanity 전용, provenance에 비정본 라벨). 선택된 CalibSet은 `kind == CalibKind.LAG`이고 `irf_a`/`irf_b` 페이로드를 보유해야 한다(calibset.py:82-84).
- **REQ-XGUI-LAG-INPUT-4 (Unwanted)** — IF 선택된 lag CalibSet이 `irf_a`/`irf_b` 페이로드를 결여하면(예: 빈 `make_synthetic_calibset(_, LAG)`), THEN 실행은 골든의 명시 오류 `LagCalibError`로 거부되어야 하며, UI는 어떤 기본 IRF도 합성하거나 대체하지 않아야 한다(SWR-000-5; 결여 키 이름을 그대로 사용자에게 표면화).

### REQ-XGUI-LAG-VIEW — 그룹 고유 뷰어: 시퀀스 스크러버 + lag/ghost 지표 곡선 (C-09, G-9)

- **REQ-XGUI-LAG-VIEW-1 (Ubiquitous)** — 이 탭의 1급 뷰어는 **다중 프레임 시퀀스 스크러버**(시간축 프레임 순회)여야 하며, 각 프레임의 보정 전/후 이미지와 프레임 인덱스를 함께 제시해 사용자가 시퀀스를 프레임 단위로 스크럽할 수 있어야 한다(단일 before/after 정지 이미지가 중심인 그룹 1/3과 구별되는 뷰어 특성).
- **REQ-XGUI-LAG-VIEW-2 (Event-Driven)** — WHEN 시퀀스가 검증 모드(입력 `XFrame.validation_mode=True`)로 구동되면, THEN 탭은 추가 실행 없이 각 프레임의 보정 전/후를 스크럽할 수 있어야 하고(단일 패스 중간 프레임), 모든 표시 수치는 골든 엔진 산출값이어야 한다(C-09, UI DSP 0).
- **REQ-XGUI-LAG-VIEW-3 (Event-Driven)** — WHEN 사용자가 시퀀스에 대한 first-frame lag 지표를 요청하면, THEN 탭은 `metrics/lag.py::compute_first_frame_lag`가 **반환한 스칼라**(`MetricResult.values`의 `first_frame_lag_pct`·`last_exposed_index`·`first_residual_index`·`dark_baseline`, lag.py:126-141)만을 판정 수치로 표시해야 하며, 이 값들을 UI가 재계산하거나 임의로 유도해서는 안 된다(C-09; 엔진 반환값 그대로 표면화). 이 엔진은 프레임별 신호 배열(`compute_first_frame_lag` 내부 `signals`, lag.py:58)을 반환하지 않으므로, 탭은 판정에 존재하지 않는 곡선 접근자를 전제하지 않는다.
- **REQ-XGUI-LAG-VIEW-4 (Event-Driven)** — WHEN 사용자가 ghost CNR 지표를 요청하고 전경/배경 ROI(각 `(top,left,height,width)`)를 지정하면, THEN 탭은 `metrics/lag.py::compute_ghost_cnr`가 산출한 `ghost_cnr = |mean_fg-mean_bg|/std_bg`(lag.py:177)와 ROI 오버레이를 표시해야 한다.
- **REQ-XGUI-LAG-VIEW-5 (Optional)** — WHERE 사용자가 IRF 계수를 검토하려 하면, THEN 탭은 선택된 CalibSet(LAG)의 지수합 IRF `h[n]=Σ a_i·b_i^n`(M=3~4)을 **감쇠 곡선 플롯**으로 시각화하고 계수 `(a_i, b_i)`와 provenance(정본/비정본 라벨, fit-quality note)를 함께 제시할 수 있어야 한다. 이 감쇠 곡선은 CalibSet에 이미 실린 계수 `(a_i, b_i)`의 **모델 평가(표시)** 일 뿐이며 계수 산출·적합이 아니다 — 계수 산출/적합은 `fit_lag_irf` 골든(REQ-XGUI-LAG-IRF)에만 있고 UI는 이를 재구현하지 않는다(C-09 "UI DSP 0" 경계 안: 알려진 계수의 표시용 평가 = 소비, 재구현 아님).
- **REQ-XGUI-LAG-VIEW-6 (Optional)** — WHERE 사용자가 first-frame lag의 노출 플래토 → 잔상 감쇠 구조를 **시간축 신호 곡선**으로 보려 하면, THEN 탭은 그 프레임별 축약을 골든 primitive `common.robust_stats.robust_mean` 호출로만 산출해야 하며(엔진의 `_frame_signal`이 프레임 신호로 쓰는 바로 그 primitive — `robust_stats.robust_mean(np.asarray(frame.pixel, dtype=np.float64))`, metrics/lag.py:34-35, common/robust_stats.py:22), UI가 자체 축약(mean/median 등)이나 지표 재구현으로 이 곡선을 만들어서는 안 된다. 이 곡선은 **표시 보조**이며 판정 수치가 아니다 — first-frame lag 판정은 오직 REQ-XGUI-LAG-VIEW-3의 엔진 반환 스칼라가 소유한다(C-09 경계: 골든 primitive 호출 = 소비, UI DSP 0 유지).

### REQ-XGUI-LAG-IRF — IRF build 서브워크플로: 다중 노출 step-response → CalibSet(LAG) (SWR-401, `fit_lag_irf`)

- **REQ-XGUI-LAG-IRF-1 (Event-Driven)** — WHEN 사용자가 IRF build 서브워크플로에 **2개 이상의 노출 레벨**에 대한 step-response(각 `StepResponse(amplitude, residual)`, lag_irf.py:49)를 공급하면, THEN 탭은 `metrics/lag_irf.py::fit_lag_irf(step_responses, m_terms=…, panel_id=…, resolution=…, valid_from=…, valid_until=…)`(lag_irf.py:72)를 호출해 CalibSet(LAG)을 산출해야 하며, 피팅 자체는 UI가 아니라 골든 도구가 수행해야 한다(C-09).
- **REQ-XGUI-LAG-IRF-2 (Unwanted)** — IF 공급된 노출 레벨이 1개뿐이면, THEN 실행은 골든의 명시 오류 `LagIRFCalibrationError`("single-exposure calibration is forbidden", SWR-401, lag_irf.py:94-98)로 거부되어야 하며, UI는 단일 노출로 IRF를 추정하지 않아야 한다.
- **REQ-XGUI-LAG-IRF-3 (Unwanted)** — IF 적합이 수렴하지 않거나 상대 RMS 잔차가 허용치(`rms_residual_tol` [T])를 초과하면(lag_irf.py:141-147), THEN 산출은 `LagIRFCalibrationError`로 거부되어야 하고 탭은 결함 CalibSet을 방출하거나 표시하지 않아야 한다(degenerate/non-LTI 곡선 차단).
- **REQ-XGUI-LAG-IRF-4 (Event-Driven)** — WHEN IRF build가 성공하면, THEN 탭은 산출 CalibSet의 계수 `(a_i, b_i)`와 provenance의 fit-quality note(`status`/`rel_rms_residual`/`m_terms`/`n_exposures`, lag_irf.py:158-162)를 표시하고, 그 CalibSet을 REQ-XGUI-LAG-INPUT-3(a) 경로로 apply 서브워크플로에 넘길 수 있어야 한다.

### REQ-XGUI-LAG-APPLY — apply 서브워크플로: `run_sequence` 상태형 구동 (SWR-000-7, C-11)

- **REQ-XGUI-LAG-APPLY-1 (Event-Driven)** — WHEN 사용자가 프레임 시퀀스와 IRF CalibSet으로 lag 보정을 실행하면, THEN WPF는 `IXdetEngine.RunSequence(SequenceRunRequest)`를 한 번 호출해야 한다. PythonNet adapter가 `run_sequence(..., registry_factory, ...)`에 위임하며 단일 `RunPipeline` 반복이나 UI 상태 진행은 금지한다.
- **REQ-XGUI-LAG-APPLY-2 (Ubiquitous)** — apply 실행은 시퀀스당 **fresh 상태형 lag 인스턴스**를 쓰는 `registry_factory`(매 호출 새 `{"lag": LagCorrector().process}` 산출, lag_seq.py:42-48 `lag_factory` 선례)를 공급해야 하며, `build_pipeline_registry()`가 반환하는 **단일 공유 `LagCorrector` 인스턴스**를 재사용해서는 안 된다(공유 인스턴스는 상태가 시퀀스 경계를 넘어 누적되어 리셋 규약 REQ-LAG-STATE-4를 위반).
- **REQ-XGUI-LAG-APPLY-3 (State-Driven)** — WHILE 한 시퀀스가 진행되는 동안 탭은 동일 `LagCorrector` 인스턴스를 프레임 k→k+1로 유지해 상태 `{s_i}`가 전방으로 이어지게 해야 하며, 새 시퀀스를 시작할 때는 `registry_factory`를 재호출해 상태를 초기화(s_i[-1]=0)해야 한다(시퀀스 간 리셋 = 새 인스턴스).
- **REQ-XGUI-LAG-APPLY-4 (Ubiquitous)** — apply 실행은 SATURATION 픽셀의 **출력값 보존**(하위-포화값 발명 금지, SWR-602 정신)과 그 픽셀의 내부 상태를 계산된 `I_hat`으로 진행시키는 골든 규약(lag.py:149-161, REQ-LAG-CORR-5)을 그대로 표면화해야 하며, UI는 포화 픽셀을 "복원"하지 않아야 한다.
- **REQ-XGUI-LAG-APPLY-5 (Optional)** — WHERE forward-bias(FB) 트리거 인터페이스가 관여하면(SWR-404), THEN 탭은 `run_sequence`의 FB 핸드셰이크를 소비하되 실제 FB 캡처는 패널 펌웨어 소관임을 존중해야 하며, `confirm()` 실패 시 골든의 `FBTriggerError`(sequence.py:48)를 표면화하고 시퀀스를 진행하지 않아야 한다(기본 `NoOpFBTrigger`).

### REQ-XGUI-LAG-METRIC — 지표 Params 계약: 판정 상수는 지표 엔진 소유 (C-09)

- **REQ-XGUI-LAG-METRIC-1 (Ubiquitous)** — 탭은 lag **모듈**에 대해 어떤 튜닝 Params도 요구하거나 노출해서는 안 된다(`modules/lag.py::REQUIRED_PARAMS = ()`, lag.py:63); lag Params는 이력 해시 결정성 목적으로만 통과되어야 한다.
- **REQ-XGUI-LAG-METRIC-2 (Event-Driven)** — WHEN first-frame lag 지표를 산출하면, THEN 탭은 필수 Params 키 `lag_settle_frac`·`lag_plateau_frac`(`compute_first_frame_lag`의 `require_param`, lag.py:75/:95)를 수집해 지표 엔진에 전달해야 하고, 선택 키 `lag_dark_baseline`·`lag_exposure_end_index`·`lag_min_exposed_signal`(lag.py:67/:87/:114)이 있으면 함께 전달해야 하며, 이 값들을 UI가 자체 계산하지 않아야 한다(C-09; 판정 상수는 외부 주입).
- **REQ-XGUI-LAG-METRIC-3 (Unwanted)** — IF first-frame lag 시퀀스가 정착된 dark tail을 갖지 않거나(잔상이 마지막 프레임에서 여전히 감쇠 중) 노출 플래토가 검출 레벨 위에 없으면, THEN 지표 산출은 골든의 명시 오류 `MetricReadError`(lag.py:80-83/:99-101)로 거부되어야 하며, UI는 임의의 argmax/마지막 프레임 기본값으로 이를 우회하지 않아야 한다.

### REQ-XGUI-LAG-EXPORT — 저장: `<name>_result.raw` + 사이드카 (C-20, foundation §3)

- **REQ-XGUI-LAG-EXPORT-1 (Event-Driven)** — WHEN 사용자가 보정 시퀀스를 저장하면, THEN 탭은 캡처 순서를 보존하는 고정 폭 frame_index 파일명으로 각 frame의 `xdet.frame-artifact/1.0` raw/sidecar와 mask artifact를 저장하고, sequence-level `xdet.run-manifest/1.0`에 ordered input/output hashes, IRF calib hash, params hash, frame_count를 기록해야 한다.
- **REQ-XGUI-LAG-EXPORT-2 (Unwanted)** — IF 저장 경로가 `data/` 하위이면, THEN C# export choke point가 실행 전에 typed validation error로 거부해야 한다. WPF/adapter는 Python `guard_output_path`를 직접 호출하지 않는다(C-20).
- **REQ-XGUI-LAG-EXPORT-3 (Optional)** — WHERE 시퀀스 전체를 저장하면, THEN 탭은 프레임 인덱스를 보존하는 명명 규약으로 다중 프레임을 일괄 내보낼 수 있어야 하며(캡처 순서 재적재 가능), 각 프레임마다 `.raw`+`.json` 쌍을 산출해야 한다.

### REQ-XGUI-LAG-DATA — 등록 실측(에드로지 GHOST) 가용성: QUARANTINE (G-5)

- **REQ-XGUI-LAG-DATA-1 (Ubiquitous)** — 탭은 등록 실측 lag 자산으로 **`GHOST` 폴더(`ghost_lag`) 원시 시퀀스만** 소비할 수 있음을 명시해야 하며, ingest가 이 폴더로 LAG CalibSet을 만들지 않으므로(ingest_edrogi.py는 offset/gain/defect 맵만 생성) 등록 GHOST 구동에는 별도의 IRF CalibSet(비정본 placeholder 또는 정본 #33)이 반드시 짝지어져야 한다.
- **REQ-XGUI-LAG-DATA-2 (Unwanted)** — IF 등록 GHOST 시퀀스 + 비정본 placeholder IRF 구동 결과를 수치 골든/EV 임계 도출·튜닝·적합에 사용하려 하면, THEN 이는 거부되어야 한다(QUARANTINE 이슈 #29; SAMPLE은 sanity=유한·비퇴화·구조 성립 확인 전용, panel_id `SAMPLE-EDROGI-16BIT` / `provenance.note`에 실린 `sample=true` 마커(`SAMPLE_PROVENANCE_NOTE = "sample=true; plumbing-only; non-authoritative (SPEC-REALDATA-001)"`, ingest_edrogi.py:67)가 비정본 강제). `CalibProvenance`는 `created_at`/`source`/`note` 3필드뿐이며(calibset.py:114-116), `sample`은 boolean 필드가 아니라 `note` 부분문자열이다 — 구현자는 `.sample` 속성이 아니라 `note` 문자열을 검사한다.
- **REQ-XGUI-LAG-DATA-3 (Ubiquitous)** — 정본 IRF와 정밀 first-frame lag / ghost CNR **수치 판정**은 정본 지침세트(이슈 #33) 도착 후로 라벨링해야 하며(엔진은 합성 데이터로 선검증됨), 탭은 정본 대기 상태를 사용자에게 명시해야 한다.

### REQ-XLAG-STATE — 상태 snapshot/restore와 전체 지표

- **REQ-XLAG-STATE-1 (Ubiquitous)** — 기본 sequence run은 매번 fresh `LagCorrector`를 생성하고 이전 run state를 암묵 재사용하지 않아야 한다.
- **REQ-XLAG-STATE-2 (Event-Driven)** — WHEN 사용자가 상태 snapshot을 요청하면 THEN engine은 실제 `LagCorrector.serialize_state`를 호출하고 source run id, frame/state hash를 포함한 typed snapshot을 반환해야 한다.
- **REQ-XLAG-STATE-3 (Event-Driven)** — WHEN 사용자가 호환 snapshot의 명시 restore를 요청하면 THEN engine은 실제 `LagCorrector.load_state`를 호출하고 restore event를 provenance에 기록해야 한다. panel/resolution/domain/hash 불일치는 거부해야 한다.
- **REQ-XLAG-STATE-4 (Ubiquitous)** — Lag 탭은 `run_sequence`, `compute_first_frame_lag`, `compute_ghost_cnr`, `fit_lag_irf`의 입력·결과를 각각 typed DTO로 운반해야 한다.
- **REQ-XLAG-STATE-5 (Event-Driven)** — WHEN strict 사용자 sequence/StepResponse가 제공되면 THEN 등록 데이터 유무와 무관하게 실행하고 승인 전 `USER_SUPPLIED_UNVERIFIED`로 표시해야 한다.

## Exclusions (What NOT to Build)

- **골든 알고리즘 변경 없음** — `modules/lag.py`·`pipeline/sequence.py`·`metrics/lag.py`·`metrics/lag_irf.py`·`common/calibset.py`(LAG 페이로드)·`pipeline/orchestrator.py`는 동결 오라클로 편집하지 않는다. 탭은 읽기-실행 전용으로만 소비한다(G-1, C-11).
- **UI에서의 IRF 추정·lag 재귀·상태 진행 재구현 없음** — 지수합 IRF 적합은 `fit_lag_irf`에, SWR-402 상태 재귀는 `LagCorrector`에, 시퀀스 상태 수명/리셋은 `run_sequence`에 남는다. UI/어댑터는 IRF 계수를 스스로 산출하거나 lag 상태 `{s_i}`를 스스로 진행시키지 않는다(C-09/C-11).
- **점근/근사 IRF·하드코딩 기본 IRF 없음** — 무단 기본 IRF 대체 금지(SWR-000-5). IRF는 `fit_lag_irf` 산출물·측정 CalibSet·명시적 비정본 placeholder로만 공급하며, 모듈/UI가 IRF를 하드코딩하지 않는다.
- **포화 픽셀 "복원" 없음** — SATURATION 픽셀은 출력값 보존 규약(SWR-602 정신, lag.py:149-161)을 따르며, UI는 하위-포화값을 발명하지 않는다.
- **파이프라인 순서 임의 변경·스테이지 재조합 없음** — lag는 `CANONICAL_ORDER`의 고정 위치(offset→gain→defect→**lag**→…, orchestrator.py)에서만 조합되며, C#/UI는 스테이지를 스스로 정렬하지 않는다(SWR-000-2, G-6). 신규 스테이지·CalibKind 신설 없음.
- **정본 수치 검증 없음(QUARANTINE)** — 등록 GHOST + placeholder IRF 구동은 sanity(유한·비퇴화·구조) 확인이며 수치 골든/EV 임계 도출·튜닝·적합에 쓰지 않는다(이슈 #29). 정본 first-frame lag/ghost CNR 판정은 정본 지침세트(이슈 #33) 별건.
- **FB 캡처 하드웨어 구동 없음** — forward-bias 트리거의 request/confirm **인터페이스**만 소비하며, 실제 FB 캡처는 패널 펌웨어 소관이다(sequence.py:60-65, 기본 `NoOpFBTrigger`).
- **성능·마샬링 최적화 없음** — 대용량 3072² 다중 프레임 시퀀스의 스루풋/마샬링 최적화는 범위 밖이다(정확성·재현성이 목적, P2 이연).
- **C++ 엔진 이식·Gen 2 없음** — 네이티브 조합/시퀀스 커널, DL/ADR, 배포는 범위 밖(SPEC-XSEAM Stage 2 / Gen 2 승계).

## 확정 결정 (v0.5.1)

1. IRF Build의 정본 검증 경로는 합성 다중 노출 step-response를 골든 `fit_lag_irf`에 전달하는 것이다. fixture 계수 직접 주입은 비정본 demo로 명시할 때만 허용한다.
2. Lag 탭은 standalone frame sequence와 IRF 검증에 집중한다. offset/gain 등 상류 조합은 마스터 Pipeline 실행 화면이 담당한다.
3. 탭은 engine-returned float32/float64 진단 차이, ROI 유효조건, 정착 tail 부재 오류를 명시적으로 표시한다.
4. 중앙 TC 레지스트리는 G2 블록 XDET-TC-104~111이다.

## v0.5.1 public operation closure

| Python EntryPoint | GUI 노출 | TC |
|---|---|---|
| `modules.lag.LagCorrector.process` | ordered sequence step | 104~105 |
| `modules.lag.LagCorrector.serialize_state` | explicit Snapshot command | 105 |
| `modules.lag.LagCorrector.load_state` | explicit Restore command | 105 |
| `metrics.lag.compute_first_frame_lag` | First-frame metric action | 106 |
| `metrics.lag.compute_ghost_cnr` | Ghost CNR action | 107 |
| `metrics.lag_irf.fit_lag_irf` | IRF build/fit action | 108 |

snapshot/restore는 숨은 adapter cache가 아니라 사용자가 관찰할 수 있는 session event이며, 다음 frame 결과와 state hash로 fidelity를 검증한다.
