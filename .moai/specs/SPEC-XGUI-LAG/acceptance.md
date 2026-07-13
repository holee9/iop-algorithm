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

# SPEC-XGUI-LAG — 인수 기준 (acceptance)

> 본 인수기준의 모든 EARS ID·중앙 TC·필수 증거 연결은 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따른다. `baseline-control.md`의 G0와 사용자 승인 전에는 이 체크리스트를 구현 완료 증거로 사용할 수 없으며 모든 TC는 `PLANNED` 상태를 유지한다.

> **구현 대상:** `apps/xdet-console/` C# WPF 앱. `apps/gui/`와 Python 테스트는 계약·검증 선례이며 구현 대상이 아니다.
Lag(잔상 보정) 그룹 검증 탭의 Given-When-Then. **1급 E2E 흐름 = 열기(형제 시퀀스 로딩) → build(IRF) / apply(`run_sequence`) → 저장(`<name>_result.raw` + 사이드카) → 검증(first-frame lag / ghost CNR / IRF 곡선).** 모든 기준은 관측 가능(폴더 브라우저 시퀀스 로딩 성공 / `fit_lag_irf` CalibSet(LAG) 산출 / `run_sequence` 상태형 구동 / 골든 명시 오류로 거부 / `<u2` raw + `.json` 산출 / C-20 게이트 거부 / 지표 엔진 반환값 표시 / 골든 파일 무변경)해야 한다.

**데이터 프로비넌스 라벨(HARD, 이슈 #29 QUARANTINE):**
- **[합성]** — 실측 도착 전 엔진·탭 자체 검증(알려진 IRF `(a_i,b_i)` 주입/회복). load-bearing 판정 = 회복 정확도·역전·명시 거부.
- **[등록-SAMPLE-sanity]** — 등록 에드로지 `GHOST` 폴더(`ghost_lag`, ingest_edrogi.py:87) **원시 시퀀스만** + 비정본 placeholder IRF 구동. **sanity(유한·비퇴화·구조 성립)만** 단언하며 수치 골든/EV 임계 도출·튜닝·적합 금지(panel_id `SAMPLE-EDROGI-16BIT`, `provenance.note`에 `sample=true` 마커, ingest_edrogi.py:67).
- **[#33 대기]** — 정본 IRF·정밀 first-frame lag/ghost CNR **수치 판정**은 정본 지침세트(이슈 #33) 도착 후 별건.

시험케이스 블록 **XDET-TC-104~111** (그룹 1 CALIB `096~103`에 이은 그룹 2 배정; 기존 XSEAM-002 `088~093`과 무충돌).

## Scenarios (Given-When-Then)

### Scenario 1 — 열기: 형제 시퀀스 로딩 (XDET-TC-104, REQ-XGUI-LAG-INPUT-1/2 · VIEW-1) — [등록-SAMPLE-sanity]
- **Given** 상주 폴더 브라우저(폴더 트리 + 가상화 썸네일 + 형제 필름스트립 + 이전/다음, foundation §4)와 등록 에드로지 `GHOST` 폴더(`ghost_lag`)의 원시 프레임들이 있고,
- **When** 사용자가 그 폴더에서 한 프레임을 지정하면,
- **Then** 탭은 그 부모 폴더의 형제 프레임을 **프레임 인덱스 순으로 정렬한 시퀀스 후보**로 함께 표시하고(단일 파일 열기가 아니라 컨텍스트 유지), 사용자가 시작/끝 프레임으로 시퀀스 경계를 선택하면 그 정렬된 `list[XFrame]`(`common/io.py::load_raw_frame`로 적재, headerless 16-bit + `.json` 사이드카)를 apply 입력으로 확보해야 한다. 로딩된 시퀀스 프레임 통계가 유한·비퇴화(SAMPLE sanity)여야 한다. (등록 `GHOST`는 ingest가 LAG CalibSet을 만들지 않으므로 IRF는 Scenario 2/별도 placeholder로 짝지어진다 — REQ-XGUI-LAG-DATA-1.)

### Scenario 2 — IRF build: 다중 노출 step-response → CalibSet(LAG) (XDET-TC-105, REQ-XGUI-LAG-IRF-1/4) — [합성]
- **Given** IRF build 서브워크플로에 알려진 합성 IRF(`IRF_A=(0.030,0.020,0.010)`, `IRF_B=(0.50,0.80,0.90)`, M=3, lag_seq.py:26-28)로 만든 **2개 이상 노출 레벨**의 step-response(각 `StepResponse(amplitude, residual)`, lag_irf.py:50)가 주어지면,
- **When** 사용자가 이를 공급해 `metrics/lag_irf.py::fit_lag_irf(step_responses, m_terms=…, panel_id=…, resolution=…, valid_from=…, valid_until=…)`(lag_irf.py:72)를 호출하면,
- **Then** 탭은 `kind == CalibKind.LAG`이고 `irf_a`/`irf_b` 페이로드(calibset.py:82-84)를 보유한 CalibSet을 산출하고, 회복된 계수 `(a_i, b_i)`가 주입 IRF를 허용 오차 내로 회복하며, provenance의 fit-quality note(`status`/`rel_rms_residual`/`m_terms`/`n_exposures`, lag_irf.py:158-162)를 표시하고, 그 CalibSet을 apply 서브워크플로에 REQ-XGUI-LAG-INPUT-3(a) 경로로 넘길 수 있어야 한다. 피팅 산술은 UI가 아니라 `fit_lag_irf` 골든이 수행해야 한다(C-09).

### Scenario 3 — IRF build 거부 가드: 단일 노출 · 비수렴 (XDET-TC-106, REQ-XGUI-LAG-IRF-2/3) — [합성] — 음성 대조
- **Given** IRF build 서브워크플로가 임의 step-response 집합을 받고,
- **When** (a) **1개 노출 레벨**만 공급하거나, (b) 적합이 수렴하지 않거나 상대 RMS 잔차가 `rms_residual_tol`(lag_irf.py:141-147)을 초과하는 degenerate/non-LTI 곡선을 공급하면,
- **Then** (a)는 골든의 `LagIRFCalibrationError("single-exposure calibration is forbidden", lag_irf.py:94-98)`로, (b)는 `LagIRFCalibrationError`(rel-RMS 게이트)로 거부되고, 탭은 결함 CalibSet을 방출하거나 표시하지 않으며(단일 노출로 IRF 추정 금지), 그 명시 오류가 사용자에게 그대로 표면화되어야 한다. (음성 대조: 실제로 예외 발생 확인 — 통과로 침묵되면 안 된다.)

### Scenario 4 — apply: `run_sequence` 상태형 구동 + fresh registry (XDET-TC-107, REQ-XGUI-LAG-APPLY-1/2/3) — [합성] — **load-bearing**
- **Given** 알려진 IRF로 forward-lag 오염된 합성 시퀀스(`forward_lag`, lag_seq.py 선례)와 **동일 IRF**의 CalibSet(LAG)(Scenario 2 산출 또는 `lag_calib` placeholder)이 주어지고,
- **When** WPF가 `IXdetEngine.RunSequence(SequenceRunRequest)`를 한 번 호출하고 PythonNet adapter가 매 시퀀스 fresh registry로 `run_sequence`에 위임하면,
- **Then** (i) matched-IRF 보정이 오염을 역전해 각 프레임이 참값 시퀀스에 수렴하고, (ii) 한 시퀀스 동안 동일 `LagCorrector` 인스턴스가 프레임 k→k+1로 상태 `{s_i}`를 전방으로 이어가며, (iii) 새 시퀀스 시작 시 `registry_factory` 재호출로 상태가 초기화(`s_i[-1]=0`, 시퀀스 간 리셋 = 새 인스턴스)되어야 한다. 단일 프레임 `run_pipeline` 반복이 아니라 시퀀스 러너를 사용해야 한다.
  - **음성 대조:** `build_pipeline_registry()`가 반환하는 **단일 공유 `LagCorrector` 인스턴스**(pipeline_panel.py:47-49)를 두 시퀀스에 재사용하면 상태가 시퀀스 경계를 넘어 누적되어 두 번째 시퀀스 출력이 fresh-registry 결과와 달라짐을 확인(REQ-XGUI-LAG-APPLY-2 위반 검출).

### Scenario 5 — apply 가드: 포화 픽셀 보존 · IRF 결여 거부 (XDET-TC-108, REQ-XGUI-LAG-APPLY-4 · INPUT-4) — [합성] — 음성 대조
- **Given** SATURATION 픽셀을 포함한 합성 시퀀스와 (경로 A) 유효 IRF CalibSet, (경로 B) `irf_a`/`irf_b` 결여 CalibSet(예: 빈 `make_synthetic_calibset(_, CalibKind.LAG)` payload `{}`, synth_calibset.py:48)이 주어지고,
- **When** (A) 유효 IRF로 apply 하거나 (B) 결여 IRF로 apply 하면,
- **Then** (A)에서는 SATURATION 픽셀의 **출력값이 보존**되고(하위-포화값 발명 금지) 그 픽셀 내부 상태만 계산된 `I_hat`으로 진행하며(lag.py:149-161, SWR-602 정신), UI가 포화 픽셀을 "복원"하지 않아야 한다. (B)에서는 골든의 `LagCalibError`(lag.py:70/82-97)로 거부되고 UI가 어떤 기본 IRF도 합성·대체하지 않으며(SWR-000-5) 결여 키 이름(`irf_a`/`irf_b`)을 그대로 표면화해야 한다.

### Scenario 6 — 검증: first-frame lag / ghost CNR + 신호 곡선 출처 (XDET-TC-109, REQ-XGUI-LAG-VIEW-3/4/6 · METRIC-2/3) — [합성] (정본 수치 [#33 대기])
- **Given** 노출 플래토 → 잔상 감쇠 구조를 갖는 시퀀스와 필수 Params `lag_settle_frac`·`lag_plateau_frac`(선택 `lag_dark_baseline`/`lag_exposure_end_index`/`lag_min_exposed_signal`)이 주어지고,
- **When** 사용자가 first-frame lag 및 ghost CNR 지표를 요청하면(ghost는 전경/배경 ROI `(top,left,height,width)` 지정),
- **Then** (i) 탭은 `metrics/lag.py::compute_first_frame_lag`가 **반환한 스칼라**(`first_frame_lag_pct`·`last_exposed_index`·`first_residual_index`·`dark_baseline`, lag.py:126-141)만을 판정 수치로 표시하고 UI가 이를 재계산하지 않으며, (ii) `compute_ghost_cnr`가 반환한 `ghost_cnr = |mean_fg-mean_bg|/std_bg`(lag.py:177)와 ROI 오버레이를 표시하고, (iii) **표시용 시간축 신호 곡선**을 그리는 경우 그 프레임별 축약은 골든 primitive `common.robust_stats.robust_mean`(엔진 `_frame_signal`이 쓰는 동일 호출 — `robust_stats.robust_mean(np.asarray(frame.pixel, dtype=np.float64))`, metrics/lag.py:34-35, common/robust_stats.py:22)으로만 산출하고 UI 자체 축약/재구현으로 만들지 않아야 한다(C-09; 곡선은 표시 보조, 판정은 (i)의 엔진 반환 스칼라 소유). **정본 수치 판정은 [#33 대기]** — 합성 데이터는 엔진 선검증용.
  - **음성 대조(METRIC-3):** 정착된 dark tail이 없거나(잔상이 마지막 프레임에서 여전히 감쇠) 노출 플래토가 검출 레벨 위에 없으면 `MetricReadError`(lag.py:80-83/99-101)로 거부되고, UI가 임의 argmax/마지막 프레임 기본값으로 우회하지 않아야 한다.

### Scenario 7 — 저장: `<name>_result.raw` + 사이드카 + C-20 게이트 (XDET-TC-110, REQ-XGUI-LAG-EXPORT-1/2/3)
- **Given** 보정된 시퀀스(또는 선택 프레임)와 사용자 지정 출력 폴더가 있고,
- **When** 사용자가 저장하면,
- **Then** (i) 각 프레임을 고정 폭 frame_index 명명의 `xdet.frame-artifact/1.0` raw/sidecar(+mask)로 쓰고, (ii) sequence-level `xdet.run-manifest/1.0`에 ordered input/output hashes, IRF calib hash, params hash, frame_count를 기록하며, (iii) pixel/mask round-trip과 재적재 순서를 검증하고, (iv) `data/` 하위는 C# export choke point가 typed error로 거부해야 한다.
  - **음성 대조:** `data/` 하위 경로 지정 시 실제로 거부 확인 — 통과로 침묵되면 안 된다.

### Scenario 8 — 등록 GHOST 실측 sanity + FB 핸드셰이크 + 권한/읽기 전용 가드 (XDET-TC-111, REQ-XGUI-LAG-APPLY-5 · DATA-1/2/3 · Exclusions) — [등록-SAMPLE-sanity]
- **Given** 등록 에드로지 `GHOST` 원시 시퀀스(Scenario 1) + 비정본 placeholder IRF(clearly-labeled)로 apply 하고,
- **When** (a) 시퀀스를 `run_sequence`로 구동하고(FB 트리거 인터페이스 관여 시), (b) 실행 후 코드 경로·쓰기 대상·데이터 사용을 검사하면,
- **Then** (i) 보정 결과가 **sanity(유한·비퇴화·구조 성립)만** 성립하고 수치 골든/EV 임계 도출·튜닝·적합에 쓰이지 않으며(QUARANTINE 이슈 #29; 정본 판정 [#33 대기]), (ii) FB `confirm()` 실패 시 골든의 `FBTriggerError`(sequence.py)가 표면화되고 시퀀스가 진행되지 않으며(기본 `NoOpFBTrigger`; 실제 FB 캡처는 패널 펌웨어 소관), (iii) `modules/lag.py`·`pipeline/sequence.py`·`metrics/lag.py`·`metrics/lag_irf.py`·`common/calibset.py`·`pipeline/orchestrator.py` 및 골든 fixture·CalibSet·`data/`에 어떤 쓰기도 없고(git diff 없음), UI/어댑터에 IRF 추정·lag 상태 진행·스테이지 재정렬 로직이 부재(조합/순서/상태 권한은 골든에 — C-09/C-11)해야 한다.

### Scenario — fresh state와 명시 snapshot/restore (XDET-TC-104~111)

- **Given** 동일 sequence를 실행할 준비가 되고 선택적으로 호환 state snapshot이 있을 때,
- **When** fresh run 두 번, snapshot, explicit restore run을 수행하면,
- **Then** fresh run은 서로 state를 공유하지 않고 bit-identical이어야 하며, snapshot/restore는 실제 `serialize_state/load_state` 호출과 state hash/event를 남겨야 한다. 불일치 snapshot과 암묵 restore는 거부돼야 한다.

## Edge Cases

- **단일 프레임 입력은 first-frame lag FAIL (REQ-XGUI-LAG-VIEW-3/METRIC-3)** — `compute_first_frame_lag`에 `len(frames) < 2`를 넘기면 `MetricReadError("need >= 2 frames …", lag.py:56-57)`로 거부돼야 한다 — 시퀀스는 노출 프레임 + 잔상 프레임을 요구한다.
- **빈 `make_synthetic_calibset(_, LAG)`는 lag apply FAIL (REQ-XGUI-LAG-INPUT-4)** — payload `{}`(synth_calibset.py:48)로 apply 하면 `LagCalibError`로 거부(다른 그룹의 빈 placeholder 통과 패턴과 갈리는 지점) — 무단 기본 IRF 대체 금지(SWR-000-5).
- **공유 인스턴스 상태 누출은 apply FAIL (REQ-XGUI-LAG-APPLY-2)** — `registry_factory`가 아니라 `build_pipeline_registry()` 단일 공유 인스턴스를 재사용하면 시퀀스 간 상태가 누적되어 리셋 규약(REQ-XGUI-LAG-APPLY-3)을 위반 — fresh-registry 미사용은 인수 실패.
- **정착 tail 없는 시퀀스는 지표 FAIL (REQ-XGUI-LAG-METRIC-3)** — 잔상이 마지막 프레임에서 여전히 감쇠 중이면 `MetricReadError`(lag.py:80-83); UI가 argmax/마지막 프레임 기본값으로 우회하면 인수 실패(`lag_dark_baseline` 명시 오버라이드는 허용).
- **포화 픽셀 "복원"은 apply FAIL (REQ-XGUI-LAG-APPLY-4)** — SATURATION 픽셀의 출력값을 UI가 하위-포화값으로 발명하면 인수 실패 — 골든 보존 규약(lag.py:149-161)만 표면화.
- **UI 자체 신호 곡선 축약은 검증 FAIL (REQ-XGUI-LAG-VIEW-6)** — 시간축 신호 곡선을 `robust_stats.robust_mean`이 아닌 UI 자체 mean/median/지표 재구현으로 만들면 C-09 위반으로 인수 실패 — 곡선 축약은 골든 primitive 호출로만.
- **SAMPLE 실측 lag의 수치 오용 (QUARANTINE, 이슈 #29)** — 등록 `GHOST` + placeholder IRF 구동 결과를 정본 first-frame lag/ghost CNR 수치·EV 임계 도출·튜닝·적합에 사용하면 인수 실패 — sanity(유한·비퇴화·구조)만 허용, 정본 판정은 정본 지침세트(#33) 도착 후 별건.
- **명목 IRF 하드코딩·순서 변경 (Exclusions)** — lag를 `CANONICAL_ORDER` 고정 위치(offset→gain→defect→**lag**→…) 밖에서 조합하거나 IRF를 모듈/UI에 하드코딩하면 인수 실패 — IRF는 `fit_lag_irf`·측정 CalibSet·명시적 비정본 placeholder로만 공급.

## Definition of Done (체크리스트)

- [ ] 열기: 폴더 브라우저가 지정 프레임의 부모 폴더 형제를 인덱스 순 정렬 시퀀스 후보로 표시 + 경계 선택으로 `list[XFrame]` 확보 (XDET-TC-104, INPUT-1/2·VIEW-1)
- [ ] IRF build: 합성 다중 노출 step-response로 `fit_lag_irf` 호출 → `kind==LAG`·`irf_a`/`irf_b` CalibSet 산출 + 알려진 IRF 회복 + fit-quality note 표시 (XDET-TC-105, IRF-1/4)
- [ ] IRF build 거부: 단일 노출 `LagIRFCalibrationError`(문자열 정확) + rel-RMS 초과/비수렴 거부, 결함 CalibSet 미방출(음성 대조 포함) (XDET-TC-106, IRF-2/3)
- [ ] apply: `run_sequence` + fresh `registry_factory`(매 시퀀스 새 `LagCorrector`)로 matched-IRF 역전 + 프레임 k→k+1 상태 전방 이음 + 시퀀스 간 리셋(새 인스턴스); 공유 인스턴스 상태 누출 음성 대조 (XDET-TC-107, APPLY-1/2/3)
- [ ] apply 가드: SATURATION 출력값 보존(하위-포화 발명 금지) + 결여 IRF `LagCalibError` 거부·무단 대체 없음 (XDET-TC-108, APPLY-4·INPUT-4)
- [ ] 검증: first-frame lag = 엔진 반환 스칼라만(UI 재계산 없음) + ghost CNR = `|mean_fg-mean_bg|/std_bg` + 시간축 신호 곡선은 `robust_stats.robust_mean` 소비로만; 정착 tail 없음 `MetricReadError`(음성 대조) (XDET-TC-109, VIEW-3/4/6·METRIC-2/3)
- [ ] 저장: frame artifact(+mask) + 고정 폭 index + sequence run manifest + ordered hash/round-trip + C# export choke point의 `data/` 거부 (XDET-TC-110, EXPORT-1/2/3)
- [ ] 등록 GHOST + placeholder IRF는 sanity(유한·비퇴화)만 단언, 수치 골든/EV/튜닝 없음 + FB `confirm()` 실패 `FBTriggerError` 표면화 (XDET-TC-111, APPLY-5·DATA-1/2)
- [ ] 정본 IRF·정밀 first-frame lag/ghost CNR 수치 판정은 [#33 대기]로 라벨, 탭이 정본 대기 상태를 명시 (DATA-3)
- [ ] C# / UI·어댑터에 IRF 추정 산술·lag 상태 진행·스테이지 정렬/조합 로직 부재 + 읽기 전용(골든/CalibSet/`data/` 쓰기 없음) (XDET-TC-111, Exclusions)
- [ ] `modules/lag.py`·`pipeline/sequence.py`·`metrics/{lag,lag_irf}.py`·`common/calibset.py`·`pipeline/orchestrator.py` 무변경(git diff 없음)
- [ ] `uv run pytest` 무회귀 green + `uv run lint-imports` green·불변(의존 방향 유지)
- [ ] 어떤 신규 파이프라인 스테이지·CalibKind도 신설하지 않음; 점근/근사·하드코딩 기본 IRF 없음(SWR-000-5)

## 판정 원칙 (측정=판정 분리)

- **판정 상수는 지표 엔진 소유(C-09).** lag **모듈**은 튜닝 Params가 없고(`REQUIRED_PARAMS = ()`, lag.py:63; Params는 이력 해시용), first-frame lag 판정 상수(`lag_settle_frac`/`lag_plateau_frac` 등)는 `compute_first_frame_lag`가 `require_param`으로 외부 주입받는다 — UI가 이 상수를 자체 계산하지 않는다.
- **표시용 파생량 vs 판정 수치.** first-frame lag/ghost CNR **판정 수치**는 오직 `compute_first_frame_lag`/`compute_ghost_cnr`의 반환값이다. 시간축 신호 곡선·IRF 감쇠 곡선은 **표시 보조**이며, 곡선 축약은 골든 primitive(`robust_stats.robust_mean`)/알려진 계수의 모델 평가로만 산출한다(엔진 primitive 호출 = 소비, UI DSP 0 유지 — C-09).
- **조합/순서/상태 권한은 골든에.** 고정 정준 순서(SWR-000-2)·캘리브레이션 진입 게이트(SWR-000-5)·시퀀스 상태 수명/리셋(`run_sequence` fresh-registry)·IRF 재귀(`LagCorrector` SWR-402)는 골든이 강제하며 UI/어댑터가 재구현하지 않는다(C-11 단방향 소비).
- **SAMPLE 실측 수치는 비정본(QUARANTINE).** 등록 GHOST + placeholder IRF의 load-bearing 인수 기준은 **sanity(유한·비퇴화·구조)**·**명시 거부**·**골든 무변경·무회귀**이지 SAMPLE 절대 수치가 아니다. 정본 수치 판정은 정본 지침세트(#33) 도착 후 별건이다.

### Scenario 11 — strict 사용자 시퀀스와 증거 등급 (XDET-TC-111, REQ-XGUI-LAG-DATA-3, REQ-XLAG-STATE-1/5)

- **Given** 등록세트 밖의 ordered frame sequence, timestamps, populated LAG CalibSet과 Params가 strict schema를 만족할 때,
- **When** fresh run과 명시 snapshot/restore run을 실행하면,
- **Then** 등록 fixture 부재로 차단하지 않고 direct-golden과 동일한 결과·state hash를 반환하되 UI/report/manifest의 evidence를 `USER_SUPPLIED_UNVERIFIED`로 유지해야 한다.
- **Given** 같은 입력이 승인 절차를 거치지 않았을 때,
- **When** 사용자가 evidence 승격을 요청하면,
- **Then** `GUIDING_CANDIDATE` 또는 `GOLDEN_APPROVED` 승격을 거부해야 한다.

## 요구사항-TC 추적

| 요구사항 | 중앙 TC |
|---|---|
| `REQ-XGUI-LAG-TARGET-1` | 104~111 |
| `REQ-XGUI-LAG-INPUT-{1..4}` | 104, 105, 110 |
| `REQ-XGUI-LAG-VIEW-{1..6}` | 104, 106, 107, 108 |
| `REQ-XGUI-LAG-IRF-{1..4}` | 105, 106, 110 |
| `REQ-XGUI-LAG-APPLY-{1..5}` | 106, 109, 110 |
| `REQ-XGUI-LAG-METRIC-{1..3}` | 107, 108 |
| `REQ-XGUI-LAG-EXPORT-{1..3}` | 109 |
| `REQ-XGUI-LAG-DATA-{1..3}` | 104, 108, 111 |
| `REQ-XLAG-STATE-{1..5}` | 105, 106, 110, 111 |

각 범위는 모든 개별 ID로 전개한다. 필수 증거 필드는 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따르며 누락·중복·orphan은 인수 실패다.

## v0.5.1 operation closure acceptance

- **Given** fresh Lag session과 ordered sequence/ROI/step-response가 있고,
- **When** `modules.lag.LagCorrector.process`, `modules.lag.LagCorrector.serialize_state`, `modules.lag.LagCorrector.load_state`, `metrics.lag.compute_first_frame_lag`, `metrics.lag.compute_ghost_cnr`, `metrics.lag_irf.fit_lag_irf`에 대응하는 command를 실행하면,
- **Then** 동일 session의 state 전이와 snapshot→restore 후 다음 출력이 golden-direct 결과와 일치하고, 세 metric의 typed result/error와 qualified call trace가 XDET-TC-104~111 증거에 남아야 한다.
