# SPEC-LAG-001 — 인수 기준 (Acceptance Criteria)

DoD: **합성 주입 IRF 보정 효과를 검증** — 실측 step-response 도착 전, 기지 지수합 IRF(aᵢ, bᵢ, M=3~4)를 주입한 합성 연속 시퀀스에 lag 보정을 적용하고 (a) first-frame lag % 개선은 T1 엔진 `metrics/lag.compute_first_frame_lag`로, (b) ghost 잔상 CNR 감소는 `metrics/lag.compute_ghost_cnr`로 `tests/`에서 판정하며, (c) **상태 직렬화 왕복(`serialize_state`→`load_state`) 후 이어 처리한 출력이 무중단 처리와 바이트 동일**함을 확인한다(REQ-INFRA-CONTRACT-2 T4 런타임 검증). XDET-TC-004는 EV-104 min 게이트로, XDET-TC-005는 부분 게이트(ghost CNR 감소; ghost 종단 비가시는 FB/실 패널 통합 후)로 skeleton(skip)에서 실동작 케이스로 전환한다. 모든 기준은 관측 가능(테스트 출력 · 산출 값 · 상태/이력 상태 · 예외 발생)해야 한다. EV 판정 수치는 엔진·모듈 외부 주입(참조), IRF 계수·재현 허용오차는 CalibSet/Params/외부 주입으로 외부화한다.

**Optional 요구 부재 노트**: 본 SPEC에는 Optional(WHERE) 요구가 없다 — 모든 요구는 필수(Ubiquitous/Event/State/Unwanted) 또는 Exclusions로 처리된다. 따라서 "WHERE 해당 입력이 제공되면 …" 형식의 조건부 인수 기준 절은 해당 없음(N/A)이다. SWR-403(노출 구간별 IRF 전환)·NLCSC 승급·전용 ghost 감쇠는 Optional이 아니라 Exclusions로 분류된다.

## Given-When-Then 시나리오

### Scenario 1 — 지수합 상태변수 재귀 보정 (REQ-LAG-CORR-1, -2)
- **Given** 유효한 입력 XFrame(불변; fixture는 SATURATION 마스크가 없는 비포화 화소만 포함)과 기지 지수합 IRF 계수 {aᵢ, bᵢ}(i=1..M, M=3~4)를 담은 CalibSet(LAG), 그리고 초기 상태 sᵢ[−1]=0의 lag 모듈 인스턴스가 주어져 있다.
- **When** 연속 시퀀스의 프레임 k에 대해 `lag.process(frame_k, calib, params)`가 실행된다.
- **Then** (비포화 화소에 대해) 각 지수항 상태가 sᵢ[k] = bᵢ·(sᵢ[k−1] + aᵢ·Î[k−1])로 갱신되고 보정 출력이 Î[k] = I[k] − Σᵢ sᵢ[k]로 산출되며(SWR-402; SATURATION 화소의 출력 값 보존은 REQ-LAG-CORR-5·EC-6 소관, 본 fixture는 포화 부재), 입력 XFrame(pixel·mask·noise·history)은 변경되지 않고 이력 체인에 모듈 버전·파라미터 해시·소비 CalibSet ID가 추가된다. IRF 계수는 CalibSet(LAG)에서만 오고 모듈에 하드코딩되지 않는다(CORR-1). LTI 단일 경로이며 조건부 분기가 없다.

### Scenario 2 — 상태 직렬화 왕복 = CONTRACT-2 첫 런타임 검증 (REQ-LAG-STATE-2, -3, REQ-LAG-VALIDATE-4)
- **Given** 기지 IRF로 생성한 합성 연속 시퀀스와, 시퀀스 중간 프레임 j에서 상태를 직렬화할 lag 인스턴스가 주어져 있다.
- **When** 프레임 1..j를 처리한 뒤 `serialize_state()`로 상태를 XFrame으로 저장하고, 새 인스턴스에 `load_state(state_xframe)`로 복원한 다음 프레임 j+1..N을 이어 처리한다.
- **Then** 왕복 후 이어 처리한 보정 출력과 최종 상태가 무중단 처리(동일 인스턴스로 1..N 처리)와 **바이트 동일**하다(상태는 (M, ny, nx) float32로 XFrame 패킹되며 dtype 고정으로 직렬화 왕복이 바이트 동일 — 결정 2; REQ-INFRA-CONTRACT-2 T4 런타임 검증 — T0에서 이연된 상태 직렬화 인터페이스의 첫 실제 상태 보유 모듈 검증). 상태는 XFrame 컨테이너로만 전달되고 컨테이너 외 사이드채널로 유지되지 않는다(SWR-000-6). 동일 IRF·입력·초기 상태에 대해 결정론적으로 재현된다(STATE-3).

### Scenario 3 — 내부 상태 보유 + 시퀀스 간 상태 리셋 + 프레임 간 threading (REQ-LAG-STATE-1, -4, -5)
- **Given** 두 개의 독립 연속 촬영 시퀀스 A·B(각각 기지 IRF 주입)와, 프레임당 M개 지수항 상태면 {sᵢ}를 내부 보유하는(REQ-LAG-STATE-1) lag 인스턴스, 그리고 시퀀스 구동 방식(신규 additive 시퀀스 러너 `pipeline/sequence.py` — 인스턴스를 시퀀스 수명 동안 재사용하고 시퀀스 개시 시 신규화로 리셋; spec 「결정 필요/확인 사항」 1 확정)이 주어져 있다.
- **When** 시퀀스 A를 프레임 순차로 처리(프레임 k 최종 상태 → 프레임 k+1 초기 상태)하고, 이어서 시퀀스 B를 개시한다.
- **Then** lag 인스턴스는 M개 상태면을 내부 보유하고(STATE-1), 시퀀스 A 내에서는 상태가 프레임 간 이어져 재귀가 지속되며(STATE-5), 시퀀스 B 개시 시 상태가 초기값(sᵢ[−1]=0)으로 재설정되어 A의 상태가 B로 누출되지 않는다(STATE-4, 결정론적). 구동 위치는 신규 시퀀스 러너 `pipeline/sequence.py`로 확정(결정 1)되었으며 리셋·threading 시맨틱은 관측 가능하다.

### Scenario 4 — first-frame lag % 개선 판정 (REQ-LAG-VALIDATE-1, -2)
- **Given** 포화 근접 노출 플래토 → X선 차단 → 잔상 감쇠 프레임열로 구성된 합성 시퀀스(기지 IRF로 생성)와, 외부 주입 EV-104 min(≤5%) 임계, 그리고 `metrics/lag`의 first-frame lag Params(플래토/베이스라인 검출)가 주어져 있다.
- **When** lag 보정을 시퀀스에 적용하고 `tests/`에서 `metrics.lag.compute_first_frame_lag`로 보정 전/후 first-frame lag %를 산출한다.
- **Then** 보정 후 first-frame lag %가 EV-104 min(≤5%) 이내이고 보정 전 대비 개선됨을 판정 가능하다(XDET-TC-004, 측정프로토콜 §1.5; REQ-METRICS-LAG-1/2 소비). 기지 IRF의 해석적 잔존 lag가 ground truth로 사용된다.

### Scenario 5 — ghost CNR 감소 T4 부분 게이트 (REQ-LAG-VALIDATE-3, REQ-LAG-CORR-4)
- **Given** 고대비 패턴 프레임 → 균일 조사 프레임으로 구성된 합성 연속 시퀀스(패턴 잔상이 기지 IRF로 균일 프레임에 이월)와, ghost CNR ROI(전경=이전 패턴 위치, 배경=청정 영역), 외부 주입 EV-104 ghost 임계가 주어져 있다.
- **When** lag 보정을 시퀀스에 적용하고 `tests/`에서 `metrics.lag.compute_ghost_cnr`로 균일 프레임의 보정 전/후 잔상 CNR을 산출한다.
- **Then** 보정 후 ghost CNR이 보정 전 대비 감소함을 판정 가능하다(XDET-TC-005, 측정프로토콜 §1.5; REQ-METRICS-LAG-5 소비). 이 감소는 SWR-402 재귀가 공간 구조 잔상을 부산물로 감산한 결과이며 전용 ghost 감쇠가 아니다(CORR-4). EV-104 ghost "비가시"의 운영 판정은 FB(패널 FW) 의존이므로 T4는 부분 게이트이고 종단 판정은 실 패널 통합(실측 후)에 둔다(spec 「결정 필요/확인 사항」 6).

### Scenario 6 — IRF 피팅 도구 복수 노출 → CalibSet(LAG) (REQ-LAG-IRF-1, -3)
- **Given** 기지 지수합 IRF로 생성한 복수 노출(포화 2~90% 범위 다점) rising/falling step-response 시퀀스가 주어져 있다.
- **When** IRF 피팅 빌더(가정 default: `metrics/lag_irf.py`, 결정 5)에 복수 노출 step-response를 입력한다.
- **Then** 빌더가 지수합 계수(aᵢ, bᵢ, M=3~4)를 피팅하여 주입 계수를 허용오차 내로 복원하고 CalibSet(kind=LAG)로 산출한다(SWR-401; 합성 IRF 선검증 REQ-LAG-IRF-3). 산출 CalibSet(LAG)를 보정 엔진(Scenario 1)에 주입하는 왕복이 성립한다.

### Scenario 7 — FB 트리거 인터페이스 (REQ-LAG-CORR-3)
- **Given** 연속 촬영 시퀀스 개시와 forward-bias(FB) 실행을 모사하는 mock(요청 수신·완료 통지)이 주어져 있다.
- **When** 시퀀스 개시 시 FB 트리거 인터페이스(요청/완료 확인 핸드셰이크)가 호출된다.
- **Then** 촬영 전 FB 실행 요청이 발행되고 완료 확인이 수신됨을 mock으로 관측 가능하다(SWR-404 — SW는 인터페이스만 정의; FB 실행 자체는 패널 FW 소관으로 Exclusions). P1에는 실 취득 계층이 없으므로 스텁 핸드셰이크로 시험한다. FB 트리거 스텁은 시퀀스 러너(`pipeline/sequence.py`)가 소유·호출한다(spec 「결정 필요/확인 사항」 4 확정).

### Scenario 8 — 공통 모듈 계약 준수 + harness 상태 확장 (REQ-LAG-CONTRACT-1, -2, -3, -6)
- **Given** lag 모듈(상태 보유)과 harness fixture(합성 입력 + 기대 출력 + 사전/사후 상태)가 주어져 있다.
- **When** `common.contract.check_process_contract` / `run_harness`(상태 확장: `load_state` 사전 상태 주입 → `process` → `serialize_state` 사후 상태 대조)와 import-linter 정적 검사가 실행된다.
- **Then** lag 모듈은 `process(frame, calib, params) -> XFrame` 시그니처·반환형을 만족하고, 입력 XFrame 불변·이력 체인 갱신·전체 XFrame 비교와 상태 왕복 대조를 통과하며, 의존 방향은 `module → common` 단방향(모듈 간·`metrics`·`pipeline` import 0건)이다. lag은 `CANONICAL_ORDER`의 lag 위치(defect 이후·line_noise 이전) 부분수열로만 등록된다. 내부 상태 보유는 SWR-000-7 명시 예외이며 계약 위반이 아니다.

## Edge Cases (부정/경계 케이스)

### EC-1 — CalibSet 부재/불일치 게이트 거부 (REQ-LAG-CONTRACT-4)
- **Given** lag 스테이지에서 CalibSet이 부재하거나 불일치(해상도 · 패널 ID · 유효기간 밖 · kind≠LAG)한 입력.
- **When** 오케스트레이터 진입 게이트(`_calibration_gate`)가 실행된다.
- **Then** 처리를 거부하고 위반 단계·필드를 명시한 `CalibrationError`를 발생시킨다(무단 기본값 대체 없음, SWR-000-5). `_KIND_BY_STAGE`가 `lag→lag`을 강제하므로 kind≠LAG는 거부된다.

### EC-2 — 단일 노출 IRF 캘리브레이션 거부 (REQ-LAG-IRF-2)
- **Given** 단일 노출만으로 생성한 step-response 입력(복수 노출 다점 아님).
- **When** IRF 피팅 빌더가 실행된다.
- **Then** 빌더가 단일 노출 캘리브레이션을 거부하고 명시 오류를 발생시킨다(SWR-401 "단일 노출 캘리브레이션 금지" — IRF는 측정 기법·노출 수준에 민감 [L]). 결정론적 거부 — 경고 후 진행 분기 없음.

### EC-3 — 전용 ghost 감쇠 시도 부정 대조 (REQ-LAG-CORR-4)
- **Given** FB 이후 잔존 ghost가 남는 합성 시퀀스.
- **When** lag 모듈이 실행된다.
- **Then** 모듈은 잔존 ghost를 추가로 감쇠(전용 ghost 모델링·외삽)하려 시도하지 않는다(SWR-404 Gen 1 범위 외). SWR-402 재귀의 부산물 ghost 감소(Scenario 5)는 본 금지 대상이 아니며, 전용 감쇠 코드 경로가 부재함을 확인한다.

### EC-4 — 사이드채널 / 의존 위반 (REQ-LAG-CONTRACT-5, -3)
- **Given** 입력 XFrame 변경을 시도하거나 부가 반환값(튜플)으로 산출물을 전달하거나 `modules/`·`pipeline`·`metrics`를 import하는 위반 코드가 있다.
- **When** XFrame 불변 검사(읽기 전용 버퍼) · 계약 검사(`check_process_contract`/`run_harness` 반환형) · import-linter 정적 검사가 실행된다.
- **Then** 입력 변경은 read-only 버퍼로 차단·검출되고, 부가 반환값·시그니처 위반은 계약 검사로 FAIL하며, 의존 위반은 import-linter로 열거되어 FAIL한다.
- **참고** lag의 내부 상태(REQ-LAG-STATE-1)는 SWR-000-7 명시 허용 예외이며 `serialize_state`로 XFrame 직렬화 가능하므로 금지된 사이드채널이 아니다. 전역 상태·파일 우회 금지는 자동 검출 대상이 아닌 설계 규칙으로 코드 리뷰 게이트에서 다룬다(본 EC의 검증 범위는 XFrame 읽기 전용 + 계약 검사 + import-linter로 한정, SPEC-INFRA-001 EC-4 방식 계승).

### EC-5 — 시퀀스 간 상태 누출 부정 대조 (REQ-LAG-STATE-4)
- **Given** 강한 잔상을 남긴 시퀀스 A 직후 개시하는 새 시퀀스 B.
- **When** 시퀀스 B의 첫 프레임을 리셋 없이 처리한 경우와 리셋 후 처리한 경우를 대조한다.
- **Then** 리셋을 적용하지 않으면 A의 잔존 상태가 B 첫 프레임 보정에 침입해 오보정을 유발함을(부정 대조) 확인하고, 시퀀스 개시 리셋(sᵢ[−1]=0)이 이를 방지함을 판정 가능하다(STATE-4 결정론적 리셋).

### EC-6 — 포화 화소 값 보존 + 재귀 계산값 진행 (REQ-LAG-CORR-5, spec 「결정 필요/확인 사항」 6)
- **Given** 상류 offset 단계가 raw 포화 검출(I_raw ≥ S_th, SPEC-CORR-001 REQ-CORR-OFFSET-4)로 SATURATION 플래그를 설정한 화소를 포함하는 입력 시퀀스.
- **When** lag 보정이 상태 Σsᵢ를 감산한다.
- **Then** SATURATION 화소의 출력 값은 보존되어 포화점 아래 값이 생성되지 않는다(REQ-LAG-CORR-5; `modules/line_noise.py` SATURATION 보존·SWR-602 복원 금지 취지 일관). 그 화소에서도 내부 상태 재귀는 보존된 출력이 아니라 계산된 감산 값 Î[k−1]로 진행하여 상태 진화가 물리적으로 유지된다(결정 6 확정, D7 축). 출력 보존 사후조건과 재귀-계산값 사용이 모두 관측 가능하다.

## 품질 게이트 / Definition of Done

- [ ] `modules/lag.py` 배치, `module → common` 단방향 import-linter 계약 통과(모듈 간 · `metrics` · `pipeline` import 0건)
- [ ] lag 모듈 `process(XFrame, CalibSet, Params) -> XFrame` 시그니처·반환형·입력 불변·이력 체인(모듈 버전·파라미터 해시·CalibSet ID) — harness(상태 확장) XDET-TC-000 통과(Scenario 8)
- [ ] 지수합 상태변수 재귀(SWR-402) sᵢ[k]=bᵢ·(sᵢ[k−1]+aᵢ·Î[k−1]), Î[k]=I[k]−Σsᵢ[k] — IRF 계수 CalibSet(LAG) 주입, 하드코딩 0건(Scenario 1)
- [ ] **상태 직렬화 왕복 바이트 재현(`serialize_state`/`load_state` ↔ XFrame; 상태 (M,ny,nx) float32 dtype 고정) = REQ-INFRA-CONTRACT-2 T4 첫 런타임 검증**(Scenario 2, 결정 2) + 결정론(STATE-3)
- [ ] 시퀀스 간 리셋(sᵢ[−1]=0, 누출 없음) + 프레임 간 threading(Scenario 3, EC-5)
- [ ] first-frame lag % 개선 판정 ≤ EV-104 min(Scenario 4, XDET-TC-004, `metrics/lag.compute_first_frame_lag`, 기지 IRF ground truth)
- [ ] ghost CNR 감소 T4 부분 게이트(Scenario 5, XDET-TC-005, `metrics/lag.compute_ghost_cnr`; SWR-402 부산물 — 전용 감쇠 아님)
- [ ] IRF 피팅 빌더: 복수 노출 → 계수 복원 → CalibSet(LAG) emit(Scenario 6) + 단일 노출 거부(EC-2)
- [ ] FB 트리거 인터페이스(요청/완료 스텁, mock) 정의·시험(Scenario 7) + 전용 ghost 감쇠 부재(EC-3)
- [ ] 포화 화소 값 보존 + 재귀는 계산값 진행(REQ-LAG-CORR-5, EC-6, SWR-602 취지 일관)
- [ ] CalibSet 부재/불일치(해상도·패널 ID·유효기간·`lag→LAG` 종류-단계 배선) 게이트 거부(EC-1)
- [ ] 사이드채널·의존 위반 검출(EC-4); 내부 상태는 SWR-000-7 예외로 위반 아님 확인
- [ ] 파라미터 등급 정합(SWR 부록 A): IRF 계수 aᵢ·bᵢ·M(SWR-401)=[B], M=3~4 구조=[L], SWR-402 재귀 방법=[C] 추론(부록 A-2 [C] 행에 402 미등재 — 대표 열거이므로 확정 [C]가 아닌 추론); lag 모듈 [T]/[P] 튜닝 상수 없음 — 전부 CalibSet 외부화, 하드코딩 0건
- [ ] EV-104 min/typ/max 판정 수치 엔진·모듈 미내장 — 외부 주입 확인(측정=판정 분리, VALIDATE-5)
- [ ] XDET-TC-004(EV-104 min 게이트) · XDET-TC-005(부분 게이트 — ghost CNR 감소; ghost 종단 비가시는 FB/실 패널 통합 후) skeleton(skip) → 합성 입력·판정 연동 실동작 케이스 전환·통과(VALIDATE-6)
- [ ] **lag 보정 합성 검증 PASS(first-frame lag % 개선·≤ EV-104 min + ghost CNR 감소 + 상태 직렬화 왕복 바이트 재현) + IRF 도구 복원·거부 + 부정/경계 케이스 정상 거부** — DoD
- [ ] spec 「결정 필요/확인 사항」 1·2·4·6 확정(1=시퀀스 러너 `pipeline/sequence.py`, 2=(M,ny,nx) float32 패킹, 4=FB 트리거 러너 소유, 6=포화 보존+재귀 계산값); 3(harness 확장)·5(IRF 도구 배치) 확인 유지
