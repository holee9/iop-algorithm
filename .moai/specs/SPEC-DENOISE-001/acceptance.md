# SPEC-DENOISE-001 인수 기준 (acceptance.md)

T5(WP5) VST+BM3D 노이즈 저감의 인수 기준. 근거: [spec.md](./spec.md) · 계획: [plan.md](./plan.md).

**판정 원칙**: EV 임계(EV-201/102; EV-101 DQE 변화는 T5 게이트 외 — spec.md Exclusions, 맥락 인용) 및 VST 편향 임계 `ε_unbias`·정규화 하한 `λ_floor`는 EVAL v1.1/Params에서 **외부 주입**된다(측정=판정 분리). 처리 모듈·판정 코드는 임계를 내장하지 않는다. 모듈은 `metrics`를 import하지 않으므로 SNR/MTF/NPS 판정은 `tests/`에서 모듈 + 지표 엔진을 함께 소비하고, VST 왕복 편향은 기지 λ 대조 직접 측정으로 판정한다. **XDET-TC 매핑은 TestSpec v1.0을 단일 출처로 채택한다**(XDET-TC-010=denoising 성능, XDET-TC-011=VST 왕복 무편향 — spec.md 「결정 필요/확인 사항」 4).

**커버리지 노트**: REQ-DENOISE-VALIDATE-1(합성 검증 컨텍스트 전제)은 Scenario 1~2·10으로, 각 처리 요구(VST/INV/BM3D/CONTRACT/VALIDATE)는 Scenario 3~12 및 EC-1~6으로 충족된다. **REQ-DENOISE-BM3D-1(BM3D 코어 denoiser)은 Scenario 6으로 전담 검증**되고, BM3D-2(마스크 제외)=Scenario 7, BM3D-3(프리셋)=Scenario 8, BM3D-4(NLM)=Scenario 9로 분리된다.

## Given-When-Then 시나리오

### Scenario 1 — VST 왕복 무편향성 [하드 DoD, XDET-TC-011] (REQ-DENOISE-VALIDATE-2, INV-1)
- **Given**: 기지 평균 λ_j(저계수~고계수 sweep, 저계수 영역 포함)·기지 (α, σ)의 합성 Poisson-Gaussian 패치 세트와 외부 주입 임계 `ε_unbias`·정규화 하한 `λ_floor`([T]).
- **When**: 각 패치에 GAT 순변환 → exact unbiased LUT 역변환을 **denoiser 우회**로 적용한다.
- **Then**: 각 준위의 편향 지표 `bias(λ_j) = |mean(왕복출력) − λ_j|`를 산출하고 그 정규화 최댓값 `max_j bias(λ_j)/max(λ_j, λ_floor)`가 `ε_unbias` 이내임을 `tests/`에서 이진 판정한다(편차 임계 내). 정규화 기준은 상대 편향 `bias(λ)/max(λ, λ_floor)`로 확정한다(저계수 λ 나눗셈 발산 방지, spec.md 「결정 필요/확인 사항」 7·D2).

### Scenario 2 — denoising 성능(SNR 개선 + MTF 유지) [XDET-TC-010] (REQ-DENOISE-VALIDATE-3)
- **Given**: 기지 clean 영상 + 저선량 Poisson-Gaussian 노이즈 주입 합성 세트(GDS-임상 모사), 외부 주입 EV-201/102 min.
- **When**: VST+BM3D 전 구간을 적용한다.
- **Then**: `tests/`에서 (a) 균일 ROI SNR 개선율을 `metrics/ndt.compute_snr`로 산출하여 EV-201 min(≥ +20%) 이상, (b) 엣지 MTF@Nyquist 유지율·SRb 열화를 `metrics/mtf.compute_mtf`/`mtf_value_at`로 산출하여 EV-102 min(유지율 ≥ 90%, SRb 열화 ≤ 10%) 이내임을 판정한다(노이즈 저감이 MTF를 EV 한계 이상으로 파괴하지 않음).

### Scenario 3 — GAT 순변환 + 노이즈 모델 소비 (REQ-DENOISE-VST-1)
- **Given**: 유효 (α, σ)를 담은 denoise 단계 CalibSet와 합성 입력 XFrame.
- **When**: denoise 모듈이 처리한다.
- **Then**: GAT 순변환 `f(z)=(2/α)·√(α·z + (3/8)·α² + σ²)`이 적용되고 근호 인자 정의역 미만 화소가 0으로 클램프됨을 harness 시험으로 확인한다.

### Scenario 4 — 노이즈 모델 부재·퇴화 거부 (REQ-DENOISE-VST-2, Unwanted)
- **Given**: denoise 단계에 유효 (α, σ)가 없거나 α ≤ 0, 또는 XFrame `NoiseModel` 기본값 (0, 0)만 존재하는 입력.
- **When**: denoise 처리를 시도한다.
- **Then**: 시스템이 GAT를 무단 기본값으로 수행하지 않고 명시 오류로 거부한다(결정론적 단일 경로, SWR-000-5).

### Scenario 5 — 점근 역변환 금지 (REQ-DENOISE-INV-2, Unwanted)
- **Given**: GAT 영역 처리 결과.
- **When**: 원 신호 영역으로 복귀시킨다.
- **Then**: exact unbiased LUT 역변환만 사용되고 점근/대수 역변환((f/2)² 계열) 경로가 코드에 부재함을 확인한다(결정론적 단일 경로).

### Scenario 6 — BM3D 코어 denoiser(원저 파라미터 + σ_BM3D 배선) (REQ-DENOISE-BM3D-1)
- **Given**: GAT 순변환으로 단위분산 안정화된 합성 입력과 Params로 주입된 BM3D 원저 파라미터(블록 8×8, step 3, N2=16, Ns=39, λ_3D=2.7, Haar, Kaiser β=2.0) 및 강도 계수 k_s([P]).
- **When**: BM3D 2단계(hard-threshold + Wiener) denoiser를 적용한다.
- **Then**: 원저 파라미터가 Params에서 주입되고(하드코딩 없음), 잡음 표준편차가 σ_BM3D = 1(GAT 후 단위분산) × k_s로 배선되며(k_s 변경이 σ_BM3D에 반영됨), 코어가 자체 순수 numpy/scipy 골든 구현(신규 의존성 없음, 결정 3)임을 harness 시험으로 확인한다.

### Scenario 7 — 마스크 제외 가중 (REQ-DENOISE-BM3D-2)
- **Given**: DEFECT·INTERPOLATION·SATURATION·SATURATION_BAND 플래그가 설정된 화소를 포함한 합성 입력.
- **When**: BM3D 블록 매칭을 수행한다.
- **Then**: 해당 화소가 블록 매칭 가중에서 제외되고, denoise 출력이 어떤 마스크 플래그도 신규 설정·해제하지 않음을 확인한다(마스크 substrate 상류 소관).

### Scenario 8 — 강도 프리셋 특성화 (REQ-DENOISE-BM3D-3, VALIDATE-4)
- **Given**: 강도 프리셋 k_s ∈ {0.6, 0.8, 1.0}([T]) Params와 저선량 합성 세트.
- **When**: 각 프리셋으로 denoising을 적용한다.
- **Then**: 프리셋별 SRb 열화(및 SNR 개선) 특성화표를 `tests/`에서 산출하여 EV-102 min과 비교 가능함을 확인한다(배제·출하 gating은 P1 범위 밖).

### Scenario 9 — NLM 대체 경로 [조건부/Optional] (REQ-DENOISE-BM3D-4)
- **Given**: WHERE Params가 NLM 대체 denoiser 경로(SWR-704 [C])를 선택한 경우.
- **When**: denoise 처리를 적용한다.
- **Then**: BM3D 대신 NLM이 동일한 VST 순/역변환·마스크 제외 가중 계약 하에서 적용되고 경로 선택이 Params 값으로 결정론적으로 이뤄짐을 확인한다. NLM 미선택 시 본 시나리오는 적용되지 않으며 REQ-DENOISE-BM3D-1(BM3D 코어) 경로가 사용된다.

### Scenario 10 — 오프라인 노이즈 모델 빌더 (REQ-DENOISE-VST-3)
- **Given**: 기지 (α, σ)를 주입한 합성 선량 계단(1–3) 데이터.
- **When**: `metrics/noise_model.py` 빌더가 분산 vs 평균 선형 회귀를 수행한다.
- **Then**: 회귀 기울기 α·절편 σ²가 기지 (α, σ)를 임계 내 재현하고 gain 모드별 CalibSet(`CalibKind.NOISE`)가 방출됨을 확인한다(빌더는 `metrics → common` 단방향).

### Scenario 11 — 모듈 계약 준수 (REQ-DENOISE-CONTRACT-1/2/3)
- **Given**: 합성 입력 XFrame.
- **When**: denoise 모듈이 `process(XFrame, CalibSet, Params) -> XFrame`으로 처리한다.
- **Then**: 입력 XFrame이 불변으로 유지되고(원본 미변경), 이력 체인에 처리 메타 + 스칼라 진단(k_s·클램프율·해결된 (α,σ), `HistoryEntry.extra`)이 추가되고, 해결된 (α, σ)가 출력 XFrame.noise 필드에 기록되며(결정 2), import-linter가 `modules → common` 단방향(다른 모듈·pipeline·metrics 미import)을 KEEP함을 확인한다.

### Scenario 12 — 진입 게이트 거부 (REQ-DENOISE-CONTRACT-5, Unwanted)
- **Given**: denoise 단계 CalibSet가 부재하거나 해상도·패널 ID·유효기간·종류-단계 배선(denoise → `CalibKind.NOISE`)이 불일치하는 파이프라인.
- **When**: 오케스트레이터가 처리를 시도한다.
- **Then**: 진입 게이트가 처리를 거부하고 위반 스테이지·필드를 명시한 오류를 발생시킨다(무단 기본값 대체 금지).

## 엣지 케이스

- **EC-1 (저계수 왕복 편향)** — λ 극단 저계수(예: λ = 1~5 count) 패치에서 exact unbiased 역변환의 `bias(λ)`가 `ε_unbias` 이내임을 확인한다(exact inverse 필요성의 핵심 영역, Scenario 1 보강).
- **EC-2 (점근 역변환 음성 대조)** — 동일 저계수 패치에 점근 역변환을 적용하면 `bias(λ)`가 `ε_unbias`를 초과함을 대조로 보여 exact unbiased 역변환이 load-bearing임을 입증한다. **점근 역변환은 테스트 로컬 참조 수식으로만 계산하며 모듈 경로가 아니다** — 모듈은 REQ-DENOISE-INV-2로 점근 경로를 금지하므로, 음성 대조는 `tests/` 국소 계산으로 수행되어 모듈 금지와 무모순이다(REQ-DENOISE-INV-2 근거).
- **EC-3 (전면 마스크)** — 블록 매칭에 필요한 비마스크 화소가 부족한 영역(포화 집중)에서 denoiser가 발산·오류 없이 통과(입력 보존 근사)함을 확인한다.
- **EC-4 (사이드채널 자동 검출 범위)** — 계약 위반 자동 검출 범위는 시그니처·부가 반환값 위반(계약 검사)과 의존 방향 위반(import-linter)이며, 전역 상태·파일 우회는 코드 리뷰 게이트로 다룸을 명시한다(REQ-DENOISE-CONTRACT-4, SPEC-INFRA-001 DATA-2 방식).
- **EC-5 (k_s 강 프리셋 MTF 경계)** — k_s = 1.0(강)에서 SRb 열화가 EV-102 min 경계에 근접·초과하는지 특성화하여 프리셋 배제 입력으로 기록한다(Scenario 8 보강).
- **EC-6 (GAT 정의역 클램프)** — 근호 인자 `α·z + (3/8)·α² + σ²`가 음수인 화소(극단 음수 잔차)에서 0 클램프가 적용되고 NaN이 전파되지 않음을 확인한다.

## 품질 게이트 (TRUST 5)

- **Tested**: XDET-TC-010·011이 pytest skeleton(skip) → 실동작 케이스로 전환, harness 단독 시험(합성 입력 + 기대 출력 fixture) 통과. 커버리지 ≥ 85%.
- **Readable**: 명확한 명명(영문 식별자)·GAT/역변환/BM3D 단계 주석(SWR 대응).
- **Unified**: ruff/black 통과, 기존 `modules/` 처리 모듈 패턴 일관.
- **Secured**: 입력 검증(노이즈 모델 부재·퇴화 거부), 무단 기본값 대체 금지.
- **Trackable**: 이력 체인 메타 + `HistoryEntry.extra` 진단, 커밋 SWR/REQ 참조, 이슈 #6.

## 완료 정의 (Definition of Done)

- [ ] **[하드 DoD]** Scenario 1 + EC-1/EC-2: VST 왕복 무편향 `max_j bias(λ_j)/max(λ_j, λ_floor) ≤ ε_unbias`([T]), 저계수 포함, 점근 음성 대조(테스트 로컬 참조 수식) 성립 (XDET-TC-011).
- [ ] Scenario 2: SNR 개선 ≥ EV-201 min, MTF@Nyquist 유지율 ≥ EV-102 min, SRb 열화 ≤ EV-102 min (XDET-TC-010).
- [ ] Scenario 3 + EC-6: GAT 순변환·정의역 클램프 (REQ-DENOISE-VST-1).
- [ ] Scenario 4: 노이즈 모델 부재·퇴화 거부 (REQ-DENOISE-VST-2).
- [ ] Scenario 5: exact unbiased LUT 단일 경로·점근 역변환 부재 (REQ-DENOISE-INV-1/2).
- [ ] Scenario 6: BM3D 코어 denoiser 원저 파라미터·σ_BM3D = k_s 배선·Params 주입(하드코딩 없음)·자체 numpy/scipy 구현 (REQ-DENOISE-BM3D-1).
- [ ] Scenario 7 + EC-3: 마스크 제외 가중(DEFECT·INTERPOLATION·SATURATION·SATURATION_BAND)·플래그 불변 (REQ-DENOISE-BM3D-2).
- [ ] Scenario 8 + EC-5: 프리셋별 SRb 열화 특성화표 (REQ-DENOISE-BM3D-3, VALIDATE-4).
- [ ] Scenario 9: NLM 대체 경로 조건부 동작(선택 시) (REQ-DENOISE-BM3D-4).
- [ ] Scenario 10: 오프라인 (α,σ) 빌더 회귀 재현·CalibSet(`CalibKind.NOISE`) 방출 (REQ-DENOISE-VST-3).
- [ ] Scenario 11 + EC-4: 모듈 계약(불변·이력·레이어링·사이드채널 범위)·해결된 (α,σ) 출력 XFrame.noise 기록 (REQ-DENOISE-CONTRACT-1/2/3/4).
- [ ] Scenario 12: 진입 게이트 거부(denoise → `CalibKind.NOISE` 종류-단계) (REQ-DENOISE-CONTRACT-5).
- [ ] denoise 스테이지가 `CANONICAL_ORDER`의 전용 `denoise` 위치(기하와 post 사이)에서만 실행, harness 단독 시험 가능 (REQ-DENOISE-CONTRACT-6).
- [ ] EV/`ε_unbias`/`λ_floor` 임계 외부 주입 확인, 임계 내장 없음 (REQ-DENOISE-VALIDATE-5).
- [ ] 「결정 필요/확인 사항」 1·2·3·5(확정) HISTORY 반영 완료(v0.1.1).
- [ ] import-linter 레이어링 계약 KEEP, 전체 회귀 통과.
