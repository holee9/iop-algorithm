# SPEC-CORR-001 — 인수 기준 (Acceptance Criteria)

DoD: **합성 주입 왜곡 제거를 T1 지표 엔진으로 before/after 판정** — 실측 도착 전, 기지 offset/gain/defect 패턴을 주입한 합성 프레임에 보정을 적용하고 metrics/ 엔진 산출로 개선·비열화를 판정한다. XDET-TC-001·002·003을 skeleton에서 실동작 케이스로 전환(EV-101/102/103 min 대비). 모든 기준은 관측 가능(테스트 출력 · 산출 값 · 마스크/이력 상태 · 경고/거부 발생)해야 한다. EV 판정 수치는 엔진·모듈 외부 주입(참조), 재현 허용오차·[T] 임계는 Params로 외부화한다.

## Given-When-Then 시나리오

### Scenario 1 — Offset 다크프레임 감산 + raw 포화 검출 (REQ-CORR-OFFSET-1, -4)
- **Given** 유효한 입력 XFrame(불변)과 CalibSet(OFFSET)의 offset map O(x,y), 그리고 offset 단계 Params `raw_saturation_threshold`(S_th, [B])와 I_raw ≥ S_th인 일부 포화 화소가 주어져 있다.
- **When** `offset.process(frame, calib, params)`가 실행된다.
- **Then** 감산 전 I_raw ≥ S_th 화소가 XFrame 마스크의 SATURATION 플래그로 표시되고(raw 포화 검출은 I_raw를 받는 유일 단계 offset 소관 — SPEC-LNSG-001 결정 2), 출력 pixel은 I₁ = I_raw − O이며, 입력 XFrame(pixel · mask · noise · history)은 변경되지 않고, 이력 체인에 모듈 버전 · 파라미터 해시 · 소비 CalibSet ID가 추가되어 있다.

### Scenario 2 — Offset 음수 클램프 + 리포트 (REQ-CORR-OFFSET-2)
- **Given** 일부 화소에서 I_raw − O < 0을 유발하는 과대 offset 입력이 주어져 있다.
- **When** offset 감산이 수행된다.
- **Then** 음수 화소는 0으로 클램프되고, 클램프 발생률(스칼라)이 해당 처리 단계의 이력 체인 엔트리 메타데이터에 기록되어 전달된다(마스크 아님, 부가 반환값 아님).

### Scenario 3 — Gain 평탄장 정규화 (REQ-CORR-GAIN-1)
- **Given** offset 보정된 XFrame(I₁)과 CalibSet(GAIN)의 단일점 gain map G(x,y)가 주어져 있다.
- **When** `gain.process(frame, calib, params)`가 실행된다.
- **Then** 출력 pixel은 I₂ = I₁ × G이고, 입력 XFrame은 변경되지 않으며, 이력 체인이 갱신된다.

### Scenario 4 — Gain 상한 클램프 + 리포트 (REQ-CORR-GAIN-2)
- **Given** 일부 화소에서 I₁ × G > 65535를 유발하는 입력이 주어져 있다.
- **When** gain 정규화가 수행된다.
- **Then** 초과 화소는 65535로 클램프되고, 클램프 발생률(스칼라)이 해당 처리 단계의 이력 체인 엔트리 메타데이터에 기록되어 전달된다(마스크 아님, 부가 반환값 아님).

### Scenario 5 — Gain 범위 밖 결함 후보 이관 (REQ-CORR-GAIN-3)
- **Given** gain map에 유효 범위 [0.5, 2.0](Params 주입 [T]) 밖 화소가 포함되어 있다.
- **When** gain 모듈이 gain map 유효성을 검사한다.
- **Then** 범위 밖 화소는 (1) 출력값이 gain 미적용 I₁으로 보존되고, (2) XFrame 마스크의 DEFECT 플래그로 표시되어 하류 defect 단계(고정 순서 gain→defect)로 결함 후보가 이관된다(결정론적 단일 경로 — 분기·무단 기본값 대체 없음, 결정 4).

### Scenario 6 — Defect 맵 기반 보간 + INTERPOLATION 플래그 + gain 플래그 화소 hand-off (REQ-CORR-DEFECT-1, -2, -8)
- **Given** 입력 XFrame과 CalibSet(DEFECT)의 결함 class_map(단일점 / line / cluster 라벨)이 주어지고, 일부 화소에는 gain 단계가 이관한 DEFECT 플래그(class_map 분류 없음)가 설정되어 있다.
- **When** `defect.process(frame, calib, params)`가 실행된다.
- **Then** 맵 분류 화소는 단일점=정상 8-이웃 거리 가중 평균, line=직교 방향 1D 선형, cluster=4방향 분산 최소 방향 1D 선형(edge-directed)으로 보간되고, gain이 플래그한 분류 없는 화소는 단일점 결함으로 취급되어 8-이웃 거리 가중 평균으로 보간되며(결정 4), 보간 화소는 INTERPOLATION 플래그로 표시되고 defect · interpolation 마스크가 하류로 전달된다.

### Scenario 7 — 합성 offset/gain before/after DQE · MTF 판정 (REQ-CORR-VALIDATE-2)
- **Given** 기지 MTF(해석적 slanted-edge)·기지 잡음에 offset/gain 왜곡을 주입한 합성 프레임과 3선량(XN/2 · XN · 2XN) 세트, 그리고 외부 주입 EV-101/102 min 임계가 주어져 있다.
- **When** offset → gain 보정을 적용하고 `tests/`에서 `metrics.dqe.compute_dqe` · `metrics.mtf.compute_mtf`/`mtf_value_at`로 보정 전/후 DQE(3선량)와 MTF@Nyquist(3.57 lp/mm) 유지율을 산출한다.
- **Then** 보정 후 DQE 열화 ≤ EV-101 min, MTF@Nyquist 유지율 ≥ EV-102 min을 판정 가능하다(XDET-TC-001 · XDET-TC-002). DQE는 T1 엔진의 IEC 형태(MTF²/(q·Ka·NNPS))로 산출된다.

### Scenario 8 — 합성 defect 잔존 cluster 0 (REQ-CORR-VALIDATE-3, 처리 모듈 게이트)
- **Given** 기지 좌표·종류(단일점/line/cluster) 결함을 주입한 합성 프레임과 대응 CalibSet(DEFECT) class_map, 그리고 외부 주입 EV-103 min 임계가 주어져 있다.
- **When** `modules/defect.py` 보간을 적용하고 `tests/`에서 `metrics.defect_stats.classify_defects`로 보정 후 잔존 결함을 산출한다.
- **Then** 검증 세트 내 잔존 가시 cluster 0건임을 판정 가능하다(XDET-TC-003 EV-103 min의 잔존 cluster 다리).

### Scenario 9 — defect-map 빌더 검출 누락률 (REQ-CORR-DEFECT-6, -3, REQ-CORR-VALIDATE-7, 빌더 게이트)
- **Given** 기지 좌표·종류(단일점/line/cluster) 결함을 주입한 합성 dark/flat 스택(ground truth 동반)과 외부 주입 EV-103 min 임계, 그리고 [P]/[S] 분류 임계(Params 주입)가 주어져 있다.
- **When** defect-map 빌더(`metrics/defect_map.py`)가 T1 엔진 `metrics/defect_stats.classify_defects`를 재사용해 CalibSet(DEFECT) 맵을 생성하고, `tests/`에서 생성 맵을 ground truth와 대조한다.
- **Then** 빌더 생성 맵의 검출 누락률이 EV-103 min 이내임을 판정 가능하다(XDET-TC-003 EV-103 min의 누락률 다리). 분류 임계는 빌더가 T1 엔진에 파라미터로 위임하며(하드코딩 0건), 누락률은 측정=판정 분리에 따라 외부 EV-103 min과 비교된다. 부정 케이스: C_max(5×5, [T]) 초과 cluster를 주입한 스택에 대해 빌더는 맵 생성을 거부하고 패널 판정 경고를 발생시킨다(SWR-302 생성 시점 게이트, REQ-CORR-DEFECT-6).

### Scenario 10 — Offset 잔여 검증 훅 (REQ-CORR-VALIDATE-4)
- **Given** 다크 프레임과 CalibSet(OFFSET)(O_map + σ_d), 그리고 잔여 임계 [T](기본 10%, Params 주입)가 주어져 있다.
- **When** 다크에 offset 보정을 적용한다.
- **Then** 잔여 offset(보정 후 다크 평균)이 σ_d 중앙값의 [T] 이내임을 확인한다(SWR-104 검증 훅).

### Scenario 11 — 공통 모듈 계약 준수 (REQ-CORR-CONTRACT-1, -2, -3, -6)
- **Given** 세 모듈(offset/gain/defect)과 harness fixture(합성 입력 + 기대 출력)가 주어져 있다.
- **When** `common.contract.check_process_contract` / `run_harness`와 import-linter 정적 검사가 실행된다.
- **Then** 각 모듈은 `process(frame, calib, params) -> XFrame` 시그니처·반환형을 만족하고, 입력 XFrame 불변·이력 체인 갱신·전체 XFrame 비교(pixel·마스크·노이즈·이력)를 통과하며, 의존 방향은 `module → common` 단방향(모듈 간·`metrics`·`pipeline` import 0건)이다. 세 모듈은 고정 순서 offset → gain → defect 부분수열로만 등록된다.

## Optional 요구 조건부 인수 기준 (WHERE 해당 입력이 제공되면)

### Scenario 12 — 동적 offset 모델 (REQ-CORR-OFFSET-3, Optional)
- **Given** 온도 T·경과시간 t 의존 동적 offset(O_ref + ΔO(T), [B] 파라미터) CalibSet 입력.
- **When** WHERE 해당 입력이 제공되면, 시스템이 취득 조건의 offset을 적용한다.
- **Then** 해당 조건 offset이 적용된다. 입력 미제공 시 본 기준은 적용되지 않으며 정적 O_ref 경로(Scenario 1)를 사용한다.

### Scenario 13 — 다점 gain 보정 (REQ-CORR-GAIN-4, Optional)
- **Given** 선량 계단 K개(K≥3) anchor([B]) 다점 gain 데이터 CalibSet 입력.
- **When** WHERE 해당 입력이 제공되면, 시스템이 픽셀별 구간 선형 보간(anchor 외삽은 최근접 기울기 연장)을 적용한다.
- **Then** 다점 구간 선형 gain이 적용된다. 입력 미제공 시 본 기준은 적용되지 않으며 단일점 경로(Scenario 3)를 사용한다.

## Edge Cases (부정/경계 케이스)

### EC-1 — CalibSet 부재/불일치 게이트 거부 (REQ-CORR-CONTRACT-5)
- **Given** offset/gain/defect 단계 중 하나에서 CalibSet이 부재하거나 불일치(해상도 · 패널 ID 상호불일치 · 종류-단계 배선 위반: 예 gain 단계에 kind≠GAIN · 유효기간 밖)한 입력.
- **When** 오케스트레이터 진입 게이트(`_calibration_gate`)가 실행된다.
- **Then** 처리를 거부하고 위반 단계·필드를 명시한 `CalibrationError`를 발생시킨다(무단 기본값 대체 없음).

### EC-2 — 결함 맵 cluster 초과 / 스키마 결손 (REQ-CORR-DEFECT-4, -7)
- **Given** (a) 연결 cluster 크기가 C_max(5×5, [T]) 초과 화소를 포함하는 CalibSet(DEFECT) 맵과, (b) 분류 라벨이 결손된 스키마 위반 맵, 두 종류.
- **When** defect 모듈이 맵 유효성을 검사한다.
- **Then** (a)는 해당 결함 맵의 보간 사용을 거부하고 패널 판정 경고를 발생시키며, (b)는 스키마 위반으로 거부한다(진단 ROI 품질 보증 불가).

### EC-3 — 정상 이웃 부족 시 무단 복원 금지 (REQ-CORR-DEFECT-5)
- **Given** 결함 화소의 8-이웃(또는 보간 방향 이웃)이 전부 결함이어서 SWR-303 보간이 유효한 정상 이웃 위에서 성립하지 못하는 입력.
- **When** defect 모듈이 보간을 시도한다.
- **Then** 해당 화소는 무단 "복원"되지 않고 다음 사후조건을 정확히 만족한다: (1) DEFECT 플래그가 유지되고, (2) INTERPOLATION 플래그가 설정되지 않으며, (3) 화소값이 입력과 동일하게 보존된다(허위 신호 생성 금지). 포화 화소 처리는 고정 순서상 defect 이후(T3)이므로 본 시나리오의 대상이 아니다.

### EC-4 — 사이드채널 / 의존 위반 (REQ-CORR-CONTRACT-4, -3)
- **Given** 입력 XFrame 변경을 시도하거나 부가 반환값(튜플)으로 산출물을 전달하거나 `modules/`·`pipeline`·`metrics`를 import하는 위반 코드가 있다.
- **When** XFrame 불변 검사(읽기 전용 버퍼) · 계약 검사(`check_process_contract`/`run_harness` 반환형) · import-linter 정적 검사가 실행된다.
- **Then** 입력 변경은 read-only 버퍼로 차단·검출되고, 부가 반환값·시그니처 위반은 계약 검사로 FAIL하며, 의존 위반은 import-linter로 열거되어 FAIL한다.
- **참고** 전역 상태·파일 우회 금지는 자동 검출 대상이 아닌 설계 규칙으로 코드 리뷰 게이트에서 다룬다(REQ-CORR-CONTRACT-4 자동 검출 범위 밖 — 본 EC의 검증 범위는 XFrame 읽기 전용 + 계약 검사 + import-linter로 한정, SPEC-INFRA-001 EC-4 방식 계승).

## 품질 게이트 / Definition of Done

- [ ] `modules/` 패키지 배치(offset · gain · defect), `module → common` 단방향 import-linter 계약 통과(모듈 간 · `metrics` · `pipeline` import 0건)
- [ ] 세 모듈 `process(XFrame, CalibSet, Params) -> XFrame` 시그니처·반환형·입력 불변·이력 체인(모듈 버전·파라미터 해시·CalibSet ID) — `run_harness` XDET-TC-000 통과(Scenario 11)
- [ ] offset: O 감산(Scenario 1) + raw ≥ S_th SATURATION 검출(REQ-CORR-OFFSET-4, Scenario 1; T3/SPEC-LNSG-001 run 단계 구현 예정) + 음수 클램프·리포트(이력 체인 메타 스칼라, Scenario 2) + 잔여 offset < σ_d 중앙값 10%[T](Scenario 10)
- [ ] gain: G 정규화(Scenario 3) + 상한 클램프·리포트(이력 체인 메타 스칼라, Scenario 4) + 범위밖 DEFECT 이관(출력값 I₁ 보존, Scenario 5)
- [ ] defect: 맵 기반 SWR-303 보간(단일점/line/cluster) + INTERPOLATION 플래그·하류 전달·gain 플래그 화소 단일점 보간(Scenario 6) + cluster > C_max 맵 거부·패널 경고·스키마 위반 맵 거부(EC-2) + 정상 이웃 부족 무단 복원 금지(DEFECT 유지·INTERPOLATION 미설정·화소값 보존, EC-3)
- [ ] defect-map 빌더 `metrics/defect_map.py`: `classify_defects` 재사용 → CalibSet(DEFECT) 생성(DEFECT-6) + `metrics → common` 단방향(모듈은 빌더·metrics import 0건, Scenario 9)
- [ ] 파라미터 등급 정합(SWR 부록 A): noisy 6× median=[S], dead/over-under/non-uniform=[P], gain 범위=[T], C_max=[T], offset 잔여=[T], 동적 offset·다점 gain=[B] — 전부 Params/CalibSet 외부화, 하드코딩 0건
- [ ] CalibSet 부재/불일치(해상도·패널 ID·종류-단계 배선·유효기간) 게이트 거부(EC-1)
- [ ] Optional 경로: 동적 offset(Scenario 12)·다점 gain(Scenario 13) — WHERE 입력 제공 시 적용, 미제공 시 정적/단일점 경로
- [ ] before/after 판정: DQE(3선량)·MTF@Nyquist 유지율(Scenario 7, XDET-TC-001/002, IEC 형태 DQE) + defect 잔존 cluster 0(Scenario 8, 처리 모듈) + defect-map 빌더 검출 누락률 ≤ EV-103 min(Scenario 9, ground truth 대조, XDET-TC-003) — metrics 엔진 소비(tests/)
- [ ] EV min/typ/max 판정 수치 엔진·모듈 미내장 — 외부 주입 확인(측정=판정 분리)
- [ ] XDET-TC-001 · XDET-TC-002 · XDET-TC-003 skeleton(skip) → 합성 입력·판정 엔진 연동 실동작 케이스 전환·통과
- [ ] **합성 주입 왜곡 3모듈 제거 PASS + before/after EV min 판정 + defect-map 빌더 누락률 ≤ EV-103 min** — DoD
