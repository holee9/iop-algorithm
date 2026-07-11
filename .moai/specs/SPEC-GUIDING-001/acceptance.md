# SPEC-GUIDING-001 — 인수 기준 (Acceptance Criteria)

DoD: 정본 지침(guiding) 취득세트의 요구·조건·매수·추적성이 EARS로 확정되고, **도착한 후보 지침 세트가 매니페스트 체크리스트에 대조되어 각 항목이 관측 가능하게 SUPPLIED/MISSING으로 판정**된다. 본 SPEC은 소프트웨어 산출물이 없으며(무-코드), 모든 기준은 물리 취득세트의 존재·매수·조건·`usage="guiding"` 등록에 대한 관측이다. 수치 확정·튜닝·EV 임계 조정은 본 SPEC 범위 밖(별도 SPEC).

기준 형태: 후보 지침 세트가 도착하면, 아래 「지침 취득세트 매니페스트 체크리스트」의 각 행을 요구 매수·조건에 대조하여 **SUPPLIED**(요구 충족) 또는 **MISSING**(미달·부재)으로 표시한다. 모든 A티어 전제 + 최고 레버리지 2종이 SUPPLIED이면 핵심 수치 아암(MTF·NPS·DQE·gain·선형성·노이즈모델)이 활성화된다.

## Given-When-Then 시나리오

### Scenario 1 — A티어 기준 셋업 확립 (REQ-GUIDING-BASELINE, 측정프로토콜 §선질/EVAL §0)
- **Given** 후보 지침 세트가 취득 조건과 함께 도착한다.
- **When** 기준 셋업을 매니페스트에 대조한다.
- **Then** RQA5(70~74kV + Al 21mm type-1100 순도 99.0%, SID≥1.5m, 조사야 16×16cm, grid 미장착)가 확인되고, 관전압이 HVL 실측으로 확정되었으며(명목 kV 고정 아님), 교정 이온챔버로 검출기면 Ka(후방산란 제외)가 실측·기록되고, 각 취득이 3점 선량(XN/2·XN·2XN, XN≈8.73µGy)으로 구성되며, offset/gain 보정 전·후 각각이 취득됨이 확인된다. 초고순도 Al 필터 또는 명목 kV-only 취득은 MISSING으로 거부된다.

### Scenario 2 — 최고 레버리지 2종 취득 → 핵심 아암 활성화 (REQ-GUIDING-LEVERAGE, EV-101/102)
- **Given** A티어 전제가 SUPPLIED인 상태에서 후보 세트가 flat 선량 계단과 슬랜티드 엣지를 포함한다.
- **When** 두 레버리지 항목을 요구 조건에 대조한다.
- **Then** flat-field 선량 계단(6~8단계 × 단계당 ≥10매 + 각 단계 선량 실측치)과 슬랜티드 엣지(W 2mm 후판, 수평·수직, 1.5~3° 미세경사, 방향·선량당 ≥5매)가 SUPPLIED로 확인되고, 이로써 gain 다점·NPS·DQE 분모·선형성·노이즈모델·MTF·SRb·DQE 분자 수치 아암이 활성화 가능으로 표시된다. 선량 실측치 없이 라벨-only인 flat 계단, 45°/알루미늄 엣지는 MISSING으로 거부된다.

### Scenario 3 — DQE 3입력 온전 공급 (REQ-GUIDING-DQE, EV-101, XDET-TC-001)
- **Given** 후보 세트가 MTF(엣지)·NPS(flat)·Ka(실측) 공급을 주장한다.
- **When** DQE 3입력을 대조한다.
- **Then** 세 입력이 모두 SUPPLIED일 때에만 DQE 수치 판정이 활성화 가능으로 표시된다 — MTF(f)(엣지 분자), NPS(f)(선량점당 ≥16매 앙상블 × 3 선량점), 교정 Ka(검출기면 실측). q는 IEC 표값 조달로 충분하나 Ka는 실측이어야 한다. 세 입력 중 하나라도 결여되면 DQE는 MISSING이다(현 샘플 상태: 온전 공급 0개).

### Scenario 4 — lag/ghost 취득 구조 제약 (REQ-GUIDING-LAG, [OBSERVE] #32, EV-104)
- **Given** 후보 세트가 lag step-response와 ghost 시간계단을 포함한다.
- **When** lag/ghost 취득 구조를 대조한다.
- **Then** lag step-response가 비포화 다중노출(포화의 2~90% 범위, 프레임 간격 기록, ≥5회)이고 노출/잔상 쌍으로 분해 가능하게 배선(자극/응답 구분)되며, ghost 세트가 납판 반차폐 강노출 후 균일 조사 직후/1분/5분으로 구성됨이 확인된다. 포화(65535 clip) 프레임 또는 단일노출로 구성된 lag 취득은 MISSING으로 거부된다(SWR-401).

### Scenario 5 — 잔여 MISSING/PARTIAL 항목의 정본 취득 (REQ-GUIDING-COVERAGE, EV-103/105/106/201~205/301~303)
- **Given** 후보 세트가 offset dark 스택·bad pixel 스택·line noise·NDT IQI·step wedge·grid·scatter·구조물/포화/기하 팬텀·임상+CDRAD를 포함한다.
- **When** 각 항목을 요구 매수·조건에 대조한다.
- **Then** 각 항목이 요구 매수·조건을 충족하면 해당 TC/EV 수치 아암이 활성화 가능으로 표시된다(예: offset dark 온도3×시점4×≥20, bad pixel dark≥50+flat≥50, line noise XN/8~XN/4 ≥20매, grid 밀도 3부류 aliased 포함 grid당 ≥5매). 요구 매수·조건 미달 항목은 MISSING이다.

### Scenario 6 — 추적성·격리·등록 (REQ-GUIDING-TRACE, RTM/SPEC-REALDATA-001)
- **Given** 정본 지침 세트가 도착·등록된다.
- **When** 추적성과 등록을 검사한다.
- **Then** 각 취득 요구가 unblock하는 TC/EV(XDET-TC-001~019, EV-101~106/201~205/301~303)에 RTM 경유로 매핑되고, 세트가 `usage="guiding"`로 등록되어 샘플 세트(`usage="sample-plumbing"`)와 구분되며, 도착 전까지 수치 검증은 합성 팬텀 경로로만 유효(BLOCKER 유지)함이 기록된다. 본 SPEC 범위 내 수치 확정·EV 임계 조정·파라미터 튜닝 시도는 거부된다.

## 지침 취득세트 매니페스트 체크리스트

후보 지침 세트가 도착하면 각 행을 요구 매수·조건에 대조하여 판정한다. 판정 = `[ ] SUPPLIED / [ ] MISSING`.

### A티어 전제 (선행 필수)

| 항목 | 요구 조건 | 대응 REQ | 판정 |
|---|---|---|---|
| RQA5 빔질 | 70~74kV + Al 21mm(type-1100, 99.0%), SID≥1.5m, FOV 16×16cm, grid 미장착 | BASELINE-1 | [ ] SUPPLIED / [ ] MISSING |
| HVL 실측 kV | 명목 kV 아닌 HVL 실측으로 관전압 확정 | BASELINE-2/7 | [ ] SUPPLIED / [ ] MISSING |
| 교정 Ka 실측 | 교정 이온챔버, 검출기면 air kerma, 후방산란 제외 | BASELINE-3 | [ ] SUPPLIED / [ ] MISSING |
| 3점 선량 | XN/2 · XN · 2XN (XN≈8.73µGy) | BASELINE-4 | [ ] SUPPLIED / [ ] MISSING |
| offset/gain 전·후 | 보정 전·후 각각 취득 | BASELINE-5 | [ ] SUPPLIED / [ ] MISSING |

### 최고 레버리지 2종 (다수 아암 동시 활성화)

| 항목 | 요구 매수·조건 | unblock TC/EV | 대응 REQ | 판정 |
|---|---|---|---|---|
| flat-field 선량 계단 | 6~8단계(1/8~8×), 단계당 ≥10매 + 단계별 선량 실측치 | XDET-TC-001/011, EV-101 (gain·NPS·DQE분모·선형성·α,σ) | LEVERAGE-1/4 | [ ] SUPPLIED / [ ] MISSING |
| 슬랜티드 엣지(MTF) | W 2mm 후판, 검출기 밀착, 수평·수직, 1.5~3° 미세경사, 방향·선량당 ≥5매 | XDET-TC-002, EV-102 (MTF·SRb·DQE분자) | LEVERAGE-2/3 | [ ] SUPPLIED / [ ] MISSING |

### DQE 3입력

| 입력 | 요구 조건 | 대응 REQ | 판정 |
|---|---|---|---|
| MTF(f) | 슬랜티드 엣지(레버리지 2) | DQE-1 | [ ] SUPPLIED / [ ] MISSING |
| NPS(f) | 선량점당 ≥16매 flat 앙상블 × 3 선량점 | DQE-1/2 | [ ] SUPPLIED / [ ] MISSING |
| 교정 Ka | 검출기면 실측(q는 IEC 표값 조달) | DQE-1/3 | [ ] SUPPLIED / [ ] MISSING |

### lag/ghost 취득 구조 (#32)

| 항목 | 요구 매수·조건 | unblock TC/EV | 대응 REQ | 판정 |
|---|---|---|---|---|
| lag step-response | 비포화 2~90% 복수 노출, 프레임 간격 기록, ≥5회, 노출/잔상 쌍 분해 가능 | XDET-TC-004, EV-104 | LAG-1/2/3/5 | [ ] SUPPLIED / [ ] MISSING |
| ghost 시간계단 | 납판 반차폐 강노출 후 균일 조사 직후/1분/5분 | XDET-TC-005, EV-104 | LAG-4 | [ ] SUPPLIED / [ ] MISSING |

### 잔여 MISSING/PARTIAL 항목 (커버리지)

| 항목 | 요구 매수·조건 | unblock TC/EV | 대응 REQ | 판정 |
|---|---|---|---|---|
| offset dark 스택 | 온도 3구간 × 시점 4회 × 시점당 ≥20매 | EV-101 | COVERAGE-1 | [ ] SUPPLIED / [ ] MISSING |
| bad pixel E2597 스택 | dark ≥50매 + flat ≥50매 raw (7종 분류) | XDET-TC-003, EV-103 | COVERAGE-2 | [ ] SUPPLIED / [ ] MISSING |
| line noise 저선량 | XN/8~XN/4, ≥20매 | XDET-TC-006, EV-105 | COVERAGE-3 | [ ] SUPPLIED / [ ] MISSING |
| 노이즈모델 α,σ | 다점 선량계단 회귀 입력(=flat 계단) | XDET-TC-011, SWR-701 | COVERAGE-4 | [ ] SUPPLIED / [ ] MISSING |
| SNRn·duplex·IQI·용접 | duplex wire + 단선 IQI + 용접시편, kV·노출 3점×5매 + 적산 연속 프레임 | XDET-TC-018, EV-301 | COVERAGE-5 | [ ] SUPPLIED / [ ] MISSING |
| CSa·SMTR step wedge | E2597 6단 wedge(강/알루미늄) + 두께 경사 시편 | XDET-TC-019, EV-303 | COVERAGE-6 | [ ] SUPPLIED / [ ] MISSING |
| grid 매트릭스 | 밀도 3부류(< 3.57 / ≈ / > lp/mm, aliased 필수), 정렬·미세경사, grid당 ≥5매 | XDET-TC-015/016, EV-203 | COVERAGE-7 | [ ] SUPPLIED / [ ] MISSING |
| scatter 팬텀 | 아크릴/물 두께 계단, grid 유/무 쌍 | XDET-TC-017, EV-202 | COVERAGE-8 | [ ] SUPPLIED / [ ] MISSING |
| 구조물/포화/기하 팬텀 | 금속 3배치×5매 / 경계 구도 3×5매 / 격자 3위치×3매 + 실측 치수 | XDET-TC-007/008/009, EV-105/106 | COVERAGE-9 | [ ] SUPPLIED / [ ] MISSING |
| 임상 모사 + CDRAD | 부위별 다구도 ≥10, 표준 + 저선량 계단 | XDET-TC-010/012/013, EV-205 | COVERAGE-10 | [ ] SUPPLIED / [ ] MISSING |

### 등록·추적성

| 항목 | 요구 조건 | 대응 REQ | 판정 |
|---|---|---|---|
| `usage="guiding"` 등록 | SPEC-REALDATA-001 매니페스트 규약, 샘플 세트와 구분 | TRACE-2 | [ ] SUPPLIED / [ ] MISSING |
| RTM TC/EV 매핑 | 각 취득 → unblock TC/EV RTM 경유 매핑 | TRACE-1 | [ ] SUPPLIED / [ ] MISSING |

## Edge Cases (부정/경계 케이스)

### EC-1 — 포화 프레임 거부 (REQ-GUIDING-LAG-2, REQ-GUIDING-COVERAGE-11)
- **Given** 후보 세트의 lag/ghost 계열에 포화(65535 clip) 프레임이 진폭 추정 대상으로 포함되거나, lag가 단일노출로 구성되어 있다.
- **When** lag step-response 항목을 대조한다.
- **Then** 해당 lag 항목은 MISSING으로 판정된다(SWR-401 위반 — 클리핑이 지수감쇠 곡선 파괴, IRF 진폭 추정 불가). 의도적 포화 자극 프레임은 비포화 응답 프레임과 구분·표시된 경우에만 유효하다(LAG-5).

### EC-2 — Ka 미실측 거부 (REQ-GUIDING-BASELINE-3, REQ-GUIDING-DQE-3)
- **Given** 후보 세트가 검출기면 air kerma를 교정 이온챔버로 실측하지 않고 명목/추정값만 제공한다.
- **When** A티어 Ka 항목과 DQE 3입력을 대조한다.
- **Then** Ka 항목이 MISSING으로 판정되고, DQE 수치 아암은 활성화 불가(절대 선량 미확정 → DQE 절대값 불가)로 표시된다.

### EC-3 — 매수 미달 거부 (REQ-GUIDING-COVERAGE-11, REQ-GUIDING-DQE-2)
- **Given** 후보 세트가 요구 매수를 미달한다(예: NPS 3매(요구 ≥16), flat 계단 단계당 5매(요구 ≥10), offset dark 시점당 10매(요구 ≥20), grid 밀도 2부류만(aliased 부류 누락)).
- **When** 해당 항목을 요구 매수·조건에 대조한다.
- **Then** 각 미달 항목은 MISSING으로 판정되어 해당 수치 아암이 활성화되지 않는다(PARTIAL은 수치 판정 활성으로 간주하지 않는다).

### EC-4 — 격리 위반 방지 (REQ-GUIDING-TRACE-5, SPEC-REALDATA-001 QUARANTINE)
- **Given** 본 SPEC 범위 내에서 샘플 세트 또는 도착한 지침 세트로 [B]/[T]/[P] 파라미터를 유도·튜닝하거나 EV 임계를 조정하려는 시도가 있다.
- **When** 작업 범위를 검토한다.
- **Then** 해당 시도는 범위 위반으로 거부된다 — 본 SPEC은 취득 요구 정의만 담당하며, 수치 확정·튜닝은 정본 세트 도착 후 별도 SPEC에서만 수행한다.

## 품질 게이트 / Definition of Done

- [ ] A티어 기준 셋업(RQA5 + HVL 실측 kV + 교정 Ka + XN 3점 선량 + offset/gain 전·후) 요구 확정·문서화 (Scenario 1, BASELINE)
- [ ] 최고 레버리지 2종(flat 선량 계단 6~8단계×≥10매+선량 실측 · 슬랜티드 엣지 W2mm 1.5~3°×≥5매) 요구 확정 → 핵심 아암 활성화 조건 정의 (Scenario 2, LEVERAGE)
- [ ] DQE 3입력(MTF 엣지 · NPS ≥16매×3선량점 · 교정 Ka) 온전 공급 요구 확정 (Scenario 3, DQE)
- [ ] lag/ghost 취득 구조(비포화 2~90% 복수노출 · 노출/잔상 쌍 분해 · ghost 직후/1분/5분 · 포화·단일노출 거부) 요구 확정 (Scenario 4, LAG, #32)
- [ ] 잔여 MISSING/PARTIAL 10항목의 정본 취득 요구(매수·조건) 확정 → EV-101~106/201~205/301~303 판정 가능화 (Scenario 5, COVERAGE)
- [ ] 매니페스트 체크리스트로 각 항목이 관측 가능하게 SUPPLIED/MISSING으로 판정 가능 (체크리스트 표)
- [ ] `usage="guiding"` 등록 규약 + RTM 경유 TC/EV 매핑 정의 (Scenario 6, TRACE)
- [ ] 포화 프레임/Ka 미실측/매수 미달 거부가 매니페스트 대조로 관측 가능 (EC-1/2/3)
- [ ] 격리(QUARANTINE) 연장 — 샘플·지침 세트로 본 SPEC 범위 내 수치 튜닝·EV 임계 조정 없음 (EC-4, TRACE-5)
- [ ] **소프트웨어 산출물 없음 · 물리 취득 요구 명세만 · 수치 확정은 별도 SPEC — DoD**
