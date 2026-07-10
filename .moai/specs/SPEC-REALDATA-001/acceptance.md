# SPEC-REALDATA-001 — 인수 기준 (Acceptance Criteria)

DoD: **샘플(플러밍 전용) 취득세트를 외부참조로 수집(무복사) + 플러밍 검증 아암 추가(합성 유지) + 헤드리스 GUI 6-스위트.** **[HARD] 샘플 세트는 비정본(NON-AUTHORITATIVE)이다** — [B]/[T]/[P] 파라미터 유도·피팅·튜닝, 골든/정본/기대 레퍼런스, EV 임계·허용오차·보정 상수 설정, 알고리즘 수치 거동 변경의 근거로 쓰이지 않으며(REQ-REALDATA-QUARANTINE), 지표 단정은 **sanity 전용**(유한·비퇴화·물리적 기대 단조)이다. 정본 "지침(guiding)" 세트는 추후 별도 SPEC. 모든 기준은 관측 가능(산출 파일 존재·매니페스트 엔트리 수·`usage` 필드·CalibSet 왕복·XFrame shape/dtype·지표 유한 출력·거부 발생·skip 발생·마커 등록)해야 한다. `[T]`/`[B]` 임계는 설정·매니페스트·CalibSet으로 외부화(하드코딩 아님)한다. `_result`는 골든 레퍼런스가 아니다(수치 권위 0 — GUI target 레이어·비수치 sanity만). 코어 4계층 계약(SWR-000-2/6/7/8)·`CANONICAL_ORDER`는 불변(KEPT). 실측(샘플) 아암은 XDET-TC-001~007 in-place, 신규 관심사는 XDET-TC-040~049.

## 자동 검출 vs 코드리뷰 설계 규칙 (과잉 약속 방지)

- **자동 검출(인수 기준 = 테스트/CI 게이트)**: 사이드카 생성(INGEST-1)·매니페스트 엔트리 + `usage="sample-plumbing"`(INGEST-2)·메타 파싱 + 선량 µGy 정규화/원 토큰 보존(INGEST-3, D5)·무복사 가드 거부(INGEST-4)·256² 픽스처 방출(소스 3종 크롭 포함, INGEST-5/D6)·샘플 CalibSet 3종 빌드·`validate()` 통과·왕복(CALIB-1/VALIDATE-3)·panel_id=`SAMPLE-EDROGI-16BIT`/provenance `sample=true`/kind/validity 필드(CALIB-2)·`_calibration_gate` 통과(CALIB-3)·소스 부재 시 거부(CALIB-4)·256² 소스 크롭 realdata-독립 상시 빌드→게이트→왕복(CALIB-6/D6)·아암 실행 증거(TESTARM-1~2/VALIDATE-2)·선형성·SNRn sanity(TESTARM-3~4/D2)·부재 skip(TESTARM-5)·합성 스켈레톤 live 유지(TESTARM-6)·GUI 6종 로직 검증(GUI-1~6)·data/ 쓰기 거부(GUI-5)·**수치-출처 가드**(VALIDATE-4: Params 기본값·EV가 샘플 수치 미참조 ∧ 매니페스트 `usage=sample-plumbing`)·마커 등록(CONTRACT-4)·수집 산출물 비어있지 않음(VALIDATE-1).
- **코드리뷰 설계 규칙(테스트 단정 아님)**: 수집기가 `scripts/` 툴링이며 `process` 시그니처·`CANONICAL_ORDER`·신규 CalibKind 부재(CONTRACT-1 — 코드 경로 부재는 리뷰 + import-linter 무변경으로 근사)·`_result` bit-동일 단정 부재(CONTRACT-3 — 테스트 코퍼스에 `_result` 동등성 단정 부재는 리뷰)·샘플 세트로부터의 파라미터 유도·코드 수치 거동 변경 부재(QUARANTINE-2/5 — 수치-출처 가드로 근사 자동 검출, 나머지는 리뷰)·샘플 CalibSet 산출물이 `tests/` 상주(파이프라인 소비 위치 부재, CALIB-5 리뷰)·`data/edrogi/` gitignore·전체 raw 무복사 설계(INGEST-4는 가드 거부로 자동 검출, 트리 무복사는 리뷰).

## Given-When-Then 시나리오

### Scenario 1 — 수집: 사이드카·매니페스트·무복사 (REQ-REALDATA-INGEST-1, -2, -3, -4, -5)
- **Given** `images/에드로지16BIT/`(5개 서브폴더, 헤더 없는 3072² uint16 raw)와 `아크릴/DOSE METER.txt`가 주어져 있다.
- **When** `uv run python scripts/ingest_edrogi.py`가 실행된다.
- **Then** (a) 각 raw에 대해 `{"resolution":[3072,3072],"dtype":"uint16"}` 사이드카가 `data/edrogi/` 미러 경로에 생성되고, (b) `data/edrogi/manifest.json`이 raw별 엔트리(raw_path·category·kv·ma·mas·dose·plate_count·frame_index·has_result_pair)로 산출되며, (c) kV/mA/mAs가 파일명에서·선량이 `DOSE METER.txt`에서 장수 기준으로 파싱되고, (d) 전체 해상도 raw를 `data/`로 복사하려는 시도가 거부되며(외부참조 무복사), (e) 소형 256² ROI 크롭만 커밋 대상 바이너리로 방출된다.

### Scenario 2 — 샘플 CalibSet 빌더 구조 검증·게이트·왕복·상시 CI (REQ-REALDATA-CALIB-1, -2, -3, -4, -5, -6, VALIDATE-3)
- **Given** `16bit cal/`의 MasterDark.raw·CalSet_*·BPM.raw(실측 아암) 또는 커밋된 256² 소스 크롭(masterdark/calset_19008/bpm, realdata-독립)이 주어져 있다.
- **When** 샘플 CalibSet 빌더가 실행되고 결과를 `save()`/`load()` 왕복한다.
- **Then** (a) `CalibSet(OFFSET)`(MasterDark)·`CalibSet(GAIN)`(단일 `G_map`, CalSet 대표 레벨)·`CalibSet(DEFECT)`(BPM)가 확정 리터럴 payload(`O_map`/`G_map`/`class_map`)로 빌드되어 `CalibSet.validate()`를 통과하고, (b) 각 CalibSet이 상호 일치 `panel_id="SAMPLE-EDROGI-16BIT"`·resolution·validity window·provenance(`sample=true`)를 가지며(L#3, 비정본 라벨), (c) `_calibration_gate`가 kind-stage·panel_id·resolution·validity를 통과시키고, (d) save→load 왕복이 스키마·payload를 보존하며, (e) 산출물이 `tests/` 아래에 상주하고 파이프라인 실 캘리브레이션 소비 위치에 없으며 CalSet DN·DOSE가 상수/임계로 승격되지 않고(CALIB-5), (f) 256² 소스 크롭 경로가 realdata 마커 없이 상시(realdata-독립) 빌드→게이트→왕복을 통과한다(CALIB-6/D6).

### Scenario 3 — 실측 아암 활성화 · 합성 유지 · 부재 skip (REQ-REALDATA-TESTARM-1, -2, -5, -6, VALIDATE-2)
- **Given** `images/에드로지16BIT/`가 존재하는 경우와 부재인 경우가 각각 주어져 있다.
- **When** `uv run pytest -m realdata`가 실행된다.
- **Then** (a) 존재 시 XDET-TC-001~003이 실측 프레임+실측 CalibSet으로 offset/gain/defect 아암을 수행하고, (b) XDET-TC-004~005가 GHOST 감쇠열, XDET-TC-006~007이 Bright_NPS 256² ROI 아암을 수행하며, (c) 각 아암이 "예외 미발생"이 아니라 XFrame shape=(3072,3072)/float32·비퇴화 통계를 단정하고(L#1), (d) 부재 시 realdata 테스트가 깨끗이 skip되며(fail/error 아님), (e) 합성 아암(XDET-TC-000~021)은 live로 유지된다.

### Scenario 4 — 선형성·SNRn sanity (비정본, REQ-REALDATA-TESTARM-3, -4; D2)
- **Given** 아크릴 스텝 팬텀(1~5장) + 최소선량 프레임 + `DOSE METER.txt` 선량 참고값(비정본·표시 전용)이 주어져 있다.
- **When** XDET-TC-042(선형성 sanity)·XDET-TC-043(SNRn sanity)이 실행된다.
- **Then** (a) 측정 mean-DN이 유한·비퇴화이고 장수(감쇠) 증가에 대해 물리적으로 기대되는 **단조성**(장수↑ → 선량↓ → 신호↓)을 만족하며 물리적으로 타당한 대역에 든다 — `DOSE METER` 값은 표시·플롯에만 쓰고 인수 임계로 승격하지 않으며, **절대 허용오차·DN-vs-µGy 판정 축은 이연되고 샘플 피팅은 차단**된다(REQ-REALDATA-QUARANTINE-2/4), (b) 최소선량(45kV/20mA/0.4mAs) 영역의 SNRn·저선량 노이즈 플로어 엔진이 유한·비퇴화 출력을 산출한다(절대 임계·튜닝은 정본 지침 세트로 이연).

### Scenario 5 — GUI 6-스위트 (REQ-REALDATA-GUI-1, -2, -3, -4, -5, -6)
- **Given** `QT_QPA_PLATFORM=offscreen` CI, 실측 프레임/`_result`/실측 CalibSet(또는 부재 시 skip)이 주어져 있다.
- **When** `uv run pytest tests/apps/gui/test_tc_realdata_gui.py`가 실행된다.
- **Then** (a) 실측 3072² 로드 시 XFrame shape=(3072,3072)/float32 + 프로브 저장 float32 원값 검증(XDET-TC-044), (b) 캡처+`_result` diff/blink가 diff 레이어+target 레이어로 렌더(XDET-TC-045, `_result`=target·수치 권위 0), (c) offset→gain 연속 `run_module`(process 산출 경로)로 2단 출력 XFrame이 **산출+유한·비퇴화**임을 검증(XDET-TC-046, 특정 수치값 아님), (d) 아크릴 프레임 MTF/NPS/SNR **엔진이 실행+유한 출력**을 `metrics/` 위임으로 산출(XDET-TC-047, C-09, 특정 수치값 아님), (e) `data/` 쓰기 시도가 `guard_output_path`로 거부(XDET-TC-048, 상시 실행), (f) 전체 3072² 다운샘플 스모크의 출력 XFrame **shape가 기대 축소 해상도와 일치 ∧ 통계 유한·비상수**(XDET-TC-049, slow+realdata; D1 — '완료' 아님).

### Scenario 6 — 계약·마커·툴링 (REQ-REALDATA-CONTRACT-1, -2, -3, -4)
- **Given** 수집기(`scripts/`)와 신규 테스트 블록, pyproject 설정이 주어져 있다.
- **When** 테스트 스위트·import-linter가 실행된다.
- **Then** (a) 수집기가 `process` 시그니처·`CANONICAL_ORDER` 스테이지·신규 CalibKind를 추가하지 않고(코어 표면 KEPT), (b) `common/contract.py`·`common/xframe.py`·`pipeline/orchestrator.py`가 불변이며, (c) 어떤 실데이터 테스트도 모듈 출력을 `_result`에 bit-동일/±1 LSB로 단정하지 않고, (d) `realdata`/`slow` 마커가 pyproject에 등록되고 신규 GUI 소스가 XDET-TC-040~049 id만 사용한다(Gen1 캡스톤 무간섭).

### Scenario 7 — 수집 실행 증거 (REQ-REALDATA-VALIDATE-1)
- **Given** 데이터셋이 존재한다.
- **When** 수집 스크립트가 완료된다.
- **Then** 비어있지 않은 산출물(프레임당 사이드카 ≥1, raw당 매니페스트 엔트리 1, CalibSet 3종, ROI 픽스처 ≥1)이 실제 실행 증거로 확인된다(lesson L#1 — 헛통과 아님).

### Scenario 8 — 격리 집행: 수치-출처 가드 (REQ-REALDATA-QUARANTINE-1~5, REQ-REALDATA-VALIDATE-4)
- **Given** 모듈 Params 기본값·인수 EV 임계 정의부와 샘플 매니페스트가 주어져 있다(실데이터 불요, 상시 실행).
- **When** 수치-출처 가드 테스트가 실행된다(`apps.gui.io_panel.guard_output_path`(C-20) 물리 쓰기 가드의 수치 아날로그).
- **Then** (a) 어떤 모듈 Params 기본값도 샘플 유도 수치를 참조하지 않고, (b) 어떤 인수 EV 임계도 샘플 유도 수치를 참조하지 않으며, (c) 샘플 매니페스트의 모든 엔트리가 `usage="sample-plumbing"`임이 단정된다(REQ-REALDATA-QUARANTINE 집행 게이트).

## Edge Cases (부정/경계 케이스)

### EC-1 — 전체 raw 복사 거부 (REQ-REALDATA-INGEST-4)
- **Given** 3072² raw를 `data/`로 복사하려는 수집 경로.
- **When** 그 경로가 실행된다.
- **Then** 복사가 거부되고 `data/`에는 사이드카/매니페스트/CalibSet/소형 픽스처만 존재한다(원본은 `images/` 상주).

### EC-2 — 데이터셋 부재 → 깨끗한 skip (REQ-REALDATA-TESTARM-5)
- **Given** `images/에드로지16BIT/` 부재.
- **When** `uv run pytest -m realdata`가 수집·실행된다.
- **Then** realdata 테스트가 pytest skip으로 처리된다(fail/error 아님; collection 오류 없음).

### EC-3 — 소스 캘리브레이션 부재 → 거부 (REQ-REALDATA-CALIB-4)
- **Given** MasterDark/CalSet/BPM 중 하나가 부재.
- **When** CalibSet 빌더가 실행된다.
- **Then** 무단 기본값 대체 없이 명시적 오류로 거부된다(SWR-000-5).

### EC-4 — `_result` 골든 오용 방지 (REQ-REALDATA-CONTRACT-3)
- **Given** 모듈 출력과 `<name>_result.raw`.
- **When** 실데이터 테스트가 비교를 수행한다.
- **Then** bit-동일/±1 LSB 동등 단정이 존재하지 않으며, 허용된 통계 교차확인/GUI target 레이어 사용만 나타난다(SWR-000-7; `_result`는 다른 알고리즘·스케일).

### EC-5 — data/ 쓰기 가드 (REQ-REALDATA-GUI-5)
- **Given** `data/` 하위 파일 쓰기를 시도하는 GUI 동작.
- **When** `guard_output_path(path, project_root)`가 그 경로를 검사한다.
- **Then** 쓰기가 거부된다(C-20 읽기-실행 전용; 실데이터 불요·상시 실행 회귀).

### EC-6 — 수집 실행 증거 비어있음 검출 (REQ-REALDATA-VALIDATE-1/2)
- **Given** 산출 사이드카·매니페스트·CalibSet.
- **When** 수집·아암 테스트가 산출물/통계를 단정한다.
- **Then** 산출물 개수>0·XFrame 비퇴화 통계를 단정하며, 비어있거나 "예외 미발생"만인 경우 실패한다(lesson L#1 헛통과 아님).

### EC-7 — 격리 위반 검출: 샘플 유도 수치 (REQ-REALDATA-QUARANTINE-2/4, VALIDATE-4)
- **Given** 모듈 Params 기본값 또는 인수 EV 임계가 샘플에서 유도된 수치(예 CalSet DN·DOSE 참고값)로 설정되려는 상황, 또는 매니페스트 엔트리에 `usage` 필드가 누락된 상황.
- **When** 수치-출처 가드 테스트가 실행된다.
- **Then** 그 참조/누락이 검출되어 실패한다(격리 집행 — Params 기본값·EV는 샘플 수치 미참조, 매니페스트는 `usage="sample-plumbing"`).

## PARTIAL (샘플·타당성 sanity · 격리·하류 이연)

### 지표 sanity (비정본 — REQ-REALDATA-GUI-4, REQ-REALDATA-TESTARM-3/4; D2)
- 샘플 세트에는 골든 레퍼런스가 없으므로 MTF/NPS/SNR/선형성/SNRn 판정은 **sanity 게이트**(유한·비퇴화·물리적 기대 단조)이며 EV min/typ/max 하드 게이트가 아니다. 절대 허용오차·DN-vs-µGy 판정 축은 이연되고, 격리 원칙상 이 샘플 세트로부터의 **피팅 자체가 차단**된다. 지표 엔진이 실데이터 형상 입력에서 유한·비퇴화 출력을 산출함만 확인한다.

### [B]/[T] 파라미터 확정 (정본 지침 세트 — 별도 SPEC)
- [B]/[T] 값(noisy median 재확인·dead/over-under 임계·IRF 계수 등)의 **모듈 Params/CalibSet 확정·튜닝은 본 SPEC 밖**이며, **현재 샘플 세트는 그 수치 검증에서 영구 제외**된다. 오직 추후 별도 SPEC으로 재등록되는 정본 "지침(guiding)" 취득세트만이 그 수치 확정·튜닝을 수행한다(REQ-REALDATA-QUARANTINE). 본 SPEC은 코드 경로·아암·CalibSet 빌더 구조 검증까지만 성립시킨다.

## 품질 게이트 / Definition of Done

- [ ] **격리(QUARANTINE)**: 샘플 세트 파라미터 유도·골든 레퍼런스·EV 임계 설정·코드 수치 거동 변경 부재(QUARANTINE-1~5, Scenario 8)
- [ ] **수치-출처 가드**: Params 기본값·EV가 샘플 수치 미참조 ∧ 매니페스트 `usage="sample-plumbing"`(VALIDATE-4, Scenario 8, EC-7 — C-20 물리 가드의 수치 아날로그)
- [ ] 수집 사이드카+매니페스트 생성(전 엔트리 `usage="sample-plumbing"`, 선량 µGy 정규화+원 토큰 D5), 전체 raw 무복사 가드(INGEST-1~5, Scenario 1, EC-1, XDET-TC-040)
- [ ] 커밋 256² 픽스처가 CalibSet 소스 3종(MasterDark/CalSet_19008/BPM) ROI 크롭 포함(INGEST-5, D6)
- [ ] 샘플 CalibSet 3종 빌더 **구조 검증**·스키마·게이트·왕복(CALIB-1~4, Scenario 2, EC-3, VALIDATE-3, XDET-TC-041)
- [ ] 샘플 CalibSet 비정본 라벨: `panel_id="SAMPLE-EDROGI-16BIT"`/provenance `sample=true`/validity 상호일치·`tests/` 상주·DN/DOSE 미승격(CALIB-2/-5, L#3)
- [ ] 256² 소스 크롭 realdata-독립 상시 빌드→게이트→왕복 CI(CALIB-6, D6)
- [ ] XDET-TC-001~007 실측(샘플) 아암 in-place + 실행 증거(TESTARM-1~2, Scenario 3, VALIDATE-2)
- [ ] 선형성(XDET-TC-042) + SNRn(XDET-TC-043) **sanity**(단조성+유한+비퇴화, 절대 축 이연·피팅 차단)(TESTARM-3~4, Scenario 4, PARTIAL, D2)
- [ ] 데이터셋 부재 시 realdata 깨끗한 skip(TESTARM-5, Scenario 3, EC-2)
- [ ] 합성 검증 경로(XDET-TC-000~021 합성 아암) live 유지(TESTARM-6)
- [ ] GUI (a) 실측 로드+프로브(GUI-1, XDET-TC-044) / (b) diff·blink vs `_result`(GUI-2, XDET-TC-045) / (c) offset→gain `run_module` 실행+유한 출력(GUI-3, XDET-TC-046) / (d) 지표 엔진 실행+유한 출력(GUI-4, XDET-TC-047) / (e) data/ 쓰기 거부(GUI-5, EC-5, XDET-TC-048) / (f) 3072² 스모크 출력 shape=기대 축소 해상도 ∧ 통계 유한·비상수(GUI-6, XDET-TC-049, D1)
- [ ] 수집기 툴링·additive·코어 표면 KEPT(CONTRACT-1~2, Scenario 6)
- [ ] `_result` bit-동일/±1 LSB 단정 부재(수치 권위 0)(CONTRACT-3, EC-4)
- [ ] `realdata`/`slow` 마커 pyproject 등록 + 신규 GUI 소스 XDET-TC-040~049만 사용(022~029·038~039 예약-미사용)(CONTRACT-4, D3/D9)
- [ ] 수집 실행 증거 비어있지 않음(VALIDATE-1, Scenario 7, EC-6, L#1)
- [ ] 「결정 필요/확인 사항」 5·6 run 착수 전 확정(1·2·3·4·7은 RESOLVED/확정-이연)
