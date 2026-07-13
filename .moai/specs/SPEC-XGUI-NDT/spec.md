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
priority: medium
labels: [xgui, gui-redesign, verification-gui, ndt, snrn, iqi, thickness, metrics-report, golden-frozen]
---

# SPEC-XGUI-NDT — NDT(적산·IQI·SNRn) 알고리즘 그룹 GUI 검증 탭 (그룹 7)

> 본 사양은 `../SPEC-XGUI-MASTER/baseline-control.md`의 G0와 `traceability-matrix.md`를 상속한다. 사용자 승인·기준선 동결·`implementation_authorized=true` 전에는 구현 입력으로 실행하지 않으며, 승인 뒤 규범 변경은 버전 상승과 재승인을 요구한다.

XDET 검증 GUI 재설계(이슈 #58)의 **그룹 7 — NDT(WP10)** 검증 탭 SPEC이다. 동결(FROZEN) 골든 지표 엔진 `metrics/ndt.py`(SWR-1201 실시간 SNRn 적산 / SWR-1202 duplex-wire SRb 20% dip 자동판독 / SWR-1203 두께보정 / SWR-1204 single-wire IQI Class A/B 리포트)를 **호출만** 하여, 스트리밍 SNRn 적산·IQI 판독 리포트·두께보정을 검증 목적 탭으로 노출한다. 공유 사실 출처는 [SPEC-XGUI-MASTER/foundation.md](../SPEC-XGUI-MASTER/foundation.md)(이하 foundation)이며, frontmatter/구조는 [SPEC-XSEAM-002](../SPEC-XSEAM-002/spec.md)를 미러링한다. 본 SPEC은 foundation의 불변 HARD 제약(G-1~G-9)을 재기술하지 않고 상속·참조한다.

**AUTHORITATIVE 원칙:** 아래 모든 함수 시그니처·Params 키·데이터 가용성은 동결 골든 소스 `metrics/ndt.py`에서 Read로 직접 대조검증했다(§9 근거표). 미확인 항목은 명시적으로 "[미확인]"으로 표기한다. 지어내기(fabrication) 금지.

**문제(사용자 요구):** NDT 지표는 다른 그룹의 보정 스테이지와 근본적으로 다르다 — 이미지 before/after/diff가 아니라 **다중 shot 적산 스트리밍**(실시간 SNRn)과 **판정 리포트**(duplex SRb·single-wire IQI Class A/B·두께보정)가 결과의 중심이다. 사용자는 프레임 시퀀스를 적산하며 목표 SNRn 도달 시점을 실시간으로 보고, 와이어 판독을 판정 테이블로 확인해야 한다. foundation 그룹 7 표대로 NDT는 `process(XFrame, CalibSet, Params) -> XFrame` **모듈이 아니라 지표 엔진**이므로 이 탭은 "모듈 실행 탭"이 아니라 **"지표 리포트 탭"** 이다(metrics/ndt.py:218-219 "metrics-layer stateful measurement tool, NOT a pipeline processing module").

**엔진 경계(G-2/G-3, 그룹 7 특이점):** NDT는 CalibKind와 `run_pipeline`을 소비하지 않지만 WPF의 Python 경계는 예외 없이 `IXdetEngine`이다. WPF는 dedicated typed NDT methods/DTO를 호출하고, `Xdet.Engine.PythonNet` 어댑터만 `metrics/ndt.py` 공개 함수/클래스에 위임한다. 이 점이 모듈 실행 그룹(1~6)의 `RunPipeline`과 NDT 지표 탭을 가르는 축이며, WPF가 Python을 직접 호출한다는 뜻은 아니다. DSP·정규화·판정 계산은 전부 골든에 남고 UI는 렌더링과 입력 수집만 한다(C-09/C-11).

- 근거(변경 없음, adapter 소비만): `metrics/ndt.py::read_duplex_srb`(:70) · `compute_snr`(:129) · `compute_snrn`(:144) · `SNRnAccumulator`(:206, `update`:252) · `correct_thickness`(:383) · `read_single_wire_iqi`(:495) · `build_iqi_report`(:583) · `metrics/result.py` · `common/io.py::load_raw_frame`(:35) · `common/xframe.py`. **`pipeline/orchestrator.py`·`CalibSet`·`run_pipeline`은 소비하지 않지만 `IXdetEngine` dedicated NDT seam은 반드시 소비한다.**
- 상속 원칙: **읽기-실행 전용**(C-20/G-4), **지표·DSP 자체 계산 0**(C-09/G-2: UI/어댑터는 스스로 계산하지 않고 실제 엔진 결과만 표시), **단방향 소비**(C-11/G-3), **측정 ≠ 판정**(Class A/B 리포트는 생산만, EV-301 합격선은 엔진 밖, metrics/ndt.py:592-595).
- 완료 정의(DoD): (1) 균일-노출 프레임 시퀀스 + ROI + SRb 출처로 `SNRnAccumulator`를 프레임별 `update` 구동, 실시간 SNRn 곡선·shot 로그·목표도달 신호 표시(§인수 acceptance.md) → (2) duplex 프로필 + `WirePair`로 `read_duplex_srb`(20% dip)·single-wire 프로필 + `WireElement`로 `read_single_wire_iqi`·`build_iqi_report`(Class A/B verdict) 판독 테이블 표시 → (3) 단일 프레임 + Params로 `correct_thickness` 구동, 보정 전/후 프로필·passthrough 상태 표시 → (4) 리포트를 `<name>_report.json`으로, (필요 시) 두께보정 flattened 프레임을 `<name>_result.raw`(16-bit headerless) + `.json` 사이드카로 사용자 지정 폴더에만 저장(C-20 게이트) → (5) SAMPLE(nps_flat→SNR sanity, acrylic_step→두께 sanity·선량 표시전용)·합성/#33 대기 데이터 가용성 라벨이 정확히 표기. 골든 무변경.
- 구현 계획: [plan.md](./plan.md) (후속 작성) · 인수 기준: [acceptance.md](./acceptance.md) (작성됨 — E2E 열기→build/apply→저장 `_result.raw`→검증 6 시나리오 + SAMPLE sanity 엣지케이스)

## HISTORY

- **v0.2.0 (2026-07-13)** — 중단 작업 복구 마무리. 구현 대상을 C# WPF `apps/xdet-console/`로 확정하고 Python `apps/gui/`는 참조 선례로 한정했다. 그룹별 결정·중앙 TC 레지스트리·plan/research를 확정했다. 골든 알고리즘은 변경하지 않는다.

- **v0.1.1 (2026-07-12)** — 라운드 1/5 교차검증(plan-auditor, PASS·우선순위 결함 0) 후속 경미 결함 교정 + `acceptance.md` 신규 작성. 각 항목 골든 `metrics/ndt.py` Read 재대조: (M-1) THICK-2를 순수 State-Driven으로 교정(`WHILE ... THEN` 혼용 제거, passthrough=`changed=False`+warning ndt.py:430-464 재확인). (M-2) `IqiShot` 필드 열거에 `shot_index` 추가(실제 4필드 shot_index/snrn/srb_um/min_visible_wire = ndt.py:553-567 확인) + §9 근거표에 `ShotVerdict` 7필드 행(ndt.py:570-580) 추가. (M-3) 저장 산출물 명명 표류 확정 해소 — 리포트 `<name>_report.json` + 두께보정 프레임 `<name>_result.raw`+`.json`(태스크 HARD 저장 규약 일치, `_ndt_`/`_thickness_` 중간자 제거). (M-4) `acceptance.md` 작성으로 참조 정합(3-file 중 plan.md만 잔여). 골든 무변경·요구 22개·EARS·frontmatter 미러 불변.
- **v0.1.0 (2026-07-12)** — 초안 생성. GitHub 이슈 #58(GUI 재설계) 그룹 7(NDT). foundation(SPEC-XGUI-MASTER) 상속, 구조는 SPEC-XSEAM-002 미러링. 6개 요구 그룹(INPUT/ACCUM/IQI/THICK/EXPORT/GUARD) EARS 22개. **본 탭이 구동하는 골든 시험케이스 = XDET-TC-018**(SNRn 적산·IQI 판정 엔진)**·XDET-TC-019**(두께보정/CSa) — 그룹 SPEC은 새 TC 블록을 신설하지 않고 골든 알고리즘의 기존 TC를 참조한다(GRID→015/016 선례). 저작 시 **AUTHORITATIVE 소스 대조 사실**: (a) `metrics/ndt.py` 공개 진입점 7종 확인(§9) — `read_duplex_srb`(:70, 1D 프로필+`WirePair`→SRb) / `compute_snr`(:129→(snr,mean,std)) / `compute_snrn`(:144→MetricResult, `SNRn=SNR×88.6/SRb`) / `SNRnAccumulator`(:206 상태형, `update(frame)->ShotLogEntry`) / `correct_thickness`(:383→ThicknessResult) / `read_single_wire_iqi`(:495→min_visible_wire) / `build_iqi_report`(:583→Class A/B ShotVerdict). (b) **12개 Params 키를 ndt.py:29-42에서 직접 확인**(§3), 하드코딩 리터럴 없음. (c) `SNRnAccumulator`는 `common/robust_stats.WelfordAccumulator`(robust_stats.py:62)를 재사용하고 정규화는 T1 `compute_snrn`을 단일 출처로 호출(ndt.py:283-299) — 로컬 공식 금지. **metrics-내부 상태**로 pipeline `StatefulModule`(lag) 계약과 무관, 오케스트레이터/`pipeline/sequence.py` 미접촉(ndt.py:216-219). (d) 데이터 가용성: `nps`(nps_flat, ingest_edrogi.py:88)→균일 ROI `compute_snr` **sanity 실행가능**; `아크릴`(acrylic_step, ingest_edrogi.py:89)→`correct_thickness` sanity + 선량/두께 **표시전용**(임계화 금지); SRb(duplex)·single-wire IQI 팬텀은 **합성/#33 대기**. (e) NDT는 CalibKind 미소비 → 파이프라인 순서(SWR-000-2)·캘리 게이트(SWR-000-5)가 구조적 N/A이나 골든 FROZEN(G-1)·DSP-0(G-2)·단방향(G-3)·내보내기 가드(G-4)·QUARANTINE(G-5)는 전면 적용. 확정 설계 결정: DSP·정규화는 골든 `metrics/ndt.py`에 남기고 탭은 입력 수집·표시만; 판정 임계(EV-301)는 엔진 밖(측정≠판정).

## Environment / Assumptions

- **본 SPEC은 T-스테이지가 아니다.** `CANONICAL_ORDER` 스테이지 추가·`process(...)` 시그니처 변경·신규 `CalibKind`가 전혀 없다. Python 코어 4계층과 오케스트레이터 표면은 불변이며, 본 SPEC은 그 위에 **그룹 7 검증 탭 소비자**를 additive로 얹는다(SPEC-VIEWER-001·SPEC-NDT-001 지표 도구 계열의 그룹별 재편).
- **NDT = 지표 엔진(모듈 아님, foundation 그룹 7).** `metrics/ndt.py`는 `CalibSet` 게이트와 `run_pipeline`을 소비하지 않는다. 입력은 **프레임(들) + ROI + 와이어 기하 + Params**이고, WPF는 이를 dedicated `IXdetEngine` NDT DTO로 전달한다.
- **입력세트(프레임 선택).** foundation §4 상주 폴더 브라우저로 `common.io.load_raw_frame`(io.py:35, headerless 16-bit + `.json` 사이드카)를 통해 프레임을 적재한다. NDT 탭은 두 종류의 프레임 입력을 다룬다: (1) **균일-노출 프레임 시퀀스(shot sequence)** — SNR/SNRn 적산용, 폴더의 형제 프레임들을 취득 순서로 순차 소비; (2) **단일 프레임** — 두께보정·1D 프로필(duplex/single-wire) 추출 대상. 기본 소스는 등록 실측 세트(에드로지 SAMPLE / 향후 #33), 합성 목업 사용자탭 금지(foundation §4).
- **ROI·와이어 기하는 사용자/메타 입력(CalibSet 아님).** 균일 ROI `(top,left,height,width)`는 사용자가 그린 사각형; duplex `WirePair`(ndt.py:45, peak1/valley/peak2 인덱스 + srb_um)와 single-wire `WireElement`(ndt.py:482, number+index) 기하는 IQI 팬텀 도면/메타에서 공급되는 프로필-인덱스 좌표다. **UI의 1D 프로필 추출은 순수 픽셀 샘플링**(선 위 픽셀값 읽기, 필터·미분·평활 없음)이며 dip/contrast/판정 계산은 전부 엔진 내부다(C-09; 엔진 내부 `grey_opening`/`gaussian_filter`(ndt.py:22/445/447)만 DSP).
- **SNRn 정규화 상수는 Params.** `SNRn = SNR × 88.6[µm] / SRb_image`(ndt.py:152-163). 88.6은 표준 정규화 상수 [S]로 `ndt_srb_norm_um`(P_SRB_NORM_UM)로 주입되며 하드코딩되지 않는다. SRb_image 출처는 (i) `read_duplex_srb`가 20% dip으로 자동판독한 값, 또는 (ii) 사용자 주입 고정 srb_um(데모/비정본) 중 사용자가 선택한다.
- **스트리밍 적산 상태(SNRnAccumulator).** `SNRnAccumulator`(ndt.py:206)는 `common.robust_stats.WelfordAccumulator`(온라인 count/mean/M2, robust_stats.py:62)를 재사용해 프레임별 running SNR/SNRn을 갱신하고, 목표 SNRn 도달 시 취득-종료 신호(`target_reached`/`target_frame_index`, ndt.py:320-327)와 ISO 17636-2 shot 로그(`ShotLogEntry`, ndt.py:187)를 산출한다. **metrics-내부 상태**로서 pipeline `StatefulModule`(lag) 계약·`pipeline/sequence.py::run_sequence`와 무관하다(ndt.py:216-219). 탭은 스트리밍 세션마다 **새 accumulator 인스턴스**를 생성하며 인스턴스 갱신이 리셋 경계다(별도 리셋 프로토콜 없음).
- **거부 계약(no-silent-default).** 엔진은 다음을 명시 오류로 거부한다: ROI 프레임 범위 초과·유효 픽셀 부족·퇴화(zero-noise) 누적 영역 → `MetricReadError`(ndt.py:256-299; 거부된 프레임은 accumulator에 **no-op** — peek 후 commit, ndt.py:273-301); 해소 dip 없음 → `MetricReadError`(ndt.py:100-103, SRb 추정 대체 금지); 가시 와이어 없음 → `MetricReadError`(ndt.py:536-539, 최소가시와이어 대체 금지); 미지 `thickness_method` → `MetricReadError`(ndt.py:425-428). UI는 이를 조용히 삼키지 않고 표면화한다.
- **저장 도메인 주의.** `correct_thickness`의 `flattened`는 **measurement-local 복사본**(float64)으로 파이프라인 XFrame으로 재유입하지 않는다(ndt.py:342-351). 16-bit `.raw` 저장 시 raw-DN 도메인 라운드트립(float→clip[0,65535]→`np.rint(...).astype("<u2")`)을 적용하며, 그룹 5(mse/window 정규화 [0,1])의 역스케일 문제와 무관하다(NDT 프레임은 입력 DN 도메인 유지). 리포트(shot 로그·verdict)는 `.json`으로 저장.
- **QUARANTINE(SAMPLE 비정본).** 등록 실측(에드로지 SAMPLE, `panel_id=SAMPLE-EDROGI-16BIT`, provenance `sample=true`)으로 본 탭에서 **실행가능한 것은 `nps_flat` 균일 ROI의 `compute_snr` sanity**(유한·비퇴화)와 `acrylic_step`의 `correct_thickness` sanity(changed/passthrough 구조)뿐이다. SRb·SNRn 정규화·IQI Class A/B는 duplex/single-wire 팬텀 부재로 **합성/#33 대기**(SRb 주입 시 데모 표시만, 비정본 배지). 아크릴 선량/두께는 **표시전용**이며 임계화·golden 도출·튜닝 금지(foundation G-5, §2 그룹 7·아크릴 매핑).
- **환경.** Python은 `uv run`으로만 실행(`uv run pytest`, `uv run lint-imports`). 정확성·재현성이 목적이며 성능·마샬링 최적화는 목적이 아니다.

## 3. 정확한 Params 키 목록 (골든 검증)

`metrics/ndt.py` 소비처를 Read로 대조한 전체 목록(ndt.py:29-42). 전부 `Params`로 외부화되어 하드코딩 리터럴이 없다(파라미터 정책 HARD). 키 이름만 계약이며 값·등급은 Params 외부화. 탭은 이 키들만 노출·수집하고 값의 의미·기본을 스스로 정하지 않는다(C-09).

| Params 키 | 상수 | 소비처 (file:line) | 등급 |
|---|---|---|---|
| `ndt_dip_threshold` | P_DIP_THRESHOLD | `read_duplex_srb` (ndt.py:93) | **[S]** — ISO 20% dip. NOTE: ndt.py:29 주석은 `[P]`로 표기하나 SPEC-NDT-001이 부록 A-2 기준 `[S]`로 교정(값 ISO 고정) |
| `ndt_srb_norm_um` | P_SRB_NORM_UM | `compute_snrn` (ndt.py:162), `SNRnAccumulator` (ndt.py:240) | **[S]** — 88.6µm 표준 정규화 상수 |
| `ndt_target_snrn` | P_TARGET_SNRN | `SNRnAccumulator` (ndt.py:245) | [S]/[P] — 취득 종료 목표 SNRn |
| `ndt_min_roi_pixels` | P_MIN_ROI_PIXELS | `SNRnAccumulator` (ndt.py:241) | [P] — 최소 유효 균일 픽셀 |
| `ndt_thickness_method` | P_THICKNESS_METHOD | `correct_thickness` (ndt.py:405) | [C] — `morphological_opening`(기본)\|`gaussian` |
| `ndt_thickness_scale_px` | P_THICKNESS_SCALE | `correct_thickness` (ndt.py:406) | [T] — 저주파 프로필 스케일 |
| `ndt_thickness_gradient_min_frac` | P_THICKNESS_GRAD_MIN | `correct_thickness` (ndt.py:407) | [T] — 그래디언트 존재 하한(passthrough 게이트) |
| `ndt_wire_visibility_threshold` | P_WIRE_VISIBILITY | `read_single_wire_iqi` (ndt.py:514) | [T]/[P] — single-wire 가시성 임계 |
| `ndt_class_a_snrn_min` | P_CLASS_A_SNRN | `build_iqi_report` (ndt.py:601) | [S]/[P] — Class A SNRn 최소 |
| `ndt_class_a_required_wire` | P_CLASS_A_WIRE | `build_iqi_report` (ndt.py:602) | [S]/[P] — Class A 요구 와이어 번호 |
| `ndt_class_b_snrn_min` | P_CLASS_B_SNRN | `build_iqi_report` (ndt.py:603) | [S]/[P] — Class B SNRn 최소 |
| `ndt_class_b_required_wire` | P_CLASS_B_WIRE | `build_iqi_report` (ndt.py:604) | [S]/[P] — Class B 요구 와이어 번호 |
| `beam_quality` (선택) | — | `compute_snrn` MetricCondition (ndt.py:177) | 서술자(descriptor) — 필수 아님, 조건 메타 |

## Requirements (EARS)

### REQ-XGUI-NDT-TARGET — 구현 대상 경계

- **REQ-XGUI-NDT-TARGET-1 (Ubiquitous)** — 시스템은 `apps/xdet-console/` C# WPF 앱을 구현 대상으로 사용해야 하며, `apps/gui/`와 Python 테스트·패널은 계약 및 검증 선례로만 참조해야 한다. WPF는 Python 모듈을 직접 호출하지 않고 `IXdetEngine`/PythonNet seam을 경유해야 한다.

### REQ-XGUI-NDT-INPUT — 입력세트: 프레임 시퀀스 · ROI · 와이어 기하 선택 (foundation §4, C-11, 지표 엔진 = CalibSet 미소비)

- **REQ-XGUI-NDT-INPUT-1 (Ubiquitous)** — 그룹 7 탭은 입력 프레임을 **상주 폴더 브라우저**(폴더 트리 + 가상화 썸네일 그리드 + 형제 필름스트립 + 이전/다음)로 선택할 수 있어야 하며, 사용자가 단일 파일을 지정해도 그 부모 폴더의 형제 목록을 함께 표시하고, `common.io.load_raw_frame`(headerless 16-bit + `{resolution,dtype}` 사이드카)로 XFrame을 무손실 적재해야 한다(NDT는 CalibKind 미소비 — 캘리 게이트 없음).
- **REQ-XGUI-NDT-INPUT-2 (Event-Driven)** — WHEN 사용자가 균일-노출 **프레임 시퀀스(shot sequence)**를 지정하면, THEN 탭은 폴더의 형제 프레임들을 취득 순서대로 스트리밍 적산의 입력으로 배열하고 현재 shot 인덱스를 표시해야 한다(적산 대상 = `SNRnAccumulator.update` 프레임열).
- **REQ-XGUI-NDT-INPUT-3 (Event-Driven)** — WHEN 사용자가 균일 영역 ROI `(top,left,height,width)`를 지정하면, THEN 탭은 그 ROI를 `compute_snr`/`compute_snrn`/`SNRnAccumulator`의 ROI 인자로 전달해야 하며, 프레임 범위·최소 픽셀 검증은 엔진에 맡기고 UI는 좌표만 수집해야 한다(C-09).
- **REQ-XGUI-NDT-INPUT-4 (Event-Driven)** — WHEN 사용자가 duplex/single-wire 프로필 선(line)과 와이어 기하(`WirePair` peak/valley 인덱스+srb_um / `WireElement` number+index)를 공급하면, THEN 탭은 선 위 픽셀값을 **순수 샘플링**하여 1D 프로필(필터·평활·미분 없음)을 만들고 그 프로필과 기하를 `read_duplex_srb`/`read_single_wire_iqi`에 전달해야 한다(모든 dip/contrast/판독은 엔진 — C-09).
- **REQ-XGUI-NDT-INPUT-5 (Unwanted)** — IF 사용자가 SNRn 정규화의 SRb_image 출처를 선택하지 않으면(자동판독 `read_duplex_srb` 결과도, 사용자 주입 고정 srb_um도 부재), THEN 탭은 SNRn 산출을 요청하지 않고 SRb 미지정을 명시적으로 표시해야 한다(엔진에 SRb 없이 진입 금지; no-silent-default).

### REQ-XGUI-NDT-ACCUM — 실시간 SNRn 적산 뷰어 (SWR-1201, ndt.py:206-332, XDET-TC-018, C-09)

- **REQ-XGUI-NDT-ACCUM-1 (Ubiquitous)** — 탭은 스트리밍 SNRn 적산을 `metrics/ndt.py::SNRnAccumulator`(ndt.py:206)로만 수행해야 하며, running SNR/SNRn·프레임 카운트·목표도달 신호를 스스로 계산하지 않고 엔진 산출값만 표시해야 한다(C-09; 정규화는 엔진이 T1 `compute_snrn`을 단일 출처로 호출 — ndt.py:283-299, 로컬 공식 금지).
- **REQ-XGUI-NDT-ACCUM-2 (Event-Driven)** — WHEN 사용자가 적산 스트리밍을 시작하면, THEN 탭은 선택된 ROI·SRb_image·Params로 **새 `SNRnAccumulator` 인스턴스**를 생성하고(인스턴스 생성이 리셋 경계), 각 shot 프레임에 대해 `update(frame)`를 호출해 반환된 `ShotLogEntry`(shot_index/frame_count/snrn/srb_um/snr, ndt.py:187)를 실시간 곡선(SNRn vs frame_count)과 shot 로그 테이블에 누적 표시해야 한다.
- **REQ-XGUI-NDT-ACCUM-3 (Event-Driven)** — WHEN 누적 SNRn이 목표 `ndt_target_snrn`에 처음 도달하면(엔진이 `target_reached=True`·`target_frame_index` 설정, ndt.py:309-311), THEN 탭은 취득-종료 신호와 도달 프레임 인덱스를 곡선상 마커·상태 배지로 표시해야 한다(취득 종료 = 반환된 결정값 표시일 뿐 하드웨어 취득 제어 아님, ndt.py:211/321).
- **REQ-XGUI-NDT-ACCUM-4 (Unwanted)** — IF 어떤 shot 프레임이 ROI 프레임 범위 초과·유효 픽셀 부족·퇴화(zero-noise) 누적 영역에 해당하면(엔진 `MetricReadError`, ndt.py:263-299), THEN 탭은 그 오류를 명시적으로 표면화하고 해당 프레임을 accumulator 상태에 반영하지 않은 채(거부=no-op, ndt.py:273-301) 다음 프레임을 계속 처리해야 하며, 조용한 SNR 산출을 하지 않아야 한다.

### REQ-XGUI-NDT-IQI — duplex SRb + single-wire + Class A/B 리포트 뷰어 (SWR-1202/1204, ndt.py:70-126/495-637, XDET-TC-018, C-09)

- **REQ-XGUI-NDT-IQI-1 (Event-Driven)** — WHEN 사용자가 duplex-wire 프로필과 `WirePair` 리스트로 SRb 판독을 요청하면, THEN 탭은 `read_duplex_srb`(ndt.py:70)를 호출해 20% dip 기준의 `srb_um`·pair별 `dips`·`first_unresolved_pair`(ndt.py:119-123)를 dip 곡선(20% 임계선 + 첫 미해소 pair 마커)과 함께 표시해야 한다.
- **REQ-XGUI-NDT-IQI-2 (Event-Driven)** — WHEN 사용자가 single-wire 프로필과 `WireElement` 리스트로 IQI 판독을 요청하면, THEN 탭은 `read_single_wire_iqi`(ndt.py:495)를 호출해 `min_visible_wire`·와이어별 contrast·가시 여부(ndt.py:541-548)를 판독 테이블로 표시해야 한다.
- **REQ-XGUI-NDT-IQI-3 (Event-Driven)** — WHEN 사용자가 shot별 입력(`IqiShot`: shot_index/snrn/srb_um/min_visible_wire, ndt.py:553-567)을 모아 리포트를 요청하면, THEN 탭은 `build_iqi_report`(ndt.py:583)를 호출해 shot별 `ShotVerdict`(shot_index/snrn/srb_um/min_visible_wire/class_a_pass/class_b_pass/verdict "A"|"B"|"FAIL", ndt.py:570-580)를 판정 테이블로 표시하되, EV-301 합격선을 UI가 재정의하지 않아야 한다(측정≠판정, ndt.py:592-595).
- **REQ-XGUI-NDT-IQI-4 (Unwanted)** — IF duplex 프로필에서 해소 가능한 dip이 하나도 없거나(→ `MetricReadError`, ndt.py:100-103) single-wire에서 가시 와이어가 하나도 없으면(→ `MetricReadError`, ndt.py:536-539), THEN 탭은 그 판독 실패를 명시적으로 표시하고 어떤 SRb 추정값·최소가시와이어 기본값도 대체 표시하지 않아야 한다(no-silent-default).

### REQ-XGUI-NDT-THICK — 두께보정 뷰어 (SWR-1203, ndt.py:383-474, XDET-TC-019, C-09)

- **REQ-XGUI-NDT-THICK-1 (Event-Driven)** — WHEN 사용자가 단일 프레임과 Params로 두께보정을 요청하면, THEN 탭은 `correct_thickness`(ndt.py:383)를 호출해 `ThicknessResult`(flattened/low_freq/method/scale_px/changed/warnings, ndt.py:340)를 소비하고, 보정 전/후 프로필과 감산된 저주파 프로필(low_freq), `changed` 여부를 표시해야 한다(flattened는 measurement-local 복사본 — 파이프라인 XFrame으로 재유입하지 않는다, ndt.py:342-351).
- **REQ-XGUI-NDT-THICK-2 (State-Driven)** — WHILE 엔진이 수치-무변경 passthrough를 반환하는 동안(저주파 그래디언트 부재 또는 스케일 과대 → `changed=False` + warning, ndt.py:430-464), 탭은 "passthrough(무변경)" 상태와 그 warning 사유를 표시하고 보정된 영상으로 오인 표시하지 않아야 한다(무단 고주파 왜곡 금지, SPEC-NDT-001 REQ-NDT-THICK-3/EC-2).
- **REQ-XGUI-NDT-THICK-3 (Unwanted)** — IF 사용자가 미지 `ndt_thickness_method` 값을 공급하면(엔진 `MetricReadError`, ndt.py:425-428), THEN 탭은 그 오류를 표면화하고 `morphological_opening`/`gaussian` 외 임의 기본값으로 조용히 대체하지 않아야 한다.

### REQ-XGUI-NDT-EXPORT — 결과 저장: 리포트 `.json` + (선택) flattened `.raw`, C-20 게이트 (foundation §3, G-4)

- **REQ-XGUI-NDT-EXPORT-1 (Event-Driven)** — WHEN 사용자가 NDT 산출물을 내보내면, THEN 탭은 `<name>_report.json`을 `schema_version: xdet.ndt-report/1.0`으로 저장하고 shot logs, IQI verdict, SRb/SNRn, input conditions, warnings를 포함해야 한다. 필요 시 flattened frame은 `xdet.frame-artifact/1.0` raw/sidecar로 저장한다. 모든 산출물은 `<name>_run_manifest.json`(`xdet.run-manifest/1.0`)의 input/params/output hash와 연결한다.
- **REQ-XGUI-NDT-EXPORT-2 (Unwanted)** — IF 저장 대상 경로가 `<project_root>/data` 하위로 해석되면, THEN C# export choke point가 실행 전에 typed validation error로 거부해야 한다. WPF/adapter는 Python `guard_output_path`를 직접 호출하지 않는다(C-20/G-4).

### REQ-XGUI-NDT-GUARD — 골든 FROZEN·DSP 0·측정≠판정·QUARANTINE 가드 (C-09/C-11/G-1/G-5)

- **REQ-XGUI-NDT-GUARD-1 (Unwanted)** — IF 탭 또는 어댑터가 SNR/SNRn/dip/contrast/verdict 중 어느 값을 스스로 계산하거나, `compute_snrn` 정규화 공식(`SNR×88.6/SRb`)을 로컬로 재구현하거나, 골든 시그니처·수치·상수를 변경하려 하면, THEN 이는 거부되어야 한다(DSP·정규화는 골든 `metrics/ndt.py`에, 골든 읽기 전용 — C-09/C-11/G-1).
- **REQ-XGUI-NDT-GUARD-2 (Ubiquitous)** — 탭은 `CalibKind`/`run_pipeline`을 사용하지 않되 dedicated `IXdetEngine` NDT methods를 반드시 거쳐야 하며, 오직 PythonNet adapter만 `metrics/ndt.py`에 의존해야 한다. `metrics/ndt.py`는 UI에 의존하지 않는다(C-11).
- **REQ-XGUI-NDT-GUARD-3 (Ubiquitous)** — 탭은 Class A/B verdict(ndt.py:583-637)를 표시하되 EV-301 시험 합격선을 UI가 재정의하지 않아야 한다(측정≠판정 — 리포트는 생산만, 합격선은 엔진 밖, ndt.py:592-595, SPEC-NDT-001 REQ-NDT-CONTRACT-4).
- **REQ-XGUI-NDT-GUARD-4 (Ubiquitous)** — 탭은 데이터 가용성을 정확히 라벨해야 한다 — `nps_flat` SAMPLE은 `compute_snr` **sanity(유한·비퇴화)** 실행가능, `acrylic_step` SAMPLE은 `correct_thickness` sanity + 선량/두께 **표시전용**(임계화 금지), SRb·SNRn 정규화·IQI Class A/B는 **합성/#33 대기**. 어떤 SAMPLE 수치도 golden 도출·EV 임계 튜닝·적합에 쓰여서는 안 된다(QUARANTINE/G-5, 이슈 #29). 정본 수치 검증은 정본 지침세트(이슈 #33: duplex/single-wire IQI·weld·연속 팬텀) 도착 후 별건이다.

### REQ-XNDT-COVERAGE — NDT 공개 연산 전수 도달성

- **REQ-XNDT-COVERAGE-1 (Ubiquitous)** — NDT 탭은 `read_duplex_srb`, `compute_snr`, `compute_snrn`, `SNRnAccumulator.update`, `correct_thickness`, `read_single_wire_iqi`, `build_iqi_report`를 각각 고유 FeatureId와 typed request/result로 노출해야 한다.
- **REQ-XNDT-COVERAGE-2 (State-Driven)** — WHILE accumulator session이 활성일 때 engine은 실제 `shot_log`, `target_reached`, `target_frame_index`, `current` 상태를 반환하고 accepted shot 순서와 hash를 보존해야 한다.
- **REQ-XNDT-COVERAGE-3 (Unwanted)** — IF shot이 입력/ROI/SRb/Params 검증에서 거부되면 THEN accumulator count/mean/variance/shot log가 변경되지 않아야 한다.
- **REQ-XNDT-COVERAGE-4 (Event-Driven)** — WHEN strict 사용자 frame/profile/landmark/shot input이 제공되면 THEN 등록 데이터 부재로 실행을 막지 않고 승인 전 `USER_SUPPLIED_UNVERIFIED`로 기록해야 한다.
- **REQ-XNDT-COVERAGE-5 (Ubiquitous)** — WirePair, WireElement, IqiShot, ShotVerdict, ThicknessResult, shot log는 임의 dictionary가 아닌 언어 중립 typed DTO여야 한다.

## Exclusions (What NOT to Build)

- **골든 모델 변경 없음** — `metrics/ndt.py`·`metrics/result.py`·`common/robust_stats.py`·`common/xframe.py`는 동결 오라클로 편집하지 않는다. 탭은 이들을 읽기-실행 전용으로 소비한다(호출만). SNR/SNRn 정규화, duplex SRb dip, single-wire contrast, Class A/B 판정, Welford 적산 로직을 UI에서 재구현하지 않는다.
- **모듈 실행·조합 UI 아님** — NDT는 pipeline stage가 아니므로 CalibSet 선택·스테이지 조합·`run_pipeline`·`intermediates`는 없다. 대신 dedicated `IXdetEngine` NDT methods와 session DTO를 사용하며 WPF의 직접 Python 호출은 없다.
- **하드웨어 취득 제어 없음** — "취득 종료 신호"는 목표 SNRn 도달 프레임 인덱스의 **표시**일 뿐, 실제 검출기 취득 트리거/정지 제어를 구현하지 않는다(ndt.py:211/321 계약).
- **판정 임계 내장 없음(측정≠판정)** — Class A/B verdict는 엔진이 생산하고 탭은 표시만 한다. EV-301 합격/불합격선을 UI가 임계로 내장·재정의하지 않는다(ndt.py:592-595).
- **CSa/SMTR·ADR 없음** — CSa/SMTR 전체 특성화(EV-303)·관찰자 연구(EV-204)·ADR(EV-302, DL/Gen2)는 본 탭 범위 밖이다(SPEC-NDT-001 승계; Gen 2 미구현).
- **lag식 시퀀스 러너 없음** — NDT 스트리밍 적산은 metrics-내부 `SNRnAccumulator`(인스턴스 상태)로 이뤄지며, 그룹 2 lag의 `pipeline/sequence.py::run_sequence`(상태형 모듈 시퀀스 러너, 오케스트레이터 경유)를 사용하지 않는다. 두 스트리밍 기전을 혼동하지 않는다.
- **정본 수치 검증 없음(QUARANTINE)** — SAMPLE 실측 구동은 sanity 확인이며, SRb·SNRn 정규화·IQI Class A/B의 정본 수치 검증은 정본 지침세트(이슈 #33) 도착 후 별건이다. 아크릴 선량/두께 값을 임계·상수로 승격하지 않는다.
- **성능·마샬링 최적화 없음** — 3072² 프레임 시퀀스 스트리밍의 스루풋/메모리 최적화는 범위 밖(정확성·재현성이 목적, P1 골든은 의도적으로 느림).

## 확정 결정 (v0.5.1)

1. 누락된 plan/research 문서를 이번 마무리 패스에서 작성한다. 구현 대상은 `apps/xdet-console/`이다.
2. 등록 SAMPLE은 SNR-only sanity로 제한한다. SRb가 없는 SAMPLE에서 SNRn 곡선이나 demo SRb를 생성하지 않는다.
3. 1D profile은 정수 좌표/nearest sampling만 허용한다. subpixel interpolation은 engine-owned 공개 계약이 생길 때까지 제외한다.
4. 리포트는 `<name>_report.json`을 필수로 하고 CSV는 선택 산출물로 허용한다. flattened frame이 있을 때만 raw/JSON을 저장한다.
5. XDET-TC-018/019는 core 알고리즘 증거로 유지하고 GUI-E2E는 중앙 G7 블록의 XDET-TC-144~151 전체를 사용한다.

## 9. 골든 대조 근거표 (AUTHORITATIVE)

모든 사실을 동결 골든 소스 `file:line`으로 Read 대조검증했다. 지어내기 금지 원칙의 추적 근거다.

| 사실 | 근거 (file:line) |
|---|---|
| duplex SRb 자동판독(1D 프로필+WirePair, 20% dip) | metrics/ndt.py:70 (`read_duplex_srb`) |
| dip = 1 − valley/mean(peaks) | metrics/ndt.py:61 (`_dip`) |
| WirePair(peak1/valley/peak2/srb_um) | metrics/ndt.py:45 |
| 해소 dip 부재 → MetricReadError(추정 대체 금지) | metrics/ndt.py:99-103 |
| robust SNR (snr,mean,std), zero-noise → MetricReadError | metrics/ndt.py:129-141 |
| SNRn = SNR × 88.6[µm] / SRb_image | metrics/ndt.py:152-163 |
| P_SRB_NORM_UM="ndt_srb_norm_um" (88.6 [S]) | metrics/ndt.py:30 |
| P_DIP_THRESHOLD="ndt_dip_threshold" (20% dip; 주석 [P]→NDT-001 [S]) | metrics/ndt.py:29 |
| SNRnAccumulator 스트리밍(Welford 재사용, target 신호) | metrics/ndt.py:206-249 |
| WelfordAccumulator(온라인 count/mean/M2) | common/robust_stats.py:62 |
| update() peek-후-commit, 거부 프레임 no-op | metrics/ndt.py:273-301 |
| 정규화 단일 출처 = T1 compute_snrn 재호출(로컬 공식 금지) | metrics/ndt.py:283-299 |
| ShotLogEntry(shot_index/frame_count/snrn/srb_um/snr) | metrics/ndt.py:187 |
| target_reached / target_frame_index | metrics/ndt.py:319-327 |
| ROI 범위 초과·최소 픽셀 미달 → MetricReadError | metrics/ndt.py:263-272 |
| metrics-내부 상태, pipeline StatefulModule/orchestrator 무관 | metrics/ndt.py:216-219 |
| correct_thickness → ThicknessResult | metrics/ndt.py:383 |
| ThicknessResult(flattened/low_freq/method/scale_px/changed/warnings) | metrics/ndt.py:340-360 |
| flattened = measurement-local 복사본(파이프라인 재유입 금지) | metrics/ndt.py:342-351 |
| passthrough(no-gradient/oversized) 수치-무변경 | metrics/ndt.py:430-464 |
| 미지 thickness_method → MetricReadError | metrics/ndt.py:425-428 |
| read_single_wire_iqi → min_visible_wire | metrics/ndt.py:495 |
| WireElement(number/index), 인덱스 범위 밖 → MetricReadError | metrics/ndt.py:482-528 |
| 가시 와이어 부재 → MetricReadError(기본 감도 대체 금지) | metrics/ndt.py:536-539 |
| build_iqi_report → ShotVerdict "A"/"B"/"FAIL" | metrics/ndt.py:583-637 |
| IqiShot(shot_index/snrn/srb_um/min_visible_wire) | metrics/ndt.py:553-567 |
| ShotVerdict(shot_index/snrn/srb_um/min_visible_wire/class_a_pass/class_b_pass/verdict) | metrics/ndt.py:570-580 |
| 측정≠판정(EV-301 합격선 엔진 밖) | metrics/ndt.py:592-595 |
| 12 Params 키(전 외부화, 하드코딩 없음) | metrics/ndt.py:29-42 |
| 엔진 내부 DSP(grey_opening/gaussian_filter) | metrics/ndt.py:22/445/447 |
| 열기 로더(headerless 16-bit + 사이드카) | common/io.py:35 (`load_raw_frame`) |
| C-20 단일 choke point(`data/` 하위 쓰기 거부) | apps/gui/io_panel.py::guard_output_path (foundation G-4) |
| SAMPLE nps_flat→SNR sanity / acrylic_step→두께 sanity·선량 표시전용 | scripts/ingest_edrogi.py:88-89; foundation §2 그룹 7 |
| NDT는 CalibKind 미소비(지표 엔진, process 아님) | foundation §2 그룹 7; metrics/ndt.py:218-219 |

## v0.5.1 public operation closure

| Python EntryPoint | GUI 노출 | TC |
|---|---|---|
| `metrics.ndt.read_duplex_srb` | Duplex SRb action | 144 |
| `metrics.ndt.compute_snr` | SNR action | 145 |
| `metrics.ndt.compute_snrn` | SNRn action | 145 |
| `metrics.ndt.SNRnAccumulator.update` | session shot update | 146 |
| `metrics.ndt.SNRnAccumulator.shot_log` | session ordered log | 146 |
| `metrics.ndt.SNRnAccumulator.target_reached` | session target state | 146 |
| `metrics.ndt.SNRnAccumulator.target_frame_index` | target transition index | 146 |
| `metrics.ndt.SNRnAccumulator.current` | current aggregate | 146 |
| `metrics.ndt.correct_thickness` | Thickness action | 147 |
| `metrics.ndt.read_single_wire_iqi` | Single-wire IQI action | 148~149 |
| `metrics.ndt.build_iqi_report` | IQI report action | 149~150 |

TC-151은 strict user input, 오류, evidence/export를 검증한다. 상태 속성은 UI가 다시 계산하지 않고 session result DTO에서 그대로 표시한다.
