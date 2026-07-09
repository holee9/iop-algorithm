# SPEC-POST-001 인수 기준 (acceptance.md)

T6(WP6 MSE/DRC + WP7 자동 윈도잉/GSDF)의 인수 기준. 근거: [spec.md](./spec.md) · 계획: [plan.md](./plan.md).

**판정 원칙**: EV 임계(EV-205/204 GSDF 적합/EV-102 min 가드레일) 및 GSDF 적합 임계 `ε_gsdf`·윈도우 정합 허용오차·IQA 대리 임계는 EVAL v1.1/Params에서 **외부 주입**된다(측정=판정 분리). 처리 모듈·판정 코드는 임계를 내장하지 않는다. 모듈은 `metrics`를 import하지 않으므로 MTF 가드레일 판정은 `tests/`에서 모듈 + 지표 엔진을 함께 소비하고, 윈도우 정합·GSDF PS3.14 편차는 기지값·표준 대조 직접 측정으로 판정한다. **XDET-TC 매핑은 TestSpec v1.0을 단일 출처로 채택한다**(XDET-TC-012=MSE/DRC IQA 비열화, XDET-TC-013=자동 윈도우 수용률, XDET-TC-014=GSDF LUT PS3.14 적합).

**게이트 정직성**: T6의 결정론적 이진 하드 게이트는 **XDET-TC-014(GSDF PS3.14 적합)** 하나이다. XDET-TC-012(IQA 비열화)·XDET-TC-013(윈도우 수용률)은 지각·관찰자 의존 지표로, P1은 합성 기지값·객관 대리 지표로 **PARTIAL 게이트** 판정하고 실 관찰자 평가(EV-204)는 인허가 이연이다(T5 EV-101/T3 EV-106 PARTIAL 선례).

**커버리지 노트**: REQ-POST-VALIDATE-1(합성 검증 컨텍스트 전제)은 Scenario 1~3으로, 각 처리 요구(MSE/DRC/WINDOW/GSDF/CONTRACT)는 Scenario 4~14 및 EC-1~7로 충족된다. REQ-POST-WINDOW-4(VOI → P-value 재매핑, GSDF 트리거 상류)는 Scenario 11로 GSDF와 양방향 검증된다. Optional 요구(REQ-POST-MSE-5 soft-clip, REQ-POST-WINDOW-3 수동 오버라이드)는 각각 조건부 Scenario 6·10으로 분리 검증된다.

## Given-When-Then 시나리오

### Scenario 1 — GSDF LUT PS3.14 적합성 [하드 DoD, XDET-TC-014] (REQ-POST-VALIDATE-2, GSDF-1/2)
- **Given**: 파라미터화된 디스플레이 특성(최소/최대 휘도, Params)과 외부 주입 임계 `ε_gsdf`([S]-인접).
- **When**: P-value → PS3.14 GSDF JND 인덱스 매핑 LUT를 구성하고 JND당 대비 응답 편차를 산출한다.
- **Then**: JND당 대비 응답 편차 최댓값이 `ε_gsdf` 이내임을 `tests/`에서 결정론적으로 이진 판정한다(PS3.14 적합). 편차 지표가 `HistoryEntry.extra`에 기록되고 `ε_gsdf`는 외부 주입(내장 없음)임을 확인한다.

### Scenario 2 — 자동 윈도우 정합률 [XDET-TC-013, PARTIAL] (REQ-POST-VALIDATE-3, WINDOW-1)
- **Given**: 기지 VOI [p_low, p_high]를 주입한 부위별 합성 팬텀 세트, 외부 주입 윈도우 정합 허용오차([T])·EV-205 min.
- **When**: 자동 윈도잉을 적용한다.
- **Then**: 자동 산출 윈도우가 기지값 허용오차 내에 드는 비율(무수정 수용 대리 지표)을 `tests/`에서 산출하여 EV-205 min(≥85%) 이상임을 판정한다. 실 관찰자 무수정 수용률은 인허가/실측 이연(PARTIAL)임을 명시한다.

### Scenario 3 — MSE/DRC IQA 비열화 [XDET-TC-012, PARTIAL] (REQ-POST-VALIDATE-4)
- **Given**: 골/연부 이중 분포 기지 해부 히스토그램 합성 팬텀, 기지 (α, σ), 외부 주입 EV-102 min·절대 IQA 대리 임계, 최초 기준선 스냅샷(절대 IQA 임계 + EV-102 가드레일 선통과 후 `tests/fixtures` 커밋, 「결정 필요/확인 사항」 6).
- **When**: MSE/DRC 전 구간을 적용한다.
- **Then**: `tests/`에서 (a) 객관 IQA 대리 지표(로컬 대비 개선율·세부대역 에너지 보존·halo/overshoot/클리핑 부재)가 기준선 스냅샷 대비 비열화이고, (b) 가드레일로 `metrics/mtf.compute_mtf`/`mtf_value_at` MTF@Nyquist 유지율이 EV-102 min(≥90%) 이상임을 판정한다. 지각 IQA·관찰자 평가(EV-204)는 인허가 이연(PARTIAL)임을 명시한다.

### Scenario 4 — Laplacian 피라미드 분해/재합성 (REQ-POST-MSE-1)
- **Given**: 합성 입력 XFrame과 Params로 주입된 레벨 수 L(=7 @3072 기준)·Gaussian 커널(5×5 [1 4 6 4 1]/16).
- **When**: `common/pyramid.py`로 피라미드 분해 후 무변조 재합성한다.
- **Then**: 공용 컴포넌트 `common/pyramid.py`(T0 스텁 최초 구현)가 분해/재합성을 담당하고(중복 구현 없음, SWR-000-9 ①), 무변조 재합성이 입력을 수치 허용오차 내 복원함을 harness 시험으로 확인한다.

### Scenario 5 — 대역 변조 + 노이즈 게이팅 (REQ-POST-MSE-2/3)
- **Given**: 유효 (α, σ)를 담은 입력 XFrame.noise와 Params로 주입된 레벨별 γ_ℓ·p_ℓ([T])·게이트 β([T]).
- **When**: 레벨 계수에 power-law 변조 c′=γ_ℓ·sign(c)·|c|^p_ℓ와 노이즈 게이트 g=c²/(c²+β·σ_ℓ²)를 적용한다.
- **Then**: γ_ℓ·p_ℓ·β가 Params에서 주입되고(하드코딩 없음), σ_ℓ이 입력 XFrame.noise (α, σ) 전파로 산출되며, 노이즈 미만 계수의 증폭이 억제됨을 harness 시험으로 확인한다(SWR-802/803).

### Scenario 6 — soft-clip 대안 함수형 [조건부/Optional] (REQ-POST-MSE-5)
- **Given**: WHERE Params가 SWR-802 대안 변조 함수형(soft-clip 계열, ⚠P)을 선택한 경우.
- **When**: MSE 대역 변조를 적용한다.
- **Then**: power-law 대신 soft-clip 함수형이 동일한 노이즈 게이팅·DRC·정규화 계약 하에서 적용되고 경로 선택이 Params 값으로 결정론적으로 이뤄짐을 확인한다. 미선택 시 본 시나리오는 적용되지 않으며 REQ-POST-MSE-2(power-law 기본형)를 사용한다. 특허 클리어런스는 P1 밖(릴리스 게이트).

### Scenario 7 — 노이즈 모델 부재·퇴화 거부 (REQ-POST-MSE-4, Unwanted)
- **Given**: `mse` 단계 입력 XFrame.noise가 부재하거나 α ≤ 0, 또는 기본값 (0, 0)만 존재하는 입력.
- **When**: `mse` 처리를 시도한다.
- **Then**: 시스템이 SWR-803 노이즈 게이팅을 무단 기본값으로 수행하지 않고 명시 오류로 거부한다(결정론적 단일 경로, SWR-000-5). 정상 파이프라인에서는 T5 CONTRACT-2가 (α, σ)를 기록하므로 항상 존재함을 확인한다.

### Scenario 8 — DRC + 재합성 + 범위 정규화 (REQ-POST-DRC-1/2)
- **Given**: 피라미드 최저역 B와 Params로 주입된 γ_DRC(<1)·B_mid, SATURATION·SATURATION_BAND 플래그 포함 입력.
- **When**: DRC 압축 B′=B_mid+(B−B_mid)·γ_DRC 적용 후 세부대역과 재합성하고 [p0.1, p99.9] 백분위 범위 정규화("선형 컷오프")한다.
- **Then**: 골/연부 동시 가시화를 조작적으로 — **최저역 동적범위 압축률 > 0**(압축이 실제 적용됨) ∧ **세부대역 에너지 보존율 ≥ 외부 주입 임계**(세부 보존) — 로 판정하고, 백분위 산출이 포화 마스크 화소를 제외함을(`common/robust_stats`·`common/mask_ops` 소비) harness 시험으로 확인한다.

### Scenario 9 — 자동 윈도잉 3단계 + 부위 프리셋 (REQ-POST-WINDOW-1/2)
- **Given**: 조사야 경계·직접선 영역·해부 히스토그램을 포함한 부위별 합성 팬텀과 부위 프리셋 테이블.
- **When**: 조사야 인식 → 직접선 분리 → 유효 해부 히스토그램 VOI 산출을 수행한다.
- **Then**: ①② 단계가 `common/histogram_fov.py`(T1 확장) 소비로 조사야 외·직접선 영역을 히스토그램에서 제외하고(SWR-901), 부위 프리셋 [p_low, p_high]가 선택되며(SWR-902), 조사야/직접선이 단계 내부 산출로 신규 마스크 플래그를 도입하지 않음을 확인한다(확인 5).

### Scenario 10 — 수동 윈도우 오버라이드 [조건부/Optional] (REQ-POST-WINDOW-3)
- **Given**: WHERE 수동 오버라이드 [p_low, p_high]가 Params로 제공된 경우.
- **When**: `window` 처리를 적용한다.
- **Then**: 자동 VOI 대신 오버라이드가 사용되고 오버라이드 발생이 `HistoryEntry.extra`에 기록됨을(EV-205 개선 입력) 확인한다. 오버라이드 미제공 시 본 시나리오는 적용되지 않으며 REQ-POST-WINDOW-1 자동 VOI를 사용한다.

### Scenario 11 — VOI 윈도우 → P-value 재매핑 (REQ-POST-WINDOW-4)
- **Given**: 기지 유효 신호 분포와 확정 VOI [p_low, p_high](자동 산출 또는 오버라이드)를 담은 합성 입력, 기지 입력에 대응하는 기대 P-value·기대 GSDF JND 인덱스 참조값.
- **When**: 유효 신호를 [p_low, p_high] 윈도우로 P-value에 재매핑하고, 그 P-value를 후속 GSDF LUT(REQ-POST-GSDF-1)에 입력한다.
- **Then**: 기지 입력에 대한 산출 P-value가 기대 P-value 참조값과 수치 허용오차 내에서 일치하고, 그 P-value가 REQ-POST-GSDF-1의 WHEN 트리거를 산출하여 GSDF JND 인덱스 출력이 기대 JND 참조값과 수치 대조됨을 `tests/`에서 확인한다(REQ-POST-WINDOW-4 → REQ-POST-GSDF-1 양방향 추적, 기지 입력→기대 P-value/JND 출력 수치 대조).

### Scenario 12 — GSDF LUT 구성 + 적합 자가검사 기록 (REQ-POST-GSDF-1/2)
- **Given**: 파라미터화된 디스플레이 특성(최소/최대 휘도)과 윈도우 적용 P-value.
- **When**: GSDF JND 매핑 LUT를 구성한다.
- **Then**: LUT가 디스플레이 특성으로부터 결정론적으로 구성되고(감사 가능), JND당 대비 응답 편차 자가검사 지표가 `HistoryEntry.extra`에 기록됨을 확인한다(합격 임계 `ε_gsdf`는 외부 주입, Scenario 1에서 판정).

### Scenario 13 — 모듈 계약 준수 (REQ-POST-CONTRACT-1/2/3)
- **Given**: 합성 입력 XFrame.
- **When**: `mse`·`window` 모듈이 각각 `process(XFrame, CalibSet, Params) -> XFrame`으로 처리한다.
- **Then**: 입력 XFrame이 불변으로 유지되고(원본 미변경), 이력 체인에 처리 메타 + 스칼라 진단(γ_ℓ/p_ℓ 요약·β·γ_DRC·정규화 범위·VOI·오버라이드·GSDF JND 편차, `HistoryEntry.extra`)이 추가되며, import-linter가 `modules → common` 단방향(다른 모듈·pipeline·metrics 미import)을 KEEP함을 확인한다.

### Scenario 14 — 진입 게이트 + 스테이지 배치 (REQ-POST-CONTRACT-5, 결정 1)
- **Given**: `mse`·`window` 스테이지가 CalibSet(OTHER, 해상도·패널 ID·유효기간 일치)로 등록된 파이프라인.
- **When**: 오케스트레이터가 처리를 실행한다.
- **Then**: 두 스테이지가 `CANONICAL_ORDER`의 전용 `mse`·`window` 위치(denoise와 post 사이)에서만 실행되고(등록 stages = 부분수열), `_KIND_BY_STAGE` 미등재로 종류-단계 강제 없이 CalibSet(OTHER)로 게이트를 충족하며, CalibSet 부재·해상도·패널 불일치 시 진입 게이트가 명시 오류로 거부함을 확인한다.

## 엣지 케이스

- **EC-1 (GSDF 경계 휘도)** — 디스플레이 최소/최대 휘도 극단(저휘도·고휘도) 특성에서 GSDF LUT의 JND당 편차가 `ε_gsdf` 이내로 유지됨을 확인한다(Scenario 1 보강).
- **EC-2 (조사야 미인식·전면 노출)** — 조사야 경계가 없는 전면 노출 팬텀에서 조사야 인식이 전체 프레임을 유효 영역으로 처리하고 VOI 산출이 발산·오류 없이 통과함을 확인한다(SWR-901 ①단계 신설 취지).
- **EC-3 (직접선 오염 히스토그램)** — 직접선(비차폐) 영역이 큰 팬텀에서 직접선 분리 실패 시 배경이 히스토그램을 오염시켜 윈도우가 오산출되는지 대조하고, 분리 후 VOI 정합률이 회복됨을 확인한다(SWR-901 ②단계 취지).
- **EC-4 (포화 화소 정규화 제외)** — SATURATION·SATURATION_BAND 화소가 집중된 팬텀에서 [p0.1, p99.9] 백분위가 포화 화소를 제외해 정규화 범위가 포화값에 끌려가지 않음을 확인한다(REQ-POST-DRC-2).
- **EC-5 (사이드채널 자동 검출 범위)** — 계약 위반 자동 검출 범위는 시그니처·부가 반환값 위반(계약 검사)과 의존 방향 위반(import-linter)이며, 전역 상태·파일 우회는 코드 리뷰 게이트로 다룸을 명시한다(REQ-POST-CONTRACT-4, SPEC-INFRA-001 DATA-2 방식).
- **EC-6 (마스크 substrate 불변·포화 미복원)** — `mse`·`window` 출력이 어떤 마스크 플래그도 신규 설정·해제하지 않고 포화 화소 값을 재구성하지 않음을 확인한다(REQ-POST-CONTRACT-6, SWR-602 [HARD] 복원 금지 계승).
- **EC-7 (MSE 강증폭 MTF 경계)** — power-law 증폭이 강한 프리셋에서 MTF@Nyquist 유지율이 EV-102 min 경계에 근접·초과하는지 특성화하고, 노이즈 게이팅이 소신호 과증폭을 억제함을 대조로 확인한다(Scenario 3 보강).

## 품질 게이트 (TRUST 5)

- **Tested**: XDET-TC-012·013·014가 pytest skeleton(skip) → 실동작 케이스로 전환, harness 단독 시험(합성 입력 + 기대 출력 fixture) 통과. 커버리지 ≥ 85%.
- **Readable**: 명확한 명명(영문 식별자)·피라미드/변조/노이즈 게이팅/DRC/윈도잉/GSDF 단계 주석(SWR 대응).
- **Unified**: ruff/black 통과, 기존 `modules/` 처리 모듈 패턴 일관.
- **Secured**: 입력 검증(XFrame.noise 부재·퇴화 거부), 무단 기본값 대체 금지, 마스크 substrate 불변.
- **Trackable**: 이력 체인 메타 + `HistoryEntry.extra` 진단, 커밋 SWR/REQ 참조, 이슈 #7.

## 완료 정의 (Definition of Done)

- [ ] **[하드 DoD]** Scenario 1 + EC-1: GSDF LUT JND당 대비 응답 편차 최댓값 ≤ `ε_gsdf`([S]-인접), PS3.14 적합 결정론 이진 판정 (XDET-TC-014).
- [ ] **[PARTIAL]** Scenario 2 + EC-2/EC-3: 자동 윈도우 정합률(기지 VOI 허용오차 내) ≥ EV-205 min, 실 관찰자 수용률 인허가 이연 (XDET-TC-013).
- [ ] **[PARTIAL]** Scenario 3 + EC-7: MSE/DRC IQA 대리 비열화(기준선 스냅샷 대비) + MTF@Nyquist 유지율 ≥ EV-102 min 가드레일, 지각 IQA·관찰자 EV-204 인허가 이연 (XDET-TC-012).
- [ ] Scenario 4: Laplacian 피라미드 분해/재합성 `common/pyramid.py` 최초 구현(무변조 재합성 복원) (REQ-POST-MSE-1).
- [ ] Scenario 5: power-law 변조 + 노이즈 게이팅(γ_ℓ·p_ℓ·β Params 주입, σ_ℓ XFrame.noise 전파) (REQ-POST-MSE-2/3).
- [ ] Scenario 6: soft-clip 대안 함수형 조건부 동작(선택 시, ⚠P) (REQ-POST-MSE-5).
- [ ] Scenario 7: XFrame.noise 부재·퇴화 거부 (REQ-POST-MSE-4).
- [ ] Scenario 8 + EC-4: DRC 압축·재합성·[p0.1, p99.9] 정규화(포화 마스크 제외) (REQ-POST-DRC-1/2).
- [ ] Scenario 9: 자동 윈도잉 3단계(조사야→직접선→VOI) + 부위 프리셋(`common/histogram_fov.py` 확장) (REQ-POST-WINDOW-1/2).
- [ ] Scenario 10: 수동 오버라이드 조건부 동작·오버라이드율 기록 (REQ-POST-WINDOW-3).
- [ ] Scenario 11: VOI 윈도우 → P-value 재매핑, 기지 입력 대비 기대 P-value/JND 출력 수치 대조(REQ-POST-WINDOW-4 → REQ-POST-GSDF-1 양방향 추적) (REQ-POST-WINDOW-4).
- [ ] Scenario 12: GSDF LUT 결정론 구성·적합 자가검사 `HistoryEntry.extra` 기록 (REQ-POST-GSDF-1/2).
- [ ] Scenario 13 + EC-5/EC-6: 모듈 계약(불변·이력·레이어링·사이드채널 범위)·마스크 substrate 불변·포화 미복원 (REQ-POST-CONTRACT-1/2/3/4/6).
- [ ] Scenario 14: 전용 `mse`·`window` 스테이지(denoise와 post 사이)·CalibSet(OTHER) 빈 placeholder 진입 게이트 (REQ-POST-CONTRACT-5, 결정 1·2 확정).
- [ ] EV/`ε_gsdf`/윈도우 허용오차/IQA 대리 임계 외부 주입 확인, 임계 내장 없음 (REQ-POST-VALIDATE-5).
- [ ] XDET-TC-012·013·014 pytest skeleton(skip) → 합성 입력·판정 연동 실동작 케이스 전환 (REQ-POST-VALIDATE-6).
- [ ] 「결정 필요/확인 사항」 1(run-blocking)·2 plan-audit iter1 확정(RESOLVED) + HISTORY 반영.
- [ ] import-linter 레이어링 계약 KEEP, 전체 회귀 통과.
