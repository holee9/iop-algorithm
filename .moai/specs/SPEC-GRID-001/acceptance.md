# SPEC-GRID-001 인수 기준 (acceptance.md)

T7(WP8 Grid line suppression)의 인수 기준. 근거: [spec.md](./spec.md) · 계획: [plan.md](./plan.md).

**판정 원칙**: EV 임계(EV-203 잔존 grid line 비가시/Moiré·aliasing 0건, EV-102 min 가드레일) 및 D_th·잔존 피크 유의성 임계는 EVAL v1.1/Params에서 **외부 주입**된다(측정=판정 분리). 처리 모듈·판정 코드는 임계를 내장하지 않는다. 모듈은 `metrics`를 import하지 않으므로 MTF 가드레일 판정은 `tests/`에서 모듈 + 지표 엔진(`metrics/mtf`)을 함께 소비하고, 검출 정확도·잔존 피크·moiré·통과는 기지 grid 주파수 대조 직접 측정으로 판정한다. **XDET-TC 매핑은 TestSpec v1.0을 단일 출처로 채택한다**(XDET-TC-015=Grid 성분 검출 정확도 + 잔존 grid line, XDET-TC-016=Moiré/aliasing 발생 검사 + GLS 실패 무처리 통과).

**게이트 정직성**: T7의 결정론적 이진 하드 게이트는 **XDET-TC-015(관측 스펙트럼 검출 + notch 후 잔존 피크 유의성 이하 + grid 직교축 MTF@Nyquist 유지율 가드레일)**이다. XDET-TC-016의 moiré 저주파 접힘 경계(감쇠 상한 하 잔존 특성화)와 관찰자 "비가시(표준)"(EV-204 계열)는 지각·관찰자 의존으로 **PARTIAL 게이트**이며 관찰자 평가는 인허가 이연이다(T5 EV-101/T6 TC-012 PARTIAL 선례). 무검출 무처리 통과(XDET-TC-016 GLS 실패)는 수치 동일성으로 결정론 판정한다.

**커버리지 노트**: REQ-GRID-VALIDATE-1(합성 검증 컨텍스트 전제, 밀도 3부류)은 Scenario 1~4로, 각 처리 요구(SEARCH/NOTCH/MOIRE/PASSTHROUGH/CONTRACT)는 Scenario 1~10 및 EC-1~7로 충족된다. 검출 피크는 REQ-GRID-SEARCH-2/3이 산출하고 REQ-GRID-NOTCH-1·REQ-GRID-MOIRE-1이 소비하는 상류-하류 추적을 Scenario 5·7·3이 양방향 검증한다. Unwanted 요구(REQ-GRID-SEARCH-4 명목-금지, REQ-GRID-NOTCH-2 2D 금지, REQ-GRID-PASSTHROUGH-2 무단 억제 금지, REQ-GRID-CONTRACT-4/6)는 Scenario 2·6·7·4 및 EC-5·EC-6으로 검증된다. Optional 요구(REQ-GRID-PASSTHROUGH-3 메타데이터 대조 경고)는 조건부 Scenario 8로 분리 검증된다.

## Given-When-Then 시나리오

### Scenario 1 — 검출 정확도 + 잔존 grid line 비가시 [하드 DoD, XDET-TC-015] (REQ-GRID-VALIDATE-2, SEARCH-2, NOTCH-1)
- **Given**: 기지 grid 주파수·방향을 주입한 밀도 3부류(f_grid < f_N / ≈ f_N / > f_N aliased) 합성 팬텀 세트, 외부 주입 D_th·잔존 피크 유의성 임계·EV-102 min.
- **When**: `grid` 억제를 적용한다.
- **Then**: `tests/`에서 (a) 관측 스펙트럼 탐색이 3부류 모두에서 올바른(aliased 부류는 f_a) 피크를 검출하고, (b) 1D Gaussian notch 후 해당 주파수의 잔존 피크 전력이 유의성 임계(국소 배경 대비 D_th dB) 이하로 떨어짐(=잔존 grid line 비가시, EV-203 min)을, (c) 가드레일로 `metrics/mtf.compute_mtf`/`mtf_value_at` grid 직교축 MTF@Nyquist 유지율이 EV-102 min(≥90%) 이상임을 결정론적으로 이진 판정한다. D_th·유의성 임계·EV-102가 외부 주입(내장 없음)임을 확인한다.

### Scenario 2 — 관측 스펙트럼 탐색 부하 [XDET-TC-015 aliased negative control] (REQ-GRID-VALIDATE-3, SEARCH-4)
- **Given**: 명목 f_grid ≠ 관측 f_a인 > f_N aliased 합성 팬텀(예: f_grid = 4.0 lp/mm → f_a = |4.0 − 7.143| = 3.143/mm), 명목 f_grid 값(대조용).
- **When**: `grid` 억제를 적용하고, 대조로 명목 f_grid 위치의 스펙트럼을 테스트-로컬로 조사한다.
- **Then**: 관측 스펙트럼 탐색이 aliased 피크 f_a를 검출·억제하고, 대조로 명목 주파수 위치에는 유의 피크가 없어 명목-기반 탐색은 실패함을 `tests/`에서 확인한다(관측-스펙트럼 탐색이 부하 핵심). 모듈은 명목값을 소비하지 않으므로(REQ-GRID-SEARCH-4) 명목-기반 탐색은 테스트-로컬 대조 계산일 뿐 모듈 경로가 아님을 명시한다.

### Scenario 3 — moiré 발생 검사 + 저주파 접힘 경계 [XDET-TC-016] (REQ-GRID-VALIDATE-4, MOIRE-1)
- **Given**: 표준 부류 합성 팬텀 + 저주파 접힘(< 0.5/mm) 경계 사례 팬텀(예: f_a가 0.4/mm로 접힘), 외부 주입 moiré 저주파 컷오프(0.5/mm)·감쇠 상한([T]).
- **When**: `grid` 억제를 적용한다.
- **Then**: `tests/`에서 (a) 표준 부류에서 처리 후 잔존 moiré 피크가 없음(0건, EV-203 Moiré)을, (b) 저주파 접힘 경계 사례에서 감쇠 계수가 상한으로 제한되고 grid 교체 권고 품질 경고("본 패널과 조합 부적합")가 `HistoryEntry.extra`에 기록되며 감쇠 상한 하 moiré 잔존이 특성화됨(PARTIAL)을 판정한다. 트리거 피크가 REQ-GRID-SEARCH 산출임을 확인한다.

### Scenario 4 — 무검출 무처리 통과 [XDET-TC-016 GLS 실패] (REQ-GRID-VALIDATE-5, PASSTHROUGH-1/2)
- **Given**: 유의 피크가 없는(grid 무장착) 해부-only 합성 입력.
- **When**: `grid` 억제를 적용한다.
- **Then**: 프레임이 무처리로 통과되어 화소·마스크가 입력과 **수치 동일**하고 "grid 미검출" 진단이 `HistoryEntry.extra`에 기록됨을 `tests/`에서 확인한다(FR-M007). 유의 피크가 없을 때 어떤 notch·화소 변경도 없음(무단 억제 금지, 결정론 단일 통과 경로)을 대조한다.

### Scenario 5 — grid 방향 추정 + 관측 스펙트럼 피크 탐색 (REQ-GRID-SEARCH-1/2/3)
- **Given**: 기지 방향(수직 grid)·기지 주파수·접힘 고조파를 담은 합성 입력, Params로 주입된 탐색 대역 [0.3, f_N]·D_th([T])·방향 판정 마진([T])·고조파 최대 차수([T]).
- **When**: 행/열 1D PSD 에너지 비교로 방향을 추정하고 해당 축 1D PSD(Welch, `common/fft_psd.py` 소비)에서 협대역 피크와 접힘 고조파 후보를 탐색한다.
- **Then**: 추정 방향이 기지 방향과 일치하고, 탐색 대역 [0.3, f_N]에서 유의성 D_th 이상 피크가 관측 스펙트럼 좌표로 검출되며, 접힘 고조파 후보(f_a 정수배·f_s 접힘 조합)가 함께 검출 집합에 포함됨을, 그리고 스펙트럼 추정이 `common/fft_psd.py`를 소비(FFT/PSD 모듈 내부 재구현 없음, SWR-000-9 ③)함을 harness 시험으로 확인한다.

### Scenario 6 — 명목 grid 주파수 사용 금지 (REQ-GRID-SEARCH-4, Unwanted)
- **Given**: grid 장착 메타데이터(명목 밀도)가 제공된 합성 입력.
- **When**: `grid` 피크 위치 탐색·notch 대상 주파수 산출을 수행한다.
- **Then**: notch 대상 주파수가 오로지 관측 스펙트럼 피크(REQ-GRID-SEARCH-2/3)에서만 도출되고 명목 grid 주파수·메타데이터 밀도값이 탐색·산출 입력으로 유입되지 않음을 확인한다([HARD] 금지, 결정론 단일 경로). 메타데이터는 REQ-GRID-PASSTHROUGH-3 대조 경고에만 소비됨을 대조한다.

### Scenario 7 — 1D Gaussian notch(grid 직교축) + 2D 등방 금지 (REQ-GRID-NOTCH-1/2)
- **Given**: 검출 피크 집합(REQ-GRID-SEARCH-2/3 산출)과 Params로 주입된 notch 대역폭 계수(FWHM × 1.5, [T]).
- **When**: 검출 피크별 주파수 도메인 1D Gaussian notch를 grid 직교축에 적용한다.
- **Then**: notch가 grid 직교 1축(수직 grid → 수평 주파수축)에만 적용되고 2D 등방 notch가 적용되지 않으며(해부 손실 최소화, SWR-1003), 대역폭이 피크 FWHM × 1.5로 산출되고, 스펙트럼 변환/역변환이 `common/fft_psd.py`를 소비함을 harness 시험으로 확인한다(검출 피크 = SEARCH 상류 추적).

### Scenario 8 — grid 메타데이터 대조 경고 [조건부/Optional] (REQ-GRID-PASSTHROUGH-3)
- **Given**: WHERE grid 장착 메타데이터(장착 여부·명목 밀도)가 Params로 제공된 경우.
- **When**: `grid` 처리를 적용하고 검출 결과와 메타데이터를 대조한다.
- **Then**: 검출 결과(피크 유무·관측 주파수)와 메타데이터가 불일치할 때 경고가 `HistoryEntry.extra`에 기록되고, 메타데이터가 피크 위치 산출에는 유입하지 않음(대조 경고 전용)을 확인한다. 메타데이터 미제공 시 본 시나리오는 적용되지 않으며 대조 경고는 생략된다.

### Scenario 9 — 모듈 계약 준수 (REQ-GRID-CONTRACT-1/2/3)
- **Given**: 합성 입력 XFrame.
- **When**: `grid` 모듈이 `process(XFrame, CalibSet, Params) -> XFrame`으로 처리한다.
- **Then**: 입력 XFrame이 불변으로 유지되고(원본 미변경), 이력 체인에 처리 메타 + 스칼라 진단(grid 방향·에너지비·검출 피크 주파수·유의성(dB)·개수·notch 대역폭·감쇠 상한 적용·moiré 경고·"grid 미검출"·메타데이터 불일치, `HistoryEntry.extra`)이 추가되며, import-linter가 `modules → common` 단방향(다른 모듈·pipeline·metrics 미import)을 KEEP하고 스펙트럼 추정이 `common/fft_psd.py` 소비임을 확인한다.

### Scenario 10 — 진입 게이트 + 스테이지 배치 (REQ-GRID-CONTRACT-5, 결정 1)
- **Given**: `grid` 스테이지가 CalibSet(OTHER, 해상도·패널 ID·유효기간 일치)로 등록된 파이프라인.
- **When**: 오케스트레이터가 처리를 실행한다.
- **Then**: `grid` 스테이지가 `CANONICAL_ORDER`의 전용 `grid` 위치(`geometry`와 `denoise` 사이)에서만 실행되고(등록 stages = 부분수열), `_KIND_BY_STAGE` 미등재로 종류-단계 강제 없이 CalibSet(OTHER)로 게이트를 충족하며, CalibSet 부재·해상도·패널 불일치 시 진입 게이트가 명시 오류로 거부함을 확인한다.

## 엣지 케이스

- **EC-1 (≈ f_N 경계 부류)** — grid 주파수가 Nyquist 근처인 경계 부류에서 탐색 대역 [0.3, f_N] 상단 피크 검출·notch가 안정적으로 동작하고 잔존 피크가 유의성 임계 이하로 떨어짐을 확인한다(Scenario 1의 ≈ f_N 부류 보강).
- **EC-2 (방향 모호·교차 grid)** — 행/열 1D PSD 에너지비가 방향 판정 마진([T]) 미만으로 모호하면(교차 격자·대각선) 확신 방향 없음 → 무검출 통과로 처리하고 임의 축 추정을 하지 않음을 확인한다(확인 4, 방향·에너지비 진단 기록).
- **EC-3 (접힘 고조파 후보)** — aliased 기본 피크의 고조파가 f_s 접힘으로 여러 위치에 나타나는 팬텀에서 고조파 후보 검사(f_a 정수배·접힘 조합)가 유의 고조파를 함께 검출·억제함을 확인한다(REQ-GRID-SEARCH-3).
- **EC-4 (저유의 잡음 피크 비검출)** — 유의성 D_th 미만의 잡음 스펙트럼 피크만 있는 입력에서 grid로 오검출하지 않고 무검출 통과(수치 동일)함을 확인한다(REQ-GRID-SEARCH-2 유의성 필터, PASSTHROUGH-2 무단 억제 금지).
- **EC-5 (사이드채널 자동 검출 범위)** — 계약 위반 자동 검출 범위는 시그니처·부가 반환값 위반(계약 검사)과 의존 방향 위반(import-linter)이며, 전역 상태·파일 우회는 코드 리뷰 게이트로 다룸을 명시한다(REQ-GRID-CONTRACT-4, SPEC-INFRA-001 DATA-2 방식).
- **EC-6 (마스크 substrate 불변·포화 미복원)** — `grid` 출력이 어떤 마스크 플래그도 신규 설정·해제하지 않고 포화 화소 값을 재구성하지 않음을 확인한다(REQ-GRID-CONTRACT-6, SWR-602 [HARD] 복원 금지 계승).
- **EC-7 (notch 후 MTF 경계)** — 대역폭이 넓은 notch 프리셋에서 grid 직교축 MTF@Nyquist 유지율이 EV-102 min 경계에 근접·초과하는지 특성화하고, 1D 직교축 한정 적용이 grid 평행축 해부를 보존함을 대조로 확인한다(Scenario 1 가드레일 보강).

## 품질 게이트 (TRUST 5)

- **Tested**: XDET-TC-015·016이 pytest skeleton(skip) → 실동작 케이스로 전환, 밀도 3부류(aliased 포함) 합성 팬텀 + harness 단독 시험(합성 입력 + 기대 출력 fixture) 통과. 커버리지 ≥ 85%.
- **Readable**: 명확한 명명(영문 식별자)·방향 추정/피크 탐색/notch/moiré 경고/무검출 통과 단계 주석(SWR 대응).
- **Unified**: ruff/black 통과, 기존 `modules/` 처리 모듈 패턴 일관, 공용 컴포넌트 `common/fft_psd.py` 소비 일관.
- **Secured**: 입력 검증(방향 모호·무피크 시 무처리 통과), 무단 억제 금지, 명목-주파수 유입 금지, 마스크 substrate 불변.
- **Trackable**: 이력 체인 메타 + `HistoryEntry.extra` 진단(방향·피크·경고), 커밋 SWR/REQ 참조, 이슈 #8.

## 완료 정의 (Definition of Done)

- [ ] **[하드 DoD]** Scenario 1 + EC-1/EC-7: 밀도 3부류 관측 스펙트럼 검출 + notch 후 잔존 피크 유의성 임계 이하(비가시) + grid 직교축 MTF@Nyquist 유지율 ≥ EV-102 min 가드레일, 결정론 이진 판정 (XDET-TC-015, EV-203 min).
- [ ] Scenario 2: aliased 부류 negative control — 관측 스펙트럼 탐색 f_a 검출·억제 + 명목 위치 무피크(명목-탐색 실패, 관측-탐색 부하 증명) (REQ-GRID-VALIDATE-3, SWR-1001).
- [ ] **[PARTIAL]** Scenario 3: 표준 부류 moiré 0건 + 저주파 접힘 경계 감쇠 상한 + grid 교체 권고 경고 기록 (XDET-TC-016, EV-203 Moiré).
- [ ] Scenario 4 + EC-4: 무검출 무처리 통과(화소·마스크 수치 동일) + "grid 미검출" 로그, 무단 억제 없음 (XDET-TC-016 GLS 실패, FR-M007).
- [ ] Scenario 5 + EC-2/EC-3: 방향 추정 + 탐색 대역 [0.3, f_N] 협대역 피크 + 접힘 고조파 후보, 방향 모호 시 무검출 통과, `common/fft_psd.py` 소비 (REQ-GRID-SEARCH-1/2/3).
- [ ] Scenario 6: 명목 grid 주파수·메타데이터 밀도 notch 산출 유입 금지, 관측 스펙트럼 단일 도출 (REQ-GRID-SEARCH-4, Unwanted, [HARD]).
- [ ] Scenario 7: 1D Gaussian notch grid 직교축 적용(대역폭 FWHM × 1.5) + 2D 등방 notch 금지 (REQ-GRID-NOTCH-1/2).
- [ ] Scenario 8: grid 메타데이터 대조 경고 조건부 동작(제공 시), 미제공 시 생략, 피크 산출 미유입 (REQ-GRID-PASSTHROUGH-3, Optional).
- [ ] Scenario 9 + EC-5/EC-6: 모듈 계약(불변·이력·레이어링·`common/fft_psd.py` 소비·사이드채널 범위)·마스크 substrate 불변·포화 미복원 (REQ-GRID-CONTRACT-1/2/3/4/6).
- [ ] Scenario 10: 전용 `grid` 스테이지(geometry와 denoise 사이)·CalibSet(OTHER) 빈 placeholder 진입 게이트·`_KIND_BY_STAGE` 미등재 (REQ-GRID-CONTRACT-5, 결정 1).
- [ ] EV-203/102 및 D_th·잔존 피크 유의성 임계 외부 주입 확인, 임계 내장 없음 (REQ-GRID-VALIDATE-6).
- [ ] XDET-TC-015·016 pytest skeleton(skip) → 합성 입력·판정 연동 실동작 케이스 전환 (REQ-GRID-VALIDATE-6).
- [ ] 「결정 필요/확인 사항」 1(run-blocking, 전용 `grid` 스테이지 배치) plan-audit 확정 + HISTORY 반영.
- [ ] import-linter 레이어링 계약 KEEP, 전체 회귀 통과.
