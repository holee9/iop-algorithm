# SPEC-REALDATA-001 — 구현 계획 (plan.md)

## 1. 개요

취득세트 `images/에드로지16BIT/`(~1.4GB, 3072² 16-bit LE uint16)를 **외부참조**로 수집하여, 기존 합성 검증에 **플러밍(코드 경로) 검증 아암**을 additive로 추가하고 `apps/gui/`(SPEC-VIEWER-001)를 그 프레임으로 구동하는 헤드리스 GUI 6-스위트를 도입한다. **[HARD] 이 취득세트는 SAMPLE/플러밍 전용·비정본(NON-AUTHORITATIVE)이다** — [B]/[T]/[P] 파라미터 유도·피팅·튜닝, 골든/정본/기대 레퍼런스, EV 임계·허용오차·보정 상수 설정, 알고리즘 수치 거동 변경에 쓰지 않으며(REQ-REALDATA-QUARANTINE), 지표 단정은 sanity 전용이다. 수치 작업의 정본 근거인 "지침(guiding)" 세트는 추후 별도 SPEC으로 재등록된다. 코어 4계층·오케스트레이터 표면은 불변(KEPT), 수집기는 `scripts/` 툴링이다. 모든 명령은 `uv run`으로 실행하며 한글 출력은 `PYTHONIOENCODING=utf-8`을 쓴다(lesson L#4).

## 2. 기술 접근

- **수집(INGEST)**: `scripts/ingest_edrogi.py` — `images/에드로지16BIT/`를 순회하며 (1) raw별 사이드카(`resolution=[3072,3072]`, `dtype="uint16"`)를 `data/edrogi/` 미러 경로에 생성, (2) 파일명·`DOSE METER.txt` 파싱으로 `data/edrogi/manifest.json` 생성(전 엔트리 `usage="sample-plumbing"`; 선량 µGy 정규화 `dose_ugy` + 원 단위 토큰 `dose_raw` 보존 — D5), (3) 소형 256² ROI 크롭을 CI 픽스처로 방출하되 **CalibSet 소스 3종(MasterDark/CalSet_19008/BPM) 크롭을 반드시 포함**(D6). 로더 `common/io.load_raw_frame`는 `load_raw_frame(<images raw>, <data 사이드카>)`로 명시 호출(원본 raw는 `images/` 상주 — 무복사).
- **샘플 CalibSet 구조 검증(CALIB)**: `scripts/ingest_edrogi.py`(또는 `scripts/build_edrogi_calibset.py`) — MasterDark→`CalibSet(OFFSET)`, CalSet 대표 레벨→`CalibSet(GAIN)`(단일 `G_map` — `modules/gain.py`가 단일점만 소비, 다중점 anchor는 `NotImplementedError` 이연), BPM→`CalibSet(DEFECT)`를 확정 리터럴 payload(`O_map`/`G_map`/`class_map`, D4)로 빌드→`_calibration_gate`→`save()`/`load()` 왕복의 **구조 검증만** 수행. 빌드물은 **비정본**: `panel_id="SAMPLE-EDROGI-16BIT"`, provenance `sample=true`, 산출물은 `tests/fixtures/realdata/calib/`(커밋 256² 소스 크롭 기반은 상시 CI, 3072² 실측 아암 산출은 `tmp_path`) — 파이프라인 실 캘리브레이션 소비 위치에 두지 않음(CALIB-5). CalSet DN·DOSE는 상수/임계로 승격 금지. panel_id·validity·provenance 필수(L#3).
- **테스트 아암(TESTARM)**: 기존 XDET-TC-001~007 테스트 모듈에 `@pytest.mark.realdata` 샘플 아암 함수를 in-place 추가(합성 스켈레톤 유지). 신규 선형성(042)/SNRn(043)은 `metrics/` 엔진(compute_mtf/nps/snr/snrn)을 tests/에서 소비하되 **sanity 게이트**(장수 단조성 + 유한·비퇴화 + 물리적 타당 대역; DOSE 참고값 표시 전용, 절대 허용오차·DN/µGy 축 이연·샘플 피팅 차단 — D2). 데이터셋 부재 시 `pytest.importorskip`/경로 skip 가드로 깨끗이 skip.
- **GUI 6-스위트(GUI)**: `tests/apps/gui/test_tc_realdata_gui.py` — VIEWER의 `io_panel.guard_output_path`·`layers.make_diff_layer`/`CompareView`·`module_panel.run_module`·`metrics_panel.plot_mtf`/`recompute_mtf_for_roi`·`probe.probe_at`를 실측 프레임으로 구동. `QT_QPA_PLATFORM=offscreen`. 테스트 (e) 쓰기 가드는 실데이터 불요 상시 실행, (f) 전체 3072² 스모크는 `slow`+`realdata`.
- **설정(CONTRACT)**: `pyproject.toml [tool.pytest.ini_options]`에 `markers = ["realdata: ...", "slow: ..."]` 등록(additive 편집 — 코어 표면 아님). `.gitignore`에 `data/edrogi/`(사이드카·매니페스트·전체 CalibSet) 추가, 소형 256² ROI 픽스처(소스 3종 크롭 포함)만 커밋.
- **격리 집행(QUARANTINE/VALIDATE-4)**: `tests/test_numeric_provenance_guard.py`(신규, 상시 실행·실데이터 불요) — 모듈 Params 기본값·인수 EV 임계 소스를 스캔하여 샘플 유도 수치 미참조를 단정하고, 샘플 매니페스트 전 엔트리가 `usage="sample-plumbing"`임을 단정. `apps.gui.io_panel.guard_output_path`(C-20) 물리 쓰기 가드의 수치 아날로그.

## 3. 파일 변경(additive only)

| 파일 | 유형 | 목적 |
|---|---|---|
| `scripts/ingest_edrogi.py` | 신규(툴링) | 사이드카·매니페스트(`usage`·`dose_raw`)·샘플 CalibSet·ROI 픽스처 생성 |
| `data/edrogi/manifest.json` | 로컬 산출물(gitignore) | 프레임 인덱스(전 엔트리 `usage="sample-plumbing"`) |
| `data/edrogi/**/<name>.json` | 로컬 산출물(gitignore) | raw별 사이드카 |
| `tests/fixtures/realdata/{masterdark,calset_19008,bpm}_256.{raw,json}` | 커밋(소형) | CalibSet 소스 3종 256² ROI 크롭(D6 상시 CI 근거) |
| `tests/fixtures/realdata/calib/{offset,gain,defect}.{npz,json}` | 커밋(소형, 256² 기반) | 비정본 샘플 CalibSet(`SAMPLE-EDROGI-16BIT`); 3072² 아암 빌드는 `tmp_path` |
| `tests/test_tc00X_*.py`(기존) | 확장 | XDET-TC-001~007 샘플 아암 in-place 추가 |
| `tests/test_tc_realdata_linearity.py` | 신규 | XDET-TC-042/043 선형성·SNRn sanity(D2) |
| `tests/test_numeric_provenance_guard.py` | 신규 | 격리 집행 수치-출처 가드(QUARANTINE/VALIDATE-4, 상시) |
| `tests/apps/gui/test_tc_realdata_gui.py` | 신규 | GUI 6-스위트 XDET-TC-044~049 |
| `pyproject.toml` | 편집(additive) | `realdata`/`slow` 마커 등록 |
| `.gitignore` | 편집(additive) | `data/edrogi/` 제외(픽스처 예외) |

**불변(KEPT)**: `common/contract.py`·`common/xframe.py`·`pipeline/orchestrator.py`·`common/io.py`·`common/calibset.py`·`common/synth_calibset.py`·기존 import-linter 계약.

## 4. 마일스톤 (우선순위 기반, 시간 예측 없음)

- **M1 — 수집 골격 (Priority High)**: `scripts/ingest_edrogi.py` 사이드카+매니페스트 생성, 무복사 가드(INGEST-1~4), 256² 픽스처(INGEST-5). DoD: XDET-TC-040 실행 증거(VALIDATE-1).
- **M2 — 샘플 CalibSet 구조 검증 (Priority High)**: OFFSET/GAIN(단일 `G_map`)/DEFECT 빌더 구조 검증, 비정본 라벨(`SAMPLE-EDROGI-16BIT`/`sample=true`/`tests/` 상주), 스키마·게이트·왕복(CALIB-1~5, VALIDATE-3) + 256² 소스 크롭 realdata-독립 상시 CI(CALIB-6/D6). DoD: XDET-TC-041 + `_calibration_gate` 통과 + 상시 256² 빌드 통과. M1 완료 후 착수.
- **M3 — 샘플 아암 sanity (Priority Medium)**: XDET-TC-001~007 in-place 샘플 아암 + 선형성(042)/SNRn(043) **sanity 게이트**(D2) + 부재 skip + 합성 유지(TESTARM-1~6). DoD: 데이터셋 존재 시 실행 증거(VALIDATE-2), 부재 시 skip. M2 완료 후.
- **M4 — GUI 6-스위트 (Priority Medium)**: XDET-TC-044~049(GUI-1~6) 헤드리스((c)(d) 실행+유한 출력, (f) shape+유한·비상수 D1). DoD: offscreen 실행 + (e) 상시 회귀. M3와 병행 가능(파일 분리).
- **M5 — 격리·계약·마커·문서 (Priority High)**: **수치-출처 가드**(QUARANTINE-1~5/VALIDATE-4, 상시 실행 — Params 기본값·EV 샘플 수치 미참조 ∧ 매니페스트 `usage=sample-plumbing`) + 마커 등록·`.gitignore`·`_result` 비-골든 가드(CONTRACT-1~4). DoD: 수치-출처 가드 통과, 마커 등록 확인, 캡스톤 무간섭. (격리 집행은 High — 다른 마일스톤과 병행)

## 5. 명령 예시 (uv 전용, 한글 출력 시 PYTHONIOENCODING=utf-8)

```bash
# 수집 (사이드카 + 매니페스트 + CalibSet + 256 ROI 픽스처)
PYTHONIOENCODING=utf-8 uv run python scripts/ingest_edrogi.py --root images/에드로지16BIT --out data/edrogi

# 샘플 아암 (데이터셋 존재 시 실행, 부재 시 skip)
QT_QPA_PLATFORM=offscreen uv run pytest -m realdata

# realdata-독립 상시 회귀 (합성 경로 + 256² 샘플 CalibSet 구조 검증 + 수치-출처 가드 — 항상 통과)
uv run pytest -m "not realdata and not slow"

# 격리 집행 수치-출처 가드 (상시, 실데이터 불요)
PYTHONIOENCODING=utf-8 uv run pytest tests/test_numeric_provenance_guard.py

# GUI 6-스위트 (헤드리스)
QT_QPA_PLATFORM=offscreen uv run pytest tests/apps/gui/test_tc_realdata_gui.py

# 전체(슬로우 포함)
QT_QPA_PLATFORM=offscreen uv run pytest -m "realdata or slow"
```

## 6. 리스크·완화

- **경로 인코딩(한글 폴더명)**: `images/에드로지16BIT/아크릴/` 등 한글 경로 — `PYTHONIOENCODING=utf-8` + `pathlib` UTF-8 처리로 완화. 매니페스트는 `ensure_ascii=False`.
- **샘플 세트 수치 오용 위험(격리)**: 샘플에서 [B]/[T]/[P] 유도·EV 임계 설정·코드 수치 거동 변경 시 QUARANTINE 위반 — 수치-출처 가드(VALIDATE-4, 상시) + QUARANTINE Unwanted REQ + EC-7로 집행. 수치 확정은 정본 지침 세트(별도 SPEC) 전용.
- **`_result` 오용 위험**: 검토 없이 `_result`를 골든으로 쓰면 SWR-000-7 위반(수치 권위 0) — CONTRACT-3 Unwanted + acceptance EC-4로 가드(bit-동일 단정 금지).
- **payload 키 드리프트**: 실측 CalibSet payload 키가 소비 모듈과 어긋나면 게이트/처리 실패 — 「확인」 2로 빌드 시점 리터럴 참조 강제.
- **CI 픽스처 결정론**: 256² 크롭이 비결정적이면 CI 흔들림 — 고정 시드/고정 ROI 좌표(`[T]`)로 VALIDATE-3 보장.
- **캡스톤 오등록(D9)**: 신규 GUI 소스가 Gen1 TC id(000~021) 문자열 포함 시 삭제 TC를 live로 오등록 — 040~049만 사용(CONTRACT-4).

## 7. 트레이서빌리티

전 요구는 이슈 #29에 대응하며 SWR-000-2/5/6/7/8·SWR-602 + XDET-TC-001~007(샘플 아암) + XDET-TC-040~049(신규)에 매핑된다. **격리(QUARANTINE) 그룹**은 사용자 HARD 제약(이슈 #29)에 대응하며 수치-출처 가드(VALIDATE-4)로 집행된다. 예약-미사용 TC 블록: 022~029·038~039(D3). 상세 매핑은 acceptance.md 참조.
