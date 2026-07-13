---
id: SPEC-XGUI-NDT
version: 0.5.1
status: planned
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-12
updated: 2026-07-13
author: drake.lee
issue_number: 58
labels: [xgui, gui-redesign, verification-gui, ndt, snrn, iqi, thickness, metrics-report, golden-frozen, acceptance]
---

# SPEC-XGUI-NDT — 인수 기준 (acceptance)

> 본 인수기준의 모든 EARS ID·중앙 TC·필수 증거 연결은 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따른다. `baseline-control.md`의 G0와 사용자 승인 전에는 이 체크리스트를 구현 완료 증거로 사용할 수 없으며 모든 TC는 `PLANNED` 상태를 유지한다.

> **구현 대상:** `apps/xdet-console/` C# WPF 앱. `apps/gui/`와 Python 테스트는 계약·검증 선례이며 구현 대상이 아니다.
각 시나리오는 core 알고리즘 증거 **XDET-TC-018/019**를 참조하고, 별도의 GUI-E2E 중앙 블록 **XDET-TC-144~151**로 7 action, accumulator session, 열기·실행·표시·저장·evidence·가드를 검증한다.

**데이터 라벨 원칙:** 등록 실측(에드로지 SAMPLE, `panel_id=SAMPLE-EDROGI-16BIT`, provenance `sample=true`)으로 **실행가능한 것은 `nps_flat` 균일 ROI의 `compute_snr` sanity와 `acrylic_step`의 `correct_thickness` sanity뿐**이다 — **QUARANTINE(이슈 #29)**: sanity만 단언하고 수치 golden/EV 임계 도출·튜닝·적합은 하지 않는다. SRb·SNRn 정규화·IQI Class A/B는 합성/#33 대기다. NDT는 `run_pipeline`/CalibSet을 사용하지 않지만 WPF는 dedicated `IXdetEngine` NDT DTO를 거치며, PythonNet adapter만 `metrics/ndt.py`를 호출한다.

## Scenarios (Given-When-Then)

### Scenario 1 — 입력세트 열기: 상주 폴더 브라우저 (REQ-XGUI-NDT-INPUT-1~4, foundation §4) — **GUI-E2E XDET-TC-144**
- **Given** 그룹 7 탭과 `common.io.load_raw_frame`(io.py:35, headerless 16-bit + `{resolution,dtype}` 사이드카)이 있고 등록 SAMPLE(`nps_flat`, `acrylic_step`)이 상주 폴더에 있으며,
- **When** 사용자가 상주 폴더 브라우저(폴더 트리 + 가상화 썸네일 그리드 + 형제 필름스트립 + 이전/다음)에서 프레임을 선택하거나 단일 파일을 지정하면,
- **Then** 탭이 `load_raw_frame`로 XFrame을 무손실 적재하고, 단일 파일을 지정한 경우에도 그 부모 폴더의 형제 목록을 함께 표시하며, (i) 균일-노출 프레임 시퀀스는 취득 순서로 배열해 현재 shot 인덱스를 표시하고 (ii) 단일 프레임은 두께보정·1D 프로필 대상으로 설정해야 한다. CalibSet 선택·캘리 게이트가 **없어야** 한다(지표 엔진). 1D 프로필 추출은 선 위 픽셀값 **순수 샘플링**(필터·평활·미분 없음)이어야 한다.

### Scenario 2 — 실시간 SNRn 적산 스트리밍 (XDET-TC-018, REQ-XGUI-NDT-ACCUM-1~3, C-09) — **GUI-E2E XDET-TC-145**
- **Given** 균일-노출 프레임 시퀀스 + 균일 ROI `(top,left,height,width)` + SRb_image 출처(자동판독 `read_duplex_srb` 결과 또는 사용자 주입 고정 `srb_um`) + Params(`ndt_srb_norm_um`=88.6, `ndt_target_snrn` 등)가 주어지면,
- **When** 사용자가 적산 스트리밍을 시작하여 각 shot 프레임에 대해 새 `SNRnAccumulator`(ndt.py:206) 인스턴스의 `update(frame)`를 구동하면,
- **Then** 탭이 반환된 `ShotLogEntry`(shot_index/frame_count/snrn/srb_um/snr, ndt.py:187-203)를 실시간 곡선(SNRn vs frame_count)과 shot 로그 테이블에 누적 표시하고, 누적 SNRn이 목표 `ndt_target_snrn`에 처음 도달하면 엔진의 `target_reached`/`target_frame_index`(ndt.py:309-311/319-327)를 곡선 마커·상태 배지로 표시해야 한다. running SNR/SNRn·목표도달을 UI가 스스로 계산하지 않고(정규화는 엔진이 T1 `compute_snrn` 단일 출처 재호출, ndt.py:283-299) 엔진 산출값만 표시해야 한다.
- **SAMPLE sanity 연결:** `nps_flat`(ingest:88) 균일 ROI로 `compute_snr` sanity(유한·비퇴화 SNR)는 실행가능. SNRn 곡선은 duplex-wire 부재로 정본 SRb가 없어 **SNR-only 또는 사용자 주입 `srb_um` 데모(비정본 배지)** 로만 그리며 정본 SRb는 #33 대기.

### Scenario 3 — duplex SRb + single-wire + Class A/B 리포트 (XDET-TC-018, REQ-XGUI-NDT-IQI-1~3, C-09) — **GUI-E2E XDET-TC-146**
- **Given** duplex-wire 1D 프로필 + `WirePair`(peak1/valley/peak2 인덱스 + srb_um, ndt.py:45) 리스트, single-wire 1D 프로필 + `WireElement`(number/index, ndt.py:482) 리스트, shot별 `IqiShot`(shot_index/snrn/srb_um/min_visible_wire, ndt.py:553-567)이 주어지면,
- **When** 사용자가 SRb 판독·IQI 판독·리포트를 요청하면,
- **Then** 탭이 (i) `read_duplex_srb`(ndt.py:70)를 호출해 `srb_um`·`dips`·`first_unresolved_pair`(ndt.py:119-123)를 dip 곡선(20% 임계선 + 첫 미해소 pair 마커)으로, (ii) `read_single_wire_iqi`(ndt.py:495)를 호출해 `min_visible_wire`·와이어별 `contrasts`·`visible`(ndt.py:543-547)을 판독 테이블로, (iii) `build_iqi_report`(ndt.py:583)를 호출해 shot별 `ShotVerdict`(class_a_pass/class_b_pass/verdict "A"|"B"|"FAIL", ndt.py:570-580)를 판정 테이블로 표시하되 EV-301 합격선을 UI가 재정의하지 않아야 한다(측정≠판정, ndt.py:592-595). 모든 dip/contrast/판독/판정은 엔진 산출(C-09).
- **데이터 라벨:** duplex/single-wire IQI 팬텀은 SAMPLE에 부재 → **합성/#33 대기**. 합성 프로필로 20% dip·Class A/B 로직을 구조 검증하고, 정본 수치 검증은 #33(duplex/single-wire IQI 지침세트) 도착 후 별건.

### Scenario 4 — 두께보정 뷰어 + passthrough 상태 (XDET-TC-019, REQ-XGUI-NDT-THICK-1~2, C-09) — **GUI-E2E XDET-TC-147**
- **Given** 단일 프레임 + Params(`ndt_thickness_method`=`morphological_opening`(기본)|`gaussian`, `ndt_thickness_scale_px`, `ndt_thickness_gradient_min_frac`)가 주어지면,
- **When** 사용자가 두께보정을 요청해 `correct_thickness`(ndt.py:383)를 구동하면,
- **Then** 탭이 `ThicknessResult`(flattened/low_freq/method/scale_px/changed/warnings, ndt.py:340-360)를 소비해 보정 전/후 프로필·감산된 저주파 프로필(low_freq)·`changed` 여부를 표시하고, 엔진이 수치-무변경 passthrough(`changed=False` + warning — 저주파 그래디언트 부재 또는 스케일 과대, ndt.py:430-464)를 반환하는 동안에는 "passthrough(무변경)" 상태와 warning 사유를 표시하며 보정된 영상으로 오인 표시하지 않아야 한다. `flattened`는 measurement-local 복사본(float64)으로 파이프라인 XFrame으로 재유입하지 않아야 한다(ndt.py:342-351).
- **SAMPLE sanity 연결:** `acrylic_step`(ingest:89)으로 `correct_thickness` sanity(changed/passthrough 구조 성립)는 실행가능. 아크릴 선량/두께는 **표시전용**이며 임계화·golden 도출·튜닝 금지(QUARANTINE/G-5).

### Scenario 5 — E2E 저장 라운드트립 + C-20 가드 (REQ-XGUI-NDT-EXPORT-1~2, foundation §3/G-4) — **load-bearing** — **GUI-E2E XDET-TC-148**
- **Given** Scenario 2~4의 산출물(shot 로그·IQI verdict·SRb/SNRn 값, 그리고 필요 시 두께보정 flattened 프레임)이 있고 사용자 지정 출력 폴더가 주어지면,
- **When** 사용자가 NDT 산출물을 내보내면,
- **Then** 탭이 (i) `<입력명>_report.json`을 `xdet.ndt-report/1.0`으로 쓰고, (ii) 필요 시 flattened frame을 `xdet.frame-artifact/1.0` raw/sidecar로 저장하며 확정 양자화 산출물의 bit-exact round-trip을 검증하고, (iii) `<입력명>_run_manifest.json`에 input/params/output hash를 기록하며, (iv) C# export choke point가 `data/` 하위를 typed error로 거부해야 한다.

### Scenario 6 — 골든 FROZEN·DSP 0·측정≠판정·QUARANTINE 가드 (REQ-XGUI-NDT-GUARD-1~4, C-09/C-11/G-1/G-5) — **GUI-E2E XDET-TC-149**
- **Given** 탭·어댑터가 NDT 산출물을 구동·표시하고,
- **When** 구동 후 코드 경로·의존 방향·쓰기 대상·데이터 라벨을 검사하면,
- **Then** (i) SNR/SNRn/dip/contrast/verdict·정규화 공식이 실제 골든에서 발생하고 UI/adapter 자체 계산이 없으며, (ii) WPF 호출이 dedicated `IXdetEngine` NDT DTO를 통과하고 오직 PythonNet adapter만 `metrics/ndt.py`에 의존하며 Python `apps.gui` helper 의존이 0건이고, (iii) EV-301 합격선을 UI가 내장하지 않으며, (iv) 데이터 capability 라벨이 정확하고, (v) 골든 파일이 무변경이어야 한다.

- **Then** UI는 engine DTO만 표시하고 측정값을 임의 판정으로 바꾸거나 SAMPLE을 승인 정본으로 승격하지 않아야 한다.

### Scenario 7 — 7개 NDT action 전수 도달성과 result DTO (XDET-TC-150, REQ-XNDT-COVERAGE-1~5)

- **Given** SNRn accumulation/current, duplex SRb, single-wire visibility, class report, thickness correction에 필요한 profile/ROI/shot 입력이 있을 때,
- **When** catalog의 7개 ACTION/SESSION command를 각각 실행하면,
- **Then** 각 command가 실제 qualified EntryPoint를 호출하고 scalar/profile/report 또는 accumulator state를 typed result로 반환하며 FeatureId·EntryPoint·input/Params hash가 manifest에 남아야 한다.

### Scenario 8 — 거부 shot 불변·사용자 증거·report 재현 (XDET-TC-151, REQ-XGUI-NDT-INPUT-5, REQ-XGUI-NDT-ACCUM-4, REQ-XGUI-NDT-EXPORT-1/2, REQ-XGUI-NDT-GUARD-2~4)

- **Given** 잘못된 ROI/단위/shot과 별도의 strict 사용자 제공 유효 입력이 있을 때,
- **When** 잘못된 shot을 먼저 제출하고 이어서 유효 shot·report 저장·재열기를 수행하면,
- **Then** 거부 shot은 accumulator current/shot_log/target을 변경하지 않고, 유효 사용자 실행은 `USER_SUPPLIED_UNVERIFIED`로 기록되며 report JSON/CSV와 run manifest hash가 재현돼야 한다.

### Scenario — NDT 7개 action과 accumulator 상태 전수 검증 (XDET-TC-144~151)

- **Given** 유효한 frame/ROI, duplex·single-wire profile landmarks, shot series, Params가 있고,
- **When** 7개 action과 accumulator session을 순서대로 실행하면,
- **Then** 실제 NDT EntryPoint가 호출되고 typed metric/thickness/report/state DTO가 golden-direct와 동일해야 한다. shot log·target transition은 accepted shot만 반영하고 rejected shot은 상태를 바꾸지 않아야 한다.

## Edge Cases

- **SRb 출처 미지정은 SNRn 산출 금지 (REQ-XGUI-NDT-INPUT-5)** — 자동판독 `read_duplex_srb` 결과도 사용자 주입 고정 `srb_um`도 부재하면 탭은 SNRn 산출을 요청하지 않고 SRb 미지정을 명시 표시해야 한다(엔진에 SRb 없이 진입 금지; `SNRnAccumulator`는 `srb_um<=0`을 `MetricReadError`로 거부, ndt.py:231-232 — 조용한 대체 없음).
- **거부 shot 프레임은 accumulator no-op (REQ-XGUI-NDT-ACCUM-4)** — 어떤 shot 프레임이 ROI 프레임 범위 초과(ndt.py:263-266)·유효 픽셀 부족(ndt.py:268-272)·퇴화(zero-noise) 누적 영역(ndt.py:296-299)에 해당하면 엔진이 `MetricReadError`를 던지고 그 프레임은 accumulator 상태에 반영되지 않아야 한다(peek-후-commit, ndt.py:273-301). 탭은 오류를 표면화하고 다음 프레임을 계속 처리하며 조용한 SNR을 산출하지 않아야 한다(음성 대조: 범위 초과 ROI 주입 시 실제 예외 + 상태 불변 확인).
- **해소 dip 부재·가시 와이어 부재는 판독 실패 (REQ-XGUI-NDT-IQI-4)** — duplex 프로필에 해소 가능한 20% dip이 하나도 없으면 `MetricReadError`(ndt.py:100-103), single-wire에 가시 와이어가 하나도 없으면 `MetricReadError`(ndt.py:536-539)로 판독 실패를 명시 표시하고 어떤 SRb 추정값·최소가시와이어 기본값도 대체 표시하면 안 된다(no-silent-default; 음성 대조: dip 없는 프로필 주입 시 실제 예외 확인).
- **미지 thickness_method는 거부 (REQ-XGUI-NDT-THICK-3)** — 사용자가 `morphological_opening`/`gaussian` 외 미지 `ndt_thickness_method` 값을 공급하면 엔진이 `MetricReadError`(ndt.py:425-428)로 거부하고 탭은 임의 기본값으로 조용히 대체하면 안 된다.
- **`data/` 하위 저장은 거부 (REQ-XGUI-NDT-EXPORT-2)** — 저장 경로가 `<project_root>/data` 하위로 해석되면 C# export choke point가 실행 전에 typed validation error로 거부해야 한다. 모든 export는 사용자 지정 폴더에만 허용한다.
- **UI 자체 계산·로컬 재구현은 FAIL (REQ-XGUI-NDT-GUARD-1)** — 탭·어댑터가 SNR/SNRn/dip/contrast/verdict를 스스로 계산하거나 `compute_snrn` 정규화 공식(`SNR×88.6/SRb`)을 로컬로 재구현하거나 골든 시그니처·수치·상수를 변경하려 하면 인수 실패 — DSP·정규화는 골든에, 골든은 읽기 전용(C-09/C-11/G-1).
- **SAMPLE 수치 오용은 FAIL (QUARANTINE, 이슈 #29)** — 등록 SAMPLE 구동 결과(`nps_flat` SNR, `acrylic_step` 선량/두께)를 정본 수치·EV 임계 도출·튜닝·적합에 사용하면 인수 실패 — sanity(유한·비퇴화·구조)만 허용, 정본 수치 검증은 정본 지침세트(#33: duplex/single-wire IQI·weld·연속 팬텀) 도착 후 별건.
- **lag식 시퀀스 러너 혼동은 FAIL** — NDT 스트리밍 적산은 metrics-내부 `SNRnAccumulator`(인스턴스 상태, 새 인스턴스=리셋 경계)로만 이뤄져야 하며 그룹 2 lag의 `pipeline/sequence.py::run_sequence`(오케스트레이터 경유 상태형 모듈 러너)를 사용하면 안 된다(ndt.py:216-219, 두 스트리밍 기전 축분리).

## Definition of Done (체크리스트)

- [ ] 상주 폴더 브라우저(폴더트리+가상화 썸네일+형제 필름스트립+이전/다음) 열기 + `load_raw_frame` 무손실 적재 + 단일 파일 지정 시 부모폴더 형제표시 (Scenario 1, INPUT-1~4)
- [ ] 균일-노출 시퀀스/단일 프레임 이원 입력 + ROI·와이어 기하 순수 샘플링 수집(필터·미분 없음), CalibSet 게이트 부재 (Scenario 1, INPUT-2~4)
- [ ] `SNRnAccumulator.update` 프레임별 구동 → 실시간 SNRn 곡선 + shot 로그 테이블(`ShotLogEntry`) + 목표도달 마커·배지(엔진 산출만) (XDET-TC-018, Scenario 2, ACCUM-1~3)
- [ ] `read_duplex_srb`(20% dip curve+first_unresolved_pair) + `read_single_wire_iqi`(min_visible_wire·contrasts 테이블) + `build_iqi_report`(`ShotVerdict` A/B/FAIL 판정 테이블) 표시, EV-301 UI 재정의 없음 (XDET-TC-018, Scenario 3, IQI-1~3)
- [ ] `correct_thickness` 보정 전/후·저주파 프로필·`changed` 표시 + passthrough(`changed=False`+warning) 상태 오인 표시 없음, flattened 파이프라인 재유입 없음 (XDET-TC-019, Scenario 4, THICK-1~2)
- [ ] E2E 저장: `xdet.ndt-report/1.0`, 선택 frame artifact, `xdet.run-manifest/1.0`, 양자화 바이트 round-trip 및 input/params/output hash 일치 (Scenario 5, EXPORT-1)
- [ ] C-20 가드: C# export choke point가 `<root>/data` 하위 쓰기를 typed error로 거부하고 export는 사용자 지정 폴더만 허용 (Scenario 5/Edge, EXPORT-2)
- [ ] 거부 계약: SRb 미지정 거부 / 거부 shot no-op / 해소 dip·가시 와이어 부재 `MetricReadError` / 미지 thickness_method `MetricReadError` 전부 표면화·무단 대체 없음(음성 대조 포함) (Edge Cases, INPUT-5/ACCUM-4/IQI-4/THICK-3)
- [ ] 골든 FROZEN·DSP 0·단방향·측정≠판정: 지표 전부 골든 산출, dedicated `IXdetEngine` DTO 경유, Python GUI helper 미의존, CalibKind/run_pipeline 미경유, EV-301 UI 미내장 (Scenario 6, GUARD-1~3)
- [ ] 데이터 라벨 정확: `nps_flat`=`compute_snr` sanity / `acrylic_step`=`correct_thickness` sanity·선량/두께 표시전용 / SRb·SNRn 정규화·IQI Class A/B=합성·#33 대기, SAMPLE 수치 golden·EV 도출·튜닝 없음 (Scenario 6, GUARD-4, QUARANTINE)
- [ ] `metrics/`·`common/`·`apps/gui/io_panel.py` 골든·가드 무변경(git diff 없음) + `uv run pytest` 무회귀 green + `uv run lint-imports` green·불변

## 판정 원칙 (측정≠판정 분리)

- **측정≠판정**: Class A/B verdict(`build_iqi_report`)와 목표 SNRn 도달 신호는 엔진이 생산하고 탭은 표시만 한다. EV-301 시험 합격/불합격선은 엔진 밖에 있으며(ndt.py:592-595) UI가 임계로 내장·재정의하지 않는다. "취득 종료 신호"는 목표 SNRn 도달 프레임 인덱스의 표시일 뿐 하드웨어 취득 트리거/정지 제어가 아니다(ndt.py:211/321).
- **QUARANTINE**: SAMPLE(에드로지) 실측 수치는 비정본 — 인수의 load-bearing 기준은 **엔진 산출값 표시 정합**·**명시 거부 계약**·**저장 라운드트립**·**무회귀**이지 SAMPLE 절대 수치가 아니다. `nps_flat` SNR·`acrylic_step` 선량/두께는 sanity·표시전용이며 정본 수치 검증은 #33 도착 후 별건.
- **골든 단일 출처**: SNRn 정규화는 엔진이 T1 `compute_snrn`(ndt.py:283-299)을 단일 출처로 재호출하며 로컬 공식이 금지된다. 허용오차·판정 임계는 CLAUDE.md·EV 기준에서 인용하고 UI에 하드코딩하지 않는다.

## 요구사항-TC 추적

| 요구사항 | 중앙 TC |
|---|---|
| `REQ-XGUI-NDT-TARGET-1` | 144~151 |
| `REQ-XGUI-NDT-INPUT-{1..5}` | 144, 151 |
| `REQ-XGUI-NDT-ACCUM-{1..4}` | 145, 150, 151 |
| `REQ-XGUI-NDT-IQI-{1..4}` | 146, 150 |
| `REQ-XGUI-NDT-THICK-{1..3}` | 147, 150 |
| `REQ-XGUI-NDT-EXPORT-{1..2}` | 148, 151 |
| `REQ-XGUI-NDT-GUARD-{1..4}` | 149, 151 |
| `REQ-XNDT-COVERAGE-{1..5}` | 150, 151 |

각 범위는 모든 개별 ID로 전개한다. 필수 증거 필드는 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따르며 누락·중복·orphan은 인수 실패다.

## v0.5.1 operation closure acceptance

- **Given** profile/frame/ROI/IQI 입력과 fresh accumulator session이 있고,
- **When** 사용자가 `metrics.ndt.read_duplex_srb`, `metrics.ndt.compute_snr`, `metrics.ndt.compute_snrn`, `metrics.ndt.correct_thickness`, `metrics.ndt.read_single_wire_iqi`, `metrics.ndt.build_iqi_report` action 및 `metrics.ndt.SNRnAccumulator.update` session을 실행하면,
- **Then** `metrics.ndt.SNRnAccumulator.shot_log`, `metrics.ndt.SNRnAccumulator.target_reached`, `metrics.ndt.SNRnAccumulator.target_frame_index`, `metrics.ndt.SNRnAccumulator.current`를 포함한 상태 DTO와 각 qualified call trace가 XDET-TC-144~151에 남고, rejected shot은 합계·target 상태를 바꾸지 않아야 한다.
