# SPEC-VGRID-001 구현 계획 (plan.md)

T8(WP9 커널 Virtual grid). `modules/virtual_grid.py`(무상태 처리 모듈)를 구현하고, WP9(SKS 산란 추정 → grid ratio 가중 감산 → 비음수·저신호 노이즈 부스트 억제, SWR-1101~1103)를 T0 계약 `process(XFrame, CalibSet, Params) -> XFrame`으로 실현한다. 다운샘플은 공용 컴포넌트 `common/pyramid.py`(① pyramid)를 SWR-000-9에 따라 소비하며 재구현하지 않는다. 산란 커널은 신규 `CalibSet(SCATTER)`(오프라인 빌더 `metrics/scatter_kernel.py` 방출)를 단일 소스로 소비한다. **⚠P — SKS 특허(US 11,911,202 등) 청구항 대조는 릴리스 게이트로 이연하고 SW 구현은 ⚠P 플래그를 유지**한다. 근거: [spec.md](./spec.md) · 인수 기준: [acceptance.md](./acceptance.md).

> **버전 0.1.0 (2026-07-09)** — 초안. GitHub 이슈 #9. 5개 요구 그룹(ESTIMATE/SUBTRACT/CALIB/CONTRACT/VALIDATE). 결정 1(전용 `virtual_grid` 스테이지 배치: `grid`↔`denoise` 사이)·결정 2(신규 `CalibKind.SCATTER` + `_KIND_BY_STAGE` 배선)는 T0 표면 변경 run-blocking으로 plan-audit 확정 대상.

## 선행 결정 (plan-audit 확정 대상)

「결정 필요/확인 사항」 1·2는 T0 표면을 변경하는 run-blocking 항목으로 plan-audit에서 확정해야 한다(T5 SPEC-DENOISE-001·T6 SPEC-POST-001·T7 SPEC-GRID-001 결정 1과 동형의 부분수열-삽입 패턴 + DENOISE 결정 2와 동형의 신규 CalibKind 패턴). 나머지 3~5는 확인 대상(가정 default 제시).

- **결정 1(스테이지 배치, run-blocking)**: 전용 `virtual_grid` 스테이지를 `grid`와 `denoise` **사이**에 신설(`CANONICAL_ORDER = … → geometry → grid → virtual_grid → denoise → mse → window → post`). 등록 stages = `CANONICAL_ORDER` 부분수열 검증으로 하류 미등록 SPEC에 하위호환(T5·T6·T7 선례). `post`는 예약 tail 유지. rationale: 기하 보정 후 축-정렬 영상에서 산란 추정(geometry 뒤) + 저신호 노이즈 부스트를 denoise가 정리·대비강화 전 산란 제거(denoise·mse 앞). **T7 grid와의 관계**: grid(물리 격자선 제거)와 virtual_grid(무그리드 산란 보정)는 상호배타, `grid → virtual_grid` 상대 순서(저비율 물리 grid 잔존 산란 경계 사례). 기각 대안: denoise 뒤(산란 저주파라 denoise 무용 + 노이즈 부스트 미정리).
- **결정 2(신규 `CalibKind.SCATTER`, run-blocking)**: 산란 커널 K는 실측 피팅([B], SWR-1101) 검출기 캘리브레이션(SWR-000-10 "scatter 커널" 종류 명시). 신규 `CalibKind.SCATTER` + `_KIND_BY_STAGE["virtual_grid"]="scatter"` + `SCATTER_PAYLOAD_KEYS` 신설, 오프라인 빌더 `metrics/scatter_kernel.py` → `CalibSet(SCATTER)`, 모듈 단일 소비·부재 REJECT(DENOISE NOISE-kind 선례 — OTHER 재사용 대신 SCATTER 신설로 종류-단계 게이트 결속 강제). T7 grid(무-캘리브레이션 CalibSet(OTHER))와 구별. T0 표면(`common/calibset.py` + orchestrator) 변경.
- **확인 3(w 소재·비음수·저신호 감쇠)**: w = 사용자 선택 Params([T]/[P], 캘리브레이션 아님), 저신호 감쇠 임계·곡선·비음수 처리 Params 외부화.
- **확인 4(SKS 추정 세부)**: ×8 다운샘플 = `common/pyramid.py` reduce_once 재사용(공간 도메인 → fft_psd 아님), 이중 Gaussian 자체 scipy conv, 마스크 화소 하향 가중.
- **확인 5(⚠P 특허 플래그·MC-LUT 예약·부록 A 등재)**: ⚠P 플래그 유지·특허 판단 릴리스 게이트 이연, MC-LUT 회피 대안 빌더 단 치환 예비 정의, 파라미터 [B]/[T]/무등급 등재 요청.

## 기술 접근 (WHAT — HOW 세부는 run 소관)

- **WP9 SKS 2단**: (1) **산란 추정(SWR-1101)** — 다운샘플(×8, `common/pyramid.py` reduce_once 소비) 도메인에서 이중 Gaussian 커널 K(CalibSet(SCATTER))로 S = conv(P̂, K) 반복(P̂₀ = I_down, P̂_{i+1} = I_down − S_i, 2~3회 [L]) → 추정 산란 Ŝ. (2) **감산(SWR-1102)** — bilinear 업샘플 후 I′ = I − w·Ŝ↑(w = grid ratio 환산 계수, 사용자 선택 Params 3:1~12:1 상당) + 비음수 제약 + 저신호 영역 w 자동 감쇠(노이즈 부스트 방지).
- **산란 커널 = 검출기 캘리브레이션(결정 2, SWR-000-10/1101 [B])**: 커널 K는 신규 `CalibSet(SCATTER)` 단일 소스에서 취한다. 오프라인 빌더 `metrics/scatter_kernel.py`가 실측(또는 선검증 시 합성) beam-stop/기준 데이터로 이중 Gaussian PSF를 피팅해 `CalibSet(SCATTER)`를 방출한다(lag_irf/noise_model/defect_map 선례, `metrics → common`). 부재·퇴화 시 침묵 기본값 없이 REJECT(무-침묵-기본값, SWR-000-5).
- **공용 컴포넌트 ① pyramid 소비 — 공간 도메인(SWR-000-9)**: 다운샘플은 `common/pyramid.py` Gaussian `reduce_once`(×2 3회)를 소비. **T7 grid(주파수 도메인 → `common/fft_psd.py`)와 달리 virtual_grid는 공간 도메인 SKS이므로 `common/pyramid.py`(① pyramid)를 소비**한다. 업샘플 bilinear·이중 Gaussian conv는 자체 scipy 구현(pyramid Gaussian expand·재구현 아님).
- **⚠P 특허 처리**: SKS 특허(US 11,911,202 등) 청구항 대조는 릴리스 게이트 이연(사용자 지시). SW 구현은 ⚠P 플래그 유지·특허 판단 미수행. 커널을 `CalibSet(SCATTER)`에서 전량 소싱하는 설계로 회피 대안(MC 사전계산 LUT 커널, SWR-1103)을 빌더 단 치환 예비 정의로 예약(구현 P1 밖).
- **측정=판정 분리**: 모듈은 EV 임계·판정 로직을 내장하지 않는다. CNR·산란 추정 정확도·노이즈 부스트는 `tests/`에서 기지 산란 주입 대조·ROI 통계(`common/robust_stats` 소비)로 판정하고 EV-202/허용오차는 외부 주입. 모듈은 `metrics` 미import.

## 마일스톤 (우선순위 순 — 시간 추정 없음)

### M0 — 선행 결정 확정 (Priority: High, run-blocking)
- 「결정 필요/확인 사항」 1(전용 `virtual_grid` 스테이지, `grid`와 `denoise` 사이)·2(신규 `CalibKind.SCATTER` + `_KIND_BY_STAGE` 배선)를 plan-audit에서 확정하고 spec.md HISTORY에 반영(house style: 항목 번호 유지 + `[확정 — RESOLVED]` + rationale). 확인 3~5 default는 run 중 검토.
- 확정 산출: `CANONICAL_ORDER = … → geometry → grid → virtual_grid → denoise → mse → window → post`, `CalibKind.SCATTER` + `_KIND_BY_STAGE["virtual_grid"]="scatter"` + `SCATTER_PAYLOAD_KEYS`, 빌더 `metrics/scatter_kernel.py`.

### M1 — CalibKind.SCATTER + 커널 빌더 (Priority: High)
- `common/calibset.py`: 신규 `CalibKind.SCATTER` + `SCATTER_PAYLOAD_KEYS`(이중 Gaussian 계수·두께/kV 의존, 스키마 [B] 이연) 추가(NOISE_PAYLOAD_KEYS/LAG_PAYLOAD_KEYS 선례).
- `metrics/scatter_kernel.py`: 오프라인 빌더 — 이중 Gaussian scatter PSF 피팅 → `CalibSet(SCATTER)` 방출(`metrics → common`, lag_irf/noise_model 선례). 선검증 시 합성 커널 경로.
- 대응: REQ-VGRID-CALIB-1/2, REQ-VGRID-CONTRACT-5.

### M2 — virtual_grid 모듈: SKS 산란 추정 (Priority: High)
- `modules/virtual_grid.py`: 다운샘플(×8, `common/pyramid.py` reduce_once 소비) → 이중 Gaussian 커널 K(CalibSet(SCATTER))로 S = conv(P̂, K) 반복(2~3회 [L], 반복 횟수 [T] Params) → 추정 산란 Ŝ.
- 커널 부재·퇴화 시 REJECT(무-침묵-기본값, REQ-VGRID-ESTIMATE-3 Unwanted).
- 대응: REQ-VGRID-ESTIMATE-1/2/3.

### M3 — virtual_grid 모듈: 감산(비음수·저신호 감쇠) (Priority: High)
- bilinear 업샘플 후 I′ = I − w·Ŝ↑(w = grid ratio 환산 계수 [T]/[P] Params) + 저신호 영역 w 자동 감쇠(SWR-1102 노이즈 부스트 방지) + 비음수 제약.
- 대응: REQ-VGRID-SUBTRACT-1/2/3.

### M4 — 모듈 계약·오케스트레이터 통합 (Priority: High)
- `virtual_grid` 모듈 `process(XFrame,CalibSet,Params)->XFrame` 무상태 순수함수, 불변성·이력 체인(`HistoryEntry.extra` 진단: 반복 횟수·w·산란 비율·저신호 감쇠·비음수 클램프·⚠P provenance)·의존 방향(`module → common`)·harness 단독 시험.
- 전용 `virtual_grid` 스테이지(`grid`와 `denoise` 사이)를 `CANONICAL_ORDER`에 신설(결정 1), `_KIND_BY_STAGE["virtual_grid"]="scatter"` 배선(결정 2), `CalibSet(SCATTER)` 진입 게이트 충족, 마스크 substrate 불변·포화 미복원(REQ-VGRID-CONTRACT-6).
- 대응: REQ-VGRID-CONTRACT-1~6, REQ-VGRID-CALIB-3.

### M5 — 합성 검증 + TC 전환 (Priority: High)
- XDET-TC-017(CNR 개선, 하드 DoD): 기지 커널로 기지 산란 주입한 합성 GDS-scatter 팬텀 → 보정 후 CNR 개선율 ≥ EV-202 min(≥ +20%) 결정론 판정 + 산란 추정 정확도(Ŝ vs S_inj 허용오차) + 저신호 노이즈 부스트 억제·비음수.
- pytest skeleton(skip) → 실동작 케이스 전환(REQ-VGRID-VALIDATE-5). 관찰자 비열등(EV-202)은 인허가 이연(PARTIAL) 명시.
- 대응: REQ-VGRID-VALIDATE-1~5, acceptance 전 시나리오.

## 산출물

| 경로 | 역할 | 대응 REQ |
|---|---|---|
| `modules/virtual_grid.py` | 커널 Virtual grid 처리 모듈(무상태) — SKS 산란 추정·grid ratio 가중 감산·비음수·저신호 노이즈 부스트 억제 | ESTIMATE, SUBTRACT, CONTRACT |
| `common/calibset.py` | 신규 `CalibKind.SCATTER` + `SCATTER_PAYLOAD_KEYS`(이중 Gaussian 계수, 스키마 [B] 이연) 추가(결정 2) | CALIB-1 |
| `metrics/scatter_kernel.py` | 오프라인 커널 빌더 — 이중 Gaussian scatter PSF 피팅 → `CalibSet(SCATTER)` 방출(`metrics → common`) | CALIB-1 |
| `pipeline/orchestrator.py` | `virtual_grid` 스테이지 `CANONICAL_ORDER`(grid와 denoise 사이) 신설(결정 1) + `_KIND_BY_STAGE["virtual_grid"]="scatter"` 배선(결정 2) | CONTRACT-5 |
| `tests/…` | XDET-TC-017 실동작 케이스 + 합성 GDS-scatter 팬텀(기지 커널·대비 주입) + harness fixture | VALIDATE |

> `pyproject.toml`은 변경 없음 — 다운샘플(`common/pyramid.py` 소비)·이중 Gaussian conv·bilinear 업샘플·감산 전부 자체 numpy/scipy 구현으로 신규 의존성 미추가.
> `common/pyramid.py`(① pyramid, T6 구현)는 소비만 하고 변경하지 않는다(다운샘플 `reduce_once` 재사용). `common/fft_psd.py`(③ FFT·PSD)는 소비하지 않는다(공간 도메인).

## 리스크 및 완화

- **[High] ⚠P 특허(SWR-1101/1103)** — SKS 수식 청구 유효 특허(US 11,911,202 등) 확인. 완화: 특허 청구항 대조·판단은 릴리스 게이트 이연(사용자 지시, SW 범위 밖), ⚠P 플래그 유지(REQ-VGRID-CALIB-3, Exclusions), 커널을 `CalibSet(SCATTER)`에서 소싱하는 설계로 MC-LUT 회피 대안 빌더 단 치환 예비 정의. 「결정 5」에서 provenance 기록 확정.
- **[High] 신규 CalibKind T0 표면 변경(결정 2)** — `CalibKind.SCATTER` + `_KIND_BY_STAGE` 신설이 진입 게이트·CalibSet 스키마 회귀. 완화: NOISE-kind(DENOISE 결정 2) 동형 패턴, 종류-단계 배선으로 침묵 기본값 차단, 기존 kind 무변경 추가만.
- **[High] 스테이지 배치 T0 표면 변경(결정 1)** — `CANONICAL_ORDER` `virtual_grid` 스테이지 신설이 하류 SPEC 회귀. 완화: 결정 1(grid와 denoise 사이), 등록 stages = 부분수열 검증 하위호환(T5·T6·T7 선례), `post` 예약 tail 유지.
- **[High] 노이즈 부스트(SWR-1102)** — 저신호 영역 산란 감산이 상대 노이즈를 증폭. 완화: 저신호 영역 w 자동 감쇠(REQ-VGRID-SUBTRACT-2) + 비음수 제약(REQ-VGRID-SUBTRACT-3), 저신호 노이즈 부스트 허용오차 검증(REQ-VGRID-VALIDATE-4), 스테이지를 denoise 앞에 배치(결정 1)해 잔존 부스트를 BM3D가 정리.
- **[Medium] 산란 커널 부재·오소싱** — 커널 부재 시 침묵 기본 커널로 대체하면 잘못된 감산. 완화: `CalibSet(SCATTER)` 단일 소스·부재 REJECT(REQ-VGRID-CALIB-2 Unwanted), 명목 커널 하드코딩 금지(REQ-VGRID-ESTIMATE-2/3).
- **[Medium] T7 grid와 혼동·중복 처리** — grid(격자선 제거)와 virtual_grid(산란 보정)를 혼동해 중복·상충 처리. 완화: 기능 구별 명문화(Environment·Exclusions·결정 1), 상호배타·`grid → virtual_grid` 상대 순서, virtual_grid는 격자선 notch 미수행(Exclusions).
- **[Low] 실측 scatter 세트 부재** — scatter 커널 실측 도착 전. 완화: 기지 커널 합성 GDS-scatter 팬텀 선검증(LAG 합성 IRF·DENOISE 합성 λ 선례), 실측 도착 후 커널 치환은 게이트 아님(부록 A 정책).

## 검증 전략

- 모든 판정은 `tests/`에서 모듈 + 기지 산란 주입 대조·ROI 통계(`common/robust_stats`)로 수행(모듈은 `metrics` 미import — CONTRACT-3).
- EV 임계(EV-202 CNR min)·산란 추정 정확도·노이즈 부스트 허용오차는 외부 주입(측정=판정 분리). 처리·판정 코드에 임계 내장 금지.
- harness 단독 시험(합성 입력 + 기대 출력 fixture)으로 모듈 격리 검증(XDET-TC-000 계승).
- 하드 DoD(XDET-TC-017: CNR 개선 ≥ EV-202 min)는 결정론 이진 게이트; 관찰자 비열등(EV-202)은 인허가 이연(PARTIAL) 정직 명시. 산란 추정 정확도(Ŝ vs 기지 주입 S_inj)·저신호 노이즈 부스트 억제·비음수를 보조 판정.
- ⚠P provenance를 `HistoryEntry.extra`에 기록해 릴리스 게이트 특허 대조 추적을 돕되, 특허 판단은 SW가 수행하지 않는다(SW 범위 밖).
