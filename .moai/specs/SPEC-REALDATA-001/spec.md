---
id: SPEC-REALDATA-001
title: "샘플(플러밍) 취득세트 외부참조 수집 + 플러밍 검증 아암 + GUI 6-스위트"
version: 0.2.0
status: draft
created: 2026-07-11
updated: 2026-07-11
author: drake.lee
priority: high
issue_number: 29
labels: [realdata, ingestion, sample-plumbing, quarantine, verification-arm, gui-test]
---

# SPEC-REALDATA-001 — 샘플(플러밍 전용) 취득세트(에드로지16BIT) 외부참조 수집 · 플러밍 검증 아암 · 헤드리스 GUI 6-스위트

XDET P1 골든 모델은 지금까지 합성 팬텀(기지 MTF/노이즈 주입)으로만 검증되어 왔다(CLAUDE.md T1 원칙, 실측 도착 전 선검증). 본 SPEC은 취득세트 `images/에드로지16BIT/`(3072×3072 16-bit little-endian raw, 총 ~1.4GB)를 **외부참조(external-reference)** 방식으로 수집하여 — 원본 1.4GB를 저장소로 복사하지 않고 — 코드 경로(I/O 로드·GUI 렌더·파이프라인 실행·계약/스모크)를 실제 형상(3072²) 프레임으로 구동하는 **플러밍 검증 아암**과, `apps/gui/`(SPEC-VIEWER-001)를 그 프레임으로 구동하는 **헤드리스 GUI 6-스위트**를 도입한다(이슈 #29).

**[HARD] 이 취득세트는 SAMPLE/플러밍 전용 데이터다.** `images/에드로지16BIT/`는 코드 경로를 돌려보기 위한 **부분(partial) 샘플 세트**이며, 수치 작업의 근거가 되는 정본(authoritative) **"지침(guiding)" 취득세트는 추후 별도 SPEC으로 재등록**되고 그 세트만이 수치 작업의 근거가 될 수 있다. 본 샘플 세트의 모든 수치 출력은 **비정본(NON-AUTHORITATIVE)**이며 — 알고리즘 파라미터([B]/[T]/[P]) 유도·피팅·튜닝, 골든/정본/기대 수치 레퍼런스, 인수 EV 임계·허용오차·보정 상수 설정, 알고리즘/모듈 수치 거동 변경의 **어떤 근거로도 쓰일 수 없다**(REQ-REALDATA-QUARANTINE 그룹, HARD). 허용되는 것은 **코드-플러밍 검증(I/O 로드, GUI 렌더, 파이프라인 실행, 계약/스모크)뿐**이며, 지표(MTF/NPS/NNPS/SNRn/선형성) 단정은 **sanity 전용**(유한·비퇴화, 물리적으로 기대되는 곳에서만 단조)이다. 정본 지침 세트로 [B]/[T] 값을 확정·튜닝하는 수치 검증은 별도 SPEC(추후)의 하류 작업이다.

**본 SPEC은 골든 모델 처리 모듈이 아니라 (샘플) 데이터 수집 도구 + 플러밍 검증 아암이다.** SWR ID에 대응하는 파이프라인 스테이지를 신설하지 않으며(`process(XFrame,CalibSet,Params)->XFrame` 시그니처 없음, `CANONICAL_ORDER`·`_KIND_BY_STAGE` 무변경, 신규 `CalibKind` 없음), `common/contract.py`·`common/xframe.py`·`pipeline/orchestrator.py`를 변경하지 않고(SPEC-VIEWER-001 additive 규약 승계) 기존 로더 `common/io.py::load_raw_frame`·`common/calibset.py::CalibSet`·`common/synth_calibset.py`를 **단방향 소비·재사용**한다. 수집기는 `modules/`가 아니라 `scripts/`에 두는 **툴링**이다(수집은 파이프라인 스테이지가 아님, SWR-000-2/6).

- 근거: `docs/XDET_SWR_spec_v1.2.md`(SWR-000-5 무단 기본값 대체 금지 · SWR-000-7 정수 bit-동일/float ±1 LSB · SWR-000-8 CalibSet 공통 스키마 · SWR-602 포화 복원 금지) · `docs/XDET_TestSpec_v1.0.md`(XDET-TC-001~007 합격 케이스의 실측 아암) · `docs/XDET_measurement_protocol_v1.0.md`(MTF/NPS/SNRn 산출) · `docs/XDET_EVAL_criteria_v1.1.md`(EV min/typ/max — 판정=측정 분리) · `images/에드로지16BIT/아크릴/DOSE METER.txt`(선량 참고값 — 표시·플롯 전용, 비정본·임계 승격 금지)
- 선행/소비 계약: [SPEC-INFRA-001](../SPEC-INFRA-001/spec.md)(`common/calibset.py` CalibSet 공통 스키마·`_calibration_gate`·`common/io.py` 로더 규약) · [SPEC-VIEWER-001](../SPEC-VIEWER-001/spec.md)(`apps/gui/` 검증 GUI: `io_panel.guard_output_path`(C-20)·`layers.make_diff_layer`/`CompareView`·`module_panel.run_module`·`metrics_panel.plot_mtf`/`recompute_mtf_for_roi`·`probe.probe_at`·`common/synth_calibset.make_synthetic_calibset`) — 전부 additive 소비, 코어 표면 무변경(KEPT).
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.2.0 (2026-07-11)** — **샘플/플러밍 전용 재정의(이슈 #29 사용자 HARD 제약).** `images/에드로지16BIT/`는 코드 경로 검증용 **부분 샘플 세트**이며 수치 작업의 정본 근거가 아님을 명문화. 수치 작업의 정본 근거인 "지침(guiding)" 취득세트는 추후 별도 SPEC으로 재등록. 주요 변경:
  - **신규 HARD 그룹 REQ-REALDATA-QUARANTINE**(INGEST 앞) 추가 — 샘플 세트의 (1) 파라미터([B]/[T]/[P]) 유도·피팅·튜닝, (2) 골든/정본/기대 수치 레퍼런스, (3) 인수 EV 임계·허용오차·보정 상수 설정, (4) 알고리즘/모듈 수치 거동 변경 사용을 전면 금지. 허용=플러밍 검증만, 지표 단정=sanity 전용. (요구 그룹 6→7)
  - **매니페스트**: 전 엔트리에 `usage="sample-plumbing"` 필드 추가(정본 세트는 추후 `usage="guiding"`, 본 범위 밖). 선량 µGy 정규화 + 원 단위 토큰 보존(850nGy→0.85µGy, D5).
  - **CALIB 재정의**: "정본 CalibSet 구축"→"빌더 **구조 검증**만"(build→`_calibration_gate`→save/load 왕복). 빌드물 비정본 라벨(`panel_id="SAMPLE-EDROGI-16BIT"`, provenance `sample=true`, 산출물 `tests/` 상주 — 파이프라인 실 캘리브레이션 소비 위치에 두지 않음). CalSet DN·DOSE 값 상수/임계 승격 금지.
  - **TESTARM 재정의(D2)**: 지표=sanity 게이트(단조성+유한+비퇴화+물리적 타당 대역), DOSE는 표시·플롯 전용, 절대 허용오차·DN/µGy 판정 축 이연(run-deferred) 및 샘플 세트 피팅 차단.
  - **VALIDATE 수치-출처 가드(신규 VALIDATE-4)** — C-20 물리 쓰기 가드의 수치 아날로그: 모듈 Params 기본값·인수 EV가 샘플 유도 수치를 참조하지 않고 매니페스트가 `usage=sample-plumbing`임을 단정(QUARANTINE 집행).
  - **GUI(6종 유지)**: (c)(d) 파이프라인/지표 패널은 '실행+유한 출력'만 단정(특정 수치값 아님); (f) XDET-TC-049 D1 — '완료' 대신 다운샘플 출력 shape=기대 축소 해상도 ∧ 통계 유한·비상수(non-constant) 단정.
  - **CI 커버리지(D6)**: 커밋 256² 픽스처가 CalibSet 소스 3종(MasterDark/대표 CalSet 레벨/BPM) ROI 크롭을 포함 → 빌드→게이트→왕복이 realdata-독립 상시 CI로 실행(각 크롭 출처 명시).
  - **결정 확정(D4/D5)**: 결정 1(gain 단일 `G_map`)·2(payload 리터럴 `O_map`/`G_map`/`class_map`)·3(sample panel_id)·7(선량 단위 정규화) RESOLVED; 결정 4(선형성 축) 이연·차단 확정.
  - **TC 예약(D3)**: XDET-TC-022~029(022 관찰자·023~025 Gen2 예약·026~029 미사용)·038~039(VIEWER 030~037 뒤 갭)를 본 SPEC 미사용 예약으로 명시; 본 SPEC은 040~049.
  - `common/contract.py`·`common/xframe.py`·`pipeline/orchestrator.py` 표면 및 코어 4계층 계약 불변(KEPT) 유지.
- **v0.1.0 (2026-07-11)** — 초안 생성. GitHub 이슈 #29. 실측 취득세트 외부참조 수집(`scripts/ingest_edrogi.py`) + 실데이터 검증 아암(XDET-TC-001~007 실측 아암 + 선형성/SNRn) + 헤드리스 GUI 6-스위트(`tests/apps/gui/`). 6개 요구 그룹(INGEST/CALIB/TESTARM/GUI/CONTRACT/VALIDATE) EARS 구조 확정. 핵심 범위 결정:
  1. **외부참조 수집 전용** — 원본 1.4GB는 `images/`에 상주, `data/`에는 JSON 사이드카 + `manifest.json` + 실측 CalibSet(npz/json) + 소형 파생물만. 유일하게 커밋되는 바이너리는 소형 파생 256×256 ROI CI 픽스처(작고 결정론적).
  2. **합성 검증 유지 + 실데이터 아암 추가** — 합성 경로(XDET-TC-000~021 합성 아암)는 제거하지 않으며, 실데이터 테스트는 `@pytest.mark.realdata`로 표시하고 `images/에드로지16BIT/` 부재 시 깨끗이 skip한다.
  3. **`_result` 프레임은 골든 레퍼런스 아님** — 모든 캡처는 벤더 처리 출력 `<name>_result.raw`를 동반하지만 이는 다른 알고리즘·다른 출력 스케일이므로 ±1 LSB/bit-동일(SWR-000-7) 판정의 골든이 될 수 없다. 통계 교차확인 + GUI diff/blink의 target 레이어로만 사용한다.
  4. **수집기는 툴링(`scripts/`), 모듈 아님** — 코어 4계층(`common/modules/pipeline/metrics`)과 오케스트레이터 표면 무변경, 기존 로더/CalibSet/합성 팩토리 재사용.
  5. **신규 TC 블록 XDET-TC-040~049** — 실데이터 전용 신규 관심사(수집/CalibSet/선형성/SNRn/GUI 6종)는 Gen 1 형상 동결 범위(XDET-TC-000~021) 밖 신규 블록을 쓰고, 실측 아암은 기존 XDET-TC-001~007을 in-place 확장한다(캡스톤 스캔 `range(0,22)` 무간섭).

## Environment / Assumptions

- Python 3.11+, numpy/scipy 기반 float 골든 모델(CLAUDE.md, tech.md). 실데이터 수집·검증도 정확성·재현성이 목적이며 성능/배포 목적이 아니다.
- **실행 환경(HARD, lesson L#4)**: 본 저장소에는 PATH에 `python`이 없다 — 모든 명령은 `uv run ...`으로 실행하며, 한글 출력이 필요한 스크립트/테스트는 `PYTHONIOENCODING=utf-8`을 설정한다. SPEC/plan의 모든 명령 예시는 `uv run` 접두를 쓴다.
- **검증된 데이터 사실(재측정 금지, 주어진 값으로 취급)**:
  - 전 raw 파일: 18,874,368 바이트 = 3072×3072 × 2B → 3072×3072 16-bit little-endian(`<u2`) uint16, 헤더 없음(CLAUDE.md 사양 일치).
  - 서브폴더 → XDET 매핑: `16bit cal/`(MasterDark.raw=offset/dark, CalSet_{19008,22245,25827,35685,47302}.raw=5개 노출 레벨 flat-field, 파일명 숫자=목표 flat DN(CalSet_19008 center≈19095 확인), BPM.raw=bad-pixel map) · `GHOST/`(Bright_ghost_00~04 + Bright_ghost_time_05~06, 75kV/320mA/25.6mAs — first-frame lag 감쇠열·IRF 피팅 입력) · `nps/`(Bright_NPS_00~02 flat — NPS/NNPS 256² ROI 앙상블) · `아크릴/`(아크릴 스텝 팬텀 1~5장, 45kV/100mA/2.5mAs, `DOSE METER.txt` 선량 참고값(비정본·표시 전용): 1장 1700DN/8.5µGy · 2장 1100/6.5µGy · 3장 700/3.2µGy · 4장 400/1.57µGy · 5장 260/**850nGy=0.85µGy**; 매니페스트는 µGy로 정규화하되 원 단위 토큰(예 `"850nGy"`)을 함께 보존한다 — D5) · `최소선량선형/`(45kV/20mA/0.4mAs ×10 + PNG — 저선량 노이즈 플로어·SNRn·암전류 제한 영역).
  - 전 캡처는 `<name>_result.raw` 벤더 처리 출력을 동반하나 다른 알고리즘·다른 스케일(예: NPS result max≈10944 vs input 65535)이라 골든 레퍼런스가 아니다.
- **로더 갭 재사용(변경 없음)**: `common/io.py::load_raw_frame(raw_path, meta_path=None)`은 `{"resolution":[rows,cols], "dtype"?}` JSON 사이드카를 요구한다(부재 시 `raw_path.with_suffix(".json")`). 에드로지 raw에는 사이드카가 없으므로 **수집이 사이드카를 생성**한다. 로더는 재사용하며 수정하지 않는다(additive).
- **사이드카 스키마(로더 규약 준수)**: raw 1개당 `{"resolution":[3072,3072], "dtype":"uint16"}`. 사이드카는 `data/edrogi/` 아래 `images/` 트리를 미러링하여 배치하고, 로더는 `load_raw_frame(<images의 raw>, <data의 사이드카>)`로 명시 호출한다(원본 raw는 `images/`에 상주).
- **매니페스트 스키마(`data/edrogi/manifest.json`)**: 프레임별 엔트리 = `{raw_path(images/ 상대), resolution, dtype, category, usage, kv, ma, mas, dose_dn?, dose_ugy?, dose_raw?, plate_count?, frame_index, has_result_pair, result_path?}`. **[HARD] 모든 엔트리는 `usage="sample-plumbing"`을 가진다**(정본 지침 세트는 추후 별도 SPEC에서 `usage="guiding"`으로 등록되며 본 SPEC 범위 밖 — 수치-출처 가드 REQ-REALDATA-VALIDATE-4가 이 필드를 단정). `category` ∈ {offset_dark, gain_flat, bad_pixel_map, ghost_lag, nps_flat, acrylic_step, min_dose_linear}. kV/mA/mAs는 파일명에서, 선량 참고값은 `DOSE METER.txt`에서 장수(plate_count)로 키잉하여 파싱하되 **µGy로 정규화(`dose_ugy`)하고 원 단위 토큰(`dose_raw`, 예 `"850nGy"`)을 보존**한다(D5). 선량 값은 표시·플롯 전용 참고값이며 임계로 승격되지 않는다(REQ-REALDATA-QUARANTINE-4). `.raw`가 아닌 부수 텍스트(예: `아크릴/4장 LNR.txt`)는 `DOSE METER.txt`를 제외하고 무시한다.
- **CalibSet 공통 스키마(재사용, 변경 없음)**: `common/calibset.py::CalibSet(panel_id, resolution, valid_from, valid_until, kind, data, provenance)`; `CalibKind`={OFFSET,GAIN,DEFECT,LAG,LINE_NOISE,NOISE,SCATTER,OTHER}; `save(path)->(npz,json)`(전체 basename에 `.npz`/`.json` 부가). 샘플 CalibSet은 **채워진 payload**를 갖되(합성 팩토리의 빈 payload와 대비) **비정본**으로 라벨링한다: `panel_id="SAMPLE-EDROGI-16BIT"`(고정), provenance에 `sample=true` 마커, 산출물은 `tests/` 아래에만 두고 프로젝트 파이프라인이 실 캘리브레이션으로 소비하는 위치에 두지 않는다. payload 키 리터럴은 소비 모듈이 읽는 **확정 리터럴** — offset=`O_map`(`modules/offset.py::K_OFFSET_MAP`)·gain=`G_map`(`modules/gain.py::K_GAIN_MAP`, 단일점 — 다중점 anchor SWR-202는 `NotImplementedError`로 이연)·defect=`class_map`(`modules/defect.py::K_CLASS_MAP`, 정수 라벨) — 를 그대로 사용하며 발명하지 않는다(D4 확정, 「결정 필요/확인」 1·2). CalSet DN 레벨·`DOSE METER` 값은 스키마에 기록되되 상수/임계로 **승격되지 않는다**(REQ-REALDATA-QUARANTINE-2/4).
- **파라미터·수치 정책(HARD, 격리)**: 전 `[T]`/`[B]` 임계는 수집/테스트 코드에 하드코딩되지 않고 설정·매니페스트·CalibSet으로 외부화된다(SWR 부록 A/A-2 등재). 선량 참고값(1700DN 등)은 `DOSE METER.txt`→매니페스트 경유로 로드하며 상수로 박지 않는다. **어떤 [B]/[T]/[P] 값도 이 샘플 세트로부터 유도·피팅·튜닝되지 않으며**, CalSet DN·DOSE 참고값은 모듈 상수·인수 임계로 승격되지 않는다(REQ-REALDATA-QUARANTINE). 수치 확정은 정본 지침 세트(별도 SPEC) 전용이다.
- **TC 번호 블록**: 실측(샘플) 아암은 기존 **XDET-TC-001~007**을 in-place 확장(합성 스켈레톤은 그대로 live 유지)하고, 샘플 전용 신규 관심사는 **XDET-TC-040~049** 블록을 쓴다. Gen 1 형상 동결 범위(`tests/test_tc_skeletons.py` `_GEN1_TC_RANGE = range(0,22)`)와 무간섭하며, 신규 GUI 테스트 소스(040~049)는 Gen 1 TC id(`000`~`021`) 문자열을 포함하지 않는다(SPEC-VIEWER-001 D9 선례). **예약-미사용 블록(D3)**: XDET-TC-022~029(022=관찰자 연구·인허가·`docs/XDET_TestSpec_v1.0.md` / 023~025=Gen 2 예약 / 026~029=미할당)과 038~039(VIEWER가 030~037 사용, 그 뒤 갭)는 본 SPEC이 사용하지 않는 **예약-미사용**이다 — 본 SPEC은 040~049만 신설한다.
- **헤드리스 CI**: GUI 6-스위트는 `QT_QPA_PLATFORM=offscreen`(pytest-qt/pyqtgraph)로 실행한다(SPEC-VIEWER-001 스택 확정 승계). 픽셀 그랩 시각 단정은 없다.

## Requirements (EARS)

### REQ-REALDATA-QUARANTINE — 샘플 세트 격리: 비정본 · 플러밍 전용 (HARD, 이슈 #29 사용자 제약)

> 이 그룹은 `images/에드로지16BIT/` 샘플 세트가 수치 작업에 오용되는 것을 구조적으로 차단한다. 정본 "지침(guiding)" 취득세트는 추후 별도 SPEC으로 재등록되며, 그 세트만이 수치 작업의 근거가 될 수 있다. 집행 게이트는 REQ-REALDATA-VALIDATE-4(수치-출처 가드).

- **REQ-REALDATA-QUARANTINE-1 (Ubiquitous)** — 시스템은 `images/에드로지16BIT/` 샘플 세트를 **플러밍(코드 경로) 검증 전용**으로만 사용해야 한다: 허용 용도 = I/O 로드·GUI 렌더·파이프라인 실행·계약/스모크. 이 세트의 모든 수치 출력은 **비정본(NON-AUTHORITATIVE)**이며, 지표(MTF/NPS/NNPS/SNRn/선형성) 단정은 **sanity 전용**(유한·비퇴화, 물리적으로 기대되는 곳에서만 단조)이어야 한다.
- **REQ-REALDATA-QUARANTINE-2 (Unwanted)** — IF 어떤 알고리즘 파라미터(모듈 Params 또는 CalibSet의 `[B]`/`[T]`/`[P]` 값)를 샘플 세트로부터 유도·피팅·튜닝하려 하면, THEN 이를 금지해야 한다(수치 근거 불가 — 정본 지침 세트 전용).
- **REQ-REALDATA-QUARANTINE-3 (Unwanted)** — IF 샘플 세트(또는 그 `_result` 또는 샘플로 빌드된 CalibSet)를 골든·정본·기대 수치 레퍼런스(bit-동일/±1 LSB/EV 합격 판정의 기준)로 사용하려 하면, THEN 이를 금지해야 한다.
- **REQ-REALDATA-QUARANTINE-4 (Unwanted)** — IF 인수 EV 임계·허용오차·보정 상수를 샘플에서 유도된 수치로 설정하거나 조정하려 하면, THEN 이를 금지해야 한다(임계는 외부 표준/정본 세트 기원만).
- **REQ-REALDATA-QUARANTINE-5 (Unwanted)** — IF 샘플 세트 관찰 결과로 알고리즘/모듈 코드나 그 수치 거동을 변경하려 하면, THEN 이를 금지해야 한다(플러밍 검증만 허용 — 코드 수치 거동 무변경).

### REQ-REALDATA-INGEST — 사이드카·매니페스트 생성 · 외부참조 무복사 (SWR-000-8, XDET-TC-040)

- **REQ-REALDATA-INGEST-1 (Event-Driven)** — WHEN 수집 스크립트가 `images/에드로지16BIT/`를 순회하면, THEN 각 raw에 대해 로더 규약을 따르는 JSON 사이드카(`resolution=[3072,3072]`, `dtype="uint16"`)를 `data/edrogi/` 미러 경로에 생성해야 한다(기존 `common/io.py` 데이터 규약 재사용).
- **REQ-REALDATA-INGEST-2 (Event-Driven)** — WHEN 수집 스크립트가 실행되면, THEN 모든 프레임을 인덱싱하는 `data/edrogi/manifest.json`을 매니페스트 스키마(raw_path·resolution·dtype·category·**usage**·kv·ma·mas·dose_dn·dose_ugy·dose_raw·plate_count·frame_index·has_result_pair·result_path)로 산출해야 하며, **모든 엔트리는 `usage="sample-plumbing"`을 가진다**(정본 지침 세트는 추후 `usage="guiding"`, 본 범위 밖).
- **REQ-REALDATA-INGEST-3 (Event-Driven)** — WHEN 취득 메타데이터를 파싱하면, THEN kV/mA/mAs는 파일명에서, 선량 참고값은 `아크릴/DOSE METER.txt`에서 장수(plate_count) 기준으로 매핑하여 매니페스트에 기록하되 **µGy로 정규화(`dose_ugy`)하고 원 단위 토큰(`dose_raw`, 예 `"850nGy"`)을 보존**해야 한다(하드코딩 금지 — 파일에서 파싱; D5). 선량 값은 표시·플롯 전용 비정본 참고값이며 임계로 승격되지 않는다(REQ-REALDATA-QUARANTINE-4).
- **REQ-REALDATA-INGEST-4 (Unwanted)** — IF 수집이 전체 해상도(3072×3072) raw 프레임을 `data/`로 복사하려 하면, THEN 그 복사를 거부해야 한다(외부참조 전용 — 1.4GB의 유일한 상주지는 `images/`; `data/`에는 사이드카·매니페스트·CalibSet·소형 파생물만).
- **REQ-REALDATA-INGEST-5 (Event-Driven)** — WHEN 수집이 CI 픽스처를 생성하면, THEN 소형 결정론적 256×256 ROI 크롭(`[T]` 크기)만을 유일한 커밋 대상 바이너리로 방출해야 하며, 이 픽스처 집합은 **CalibSet 소스 3종 프레임의 ROI 크롭 — MasterDark.raw · 대표 CalSet 레벨 1개(CalSet_19008) · BPM.raw — 을 반드시 포함**해야 한다(D6: 실데이터 부재에도 CalibSet 빌드→게이트→왕복이 상시 실행되는 realdata-독립 CI 근거). 각 크롭이 어느 소스 프레임에서 왔는지 사이드카/픽스처 파일명으로 명시한다(예 `masterdark_256.raw`·`calset_19008_256.raw`·`bpm_256.raw`).

### REQ-REALDATA-CALIB — 샘플 CalibSet 빌더의 **구조 검증**(비정본) (SWR-000-5/8, XDET-TC-041)

- **REQ-REALDATA-CALIB-1 (Event-Driven)** — WHEN 샘플 CalibSet 빌더가 실행되면, THEN MasterDark.raw→`CalibSet(OFFSET)`, CalSet_*→`CalibSet(GAIN)`, BPM.raw→`CalibSet(DEFECT)`를 빌드→`_calibration_gate`→save/load 왕복의 **구조(빌더 배선) 검증**으로만 수행해야 한다(스키마 유효 `CalibSet.validate()`·채워진 payload·npz+json). 빌드 결과는 **비정본**으로 라벨링한다: `panel_id="SAMPLE-EDROGI-16BIT"`, provenance에 `sample=true` 마커, 산출물은 `tests/` 아래에 둔다(프로젝트 파이프라인이 실 캘리브레이션으로 소비하는 위치에 절대 두지 않음). payload 키 리터럴은 소비 모듈이 읽는 확정 리터럴 `O_map`(offset)/`G_map`(gain, 단일점)/`class_map`(defect)를 그대로 사용한다(발명 금지, D4).
- **REQ-REALDATA-CALIB-2 (Ubiquitous)** — 모든 샘플 CalibSet은 상호 일치하는 `panel_id="SAMPLE-EDROGI-16BIT"`, resolution(3072×3072 실측 아암 / 256×256 CI 픽스처), 명시적 validity window(valid_from/valid_until), kind, provenance(`sample=true` + 출처)를 가져야 한다(lesson L#3: 게이팅은 resolution만이 아니라 panel_id 상호일치·kind-stage 배선·validity를 요구). CalSet DN 레벨(19008 등)·`DOSE METER` 값은 이 스키마에 기록되되 **상수/임계로 승격되지 않는다**(REQ-REALDATA-QUARANTINE-2/4).
- **REQ-REALDATA-CALIB-3 (Event-Driven)** — WHEN 샘플 CalibSet이 오케스트레이터 진입 게이트에 소비되면, THEN 기존 `pipeline/orchestrator.py::_calibration_gate`가 kind-stage 배선·panel_id 상호일치·resolution 일치·validity를 검증해야 한다(신규 게이트 없이 기존 게이트 재사용 — 배선 구조 검증이 목적, 출력 수치는 비정본).
- **REQ-REALDATA-CALIB-4 (Unwanted)** — IF 빌더가 소스 캘리브레이션 프레임(MasterDark/CalSet/BPM) 부재 상태에서 기본값으로 대체하려 하면, THEN 명시적 오류로 거부해야 한다(SWR-000-5 무단 기본값 대체 금지 — 무음 대체 아님).
- **REQ-REALDATA-CALIB-5 (Unwanted)** — IF 샘플 CalibSet 산출물을 프로젝트 파이프라인이 실 캘리브레이션으로 소비하는 경로(운영 소비 지점)에 두거나, CalSet DN·DOSE 값을 모듈 상수·인수 임계로 승격하려 하면, THEN 이를 금지해야 한다(산출물은 `tests/` 아래 비정본 픽스처로만 — REQ-REALDATA-QUARANTINE-3).
- **REQ-REALDATA-CALIB-6 (Event-Driven)** — WHEN CI가 realdata 마커 없이 실행되면, THEN 커밋된 256² 소스 크롭(MasterDark/대표 CalSet/BPM)으로부터 샘플 CalibSet 빌드→`_calibration_gate`→save/load 왕복이 **상시(realdata-독립) 통과**해야 한다(D6 — 실데이터 부재에도 빌더 구조 검증이 항상 실행되는 always-on CI).

### REQ-REALDATA-TESTARM — 실측 아암 활성화 · 합성 유지 · 부재 skip (XDET-TC-001~007, 042~043)

- **REQ-REALDATA-TESTARM-1 (Event-Driven)** — WHEN `images/에드로지16BIT/`가 존재하고 realdata 스위트가 실행되면, THEN XDET-TC-001~003이 실측 프레임 + 실측 CalibSet으로 offset/gain/defect 실측 아암을 수행해야 한다(CLAUDE.md T2 "TC-001~003 합성+실측").
- **REQ-REALDATA-TESTARM-2 (Event-Driven)** — WHEN 데이터셋이 존재하면, THEN XDET-TC-004~005가 GHOST 감쇠열(first-frame lag·IRF 입력) 실측 아암을, XDET-TC-006~007이 Bright_NPS 앙상블의 256² ROI NPS/NNPS 실측 아암을 수행해야 한다.
- **REQ-REALDATA-TESTARM-3 (Event-Driven)** — WHEN 데이터셋이 존재하면, THEN XDET-TC-042가 아크릴 스텝 팬텀의 측정 신호에 대해 **sanity 게이트**만 수행해야 한다: 측정 mean-DN이 유한·비퇴화이고 장수(감쇠) 증가에 대해 물리적으로 기대되는 **단조성**(장수↑ → 선량↓ → 신호↓)을 만족하며 물리적으로 타당한 대역에 든다. `DOSE METER` 값은 표시·플롯에만 쓰고 인수 임계로 승격하지 않는다. **절대 허용오차 및 DN-vs-µGy 판정 축은 명시적으로 이연(run-deferred)**하며, 격리 원칙상 이 샘플 세트로부터의 **피팅 자체가 차단**된다(정본 지침 세트 전용, REQ-REALDATA-QUARANTINE-2/4; D2).
- **REQ-REALDATA-TESTARM-4 (Event-Driven)** — WHEN 데이터셋이 존재하면, THEN XDET-TC-043이 최소선량(45kV/20mA/0.4mAs) 영역에서 SNRn·저선량 노이즈 플로어 엔진이 **유한·비퇴화 출력을 산출**하는지 **sanity 게이트**로만 확인해야 한다(암전류 제한 영역; 비정본 — 절대 임계·튜닝은 정본 지침 세트로 이연, REQ-REALDATA-QUARANTINE; D2).
- **REQ-REALDATA-TESTARM-5 (State-Driven)** — WHILE `images/에드로지16BIT/`가 부재인 동안, `@pytest.mark.realdata`로 표시된 모든 테스트는 깨끗이 skip되어야 한다(pytest skip — fail/error 아님).
- **REQ-REALDATA-TESTARM-6 (Ubiquitous)** — 시스템은 기존 합성 검증 경로(T1 합성 팬텀 기반 XDET-TC-000~021 합성 아암)를 제거하지 않고 live로 유지해야 한다(CLAUDE.md T1 원칙 — 실측 아암은 additive 병렬 추가).

### REQ-REALDATA-GUI — 헤드리스 GUI 6-스위트 (SPEC-VIEWER-001 소비, XDET-TC-044~049)

- **REQ-REALDATA-GUI-1 (Event-Driven)** — WHEN 실측 3072² 프레임이 로더로 로드되면, THEN GUI 테스트 (a)가 XFrame shape=(3072,3072)/float32와 호버 프로브의 저장 float32 원값을 검증해야 한다(XDET-TC-044; `common/io.load_raw_frame`·`probe.probe_at`).
- **REQ-REALDATA-GUI-2 (Event-Driven)** — WHEN 캡처와 그 `_result`가 함께 로드되면, THEN GUI 테스트 (b)가 diff/blink를 diff 레이어 + target 레이어로 렌더해야 한다(XDET-TC-045; `layers.make_diff_layer`/`CompareView` — `_result`는 골든 아닌 target 레이어).
- **REQ-REALDATA-GUI-3 (Event-Driven)** — WHEN 샘플 CalibSet으로 offset 다음 gain을 모듈 패널로 연속 실행하면, THEN GUI 테스트 (c)가 2단 처리의 출력 XFrame이 **산출되고 유한·비퇴화**임을 검증해야 한다(XDET-TC-046; `module_panel.run_module` offset 출력→gain 입력의 `process` 산출 경로 — `run_harness`는 출력 프레임 미산출이므로 이 경로가 아님; 특정 수치값이 아니라 **실행+유한 출력** sanity).
- **REQ-REALDATA-GUI-4 (Event-Driven)** — WHEN 지표 패널이 아크릴 팬텀 프레임에 대해 실행되면, THEN GUI 테스트 (d)가 MTF/NPS/SNR **엔진이 실행되어 유한 출력을 산출**함을 `metrics/` 위임으로 검증해야 한다(XDET-TC-047; `metrics_panel.plot_mtf` + 엔진 NPS/SNR, C-09 지표 자체계산 0 — **특정 수치값이 아니라 실행+유한 출력** sanity, EV 하드 게이트 아님).
- **REQ-REALDATA-GUI-5 (Unwanted)** — IF 어떤 GUI 동작이 `data/` 하위 파일 쓰기를 시도하면, THEN 쓰기 가드가 이를 거부해야 한다(XDET-TC-048; `io_panel.guard_output_path`, C-20 읽기-실행 전용 — 실데이터 불요, 상시 실행 회귀).
- **REQ-REALDATA-GUI-6 (Event-Driven)** — WHEN 전체 해상도 3072² 프레임이 다운샘플 스모크 경로로 처리되면, THEN GUI 테스트 (f)가 **다운샘플 출력 XFrame의 shape가 기대 축소 해상도와 일치하고 통계가 유한·비상수(non-constant)**임을 단정해야 한다(XDET-TC-049; `@pytest.mark.slow`+`@pytest.mark.realdata` — '완료'라는 공허한 후치조건 대신 구체적 형상·통계 단정, D1).

### REQ-REALDATA-CONTRACT — additive·툴링·`_result` 비-골든·마커 (SWR-000-2/6/7, VIEWER additive 규약)

- **REQ-REALDATA-CONTRACT-1 (Ubiquitous)** — 수집기는 `scripts/` 툴링이며 처리 모듈이 아니다: `process(XFrame,CalibSet,Params)->XFrame`를 정의하지 않고, `CANONICAL_ORDER` 스테이지·신규 `CalibKind`·`_KIND_BY_STAGE` 엔트리를 추가하지 않는다(SWR-000-2/6).
- **REQ-REALDATA-CONTRACT-2 (Ubiquitous)** — 본 작업은 additive이다: `common/contract.py`·`common/xframe.py`·`pipeline/orchestrator.py` 표면은 불변(KEPT)이며, `common/io.load_raw_frame`·`common/calibset.CalibSet`·`common/synth_calibset.make_synthetic_calibset`를 재사용한다.
- **REQ-REALDATA-CONTRACT-3 (Unwanted)** — IF 실데이터 인수 테스트가 모듈 출력을 `_result` 프레임에 대해 bit-동일 또는 ±1 LSB 동등으로 단정하면, THEN 이를 금지해야 한다(`_result`는 다른 알고리즘·다른 출력 스케일 — SWR-000-7 골든 아님, **수치 권위 0(zero numeric authority)**; 허용 용도 = GUI diff/시각 target 레이어 + 비수치 sanity 교차확인에 한함, REQ-REALDATA-QUARANTINE-3).
- **REQ-REALDATA-CONTRACT-4 (Event-Driven)** — WHEN `realdata`/`slow` 마커가 사용되면, THEN 이들은 pyproject pytest 설정에 등록되어야 하며, 신규 GUI 테스트 블록은 XDET-TC-040~049 범위 id만 사용해 Gen 1 캡스톤 스캔(`range(0,22)`)을 오작동시키지 않아야 한다(D9 선례).

### REQ-REALDATA-VALIDATE — 실행 증거 게이트 · CalibSet 왕복 · 결정론 픽스처 · 수치-출처 가드 (lesson L#1, XDET-TC-040~049)

- **REQ-REALDATA-VALIDATE-1 (Event-Driven)** — WHEN 수집 스크립트가 데이터셋 존재 하에 완료되면, THEN 검증 가능한 비어있지 않은 산출물(프레임당 사이드카 ≥1, raw당 매니페스트 엔트리 1, CalibSet 3종, ROI 픽스처 ≥1)을 실제 실행 증거로 산출해야 한다(lesson L#1 — 헛통과 아님).
- **REQ-REALDATA-VALIDATE-2 (Event-Driven)** — WHEN realdata 테스트가 데이터셋 존재 하에 실행되면, THEN "예외 미발생"이 아니라 구체적 실행 증거(XFrame shape/dtype, 비퇴화 통계, 지표 범위 내)를 단정해야 한다(lesson L#1).
- **REQ-REALDATA-VALIDATE-3 (Event-Driven)** — WHEN 빌드된 샘플 CalibSet을 save 후 load하면, THEN 왕복이 스키마·payload를 보존해야 하며(`CalibSet.save/load`), 커밋된 256² CI 픽스처는 결정론적으로 재현되어야 한다.
- **REQ-REALDATA-VALIDATE-4 (Event-Driven)** — WHEN 수치-출처 가드 테스트가 실행되면, THEN (a) 어떤 모듈 Params 기본값도 샘플 유도 수치를 참조하지 않고, (b) 어떤 인수 EV 임계도 샘플 유도 수치를 참조하지 않으며, (c) 샘플 매니페스트의 모든 엔트리가 `usage="sample-plumbing"`임을 단정해야 한다(REQ-REALDATA-QUARANTINE 그룹의 집행 게이트 — `apps.gui.io_panel.guard_output_path`(C-20) 물리 쓰기 가드의 **수치 아날로그**; 상시 실행, 실데이터 불요).

## Exclusions (What NOT to Build)

- **샘플 세트로 수치 작업 없음(격리, HARD)** — `images/에드로지16BIT/`는 SAMPLE/플러밍 전용이다. 이 세트로 [B]/[T]/[P] 파라미터 유도·피팅·튜닝, 골든/정본/기대 수치 레퍼런스, 인수 EV 임계·허용오차·보정 상수 설정, 알고리즘/모듈 수치 거동 변경을 **하지 않는다**. 수치 작업의 정본 근거는 추후 별도 SPEC으로 재등록될 "지침(guiding)" 취득세트뿐이다(REQ-REALDATA-QUARANTINE).
- **원본 raw 저장소 복사 없음** — 1.4GB 전체 해상도 raw는 `images/`에만 상주한다. `data/`에는 사이드카·매니페스트·실측 CalibSet(npz/json)·소형 파생 256² ROI 픽스처만 둔다. 전체 실측 CalibSet npz·사이드카·매니페스트는 `images/`에서 재생성 가능한 **로컬 빌드 산출물**(gitignore)이며, 커밋되는 유일한 바이너리는 소형 256² ROI 픽스처다.
- **`_result` 골든 레퍼런스 사용 없음(SWR-000-7)** — 벤더 `_result.raw`는 다른 알고리즘·다른 스케일이므로 ±1 LSB/bit-동일 판정의 기준이 되지 않는다. 통계 교차확인 + GUI diff/target 레이어로만 쓴다.
- **[B]/[T] 파라미터 확정·튜닝 없음 + 샘플 세트 영구 제외** — [B]/[T] 값(예: noisy 6× median 재확인, dead/over-under/non-uniform 임계, IRF 계수)의 모듈 Params/CalibSet 확정·튜닝은 본 SPEC 범위 밖이며, **현재 샘플 세트(`images/에드로지16BIT/`)는 그 수치 검증에서 영구적으로 제외**된다. 오직 추후 별도 SPEC으로 재등록되는 정본 "지침(guiding)" 취득세트만이 [B]/[T] 수치 확정·튜닝을 수행할 수 있다(REQ-REALDATA-QUARANTINE). 본 SPEC은 코드 경로·아암·CalibSet 빌더 구조 검증까지만 성립시킨다.
- **처리 모듈·오케스트레이터 표면 변경 없음** — `process` 시그니처·`CANONICAL_ORDER`·`_KIND_BY_STAGE`·신규 `CalibKind`·기존 import-linter 계약은 불변(KEPT). 수집은 `scripts/` 툴링이다.
- **포화 복원 없음(SWR-602)** — 실데이터 처리 아암은 포화 영역을 "복원"하지 않는다.
- **합성 검증 제거 없음** — T1 합성 팬텀 검증(XDET-TC-000~021 합성 아암)은 유지된다. 실측 아암은 그것을 대체하지 않고 병렬 추가한다.
- **Gen 2 항목 없음** — DL·ADR 등은 구현하지 않는다.
- **성능·해상도 최적화 없음** — 전체 3072² 스모크(테스트 f) 외에 속도/메모리 미세 최적화는 범위 밖(정확성·재현성 목적).

## 결정 필요/확인 사항

아래 항목 중 **1·2·3·7은 확정(RESOLVED)**, **4는 확정-이연/차단**, **5·6은 여전히 확인 대상**이다. 항목 번호는 하류 참조를 위해 유지한다. 확정 요지는 v0.2.0 HISTORY로 접었다.

1. **[확정 — RESOLVED] GAIN CalibSet 구성** — `modules/gain.py`는 단일점 `G_map` 하나만 읽는다(다중점 anchor SWR-202는 `NotImplementedError`로 명시 이연: "provide a single-point 'G_map' CalibSet"). **결정**: 샘플 GAIN CalibSet은 단일 `G_map`(운영 DN에 가까운 CalSet 레벨 1개, 예 CalSet_19008 center≈19095)만 채운다. 다른 레벨은 매니페스트에 인덱싱만 하고 CalibSet에는 넣지 않는다. **rationale**: 소비 모듈이 단일 map만 소비하며, 다중 레벨 선형성 fit은 격리 원칙상 이 샘플 세트에서 금지(정본 세트 전용).
2. **[확정 — RESOLVED] OFFSET/GAIN/DEFECT payload 키 리터럴** — 소스 확인 완료: offset=`O_map`(`modules/offset.py::K_OFFSET_MAP`), gain=`G_map`(`modules/gain.py::K_GAIN_MAP`, 단일점), defect=`class_map`(`modules/defect.py::K_CLASS_MAP`, 정수 분류 라벨). **rationale**: 빌더는 이 확정 리터럴을 그대로 사용하며 발명하지 않는다(D4).
3. **[확정 — RESOLVED] panel_id 값 + validity window** — 샘플 세트는 비정본이므로 실 패널 식별자에 의존하지 않는다. **결정**: `panel_id="SAMPLE-EDROGI-16BIT"`(고정), validity window는 넓은 플레이스홀더, provenance에 `sample=true` + 출처 기록. **rationale**: 정본 panel_id·유효기간은 추후 정본 지침 세트 SPEC에서 부여되며, 여기 값들은 수치 근거가 아니다(REQ-REALDATA-QUARANTINE).
4. **[확정 — 이연/차단] 선형성 허용오차·선량 축(XDET-TC-042)** — **결정**: 절대 허용오차·DN-vs-µGy 판정 축은 **run-deferred**이며, 격리 원칙상 이 샘플 세트로부터의 **피팅 자체가 차단**된다. P1 샘플 아암은 장수 단조성 + 유한·비퇴화 + 물리적 타당 대역의 sanity만 판정한다(D2). **rationale**: 절대 선량 축·허용오차 확정은 정본 지침 세트(별도 SPEC)의 수치 검증 소관(REQ-REALDATA-QUARANTINE-2/4).
5. **[확인] `_result` sanity 교차확인 항목** — `_result`는 수치 권위 0이므로 **비수치 sanity 교차확인**(히스토그램 겹침·순서/경계 상관 등, 동등성 단정 없음)만 허용. 기본값: 순서·경계 sanity만. 확인: 채택할 비수치 sanity 항목(임계 없음 — 격리상 `[T]` 임계 유도도 금지).
6. **[확인] TC 번호 블록 XDET-TC-040~049** — 샘플 신규 관심사 블록. 기본값: 040~049(수집=040, CalibSet=041, 선형성=042, SNRn=043, GUI a~f=044~049). 확인: 이 블록이 향후 예약 블록과 충돌하지 않는지(Gen1=000~021, 022~029 예약-미사용, VIEWER=030~037, 038~039 갭).
7. **[확정 — RESOLVED] 아크릴 장수→프레임 매핑 + 선량 단위 정규화(D5)** — 폴더/파일명 토큰 `아크릴N장`=장수, 접미사=프레임 인덱스, `DOSE METER.txt`가 장수로 키잉(1장 1700DN/8.5µGy … 5장 260DN/850nGy; 낮은 장수=얇은 감쇠=높은 선량). **결정**: 매니페스트는 선량을 µGy로 정규화(`dose_ugy`, 850nGy → 0.85µGy)하되 원 단위 토큰(`dose_raw="850nGy"`)을 함께 보존한다. **rationale**: 단위 혼용(nGy/µGy) 제거 + 원문 추적성 유지; 값들은 표시·플롯 전용(비임계, REQ-REALDATA-QUARANTINE-4).
