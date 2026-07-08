# SPEC-LNSG-001 — 인수 기준 (Acceptance Criteria)

DoD: **합성 주입 왜곡 억제·처리를 검증** — 실측 도착 전, 기지 line noise/포화/기하 왜곡을 주입한 합성 팬텀에 각 처리를 적용하고 (a) line noise 제거는 T1 엔진 `metrics/nps.detect_line_noise`로 1D NPS 저주파 이상 피크 제거를 판정(SWR-504 + REQ-METRICS-NPS-8 확장(행/열)), (b) 구조물 오보정률·(c) 포화 마스크 통합/경계 밴드/복원 금지 사후조건·(d) 기하 잔차는 `tests/`에서 ground truth 대조 직접 측정으로 판정한다. XDET-TC-006·007·008·009를 skeleton에서 실동작 케이스로 전환(EV-105/106 min 대비). 모든 기준은 관측 가능(테스트 출력 · 산출 값 · 마스크/이력 상태 · 경고/거부 발생)해야 한다. EV 판정 수치는 엔진·모듈 외부 주입(참조), 재현 허용오차·[B]/[T] 상수는 Params/CalibSet로 외부화한다.

**REQ-LNSG-VALIDATE-1 커버리지 노트**: REQ-LNSG-VALIDATE-1(합성 검증 컨텍스트 전제, State-Driven)은 개별 단독 시나리오가 아니라 Scenario 6~9(line noise 이상 피크 제거·구조물 오보정률·포화 검증·기하 잔차)의 합성 주입 검증 전체로 충족되는 우산(umbrella) 요구이다 — 각 모듈이 기지 왜곡을 억제·처리함을 보이는 합성 검증 컨텍스트가 성립함을 이들 시나리오가 집합적으로 입증한다.

## Given-When-Then 시나리오

### Scenario 1 — Line noise 우선 경로(SWR-503) 열 프로파일 감산 + 고역 제한 (REQ-LNSG-LINE-1)
- **Given** 유효한 입력 XFrame(불변)과 reference 영역을 담지 않은 CalibSet(LINE_NOISE), 그리고 창 length·고역 컷오프([T], Params 주입)가 주어져 있다.
- **When** `line_noise.process(frame, calib, params)`가 실행된다(CalibSet에 reference 영역이 없어 SWR-503 경로가 결정론적으로 선택된다).
- **Then** 출력 pixel은 열 방향 저주파 프로파일(행별 강건 평균 → 1D median, 창 length [T])을 감산하되 감산 성분에 고역 제한(컷오프 [T])이 적용된 결과이고, 입력 XFrame(pixel · mask · noise · history)은 변경되지 않으며, 이력 체인에 모듈 버전 · 파라미터 해시 · 소비 CalibSet ID가 추가되어 있다.

### Scenario 2 — Line noise 마스크 제외 + 노이즈 모델 미갱신 (REQ-LNSG-LINE-3)
- **Given** DEFECT · INTERPOLATION · SATURATION 플래그 화소를 포함하는 입력 XFrame과 노이즈 모델(α, σ)이 주어져 있다.
- **When** line noise 보정이 강건 통계(프로파일 · 행 중앙값)를 산출한다.
- **Then** DEFECT · INTERPOLATION · SATURATION 화소는 통계에서 제외 가중되어 오염이 방지되고, 출력 XFrame의 노이즈 모델(α, σ)은 입력과 동일하게 유지된다(재추정·변경 없음 — SWR-701/T5 소관).

### Scenario 3 — 누적 SATURATION 마스크 소비·하류 전달 (REQ-LNSG-SAT-1)
- **Given** 상류 offset 단계가 raw 포화 검출(I_raw ≥ S_th, SPEC-CORR-001 REQ-CORR-OFFSET-4)로 설정한 SATURATION 플래그와 gain 클램프(65535)가 설정한 SATURATION 플래그가 마스크 스택에 누적된 입력 XFrame이 주어져 있다(S_th는 offset 단계 Params `raw_saturation_threshold`, [B]).
- **When** `saturation.process(frame, calib, params)`가 실행된다.
- **Then** offset(raw) ∪ gain 클램프로 누적된 SATURATION 마스크가 그대로 소비·하류 전달되고(denoiser · 대비강화 제외 가중 대상), 입력 XFrame은 변경되지 않으며 이력 체인이 갱신된다(포화 모듈은 raw를 재검출하지 않음 — 결정 2).

### Scenario 4 — 포화 경계 밴드 완충 가중 표시 (REQ-LNSG-SAT-2)
- **Given** 상류 offset(raw)·gain 클램프로 SATURATION이 누적된 XFrame과 경계 밴드 폭 W_band(SWR-602 명시값 2px, Params 주입)가 주어져 있다.
- **When** 포화 단계가 누적 SATURATION 마스크를 소비한다.
- **Then** 포화 영역 경계의 W_band 밴드가 완충 가중 대상으로 표시되어 하류 링잉 억제 substrate가 된다(가정 default: SATURATION 마스크 W_band 팽창 — spec 「결정 필요/확인 사항」 3; 실제 graded 가중 적용은 T5 소관).

### Scenario 5 — 포화 통계 이력 메타 기록 (REQ-LNSG-SAT-4)
- **Given** 포화 화소를 포함하는 입력.
- **When** 포화 처리가 완료된다.
- **Then** 포화 화소 비율 등 포화 통계(스칼라)가 해당 처리 단계의 이력 체인 엔트리 메타데이터에 기록되어 전달된다(마스크 아님, 부가 반환값 아님; DICOM 태그 실제 emission은 출력 포맷 소관 — Exclusions).

### Scenario 6 — 합성 line noise 제거 detect_line_noise 판정 (REQ-LNSG-VALIDATE-2)
- **Given** 균일 조사 합성 프레임에 기지 행/열 line noise(저주파 오프셋)를 주입한 팬텀과, 외부 주입 EV-105 min 임계, 그리고 detect_line_noise 유의성 계수(sig_factor, SPEC-METRICS-001 Params)가 주어져 있다.
- **When** line noise 보정을 적용하고 `tests/`에서 `metrics.nps.detect_line_noise`로 보정 전/후 행·열 방향 1D NPS 저주파 이상 피크를 산출한다.
- **Then** 보정 전에는 이상 저주파 피크가 검출(detected=True)되고, 보정 후에는 유의성 임계(median + sig_factor·MAD) 이하로 미검출(detected=False)임을 판정 가능하다(SWR-504 + REQ-METRICS-NPS-8 확장(행/열), XDET-TC-006 EV-105 min "잔존 line artifact 비가시" 표준 window의 관측 가능 대리 지표).

### Scenario 7 — 구조물 오염 오보정률 (REQ-LNSG-VALIDATE-3)
- **Given** 금속 구조물 오염을 모사한(고감쇠 영역, 기지 ground truth 동반) 합성 프레임과 line noise 주입, 그리고 외부 주입 EV-105 min(≤1%) 임계가 주어져 있다.
- **When** line noise 보정을 적용하고 `tests/`에서 구조물 영역 오보정률(ground truth 대비 허위 변경 화소 비율)을 산출한다.
- **Then** 오보정률이 EV-105 min(≤1%) 이내임을 판정 가능하다(XDET-TC-007). 오보정 억제는 활성 경로에 따른다 — 우선 경로(SWR-503)는 고역 제한 + 마스크 제외, 레퍼런스 경로 fixture 제공 시 오염 행 k·MAD(6) 배제(SWR-502)에 의한다(spec 「결정 필요/확인 사항」 5).

### Scenario 8 — 포화 검출·마스킹·복원 금지 T3 부분 게이트 (REQ-LNSG-VALIDATE-4)
- **Given** 기지 포화 영역(좌표·강도, raw ≥ S_th)을 주입하고 offset 단계가 이를 SATURATION으로 검출·설정한 합성 프레임과 외부 주입 EV-106 min 임계가 주어져 있다.
- **When** 포화 처리를 적용하고 `tests/`에서 마스크·경계 밴드·화소값을 검사한다.
- **Then** (a) offset 검출(raw ≥ S_th, SPEC-CORR-001 REQ-CORR-OFFSET-4)로 설정된 SATURATION 플래그가 포화 단계 출력에 전수 보존되고, (b) 경계 밴드 W_band가 완충 가중 대상으로 표시되며, (c) 복원 금지 사후조건(포화 화소값 불변 · SATURATION 유지 · INTERPOLATION 신규 미설정[기존 보존])이 성립함을 판정 가능하다(XDET-TC-008 EV-106 min의 T3 게이트 범위 = 마스크 통합·경계 밴드·복원 금지 메커니즘). 최종 경계 아티팩트 비가시(denoiser·대비 후 종단 판정)는 T5/T6 의존으로 T3 범위 밖이다(spec 「결정 필요/확인 사항」 4).

### Scenario 9 — 기하 잔차 (REQ-LNSG-VALIDATE-5, REQ-LNSG-GEOM-2)
- **Given** (a) 이상 격자에 기지 저차 다항 왜곡(격자선 변위, 잔차 ≥ EV-106 min)을 주입한 격자 팬텀 + 대응 왜곡 모델 CalibSet(OTHER), 그리고 (b) 잔차 < EV-106 min인 왜곡 미미 격자 팬텀, 두 종류와 외부 주입 EV-106 min(≤1px) 임계가 주어져 있다.
- **When** 기하 보정을 적용하고 `tests/`에서 보정 후 격자선 위치(centroid) 대 이상 격자 위치의 변위를 산출한다.
- **Then** (a)는 보정 후 격자선 잔차가 EV-106 min(≤1px) 이내임을 판정 가능하고, (b)는 모듈이 비활성(무처리 통과)되어 입력이 왜곡 보정 없이 반환됨을 관측 가능하다(XDET-TC-009; GEOM-2 결정론적 활성/비활성 경계).

### Scenario 10 — 공통 모듈 계약 준수 (REQ-LNSG-CONTRACT-1, -2, -3, -6)
- **Given** 세 모듈(line_noise/saturation/geometry)과 harness fixture(합성 입력 + 기대 출력)가 주어져 있다.
- **When** `common.contract.check_process_contract` / `run_harness`와 import-linter 정적 검사가 실행된다.
- **Then** 각 모듈은 `process(frame, calib, params) -> XFrame` 시그니처·반환형을 만족하고, 입력 XFrame 불변·이력 체인 갱신·전체 XFrame 비교(pixel·마스크·노이즈·이력)를 통과하며, 의존 방향은 `module → common` 단방향(모듈 간·`metrics`·`pipeline` import 0건)이다. 세 모듈은 `CANONICAL_ORDER`의 line_noise → saturation → geometry 부분수열로만 등록된다.

## Optional 요구 조건부 인수 기준 (WHERE 해당 입력이 제공되면)

### Scenario 11 — Line noise 레퍼런스 경로 (REQ-LNSG-LINE-2, Optional)
- **Given** 패널 비조사/차폐 reference 영역 좌표([B], SWR-501)를 담은 CalibSet(LINE_NOISE)와 오염 배제 계수 k(SWR-502 명시값 6, Params 주입) 입력.
- **When** WHERE 해당 reference 영역이 제공되면, 시스템이 행 r의 reference 픽셀 중앙값 m(r)을 행 전체에서 감산하고, |m(r) − median(m)| > k·MAD인 행은 인접 행 보간값을 사용한다.
- **Then** 레퍼런스 기반 행 단위 보정이 적용되고, 금속 구조물·직접선 오염 행은 인접 행 보간으로 배제된다(SWR-502). reference 영역 미제공 시 본 기준은 적용되지 않으며 우선 경로(Scenario 1, SWR-503)를 사용한다.

### Scenario 12 — 기하 보정 조건부 활성 (REQ-LNSG-GEOM-1, Optional)
- **Given** 격자 팬텀 캘리브레이션 저차 다항 왜곡 모델(차수 [B], 2-6)을 담은 CalibSet(OTHER, geometry 단계)과 그 캘리브레이션 잔차(≥ EV-106 min) 입력.
- **When** WHERE 해당 왜곡 모델이 제공되고 캘리브레이션 잔차가 EV-106 min 이상이면, 시스템이 다항 왜곡 모델로 기하 보정을 적용한다.
- **Then** 보정 후 잔차가 EV-106 min 이내로 낮아진다(Scenario 9a). 왜곡 모델 미제공 또는 잔차 < EV-106 min이면 본 기준은 적용되지 않으며 모듈 비활성(무처리 통과, GEOM-2/Scenario 9b)이다.

## Edge Cases (부정/경계 케이스)

### EC-1 — CalibSet 부재/불일치 게이트 거부 (REQ-LNSG-CONTRACT-5)
- **Given** line_noise/saturation/geometry 단계 중 하나에서 CalibSet이 부재하거나 불일치(해상도 · 패널 ID 상호불일치 · 유효기간 밖, 그리고 line_noise 단계는 kind≠LINE_NOISE)한 입력.
- **When** 오케스트레이터 진입 게이트(`_calibration_gate`)가 실행된다.
- **Then** 처리를 거부하고 위반 단계·필드를 명시한 `CalibrationError`를 발생시킨다(무단 기본값 대체 없음). saturation/geometry는 `_KIND_BY_STAGE` 미등재로 종류 강제는 없으나(CalibKind.OTHER 허용) 존재·해상도·패널 ID·유효기간 위반은 거부된다.

### EC-2 — 포화 복원 금지 사후조건 (REQ-LNSG-SAT-3)
- **Given** 포화 화소(SATURATION 플래그; 일부는 상류 defect 단계가 설정한 INTERPOLATION 플래그와 공존)를 포함하는 입력과, 포화 아래 값 생성을 유발할 수 있는 처리 경로.
- **When** 포화 모듈이 실행된다.
- **Then** 포화 화소는 무단 "복원"되지 않고 다음 사후조건을 정확히 만족한다: (1) 화소값이 입력과 동일하게 보존되고, (2) SATURATION 플래그가 유지되며, (3) 포화 처리가 INTERPOLATION 플래그를 새로 설정하지 않는다(입력에 이미 존재하던 플래그는 보존 — 상류 defect 단계 INTERPOLATION과 SATURATION의 적법 공존)(허위 신호 생성 금지, SWR-602 [HARD]). 조건부 복원 분기 없음.

### EC-3 — Line noise 마스크 제외 미준수 부정 대조 (REQ-LNSG-LINE-3)
- **Given** 구조물·결함·포화 화소가 reference/프로파일 통계 영역에 겹치는 입력.
- **When** line noise 보정이 강건 통계를 산출한다.
- **Then** 마스크 제외를 적용하지 않으면 오염 화소가 프로파일·행 중앙값을 편향시켜 오보정을 유발함을(부정 대조) 확인하고, 모듈이 DEFECT · INTERPOLATION · SATURATION 화소를 제외 가중하여 이를 방지함을 판정 가능하다.

### EC-4 — 사이드채널 / 의존 위반 (REQ-LNSG-CONTRACT-4, -3)
- **Given** 입력 XFrame 변경을 시도하거나 부가 반환값(튜플)으로 산출물을 전달하거나 `modules/`·`pipeline`·`metrics`를 import하는 위반 코드가 있다.
- **When** XFrame 불변 검사(읽기 전용 버퍼) · 계약 검사(`check_process_contract`/`run_harness` 반환형) · import-linter 정적 검사가 실행된다.
- **Then** 입력 변경은 read-only 버퍼로 차단·검출되고, 부가 반환값·시그니처 위반은 계약 검사로 FAIL하며, 의존 위반은 import-linter로 열거되어 FAIL한다.
- **참고** 전역 상태·파일 우회 금지는 자동 검출 대상이 아닌 설계 규칙으로 코드 리뷰 게이트에서 다룬다(REQ-LNSG-CONTRACT-4 자동 검출 범위 밖 — 본 EC의 검증 범위는 XFrame 읽기 전용 + 계약 검사 + import-linter로 한정, SPEC-INFRA-001 EC-4 방식 계승).

## 품질 게이트 / Definition of Done

- [ ] `modules/` 패키지 배치(line_noise · saturation · geometry), `module → common` 단방향 import-linter 계약 통과(모듈 간 · `metrics` · `pipeline` import 0건)
- [ ] 세 모듈 `process(XFrame, CalibSet, Params) -> XFrame` 시그니처·반환형·입력 불변·이력 체인(모듈 버전·파라미터 해시·CalibSet ID) — `run_harness` XDET-TC-000 통과(Scenario 10)
- [ ] line noise: SWR-503 우선 경로 열 프로파일 감산 + 고역 제한(Scenario 1) + 마스크 제외·노이즈 모델 미갱신(Scenario 2) + (Optional) 레퍼런스 경로 6·MAD 오염 배제(Scenario 11)
- [ ] 포화: offset(raw≥S_th, REQ-CORR-OFFSET-4) ∪ gain 클램프 누적 SATURATION 마스크 소비·하류 전달(Scenario 3) + 경계 밴드 완충 가중 표시(Scenario 4) + 포화 통계 이력 메타(Scenario 5) + 복원 금지 사후조건(값 불변·SATURATION 유지·INTERPOLATION 신규 미설정[기존 보존], EC-2)
- [ ] 기하: 다항 왜곡 보정 조건부 활성(Scenario 12) + 잔차 < EV-106 min 비활성(Scenario 9b, GEOM-2 결정론적 경계)
- [ ] 파라미터 등급 정합(SWR 부록 A): reference 좌표(SWR-501)=[B], SWR-503 창/컷오프=[T], SWR-503 방법=[C], S_th(SWR-601, offset 단계 `raw_saturation_threshold`)=[B], 다항 차수(SWR-603)=[B]; 6·MAD 계수·2px 밴드폭=부록 A 미등재(Params 외부화, 등재 필요) — 전부 Params/CalibSet 외부화, 하드코딩 0건
- [ ] CalibSet 부재/불일치(해상도·패널 ID·유효기간·line_noise 종류-단계 배선) 게이트 거부(EC-1)
- [ ] line noise 마스크 제외 부정 대조 확인(EC-3), 사이드채널·의존 위반 검출(EC-4)
- [ ] Optional 경로: 레퍼런스 line noise(Scenario 11)·기하 보정(Scenario 12) — WHERE 입력 제공 시 적용, 미제공 시 우선 경로/비활성
- [ ] 왜곡 억제 판정: line noise 이상 피크 제거(Scenario 6, XDET-TC-006, `detect_line_noise`) + 구조물 오보정률 ≤ EV-105 min(Scenario 7, XDET-TC-007, ground truth 대조) + 포화 마스크 통합/경계 밴드/복원 금지(Scenario 8, XDET-TC-008 T3 부분 게이트) + 기하 잔차 ≤ EV-106 min(Scenario 9, XDET-TC-009, 격자선 대조) — line noise는 metrics 엔진 소비(tests/)
- [ ] EV-105/106 min/typ/max 판정 수치 엔진·모듈 미내장 — 외부 주입 확인(측정=판정 분리)
- [ ] XDET-TC-006 · XDET-TC-007 · XDET-TC-008 · XDET-TC-009 skeleton(skip) → 합성 입력·판정 연동 실동작 케이스 전환·통과
- [ ] **합성 주입 왜곡 3모듈 억제·처리 PASS + EV-105/106 min 판정 + 포화 복원 금지 사후조건 성립** — DoD
- [ ] spec 「결정 필요/확인 사항」 1·3·4·5·6 run 착수 전 확인(경로 선택·게이트, 경계 밴드 표현, 포화 비가시 게이트 범위, 오보정률 경로, 부록 A 등재) — 항목 2(raw 포화 검출 단계)는 결정 확정(offset REQ-CORR-OFFSET-4)
