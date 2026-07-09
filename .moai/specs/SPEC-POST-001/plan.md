# SPEC-POST-001 구현 계획 (plan.md)

T6(WP6 MSE/DRC + WP7 자동 윈도잉/GSDF). `modules/mse.py`·`modules/window.py`(무상태 처리 모듈)를 구현하고, WP6(Laplacian 피라미드 분해 → power-law 대역 변조 + 노이즈 게이팅 → DRC → 재합성·범위 정규화)·WP7(조사야 인식 → 직접선 분리 → VOI + 부위 프리셋 → GSDF LUT)을 T0 계약 `process(XFrame, CalibSet, Params) -> XFrame`으로 실현한다. 공용 컴포넌트 `common/pyramid.py`(T0 스텁 최초 구현)·`common/histogram_fov.py`(T1 확장)을 SWR-000-9에 따라 1회 구현한다. 근거: [spec.md](./spec.md) · 인수 기준: [acceptance.md](./acceptance.md).

> **버전 0.1.1 (2026-07-09)** — plan-audit iter1(FAIL 0.76) 반영: 「결정 필요/확인 사항」 1·2 확정(전용 `mse`·`window` 스테이지 신설·CalibSet(OTHER) 빈 placeholder), 결함 D1~D7 국소 수정(spec.md HISTORY v0.1.1 참조). B_mid 단일 결정론 규칙(D2) 동기화. 이전: v0.1.0(2026-07-09) 초안.

## 선행 결정 (plan-audit iter1 확정 완료)

「결정 필요/확인 사항」 1·2는 plan-audit iter1에서 확정(RESOLVED). 1은 T0 표면(`CANONICAL_ORDER`)을 변경하던 run-blocking 항목으로 본 확정으로 해소(T5 SPEC-DENOISE-001 결정 1과 동형). 나머지 3~7은 확인 대상(가정 default 제시).

- **결정 1(스테이지 배치, 확정)**: 전용 `mse`(WP6)·`window`(WP7) 스테이지를 `denoise`와 `post` 사이에 신설(`CANONICAL_ORDER = … → geometry → denoise → mse → window → post`). 등록 stages = `CANONICAL_ORDER` 부분수열 검증으로 하류 미등록 SPEC에 하위호환(T5 결정 1 선례). `post`는 예약 tail 유지("기존 post 실현" 기각). 두 스테이지 모두 검출기 캘리브레이션 없음 → `_KIND_BY_STAGE` 미등재, 진입 게이트 충족을 위해 CalibSet(OTHER) 소비(saturation/geometry 선례).
- **확인 2(CalibSet 소재, 확정)**: 디스플레이 특성·부위 프리셋 VOI = Params 단일 소재, CalibSet(OTHER)는 진입 게이트 충족용 빈 placeholder(payload 미탑재, 신규 CalibKind 미신설). CalibSet(OTHER) payload 소재 대안 기각(disjunction 제거).
- **확인 3~7**: SWR-802 ⚠P 특허 플래그·soft-clip 대안(3), "선형 컷오프"=SWR-805 해석(4), 조사야/직접선 내부 산출 vs 마스크(5), TC-012 IQA 대리·최초 기준선 의미론(6), ε_gsdf·β·γ_DRC 등 부록 A 등재(7) — 각 가정 default는 spec.md 참조.

## 기술 접근 (WHAT — HOW 세부는 run 소관)

- **WP6 MSE/DRC 4단**: (1) Laplacian 피라미드 L레벨 분해(`common/pyramid.py`, SWR-801) → (2) 레벨별 power-law 변조(SWR-802) + 로컬 노이즈 게이팅 g=c²/(c²+β·σ_ℓ²)(SWR-803, 입력 XFrame.noise (α,σ) 소비) → (3) DRC 최저역 압축(SWR-804) → (4) 재합성 + [p0.1, p99.9] 백분위 범위 정규화(SWR-805, 포화 마스크 제외). ⚠P: SWR-802 함수형은 power-law 기본형 + soft-clip 대안 예비.
- **WP7 윈도잉/GSDF 4단**: (1) 조사야 인식 → (2) 직접선·차폐 분리(`common/histogram_fov.py` 확장, SWR-901) → (3) 유효 해부 히스토그램 VOI [p_low, p_high] + 부위 프리셋·수동 오버라이드(SWR-902) → (4) P-value → PS3.14 GSDF JND LUT + 적합 자가검사(SWR-903).
- **XFrame.noise 소비(T5→T6 핸드오프)**: T5(SPEC-DENOISE-001 CONTRACT-2)가 해결된 (α, σ)를 출력 XFrame.noise에 기록하므로, `mse`는 입력 XFrame.noise를 SWR-803 노이즈 게이팅에 소비한다. (0,0)·퇴화 시 거부(무단 기본값 금지, T5 REQ-DENOISE-VST-2 선례). 이 SPEC이 T5→T6 XFrame.noise 계약의 최초 소비 검증이다.
- **측정=판정 분리**: 모듈은 EV 임계·판정 로직을 내장하지 않는다. MTF 가드레일은 `tests/`에서 T1 지표 엔진(`metrics/mtf.compute_mtf`/`mtf_value_at`)을 소비하고, 윈도우 정합·GSDF PS3.14 편차·IQA 대리는 `tests/`에서 기지값·표준 대조 직접 측정으로 판정한다.
- **공용 컴포넌트 최초 구현(SWR-000-9)**: `common/pyramid.py`(build_pyramid + reconstruct, `mse` 최초 소비자)·`common/histogram_fov.py`(조사야/직접선 분리 확장, `window` 소비). 중복 구현 금지, `module → common` 단방향 유지.

## 마일스톤 (우선순위 순 — 시간 추정 없음)

### M0 — 선행 결정 확정 (Priority: High, plan-audit iter1 완료)
- 「결정 필요/확인 사항」 1·2를 plan-audit iter1에서 확정(RESOLVED)하고 spec.md HISTORY v0.1.1에 반영 완료(house style: 항목 번호 유지 + `[확정 — RESOLVED]` + rationale). 확인 3~7 default는 run 중 검토.
- 확정 산출: `CANONICAL_ORDER = … → geometry → denoise → mse → window → post`, `_KIND_BY_STAGE` 미등재(OTHER 빈 placeholder 소비), 디스플레이 특성·프리셋 = Params 단일 소재.

### M1 — 공용 컴포넌트 구현 (Priority: High)
- `common/pyramid.py`: T0 스텁 `build_pyramid`를 Gaussian(5×5 [1 4 6 4 1]/16)/Laplacian 분해 + reconstruct로 구현(SWR-801, `mse` 최초 소비자, SWR-000-9 ①). L레벨 파라미터화([T]).
- `common/histogram_fov.py`: 조사야(collimation field) 인식·직접선(direct exposure) 분리 확장(SWR-901, `window` 소비, SWR-000-9 ②; SWR-000-9 첫-소비자 이연 원칙에 따른 T6 확장).
- 대응: REQ-POST-MSE-1, REQ-POST-WINDOW-1.

### M2 — MSE 모듈: 대역 변조 + 노이즈 게이팅 (Priority: High)
- `modules/mse.py`: 피라미드 분해 → 레벨별 power-law 변조 c′=γ_ℓ·sign(c)·|c|^p_ℓ(SWR-802, γ_ℓ·p_ℓ [T] Params) → 노이즈 게이트 g=c²/(c²+β·σ_ℓ²)(SWR-803, 입력 XFrame.noise 소비, β [T] 등재 요청).
- XFrame.noise 부재·퇴화 거부(REQ-POST-MSE-4, Unwanted 단일 경로). soft-clip 대안 함수형 Optional(REQ-POST-MSE-5, ⚠P).
- 대응: REQ-POST-MSE-2/3/4/5.

### M3 — MSE 모듈: DRC + 재합성 + 범위 정규화 (Priority: High)
- DRC 최저역 압축 B′=B_mid+(B−B_mid)·γ_DRC(SWR-804, γ_DRC·B_mid 무등급 Params·등재 요청, B_mid는 단일 결정론 규칙 — Params 제공 시 그 값, 미제공 시에만 `common/robust_stats` 산출, fallback 순서 고정) → 미압축 세부대역과 재합성 → [p0.1, p99.9] 백분위 범위 정규화(SWR-805, "선형 컷오프", 포화 마스크 제외 via `common/mask_ops`).
- 대응: REQ-POST-DRC-1/2.

### M4 — WINDOW 모듈: 자동 윈도잉 + 부위 프리셋 (Priority: High)
- `modules/window.py`: 조사야 인식 → 직접선 분리(`common/histogram_fov.py`) → 유효 해부 히스토그램 VOI [p_low, p_high](SWR-901, 프리셋 [T]) → 부위 프리셋 테이블(SWR-902) + 수동 오버라이드(Optional, 오버라이드율 `HistoryEntry.extra` 기록) → VOI 확정 후 유효 신호를 [p_low, p_high] 윈도우로 P-value 재매핑(SWR-901 VOI 적용, REQ-POST-GSDF-1 트리거 상류).
- 조사야/직접선은 단계 내부 산출(신규 마스크 플래그 미도입, 확인 5).
- 대응: REQ-POST-WINDOW-1/2/3/4.

### M5 — WINDOW 모듈: GSDF LUT + 적합 자가검사 (Priority: High, 하드 DoD 핵심)
- P-value → PS3.14 GSDF JND 인덱스 매핑 LUT 구성(SWR-903, GSDF=[S], 디스플레이 최소/최대 휘도 Params). JND당 대비 응답 편차 산출 자가검사 → `HistoryEntry.extra` 기록.
- 대응: REQ-POST-GSDF-1/2. **하드 DoD(XDET-TC-014)의 알고리즘 근간.**

### M6 — 모듈 계약·오케스트레이터 통합 (Priority: High)
- 두 모듈 `process(XFrame,CalibSet,Params)->XFrame` 무상태 순수함수, 불변성·이력 체인(`HistoryEntry.extra`)·의존 방향(`module → common`)·harness 단독 시험.
- 전용 `mse`·`window` 스테이지(denoise와 post 사이)를 `CANONICAL_ORDER`에 신설(결정 1), CalibSet(OTHER) 진입 게이트 충족, 마스크 substrate 불변·포화 미복원(REQ-POST-CONTRACT-6).
- 대응: REQ-POST-CONTRACT-1~6.

### M7 — 합성 검증 + TC 전환 (Priority: High)
- XDET-TC-014(GSDF 적합, 하드 DoD): 파라미터화 디스플레이 특성 → GSDF LUT → JND당 편차 최댓값 ≤ ε_gsdf([S]-인접, 외부 주입) 결정론 이진 판정.
- XDET-TC-013(윈도우 수용률, PARTIAL): 기지 VOI 주입 부위별 팬텀 → 자동 윈도우 정합률(허용오차 [T]) ≥ EV-205 min.
- XDET-TC-012(MSE/DRC IQA 비열화, PARTIAL): 객관 IQA 대리(로컬 대비·세부대역 에너지·halo/overshoot/클리핑) 기준선 스냅샷 비열화 + `metrics/mtf` MTF@Nyquist 유지율 EV-102 min 가드레일.
- pytest skeleton(skip) → 실동작 케이스 전환(REQ-POST-VALIDATE-6).
- 대응: REQ-POST-VALIDATE-1~6, acceptance 전 시나리오.

## 산출물

| 경로 | 역할 | 대응 REQ |
|---|---|---|
| `modules/mse.py` | MSE/DRC 처리 모듈(무상태) — 피라미드·대역 변조·노이즈 게이팅·DRC·정규화 | MSE, DRC, CONTRACT |
| `modules/window.py` | 자동 윈도잉/GSDF 처리 모듈(무상태) — 조사야·직접선·VOI·프리셋·GSDF LUT | WINDOW, GSDF, CONTRACT |
| `common/pyramid.py` | T0 스텁 `build_pyramid` 최초 구현(Laplacian 분해/재합성, SWR-801) | MSE-1 |
| `common/histogram_fov.py` | 조사야/직접선 분리 확장(SWR-901, T1 구현 확장) | WINDOW-1 |
| `pipeline/orchestrator.py` | `mse`·`window` 스테이지 `CANONICAL_ORDER`(denoise와 post 사이) 신설(결정 1) | CONTRACT-5 |
| `tests/…` | XDET-TC-012/013/014 실동작 케이스 + harness fixture | VALIDATE |

> `pyproject.toml`은 변경 없음 — 피라미드·DRC·윈도잉·GSDF LUT 전부 자체 numpy/scipy 구현으로 신규 의존성 미추가.
> `common/calibset.py`는 신규 CalibKind 미추가 — `mse`·`window`는 CalibSet(OTHER) 소비(GSDF는 디스플레이 장치 데이터로 검출기 panel_id/resolution 키 스키마에 부적합, 확인 2).

## 리스크 및 완화

- **[High] GSDF LUT PS3.14 부적합(ε_gsdf 초과)** — 디스플레이 특성 파라미터화 오류·LUT 보간 편차로 JND당 대비 응답이 GSDF에서 이탈. 완화: 결정론 LUT 구성·감사 가능(REQ-POST-GSDF-1), 자가검사 편차 `HistoryEntry.extra` 기록, ε_gsdf 외부 주입 이진 게이트(하드 DoD).
- **[High] MSE/DRC가 MTF 파괴(EV-102 초과)** — 과도한 power-law 증폭·DRC가 SRb 열화. 완화: SWR-803 노이즈 게이팅으로 소신호 과증폭 억제, MTF@Nyquist 유지율 EV-102 min 가드레일(REQ-POST-VALIDATE-4), IQA 대리 halo/overshoot 부재 검사.
- **[High] 스테이지 배치 T0 표면 변경** — `CANONICAL_ORDER` 2개 스테이지 신설이 하류 SPEC 회귀. 완화: 결정 1(denoise와 post 사이 전용 `mse`·`window`), 등록 stages = 부분수열 검증 하위호환(T5 선례), `post` 예약 tail 유지.
- **[Medium] XFrame.noise 무단 기본값(SWR-803)** — 입력 XFrame.noise (0,0) 사용 시 노이즈 게이트 무의미. 완화: 부재·퇴화 거부(REQ-POST-MSE-4), T5 CONTRACT-2 핸드오프 계약 최초 소비 검증.
- **[Medium] TC-012·013 지각 지표 대리 한계** — IQA 스코어·관찰자 수용률은 본질적으로 지각·관찰자 의존이라 P1 합성 대리 지표로 완전 대체 불가. 완화: PARTIAL 게이트 명시(객관 대리 + 기준선 스냅샷 비열화 + MTF 가드레일), 실 관찰자 평가(EV-204)는 인허가 이연 명문화.
- **[Medium] SWR-802 ⚠P 특허 리스크** — 변조 함수형이 벤더 청구항과 충돌 가능. 완화: power-law 기본형 + soft-clip 대안 예비(REQ-POST-MSE-5), 특허 클리어런스는 릴리스 게이트(P1 밖)로 ⚠P 플래그 보존(T8 처리 계승).
- **[Low] 실측·디스플레이 프로파일 부재** — 부위 프리셋·디스플레이 휘도 실측 대기. 완화: 파라미터화 + 합성 기지값 선검증, 실측 도착 후 치환은 게이트 아님(부록 A 정책).

## 검증 전략

- 모든 판정은 `tests/`에서 모듈 + T1 지표 엔진(MTF 가드레일)·기지값·PS3.14 대조로 수행(모듈은 `metrics` 미import — CONTRACT-3).
- EV 임계·ε_gsdf·윈도우 허용오차·IQA 대리 임계는 외부 주입(측정=판정 분리). 처리·판정 코드에 임계 내장 금지.
- harness 단독 시험(합성 입력 + 기대 출력 fixture)으로 모듈 격리 검증(XDET-TC-000 계승).
- 하드 DoD(XDET-TC-014 GSDF PS3.14)는 결정론 이진 게이트; PARTIAL(XDET-TC-012/013)은 합성 기지값·객관 대리 지표로 정직하게 부분 판정하고 관찰자 의존 부분을 인허가 이연으로 명시.
