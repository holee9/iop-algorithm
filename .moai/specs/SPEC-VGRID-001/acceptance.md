# SPEC-VGRID-001 인수 기준 (acceptance.md)

T8(WP9 커널 Virtual grid, SKS scatter 보정)의 인수 기준. 근거: [spec.md](./spec.md) · 계획: [plan.md](./plan.md).

**판정 원칙**: EV 임계(EV-202 CNR 개선 ≥ +20% min)·산란 추정 정확도 허용오차·노이즈 부스트 허용오차는 EVAL v1.1/Params에서 **외부 주입**된다(측정=판정 분리). 처리 모듈·판정 코드는 임계를 내장하지 않는다. 모듈은 `metrics`를 import하지 않으므로 CNR·산란 정확도 판정은 `tests/`에서 기지 산란 주입 대조·ROI 통계(`common/robust_stats` 소비)로 수행한다. **XDET-TC 매핑은 TestSpec v1.0을 단일 출처로 채택한다**(XDET-TC-017 = 무그리드+커널 보정 CNR 개선, GDS-scatter 팬텀, EV-202 min).

**게이트 정직성**: T8의 결정론적 이진 하드 게이트는 **XDET-TC-017(합성 GDS-scatter 팬텀 보정 후 CNR 개선율 ≥ EV-202 min)**이다. 산란 추정 정확도(Ŝ vs 기지 주입 S_inj)·저신호 노이즈 부스트 억제·비음수는 보조 결정론 판정이다. EV-202 "무그리드+보정 vs 물리 grid(관찰자) 비열등"은 지각·관찰자 의존으로 **PARTIAL 게이트**이며 관찰자 평가는 인허가 이연이다(T5 EV-101/T6 TC-012/T7 EV-203 PARTIAL 선례). EV-202 "DL scatter 추정 편차(MC 기준)" 행은 DL/Gen2 이연으로 P1 범위 밖이다.

**⚠P 정직성**: SKS 특허(US 11,911,202 등) 청구항 대조·특허 판단·릴리스 게이팅은 **SW 구현 범위 밖**이며 릴리스 게이트 소관이다. 인수 기준은 특허 판단을 게이팅하지 않고, ⚠P 플래그 유지·커널의 `CalibSet(SCATTER)` 소싱(MC-LUT 회피 대안 빌더 단 치환 가능성)·⚠P provenance 진단 기록만 확인한다.

**커버리지 노트**: REQ-VGRID-VALIDATE-1(합성 검증 컨텍스트 전제)은 Scenario 1~3으로, 각 처리 요구(ESTIMATE/SUBTRACT/CALIB/CONTRACT)는 Scenario 1~10 및 EC-1~6으로 충족된다. 추정 산란은 REQ-VGRID-ESTIMATE가 산출하고 REQ-VGRID-SUBTRACT가 소비하는 상류-하류 추적을 Scenario 4·5가 검증한다. Unwanted 요구(REQ-VGRID-ESTIMATE-3 명목 커널 금지, REQ-VGRID-SUBTRACT-3 비음수, REQ-VGRID-CALIB-2 무-침묵-기본값, REQ-VGRID-CONTRACT-4/6)는 Scenario 3·6 및 EC-2·EC-4·EC-6으로 검증된다. ⚠P 회피 대안 예약(REQ-VGRID-CALIB-3)은 Scenario 8로 검증한다.

## Given-When-Then 시나리오

### Scenario 1 — CNR 개선 [하드 DoD, XDET-TC-017] (REQ-VGRID-VALIDATE-1/2, ESTIMATE-1, SUBTRACT-1)
- **Given**: 기지 산란 커널로 기지 저주파 산란을 주입한 합성 GDS-scatter 팬텀(기지 대비 신호·기지 배경 ROI), 외부 주입 EV-202 min(≥ +20%), `CalibSet(SCATTER)` 커널, Params w.
- **When**: `virtual_grid` 보정을 적용한다.
- **Then**: `tests/`에서 보정 후 관심/배경 ROI의 CNR 개선율(보정 후 CNR / 보정 전 CNR − 1)이 EV-202 min(≥ +20%) 이상임을 결정론적으로 이진 판정한다. CNR은 기지 ROI 통계(`common/robust_stats` 소비)로 산출하고 EV-202 임계가 외부 주입(내장 없음)임을 확인한다.

### Scenario 2 — 산란 추정 정확도 (REQ-VGRID-VALIDATE-3, ESTIMATE-1/2)
- **Given**: 기지 커널로 기지 산란 S_inj를 주입한 합성 팬텀, 외부 주입 산란 추정 정확도 허용오차([T]).
- **When**: `virtual_grid` SKS 추정을 적용한다.
- **Then**: `tests/`에서 추정 산란 Ŝ가 주입 산란 S_inj와 허용오차([T]) 이내로 일치함을 판정한다(SKS 추정 정확도). 허용오차가 외부 주입임을 확인한다. EV-202 "DL scatter 추정 편차(MC 기준)"는 DL/Gen2 이연이며 본 판정은 SKS 추정 정확도 원리를 기지-주입 대조로 P1에 적용한 것임을 명시한다.

### Scenario 3 — 노이즈 부스트 억제 + 비음수 (REQ-VGRID-VALIDATE-4, SUBTRACT-2/3)
- **Given**: 저신호 영역을 포함한 합성 팬텀, 외부 주입 노이즈 부스트 허용오차([T])·저신호 감쇠 임계.
- **When**: `virtual_grid` 감산을 적용한다.
- **Then**: `tests/`에서 (a) 저신호 영역에서 보정 후 노이즈가 허용오차([T]) 초과로 증가하지 않고(w 자동 감쇠, SWR-1102), (b) 출력 화소가 음수가 되지 않음(비음수 제약)을 판정한다. 저신호 감쇠·비음수 처리가 결정론적 단일 경로임을 대조한다.

### Scenario 4 — SKS 산란 추정(다운샘플 pyramid 소비 + 이중 Gaussian 커널) (REQ-VGRID-ESTIMATE-1/2, CALIB-1)
- **Given**: 기지 산란·기지 대비를 담은 합성 입력, `CalibSet(SCATTER)`의 이중 Gaussian 커널 K, Params 반복 횟수(2~3)·다운샘플 배율(×8).
- **When**: 다운샘플(×8) 도메인에서 S = conv(P̂, K) 반복(P̂₀ = I_down, P̂_{i+1} = I_down − S_i)을 수행한다.
- **Then**: 다운샘플이 `common/pyramid.py` Gaussian `reduce_once`(×2 3회)를 소비(다운샘플 모듈 내부 재구현 없음, SWR-000-9 ①)하고, 커널 K가 `CalibSet(SCATTER)` payload에서만 도출되며(모듈 내부 하드코딩 없음), 반복이 Params 지정 횟수만큼 수행됨을 harness 시험으로 확인한다. **공간 도메인이므로 `common/fft_psd.py`를 소비하지 않음**(T7 grid와 구별)을 대조한다.

### Scenario 5 — grid ratio 가중 감산(업샘플 bilinear + w) (REQ-VGRID-SUBTRACT-1)
- **Given**: 추정 산란 Ŝ(REQ-VGRID-ESTIMATE 산출), Params grid ratio 환산 계수 w(사용자 선택 3:1~12:1 상당).
- **When**: Ŝ를 bilinear 업샘플(Ŝ↑)하고 I′ = I − w·Ŝ↑로 감산한다.
- **Then**: 업샘플이 SWR-1102 명시 bilinear(pyramid Gaussian expand와 구별)이고, w가 Params에서 취해짐(캘리브레이션 아님)을, 감산이 추정 산란(ESTIMATE 상류 추적)을 소비함을 harness 시험으로 확인한다.

### Scenario 6 — 커널 부재 무-침묵-기본값 REJECT (REQ-VGRID-CALIB-2, ESTIMATE-3, Unwanted)
- **Given**: `CalibSet(SCATTER)`가 부재하거나 payload가 퇴화(빈 커널·비유한 계수)인 입력.
- **When**: `virtual_grid` 처리를 시도한다.
- **Then**: 시스템이 침묵 기본 커널 대체 없이 명시 오류로 REJECT함을 확인한다(SWR-000-5, 결정론 단일 경로). 임의 기본 커널·대역통과 근사 분기가 없음(무-침묵-기본값, DENOISE NOISE·LAG IRF 선례)을 대조한다.

### Scenario 7 — CalibKind.SCATTER 진입 게이트 + 스테이지 배치 (REQ-VGRID-CONTRACT-5, 결정 1·2)
- **Given**: `virtual_grid` 스테이지가 `CalibSet(SCATTER)`(종류·해상도·패널 ID·유효기간 일치)로 등록된 파이프라인.
- **When**: 오케스트레이터가 처리를 실행한다.
- **Then**: `virtual_grid` 스테이지가 `CANONICAL_ORDER`의 전용 위치(`grid`와 `denoise` 사이)에서만 실행되고(등록 stages = 부분수열), `_KIND_BY_STAGE["virtual_grid"]="scatter"`로 종류-단계가 강제되어 CalibSet 종류가 SCATTER가 아니거나 부재·해상도·패널 불일치 시 진입 게이트가 명시 오류로 거부함을 확인한다(T7 grid의 CalibSet(OTHER) 무-캘리브레이션과 구별).

### Scenario 8 — ⚠P 특허 플래그 + MC-LUT 회피 대안 예약 (REQ-VGRID-CALIB-3)
- **Given**: 합성 입력 XFrame + `CalibSet(SCATTER)`.
- **When**: `virtual_grid` 처리를 적용한다.
- **Then**: (a) 산란 커널이 `CalibSet(SCATTER)`에서 전량 소싱되어 대체 커널 도출(MC 사전계산 LUT 등)을 **빌더 단(`metrics/scatter_kernel.py`)에서 모듈 재설계 없이 치환** 가능한 구조임을 확인하고, (b) ⚠P 커널 provenance가 `HistoryEntry.extra` 진단에 기록됨을 확인한다. SW 구현이 특허 판단·릴리스 게이팅을 수행하지 않음(범위 밖)을 명시한다.

### Scenario 9 — 모듈 계약 준수 (REQ-VGRID-CONTRACT-1/2/3)
- **Given**: 합성 입력 XFrame + `CalibSet(SCATTER)`.
- **When**: `virtual_grid` 모듈이 `process(XFrame, CalibSet, Params) -> XFrame`으로 처리한다.
- **Then**: 입력 XFrame이 불변으로 유지되고(원본 미변경, 무상태), 이력 체인에 처리 메타 + 스칼라 진단(반복 횟수·적용 w·산란 비율·저신호 감쇠 적용·비음수 클램프 수·⚠P provenance, `HistoryEntry.extra`)이 추가되며, import-linter가 `modules → common` 단방향(다른 모듈·pipeline·metrics 미import)을 KEEP하고 다운샘플이 `common/pyramid.py` 소비(`common/fft_psd.py` 미소비)임을 확인한다.

### Scenario 10 — T7 grid와의 기능 구별(상호배타·격자선 미제거) (Environment, Exclusions, 결정 1)
- **Given**: 물리 grid가 없는(무그리드) 검출기의 합성 산란 팬텀.
- **When**: `virtual_grid` 보정을 적용한다.
- **Then**: `virtual_grid`가 산란 추정·감산만 수행하고 격자선 주파수 notch(T7 `grid` 소관)를 수행하지 않으며, `grid`와 `virtual_grid`가 취득 컨텍스트상 상호배타이고 `CANONICAL_ORDER`에서 `grid → virtual_grid` 상대 순서(저비율 물리 grid 잔존 산란 경계 사례)임을 확인한다.

## 엣지 케이스

- **EC-1 (고 SPR 반복 강건성)** — 산란-대-일차선 비(SPR)가 높은 팬텀에서 2~3회 반복이 발산·과감산 없이 안정적으로 수렴함을 확인한다(SWR-1101 "고 SPR에서 반복 구조 강건성 문헌 확인" [L]).
- **EC-2 (커널 퇴화 REJECT)** — `CalibSet(SCATTER)` payload가 빈 커널·비유한 계수·해상도 불일치일 때 침묵 기본값 없이 명시 오류로 REJECT됨을 확인한다(REQ-VGRID-CALIB-2, Scenario 6 보강).
- **EC-3 (저신호 감쇠 경계)** — 저신호 임계 경계 영역에서 w 자동 감쇠가 연속적으로 적용되어 노이즈 부스트가 억제되고 경계 불연속 아티팩트가 없음을 확인한다(REQ-VGRID-SUBTRACT-2).
- **EC-4 (사이드채널 자동 검출 범위)** — 계약 위반 자동 검출 범위는 시그니처·부가 반환값 위반(계약 검사)과 의존 방향 위반(import-linter)이며, 전역 상태·파일 우회는 코드 리뷰 게이트로 다룸을 명시한다(REQ-VGRID-CONTRACT-4, SPEC-INFRA-001 DATA-2 방식).
- **EC-5 (마스크 화소 추정 오염 방지)** — DEFECT/SATURATION/SATURATION_BAND/INTERPOLATION 화소가 SKS 저주파 산란 추정을 오염시키지 않도록 하향 가중됨을 확인한다(확인 4, DENOISE SWR-706 마스크 가중 선례; 실제 배제/포함 방침은 run 확정).
- **EC-6 (마스크 substrate 불변·포화 미복원)** — `virtual_grid` 출력이 어떤 마스크 플래그도 신규 설정·해제하지 않고 포화 화소의 클리핑 소실 정보를 복원하지 않음을 확인한다(REQ-VGRID-CONTRACT-6, SWR-602 [HARD] 복원 금지 계승).

## 품질 게이트 (TRUST 5)

- **Tested**: XDET-TC-017이 pytest skeleton(skip) → 실동작 케이스로 전환, 기지 커널 합성 GDS-scatter 팬텀 + harness 단독 시험(합성 입력 + 기대 출력 fixture) 통과. 커버리지 ≥ 85%.
- **Readable**: 명확한 명명(영문 식별자)·SKS 추정/감산/비음수/저신호 감쇠 단계 주석(SWR 대응), ⚠P 특허 플래그 주석 명시.
- **Unified**: ruff/black 통과, 기존 `modules/` 처리 모듈 패턴 일관, 공용 컴포넌트 `common/pyramid.py` 소비 일관, CalibKind 신설(NOISE/LAG payload 선례) 일관.
- **Secured**: 입력 검증(커널 부재·퇴화 REJECT), 무-침묵-기본값, 비음수 제약, 마스크 substrate 불변·포화 미복원, ⚠P 특허 판단 SW 미수행(범위 밖).
- **Trackable**: 이력 체인 메타 + `HistoryEntry.extra` 진단(반복·w·산란 비율·저신호 감쇠·비음수 클램프·⚠P provenance), 커밋 SWR/REQ 참조, 이슈 #9.

## 완료 정의 (Definition of Done)

- [ ] **[하드 DoD]** Scenario 1: 합성 GDS-scatter 팬텀 보정 후 CNR 개선율 ≥ EV-202 min(≥ +20%), 결정론 이진 판정 (XDET-TC-017, EV-202 min).
- [ ] Scenario 2: 산란 추정 정확도 — Ŝ vs 기지 주입 S_inj 허용오차([T]) 이내 (REQ-VGRID-VALIDATE-3).
- [ ] Scenario 3 + EC-3: 저신호 노이즈 부스트 억제(w 자동 감쇠) + 비음수 제약 (REQ-VGRID-SUBTRACT-2/3, VALIDATE-4).
- [ ] Scenario 4: SKS 산란 추정 — 다운샘플 `common/pyramid.py` 소비(fft_psd 미소비) + 이중 Gaussian 커널 CalibSet(SCATTER) 도출 + Params 반복 횟수 (REQ-VGRID-ESTIMATE-1/2).
- [ ] Scenario 5: bilinear 업샘플 + grid ratio w 가중 감산, w = Params 소싱 (REQ-VGRID-SUBTRACT-1).
- [ ] Scenario 6 + EC-2: 커널 부재·퇴화 무-침묵-기본값 REJECT (REQ-VGRID-CALIB-2, ESTIMATE-3, Unwanted).
- [ ] Scenario 7: 전용 `virtual_grid` 스테이지(grid와 denoise 사이) + `_KIND_BY_STAGE["virtual_grid"]="scatter"` 진입 게이트 + CalibSet(SCATTER) (REQ-VGRID-CONTRACT-5, 결정 1·2).
- [ ] Scenario 8: ⚠P 커널 provenance 진단 기록 + 커널 CalibSet(SCATTER) 소싱(MC-LUT 빌더 단 치환 가능) + SW 특허 판단 미수행 (REQ-VGRID-CALIB-3).
- [ ] Scenario 9 + EC-4: 모듈 계약(불변·이력·레이어링·`common/pyramid.py` 소비·사이드채널 범위) (REQ-VGRID-CONTRACT-1/2/3/4).
- [ ] Scenario 10 + EC-5/EC-6: T7 grid와 기능 구별(상호배타·격자선 미제거)·마스크 substrate 불변·포화 미복원 (Environment/Exclusions, REQ-VGRID-CONTRACT-6).
- [ ] EV-202 및 산란 추정 정확도·노이즈 부스트 허용오차 외부 주입 확인, 임계 내장 없음 (REQ-VGRID-VALIDATE-5). 관찰자 비열등(EV-202)·DL 추정 편차(MC)는 인허가/Gen2 이연 명시.
- [ ] XDET-TC-017 pytest skeleton(skip) → 합성 입력·판정 연동 실동작 케이스 전환 (REQ-VGRID-VALIDATE-5).
- [ ] 「결정 필요/확인 사항」 1(전용 `virtual_grid` 스테이지 배치)·2(신규 `CalibKind.SCATTER` + `_KIND_BY_STAGE` 배선) run-blocking plan-audit 확정 + HISTORY 반영.
- [ ] import-linter 레이어링 계약 KEEP, 전체 회귀 통과, `pyproject.toml` 신규 의존성 미추가.
