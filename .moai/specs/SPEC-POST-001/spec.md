---
id: SPEC-POST-001
version: 0.2.0
status: implemented
created: 2026-07-09
updated: 2026-07-09
author: drake.lee
priority: high
issue_number: 7
---

# SPEC-POST-001 — T6 WP6 다중스케일 대비강화(MSE)/DRC + WP7 자동 윈도잉/GSDF 처리 모듈 (modules/)

XDET 영상처리 SW P1의 일곱 번째 작업 T6. 의료용 표시 후처리 두 작업 **WP6(다중스케일 대비강화 + DRC, SWR-801~805)**·**WP7(자동 윈도잉 + GSDF, SWR-901~903)**을 각각 전용 처리 모듈 `modules/mse.py`·`modules/window.py`로 T0 프레임워크의 단일 계약 `process(XFrame, CalibSet, Params) -> XFrame` 순수함수형으로 구현한다. WP6은 **(1) Laplacian 피라미드 L레벨 분해(공용 컴포넌트 `common/pyramid.py`, SWR-801) → (2) 레벨별 power-law 대역 변조(SWR-802) + 레벨별 로컬 노이즈 게이팅(SWR-803, T5가 XFrame.noise에 기록한 (α, σ) 소비) → (3) DRC 최저역 압축(SWR-804) → (4) 재합성 후 백분위 기준 범위 정규화(SWR-805, 포화 마스크 제외)**의 순서로, WP7은 **(1) 조사야 인식 → (2) 직접선·차폐 분리 → (3) 유효 해부 히스토그램 VOI [p_low, p_high] 산출(공용 컴포넌트 `common/histogram_fov.py`, SWR-901) + 부위 프리셋·수동 오버라이드(SWR-902) → (4) P-value → PS3.14 GSDF JND 인덱스 매핑 LUT(SWR-903)**의 순서로 구성된다. 두 단계는 고정 파이프라인 순서 offset → gain → defect → lag → line noise → 포화 → 기하 → denoise → **mse → window** → post 중 전용 `mse`·`window` 스테이지(denoise와 post 사이)에서만 실행된다(결정 1, 「결정 필요/확인 사항」 1). **⚠P: SWR 8장(다중스케일 대비강화 + DRC) 전체가 특허 대조 대상**으로, SWR-802 변조 함수형은 청구항 대조 후 확정하는 릴리스 게이트 항목이며 P1은 power-law 기본형을 구현하되 대안 함수형(soft-clip 계열)을 예비 정의한다(「결정 필요/확인 사항」 3). 실측·관찰자 데이터 도착 전에는 **기지 해부 신호를 주입한 합성 팬텀으로 대비강화 비열화·자동 윈도우 정합·GSDF 적합성을 선검증**한다.

- 근거: SWR-801~805(MSE/DRC, FR-M001~M003, ⚠P) · SWR-901~903(자동 윈도잉/GSDF, FR-M004/M005) · SWR-000-1~12(아키텍처, 특히 SWR-000-9 공용 컴포넌트 pyramid/히스토그램·조사야 분리) — `docs/XDET_SWR_spec_v1.2.md`; EVAL v1.1 XDET-EV-205(자동 윈도우 수용률) / XDET-EV-204(GSDF 적합 PS3.14) / XDET-EV-102(MTF·SRb 열화 — 대비강화 가드레일, 맥락 인용); TestSpec XDET-TC-012~014; 측정프로토콜(MTF 지표 엔진 — 가드레일 판정)
- 완료 정의(DoD): **합성 팬텀으로 MSE/DRC 비열화 + 자동 윈도우 정합 + GSDF 적합성을 검증** — 실측·관찰자 데이터 도착 전, (a) **[하드 DoD] GSDF LUT PS3.14 적합성**(XDET-TC-014): 파라미터화된 디스플레이 특성(최소/최대 휘도)으로 구성한 P-value → JND 인덱스 매핑 LUT의 JND당 대비 응답 편차 최댓값이 외부 주입 임계 `ε_gsdf` 이내임을 결정론적으로 이진 판정한다(SWR-903 자가검사 리포트, GSDF=[S]). (b) **자동 윈도우 정합**(XDET-TC-013, PARTIAL): 기지 VOI [p_low, p_high]를 주입한 부위별 합성 팬텀에서 자동 산출 윈도우가 기지값 허용오차 내에 드는 비율(무수정 수용 대리 지표)이 EV-205 min(≥85%) 이상임을 판정한다 — 실 관찰자 무수정 수용률은 인허가/실측 이연. (c) **MSE/DRC 비열화**(XDET-TC-012, PARTIAL): 대비강화/DRC 적용 후 객관 IQA 대리 지표(로컬 대비 개선·세부대역 에너지 보존·halo/overshoot/클리핑 부재)가 기준선 스냅샷 대비 비열화이고, 가드레일로 `metrics/mtf` MTF@Nyquist 유지율이 EV-102 min(≥90%) 이상임을 판정한다 — 지각 IQA·관찰자 평가(EV-204)는 인허가 이연. XDET-TC-012·013·014를 pytest skeleton(skip)에서 실동작 케이스로 전환
- 선행 계약: [SPEC-INFRA-001](../SPEC-INFRA-001/spec.md) — `process` 계약·XFrame 불변·마스크 스택 비트플래그(DEFECT=1/SATURATION=2/INTERPOLATION=4/SATURATION_BAND=8)·이력 체인(`HistoryEntry.extra` 스칼라 진단 위탁 채널)·오케스트레이터 진입 게이트(CalibSet 존재·해상도·패널 ID·유효기간·종류-단계 배선)·import-linter 레이어링(`module → common` 단방향)·`CANONICAL_ORDER`·XFrame `NoiseModel(alpha, sigma)` 필드·공용 컴포넌트 스텁 `common/pyramid.py`(SWR-000-9 ①); [SPEC-METRICS-001](../SPEC-METRICS-001/spec.md) — 판정 엔진 `metrics/mtf.compute_mtf`/`mtf_value_at`(MTF 가드레일)·공용 컴포넌트 `common/histogram_fov.py`(detect_fov/largest_uniform_region — T1 최초 구현, SWR-000-9 첫-소비자 이연 원칙(SPEC-INFRA-001 Exclusions)에 따라 T6가 확장../SPEC-DENOISE-001/spec.md) — **T5가 해결된 노이즈 모델 (α, σ)를 출력 XFrame.noise 필드에 기록(CONTRACT-2 확정)하여 T6 SWR-803 노이즈 게이팅이 재사용**·전용 스테이지 신설의 부분수열 하위호환 선례(결정 1)·마스크 제외 substrate 계약·오프라인 빌더/무단 기본값 대체 금지 선례
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.2.0 (2026-07-09)** — 구현 완료(status: implemented). 커밋 ec9c7c0(mse/window/pyramid 구현) + 리뷰 결함 10건 수정. 288 passed / 7 skipped(2회 동일), 계약 5건 KEPT. 확정:
  - 포화 '값 보존'은 도메인 최댓값 매핑(raw DN 유입 금지) — mse/window 공통.
  - σ_ℓ 전파는 LSI 자기상관 전파(laplacian_band_noise_gains, 측정 대비 1~4% 이내) — coarse 레벨 노이즈 게이트 정확도 확보.
  - DRC는 상위 K개 레벨 합(B, mse_drc_low_levels [T])을 압축 대상으로 함(SWR-804 준수).
  - 콜리메이션 검출은 로그공간 Otsu + gap-ratio 가드(경계 우세 프레임에서도 강건).
  - GSDF TC-014는 PS3.14 독립 정의 앵커 대조를 포함(순환 잔차 지표 한계를 문서화하고 보강).
  - 피라미드 레벨 부족 시 조용한 절단 대신 명시 오류.

- **v0.1.1 (2026-07-09)** — plan-audit iter1(FAIL 0.76) 반영. 「결정 필요/확인 사항」 1·2 확정 + 결함 D1~D7 국소 수정:
  1. **결정 1 확정(RESOLVED)**: 전용 `mse`·`window` 스테이지를 `denoise`와 `post` 사이에 신설 확정(`CANONICAL_ORDER = … → geometry → denoise → mse → window → post`), `post`는 예약 tail 유지. 등록 stages = `CANONICAL_ORDER` 부분수열 검증으로 하류 미등록 SPEC 하위호환(T5 결정 1 선례). T0 표면 변경 run-blocking 해소.
  2. **확인 2 확정(RESOLVED)**: 디스플레이 특성·부위 프리셋 VOI = **Params 단일 소재**. CalibSet(OTHER)는 진입 게이트 충족용 **빈 placeholder**(payload 미탑재, 신규 CalibKind 미신설). CalibSet(OTHER) payload 소재 대안 표기 제거(disjunction 해소) — Environment·REQ-POST-WINDOW-2 동기화.
  3. **D1(필수)**: MTF@Nyquist 유지율 방향 오기 수정 — DoD(c)·REQ-POST-VALIDATE-4·acceptance Scenario 3의 "EV-102 min 이내" → "EV-102 min(≥90%) 이상"(3곳 통일).
  4. **D3(필수)**: REQ-POST-WINDOW-4(Event-Driven) 신설 — VOI 확정 시 유효 신호를 [p_low, p_high] 윈도우로 P-value 재매핑. REQ-POST-GSDF-1의 WHEN 트리거("윈도우 적용 P-value")를 산출하는 상류 REQ를 양방향으로 명시(추적성 공백 해소). acceptance 신규 Scenario 11(기지 입력 → 기대 P-value/JND 수치 대조) + DoD 체크박스 추가.
  5. **D2**: REQ-POST-DRC-1 B_mid 산출을 단일 결정론 규칙으로 — Params 제공 시 그 값, 미제공 시에만 `common/robust_stats` 산출(fallback 순서 고정, disjunction 제거).
  6. **D4**: 「결정 필요/확인 사항」 6에 최초 기준선 의미론 명문화 — 외부 주입 절대 IQA 대리 임계 + EV-102 가드레일 선통과 → `tests/fixtures` 스냅샷 커밋 → 이후 회귀 전용(자기 자신 기준 자명 통과 순환 차단).
  7. **D5**: DoD에 REQ-POST-VALIDATE-6(XDET-TC-012~014 skeleton→실동작 전환) 체크박스 추가.
  8. **D6**: acceptance Scenario 8 "골/연부 동시 가시화"를 조작적 정의로 — 최저역 동적범위 압축률 > 0 ∧ 세부대역 에너지 보존율 ≥ 주입 임계.
  9. **D7**: Environment에 [P] 등급 프리셋 수치의 config `[P]` 주석 표기 의무 1문장 추가(부록 A-2 근거). 「결정 필요/확인 사항」 4에 soft-clip 대안 함수형이 문헌상 선형-구간 형태를 포괄 가능함을 기록.
  - status: draft 유지(run 착수 전). 결정 1 run-blocking 해소로 run 착수 가능.

- **v0.1.0 (2026-07-09)** — 초안 생성. GitHub 이슈 #7. 6개 요구 그룹(MSE/DRC/WINDOW/GSDF/CONTRACT/VALIDATE) EARS 구조 확정. 핵심 범위 결정:
  1. **두 전용 스테이지 신설(run-blocking, 「결정 필요/확인 사항」 1)**: WP6·WP7이 하나의 `post` 슬롯에 대응해야 하나, WP별 개별 스테이지 선례(line_noise/saturation/geometry/denoise)와 T5 부분수열-삽입 하위호환 선례를 따라 전용 `mse`(WP6)·`window`(WP7) 스테이지를 `denoise`와 `post` 사이에 신설한다(`CANONICAL_ORDER = … → geometry → denoise → mse → window → post`). `post`는 예약 tail로 유지(T5 결정 1의 "기존 post 실현" 기각 계승). 가정 default이며 T0 표면(`CANONICAL_ORDER`) 변경이므로 run-blocking.
  2. **노이즈 게이팅(SWR-803) = T6 소관·XFrame.noise 소비**: T5(SPEC-DENOISE-001 CONTRACT-2)가 해결된 (α, σ)를 출력 XFrame.noise에 기록하므로, `mse` 모듈은 **입력 XFrame.noise에서 (α, σ)를 소비**하여 레벨별 로컬 노이즈 σ_ℓ을 전파하고 증폭 억제 게이트 g = c²/(c²+β·σ_ℓ²)를 적용한다(SWR-803 [C]). (0, 0) 기본값·퇴화 시 거부(무단 기본값 대체 금지, SWR-000-5; T5 REQ-DENOISE-VST-2 선례) — Unwanted 요구(REQ-POST-MSE-4).
  3. **⚠P 특허 플래그(SWR 8장·SWR-802)**: SWR 8장 전체가 특허 대조 대상이고 SWR-802 변조 함수형은 청구항 대조 후 확정한다(릴리스 게이트). P1은 power-law 기본형(SWR-802)을 구현하되 대안 함수형(soft-clip 계열, SWR-802 예비 정의)을 Optional로 유지한다(REQ-POST-MSE-5). 특허 클리어런스·릴리스 게이트는 P1 범위 밖(T8 SWR-1101/1103 ⚠P 처리 방식 계승).
  4. **공용 컴포넌트 최초 구현(SWR-000-9)**: `common/pyramid.py`(T0 스텁 `build_pyramid`)는 `mse`가 **최초 소비자**로서 Laplacian/Gaussian 분해·재합성을 구현하고(SWR-801, 커널 5×5 [1 4 6 4 1]/16), `common/histogram_fov.py`(T1 구현)는 `window`가 조사야 인식·직접선 분리로 확장한다(SWR-901; SWR-000-9 첫-소비자 이연 원칙에 따른 T6 확장). 중복 구현 금지(SWR-000-9), 계층은 `module → common` 단방향 유지.
  5. **하드 DoD = GSDF PS3.14 적합(XDET-TC-014)**: T6의 결정론적 이진 게이트는 GSDF LUT의 PS3.14 적합성(=[S])이다. TC-012(IQA 비열화)·TC-013(윈도우 수용률)은 지각·관찰자 의존 지표로 합성 기지값·객관 대리 지표를 쓰는 **PARTIAL 게이트**로 명시한다(EV-204 관찰자·지각 IQA는 인허가 이연; T5 EV-101/T3 EV-106 PARTIAL 선례).
  6. **"선형 컷오프" 해석 default**: CLAUDE.md T6 "power law + 선형 컷오프"의 "선형 컷오프"는 SWR-805 백분위([p0.1, p99.9]) 기준 선형 재매핑(포화 마스크 제외)으로 해석한다. 소신호 과증폭 억제는 SWR-803 노이즈 게이트가 담당하며 별도 선형 구간을 발명하지 않는다(「결정 필요/확인 사항」 4).
  - 파라미터 등급 확정(SWR 부록 A/A-2 대조): Laplacian 분해 방식(SWR-801)=[L](부록 A-2, Dippel TMI 2002), 레벨 수 L=7·튜닝(SWR-801)=[T](부록 A); power-law 변조(SWR-802)=[L](부록 A-2, Vuylsteke 1994), γ_ℓ·p_ℓ(SWR-802)=[T](부록 A), 변조 함수형=⚠P; 노이즈 게이팅(SWR-803)=[C](부록 A-2), β=부록 A 미등재([T] 등재 요청); DRC γ_DRC·B_mid(SWR-804)=부록 A/A-2 미등재(무등급, 등재 요청); 범위 정규화 백분위 p0.1/p99.9(SWR-805)=SWR 본문 명시값·부록 A 미등재(무등급, 등재 요청); 자동 윈도우 3단계 구조(SWR-901)=[L](부록 A-2), VOI [p_low, p_high] 부위 프리셋(SWR-901)=[T](부록 A); 부위 프리셋 테이블(SWR-902)=무등급(config); GSDF(SWR-903)=[S](부록 A-2, GSDF PS3.14), 디스플레이 특성=Params, GSDF 적합 임계 ε_gsdf=부록 A 미등재([S]-인접, 등재 요청).
  - status: draft (run 단계 착수 전까지 유지; 「결정 필요/확인 사항」 1은 run-blocking 확정 대상).

## Environment / Assumptions

- Python 3.11+, numpy/scipy 기반 float 골든 모델(tech.md). **속도 최적화 금지 — 정확도 단일 목표**(P2에서 최적화). 현재 `pyproject.toml` 의존성은 numpy/scipy 전용이며, MSE 피라미드·DRC·자동 윈도우·GSDF LUT를 전부 자체 numpy/scipy로 구현하므로 신규 의존성을 추가하지 않는다.
- 대상 프레임: 3072×3072 / 3072×2560, 16-bit unsigned raw, pitch 140µm, Nyquist f_N = 3.57 lp/mm(EVAL v1.1 §0). Laplacian 피라미드 L=7은 3072 기준 최상위 근사 ≈ 24×24(SWR-801).
- **실측·관찰자 데이터 도착 전 — 합성 팬텀으로 모듈을 검증한다.** 기지 해부 히스토그램(골/연부 이중 분포)·기지 VOI [p_low, p_high]·기지 노이즈 모델 (α, σ)를 주입한 합성 팬텀으로 대비강화 비열화(IQA 대리)·자동 윈도우 정합(수용 대리)·GSDF PS3.14 적합성을 확인한다.
- **용어 정의 — 합성 검증 컨텍스트(synthetic-validation context)**: 합성 팬텀 fixture 시험 실행(기지 신호/히스토그램/노이즈 주입 → 처리 후 판정)을 가리키는 단일 용어로, T0(SPEC-INFRA-001)의 검증 모드(validation_mode — float64 병행 버퍼·단계별 중간 XFrame 보존)와는 별개 개념이다. SPEC-CORR/LNSG/LAG/DENOISE의 동명 정의를 계승한다.
- T0 계약 소비: `mse`·`window` 모듈은 XFrame(불변)을 입력받아 새 XFrame을 반환하는 **무상태 처리 모듈**이며(lag과 달리 내부 상태 없음) `process(XFrame, CalibSet, Params) -> XFrame` 계약을 따른다. 마스크 스택 비트플래그·이력 체인·오케스트레이터 진입 게이트·`CANONICAL_ORDER`를 그대로 소비한다. 의존 방향은 `modules → common` 단방향(import-linter). 지표 엔진(`metrics/mtf`)·기지값 대조 판정은 `tests/`에서만 소비한다(모듈은 `metrics` 미import).
- **노이즈 모델 소비(SWR-803)**: `mse` 모듈은 상류 T5(denoise)가 출력 XFrame.noise에 기록한 노이즈 모델 (α, σ)를 소비하여 레벨별 로컬 분산 σ_ℓ²(≈ α·signal + σ²의 레벨 전파)을 산출하고 노이즈 게이트에 사용한다. XFrame.noise 기본값 (0, 0)만 존재하거나 α ≤ 0로 퇴화하면 무단 사용하지 않고 거부한다(무단 기본값 대체 금지, SWR-000-5; T5 REQ-DENOISE-VST-2 선례). T5가 유일 소재이며 `mse`는 재추정하지 않는다.
- **마스크 소비**: `mse`(SWR-805 범위 정규화 백분위 산출)·`window`(SWR-901 유효 해부 히스토그램)는 상류 누적 마스크 스택(DEFECT/INTERPOLATION/SATURATION/SATURATION_BAND)에서 포화·결함 화소를 백분위·히스토그램 통계에서 제외하며, 어떤 마스크 플래그도 신규 설정·해제하지 않는다(마스크 substrate는 상류 소관). 조사야·직접선 영역은 `window` 단계 내부 산출물로 다루며 신규 마스크 플래그를 도입하지 않는다(「결정 필요/확인 사항」 5).
- **공용 컴포넌트(SWR-000-9)**: ① 피라미드 분해/재합성은 `common/pyramid.py`(T0 스텁, `mse` 최초 구현)에 1회 구현, ② 히스토그램 분석·조사야/직접선 분리는 `common/histogram_fov.py`(T1 구현, `window` 확장)에서, ④ 강건 통계(백분위·MAD)는 `common/robust_stats`, ⑤ 마스크 연산은 `common/mask_ops`에서 소비한다. 중복 구현 금지. GSDF LUT는 공용 5종에 없으므로 `modules/window.py` 내부 구현이며 디스플레이 특성 Params로부터 결정론적으로 구성된다(오프라인 캘리브레이션 빌더 아님 — 측정 데이터 미소비).
- 물리·튜닝·무등급 상수(레벨 수 L, 커널, γ_ℓ·p_ℓ, 노이즈 게이트 β, DRC γ_DRC·B_mid, 정규화 백분위 p0.1/p99.9, VOI 프리셋 [p_low, p_high], 부위 프리셋 테이블, 디스플레이 최소/최대 휘도, GSDF 적합 임계 ε_gsdf, IQA 대리 임계)는 전부 **Params 단일 소재**로 외부화한다(하드코딩 금지). CalibSet(OTHER)는 진입 게이트 충족용 빈 placeholder이며 파라미터 payload를 담지 않는다(「결정 필요/확인 사항」 2 확정). 등급은 SWR 부록 A/A-2를 따르며 미등재 항목은 등재 요청한다.
- **[P] 등급 프리셋 표기 의무**: 부위 프리셋·디스플레이 특성 등에서 [P] 등급(제안값, 부록 A-2 근거 등급)을 기본값으로 넣을 경우 config에 주석으로 `[P]`를 표기해야 한다(CLAUDE.md 파라미터 정책 — [P]는 기본값 삽입 허용하되 근거 등급 명시).
- EV 판정 수치(EVAL v1.1 EV-205 / EV-204 GSDF 적합 / EV-102 min·가드레일)와 GSDF 적합 임계 ε_gsdf·IQA 대리 임계·윈도우 정합 허용오차는 **엔진·모듈 외부에서 주입**된다(측정=판정 분리, METRICS/CORR/LNSG/LAG/DENOISE 계승). 처리 모듈·판정 코드는 게이트 임계를 내장하지 않는다.

## Requirements (EARS)

### REQ-POST-MSE — 다중스케일 대비강화(피라미드 + 대역 변조 + 노이즈 게이팅) (SWR-801~803, FR-M001/M002)

- **REQ-POST-MSE-1 (Event-Driven)** — WHEN `mse` 모듈이 입력 XFrame을 처리하면, THEN 시스템은 공용 컴포넌트 `common/pyramid.py`로 Laplacian 피라미드 L레벨(L=7 @3072 기준, Gaussian 커널 5×5 [1 4 6 4 1]/16)을 분해해야 한다(SWR-801; 분해 방식 [L], 레벨 수·튜닝 [T] 부록 A). 피라미드 분해/재합성은 `common/`에 1회 구현하며 중복 구현하지 않는다(SWR-000-9 ①).
- **REQ-POST-MSE-2 (Event-Driven)** — WHEN 피라미드 레벨 계수 c가 산출되면, THEN 시스템은 레벨별 power-law 변조 c′ = γ_ℓ · sign(c) · |c|^p_ℓ (p_ℓ ∈ (0, 1] 소신호 상대 증폭)을 적용해야 한다(SWR-802 기본형 [L], γ_ℓ·p_ℓ [T] 부록 A). γ_ℓ·p_ℓ는 레벨·프리셋별 Params 외부화(하드코딩 금지).
- **REQ-POST-MSE-3 (Event-Driven)** — WHEN 대역 변조를 적용하면, THEN 시스템은 상류 XFrame.noise (α, σ)로 산출한 레벨별 로컬 노이즈 σ_ℓ에 대해 증폭 억제 게이트 g = c²/(c² + β·σ_ℓ²)를 곱해 노이즈 미만 계수의 증폭을 억제해야 한다(SWR-803 [C], β는 부록 A 미등재 [T] 등재 요청). σ_ℓ은 T5가 XFrame.noise에 기록한 (α, σ) 모델의 레벨 전파로 산출한다.
- **REQ-POST-MSE-4 (Unwanted)** — IF `mse` 단계 입력 XFrame.noise가 부재하거나 퇴화(α ≤ 0, 또는 기본값 (0, 0)만 존재)하면, THEN 시스템은 SWR-803 노이즈 게이팅을 무단 기본값으로 수행하지 않고 명시 오류로 거부해야 한다(무단 기본값 대체 금지, SWR-000-5; T5 CONTRACT-2가 (α, σ)를 XFrame.noise에 기록하므로 정상 파이프라인에서는 항상 존재). 결정론적 단일 경로 — 추정·대체 분기 없음.
- **REQ-POST-MSE-5 (Optional)** — WHERE Params가 SWR-802 대안 변조 함수형(soft-clip 계열 예비 정의, ⚠P 특허 대조 대응)을 선택하면, 시스템은 power-law 대신 대안 함수형을 동일한 노이즈 게이팅·DRC·정규화 계약 하에서 적용해야 한다. 대안 미선택 시 본 요구는 적용되지 않으며 REQ-POST-MSE-2(power-law 기본형)를 사용한다. 경로 선택은 Params 값으로 결정론적으로 이뤄진다. 특허 클리어런스·릴리스 게이트는 P1 범위 밖이다(「결정 필요/확인 사항」 3).

### REQ-POST-DRC — 동적범위 압축(DRC) + 재합성 + 범위 정규화 (SWR-804~805, FR-M003)

- **REQ-POST-DRC-1 (Event-Driven)** — WHEN 피라미드 최저역(최상위 복수 레벨 합) 성분 B가 산출되면, THEN 시스템은 압축 곡선 B′ = B_mid + (B − B_mid)·γ_DRC (γ_DRC < 1)를 적용하고 미압축 세부 대역과 재합성하여 골/연부를 동시 가시화해야 한다(SWR-804; γ_DRC·B_mid는 부록 A/A-2 미등재 무등급, Params 외부화·등재 요청). B_mid(중간역 기준)는 단일 결정론 규칙으로 산출한다 — Params로 제공되면 그 값을 사용하고, 미제공 시에만 `common/robust_stats` 강건 통계로 산출한다(fallback 순서 고정, 분기 없음).
- **REQ-POST-DRC-2 (Event-Driven)** — WHEN 세부 대역과 최저역을 재합성한 뒤, THEN 시스템은 유효 신호 범위 [p0.1, p99.9] 백분위를 기준으로 선형 재매핑(범위 정규화, "선형 컷오프")하되 포화 마스크(SATURATION·SATURATION_BAND) 화소를 백분위 산출에서 제외해야 한다(SWR-805; 백분위값 SWR 본문 명시·부록 A 미등재 무등급, Params 외부화·등재 요청). 백분위 산출은 `common/robust_stats`, 마스크 제외는 `common/mask_ops`를 소비한다(SWR-000-9 ④⑤).

### REQ-POST-WINDOW — 자동 윈도잉(조사야 인식 → 직접선 분리 → VOI + 부위 프리셋) (SWR-901~902, FR-M004)

- **REQ-POST-WINDOW-1 (Event-Driven)** — WHEN `window` 모듈이 입력 XFrame을 처리하면, THEN 시스템은 3단계 [L] 구조 — ① 조사야(collimation field) 인식으로 조사야 외 영역 제외(edge 기반) → ② 직접선(direct exposure)·차폐 영역 분리(히스토그램 모드/entropy) → ③ 유효 해부 히스토그램에서 VOI [p_low, p_high] 산출 — 를 수행해야 한다(SWR-901 구조 [L] 부록 A-2, VOI 백분위 프리셋 [T] 부록 A). ①② 조사야/직접선 분리는 공용 컴포넌트 `common/histogram_fov.py`(T1 구현)를 확장하여 소비하며 중복 구현하지 않는다(SWR-000-9 ②).
- **REQ-POST-WINDOW-2 (Event-Driven)** — WHEN 촬영 부위 코드가 입력되면, THEN 시스템은 부위 프리셋 테이블에서 해당 부위의 VOI 백분위 프리셋을 선택해야 한다(SWR-902; 프리셋 테이블 무등급 config·Params 단일 소재 외부화, 「결정 필요/확인 사항」 2 확정).
- **REQ-POST-WINDOW-3 (Optional)** — WHERE 수동 윈도우 오버라이드가 Params로 제공되면, 시스템은 자동 산출 VOI 대신 오버라이드 [p_low, p_high]를 사용하고 오버라이드 발생을 이력 체인(`HistoryEntry.extra`)에 기록해야 한다(SWR-902 수동 오버라이드 허용, 오버라이드율 로깅 → EV-205 개선 입력). 오버라이드 미제공 시 본 요구는 적용되지 않으며 REQ-POST-WINDOW-1 자동 VOI를 사용한다.
- **REQ-POST-WINDOW-4 (Event-Driven)** — WHEN VOI [p_low, p_high]가 확정되면(REQ-POST-WINDOW-1 자동 산출 또는 REQ-POST-WINDOW-3 오버라이드), THEN 시스템은 유효 신호를 [p_low, p_high] 윈도우로 P-value에 재매핑해야 한다(윈도우 내 신호를 표준 P-value 스케일로 선형 매핑, SWR-901 VOI 적용). 이 재매핑 출력 P-value가 REQ-POST-GSDF-1의 WHEN 트리거("윈도우가 적용된 P-value")를 산출하는 상류이다(REQ-POST-WINDOW-4 → REQ-POST-GSDF-1 양방향 추적).

### REQ-POST-GSDF — GSDF LUT(P-value → PS3.14 JND 매핑) + 적합 자가검사 (SWR-903, FR-M005)

- **REQ-POST-GSDF-1 (Event-Driven)** — WHEN 윈도우가 적용된 P-value가 산출되면(REQ-POST-WINDOW-4 재매핑 출력이 이 트리거를 산출), THEN 시스템은 파라미터화된 디스플레이 특성(최소/최대 휘도, Params)으로 구성한 LUT로 P-value를 DICOM PS3.14 GSDF JND 인덱스에 매핑해야 한다(SWR-903, GSDF=[S] 부록 A-2). LUT는 디스플레이 특성으로부터 결정론적으로 구성되며 감사 가능해야 한다.
- **REQ-POST-GSDF-2 (Event-Driven)** — WHEN GSDF LUT가 구성되면, THEN 시스템은 JND당 대비 응답 편차를 산출하는 적합 자가검사 지표를 이력 체인(`HistoryEntry.extra`)에 기록해야 한다(SWR-903 적합 자가검사 리포트, XDET-TC-014). 합격/불합격 임계 `ε_gsdf`는 내장하지 않고 외부(EVAL v1.1/Params)에서 주입되어 `tests/`에서 비교된다(측정=판정 분리).

### REQ-POST-CONTRACT — 공통 모듈 계약 준수 (SWR-000-2~12, REQ-INFRA-* 소비)

- **REQ-POST-CONTRACT-1 (Ubiquitous)** — `mse`·`window` 모듈은 각각 단일 시그니처 `process(XFrame, CalibSet, Params) -> XFrame` 순수함수형이어야 하며(SWR-000-7, REQ-INFRA-CONTRACT-1), 입력 XFrame을 불변으로 취급(원본 미변경)하고 새 XFrame을 반환해야 한다(SWR-000-3, REQ-INFRA-DATA-6). 두 모듈 모두 내부 상태를 보유하지 않는다(lag과 달리 상태 재귀 없음).
- **REQ-POST-CONTRACT-2 (Event-Driven)** — WHEN `mse`·`window` 모듈이 출력 XFrame을 생성하면, THEN 시스템은 처리 메타(모듈 버전 · 파라미터 해시 · 소비 CalibSet ID)와 스칼라 진단(적용 γ_ℓ/p_ℓ 요약 · 노이즈 게이트 β · γ_DRC · 정규화 범위 · VOI [p_low, p_high] · 오버라이드 여부 · GSDF JND 편차 등)을 이력 체인 엔트리(`HistoryEntry.extra`)에 결정론적으로 추가해야 한다(SWR-000-4, REQ-INFRA-DATA-4, IEC 62304 추적).
- **REQ-POST-CONTRACT-3 (Ubiquitous)** — 의존 방향은 `modules → common` 단방향이어야 하며, `mse`·`window` 모듈은 다른 처리 모듈 · `pipeline` · `metrics`를 import해서는 안 된다(SWR-000-8, REQ-INFRA-STATIC import-linter 계약). 실행 순서·조합은 오케스트레이터 단독 소관이며 모듈 간 직접 호출은 금지된다(REQ-INFRA-ORCH-1/2). 지표 엔진(`metrics/mtf`) 소비는 `tests/`에서만 이뤄진다.
- **REQ-POST-CONTRACT-4 (Unwanted)** — IF `mse`·`window` 모듈이 XFrame 컨테이너 외 채널(전역 상태 · 부가 반환값 · 파일 우회)로 데이터를 전달하려 하면, THEN 시스템은 이를 계약 위반으로 취급해야 한다(SWR-000-6 사이드채널 금지). 자동 검출 가능 범위는 시그니처·부가 반환값 위반(계약 검사)과 의존 방향 위반(import-linter 정적 검사)이며(acceptance.md EC-5의 검증 범위와 동일), 전역 상태·파일 우회는 테스트 가능 AC가 아닌 설계 규칙으로서 코드 리뷰 게이트로 다룬다(SPEC-INFRA-001 REQ-INFRA-DATA-2 방식 계승).
- **REQ-POST-CONTRACT-5 (Ubiquitous)** — `mse`·`window` 모듈은 고정 파이프라인 순서 `CANONICAL_ORDER`의 전용 `mse`·`window` 스테이지(denoise와 post 사이, 결정 1)에서만 실행되어야 하며(SWR-000-2, REQ-INFRA-ORCH-3; 등록 stages는 `CANONICAL_ORDER`의 부분수열), 합성 입력 + 기대 출력 fixture로 harness 단독 시험이 가능해야 한다(SWR-000-11, XDET-TC-000). 두 스테이지는 검출기 캘리브레이션이 없으므로 `_KIND_BY_STAGE`에 종류-단계를 강제하지 않으며, 진입 게이트 충족을 위해 CalibSet(OTHER)를 소비한다(geometry 선례; 「결정 필요/확인 사항」 2).
- **REQ-POST-CONTRACT-6 (Unwanted)** — IF `mse`·`window` 모듈이 포화 화소 값을 "복원"하거나(SWR-602 [HARD] 복원 금지 계승) 마스크 플래그를 신규 설정·해제하면, THEN 시스템은 이를 계약 위반으로 취급해야 한다. 두 모듈은 마스크를 통계 제외에만 소비하고 substrate를 변경하지 않는다. 결정론적 단일 경로.

### REQ-POST-VALIDATE — 합성 검증(GSDF 적합 + 윈도우 정합 + MSE/DRC 비열화) (XDET-TC-012~014, EV-205/204/102)

- **REQ-POST-VALIDATE-1 (State-Driven)** — WHILE 실측·관찰자 데이터 도착 전 합성 검증 컨텍스트인 동안, 시스템은 기지 해부 히스토그램·기지 VOI·기지 (α, σ)·파라미터화된 디스플레이 특성을 주입한 합성 팬텀으로 MSE/DRC 비열화·자동 윈도우 정합·GSDF 적합성을 보여야 한다(DoD 전제, CLAUDE.md T6).
- **REQ-POST-VALIDATE-2 (Event-Driven)** — WHEN 파라미터화된 디스플레이 특성으로 GSDF LUT를 구성하면, THEN 시스템은 JND당 대비 응답 편차 최댓값을 산출하고 그것이 외부 주입 임계 `ε_gsdf` 이내임을 `tests/`에서 결정론적으로 이진 판정 가능해야 한다(XDET-TC-014 "GSDF LUT 적합성 자가검사", PS3.14 적합, GSDF=[S]). 이것이 T6의 하드 DoD이다.
- **REQ-POST-VALIDATE-3 (Event-Driven)** — WHEN 기지 VOI [p_low, p_high]를 주입한 부위별 합성 팬텀에 자동 윈도잉을 적용하면, THEN 시스템은 자동 산출 윈도우가 기지값 허용오차([T]) 내에 드는 비율(무수정 수용 대리 지표)을 `tests/`에서 산출하여 EV-205 min(≥85%) 이상임을 판정 가능해야 한다(XDET-TC-013 "자동 윈도우 수용률 집계", PARTIAL — 실 관찰자 무수정 수용률은 인허가/실측 이연).
- **REQ-POST-VALIDATE-4 (Event-Driven)** — WHEN 합성 팬텀에 MSE/DRC를 적용하면, THEN 시스템은 `tests/`에서 (a) 객관 IQA 대리 지표(로컬 대비 개선율 · 세부대역 에너지 보존 · halo/overshoot/클리핑 부재)가 기준선 스냅샷 대비 비열화이고, (b) 가드레일로 `metrics/mtf.compute_mtf`/`mtf_value_at` MTF@Nyquist 유지율이 EV-102 min(≥90%) 이상임을 판정 가능해야 한다(XDET-TC-012 "대비강화/DRC 자동 IQA 회귀, 기준 버전 대비 비열화", PARTIAL — 지각 IQA·관찰자 평가 EV-204는 인허가 이연). 최초 기준선 스냅샷은 외부 주입 절대 IQA 대리 임계 + EV-102 가드레일을 선통과한 뒤에만 `tests/fixtures`에 커밋되어 이후 비열화 회귀 기준으로 쓰인다(자기 자신 기준 자명 통과 순환 방지, 「결정 필요/확인 사항」 6).
- **REQ-POST-VALIDATE-5 (Ubiquitous)** — EV-205/204/102 min 및 GSDF 적합 임계 `ε_gsdf` · 윈도우 정합 허용오차 · IQA 대리 임계 판정 수치는 EVAL v1.1/Params에서 외부 주입되어야 하며, 검증은 산출값과 외부 임계의 비교로만 이뤄져야 한다(측정=판정 분리 계승). 처리 모듈·판정 코드는 게이트 임계를 내장하지 않는다.
- **REQ-POST-VALIDATE-6 (Ubiquitous)** — 시험 케이스 XDET-TC-012 · XDET-TC-013 · XDET-TC-014는 현재 pytest skeleton(skip)에서 합성 입력·판정 연동의 실동작 케이스로 전환되어야 한다(REQ-INFRA-CI-1 계승). 모듈은 `metrics`를 import하지 않으므로 MTF 가드레일 판정은 `tests/`에서 모듈 + 지표 엔진을 함께 소비하고, 윈도우 정합·GSDF 편차는 `tests/`에서 기지값·PS3.14 대조 직접 측정으로 판정한다.

## Exclusions (What NOT to Build)

- **후속·타 WP 처리 모듈 없음** — grid 억제(SWR-1001~1006/T7), 커널 virtual grid(SWR-1101~1103/T8), NDT(SWR-1201~1204/T9), 티어·동일성(SWR-1301~1303/T10)은 T6 범위 밖. 선행 offset/gain/defect(T2)·lag(T4)·line noise/포화/기하(T3)·denoise(T5)도 본 SPEC 범위 밖(이미 구현됨).
- **`post` 스테이지 실현 없음** — 결정 1로 `mse`·`window` 전용 스테이지를 신설하며 `post`는 예약 tail로 유지한다. `post`를 특정 WP로 실현하지 않는다(T5 결정 1 "기존 post 실현" 기각 계승; 후속 T7~T10의 스테이지 위치는 각 SPEC이 본 결정과 독립적으로 재확인).
- **노이즈 모델 (α, σ) 재추정 없음** — (α, σ)는 T5(SWR-701) 소관이며 T6는 T5가 XFrame.noise에 기록한 값을 SWR-803 게이팅에 소비만 한다. `metrics/noise_model.py` 빌더·재추정은 T5 소관(SPEC-DENOISE-001).
- **⚠P 특허 클리어런스·릴리스 게이트 없음** — SWR 8장·SWR-802 변조 함수형의 특허 청구항 대조·릴리스 게이트는 P1 범위 밖. P1은 power-law 기본형을 구현하되 soft-clip 대안 함수형을 예비 유지하고 ⚠P 플래그를 보존한다(T8 SWR-1101/1103 ⚠P 처리 계승).
- **관찰자 평가·지각 IQA 없음** — EV-204(ICC/VGA/관찰자 GSDF 판독)·지각 IQA는 인허가 제출용 관찰자 연구(XDET-TC-022) 대상으로 개발 게이트 아님. T6는 객관 대리 지표(윈도우 정합·GSDF PS3.14 편차·IQA 대리)로만 판정한다.
- **선량·CNR·scatter 지표 없음** — EV-201(노이즈 저감·선량)/EV-202(scatter)/EV-203(grid)은 T5·T7·T8 소관. T6는 MSE/DRC·윈도잉·GSDF만 담당한다.
- **신규 마스크 플래그 없음** — 조사야·직접선 영역은 `window` 단계 내부 산출물이며 XFrame 마스크 스택에 COLLIMATION/DIRECT_BEAM 플래그를 신규 도입하지 않는다(T0 표면 무변경, 「결정 필요/확인 사항」 5).
- **디스플레이 특성 실측 확정 없음** — GSDF 디스플레이 최소/최대 휘도는 파라미터화되며 실 디스플레이 프로파일 확정은 배치 시점. P1은 파라미터화된 특성으로 LUT 구성·PS3.14 적합만 검증.
- **EV 게이트 임계·IQA 기준선 절대값 내장 없음** — EV-205/204/102 및 ε_gsdf·윈도우 허용오차·IQA 대리 임계는 외부 주입. 처리 모듈·판정 코드는 합격/불합격 임계를 내장하지 않는다.
- **성능·처리시간·티어 게이트 없음** — EV-401/402, XDET-TC-020/021은 P2.

## 결정 필요/확인 사항

SWR 조항이 T0/T1/T5 구현과 모호하거나 상충하는 지점. **「1」·「2」는 plan-audit iter1에서 확정(RESOLVED)** — 「1」은 T0 표면(`CANONICAL_ORDER`)을 변경하던 run-blocking 항목(전용 `mse`·`window` 스테이지 신설), 「2」는 캘리브레이션 없는 스테이지의 CalibSet 소재 방침(Params 단일 소재 + CalibSet(OTHER) 빈 placeholder). **「3~7」은 확인 대상**으로 각 항목에 가정 default를 명시한다. 최종 확정은 orchestrator 결정(plan-audit)을 따른다.

1. **[확정 — RESOLVED] mse·window 파이프라인 스테이지 배치** — 전용 `mse`(WP6)·`window`(WP7) 스테이지를 `denoise`와 `post` 사이에 신설 확정한다(`CANONICAL_ORDER = … → geometry → denoise → mse → window → post`). `post`는 예약 tail로 유지(특정 WP로 실현하지 않음). **rationale**: 오케스트레이터 진입 게이트는 등록 stages가 `CANONICAL_ORDER`의 부분수열이면 통과하므로 스테이지 신설은 하류 미등록 SPEC에 하위호환(무영향, T5 결정 1 선례)이고, WP별 개별 스테이지 선례(line_noise/saturation/geometry/denoise)를 따른다. **기각 대안**: 기존 `post`를 `window`/GSDF로 실현 — WP 응집성 저해 + 후속 T7(grid)/T8(virtual grid)이 표시-실현된 `post` 앞에 삽입되어야 하는 오배치 유발, T5가 이미 "post 실현"을 기각. GSDF/mse는 검출기 캘리브레이션이 없어 종류-단계 게이트 논거(T5 NOISE-kind)가 적용되지 않으므로 kind 배선은 중립이고, 스테이지 분리 논거는 WP 응집·harness 격리·검증모드 중간프레임 보존이다. T0 표면(`CANONICAL_ORDER`) 변경 run-blocking은 본 확정으로 해소(plan-audit iter1).
2. **[확정 — RESOLVED] 캘리브레이션 없는 스테이지의 CalibSet 처리** — 진입 게이트는 등록 스테이지마다 CalibSet 존재를 요구하나(`_calibration_gate`) `mse`·`window`는 검출기 캘리브레이션이 없다. **확정**: 두 스테이지 모두 gate 충족을 위해 CalibSet(OTHER)를 소비하고(saturation/geometry 선례) `_KIND_BY_STAGE`에 종류-단계를 등재하지 않는다. `window`의 부위 프리셋 VOI 테이블·GSDF 디스플레이 특성은 **Params 단일 소재**로 외부화하며, CalibSet(OTHER)는 진입 게이트 충족용 **빈 placeholder**(파라미터 payload 미탑재)로만 소비한다 — CalibSet(OTHER) payload 소재 대안은 채택하지 않는다(disjunction 제거). **신규 CalibKind 미신설** — CalibSet 스키마는 검출기 panel_id·resolution 키 기반이라 디스플레이 장치 데이터(GSDF)에 부적합(T5 NOISE-kind는 검출기 관련이라 신설한 것과 대조). **rationale**: 파라미터의 단일 진리 소재를 Params로 고정하면 payload 이중화 없이 결정론적 주입이 보장되고, gate는 CalibSet 존재만 요구하므로 빈 placeholder로 충분하다.
3. **[확인] SWR 8장·SWR-802 ⚠P 특허 플래그** — SWR 8장 전체가 특허 대조 대상이고 SWR-802 변조 함수형은 청구항 대조 후 확정(릴리스 게이트)이다. **가정 default**: power-law 기본형(SWR-802)을 구현하고 soft-clip 대안 함수형(SWR-802 예비 정의)을 Optional(REQ-POST-MSE-5, Params 선택)로 유지하며, 특허 클리어런스·릴리스 게이트는 P1 범위 밖으로 ⚠P 플래그를 보존한다(T8 SWR-1101/1103 "구현하되 릴리스 전 특허 대조 플래그 유지" 계승). 확인: 대안 함수형 우선 여부, 릴리스 게이트 산출물 위치.
4. **[확인] CLAUDE.md T6 "선형 컷오프" 해석** — CLAUDE.md T6는 "power law + 선형 컷오프"로 표기하나 SWR-802 본문은 순수 power-law이다. **가정 default**: "선형 컷오프"는 SWR-805 백분위([p0.1, p99.9]) 기준 선형 재매핑(포화 마스크 제외, REQ-POST-DRC-2)으로 해석하며, 소신호 과증폭 억제는 SWR-803 노이즈 게이트(REQ-POST-MSE-3)가 담당한다. 별도 선형 구간(power-law 하단 선형 세그먼트)을 발명하지 않는다(no HOW 발명). soft-clip 계열 대안 함수형(REQ-POST-MSE-5)은 문헌상 선형-구간(piecewise-linear) 형태 — 저대비 구간 선형 + 고대비 구간 완만 포화 — 를 포괄할 수 있어 "선형 컷오프" 표기와 모순되지 않는다. 확인: SWR-802 대안 함수형(soft-clip)이 "선형 컷오프"를 포함하는지.
5. **[확인] 조사야/직접선 영역의 XFrame 마스크화 vs 내부 산출** — 마스크 스택에 COLLIMATION/DIRECT_BEAM 플래그가 없다(추가 시 T0 표면 변경). **가정 default**: `window`가 조사야/직접선 영역을 단계 내부 산출물로 다루고(신규 마스크 플래그 미도입), VOI 백분위·오버라이드율을 `HistoryEntry.extra`에 진단 기록한다. NDT(T9)가 조사야 정보를 재사용하지만 별개 취득 브랜치이므로 XFrame 마스크 지속화는 불필요. 확인: 하류 재사용 필요 시 마스크 플래그 신설 여부.
6. **[확인] TC-012 IQA 대리 지표·기준선 스냅샷** — XDET-TC-012 판정은 "IQA 스코어 기준선"(기준 버전 대비 비열화)이며 EV 수치가 없고 P1엔 선행 기준선이 없다. **가정 default**: 합성 팬텀에서 객관 IQA 대리 지표(로컬 대비 개선율·세부대역 에너지 보존·halo/overshoot/클리핑 부재)와 EV-102 MTF 가드레일로 최초 기준선 스냅샷을 산출하고, TC-012를 그 스냅샷 대비 비열화 회귀로 판정한다(PARTIAL). **최초 기준선 의미론(순환 방지)**: 최초 스냅샷은 (i) 외부 주입 **절대 IQA 대리 임계** + **EV-102 MTF 가드레일**을 먼저 통과해야 하며, (ii) 통과한 경우에 한해 스냅샷으로 `tests/fixtures`에 커밋되고, (iii) 이후 실행은 그 커밋된 스냅샷 대비 **비열화 회귀 전용**으로만 판정한다(최초 실행이 자기 자신을 기준으로 자명 통과하는 순환을 절대 임계 선통과로 차단). 지각 IQA·관찰자 수용(EV-204)은 인허가 이연. 확인: 절대 IQA 대리 임계값 크기·스냅샷 저장 위치(`tests/fixtures` 확정).
7. **[확인] ε_gsdf·IQA 대리 임계·β·γ_DRC·B_mid·정규화 백분위·VOI 프리셋의 부록 A 등재** — GSDF 적합 임계 ε_gsdf, IQA 대리 임계, 노이즈 게이트 β, DRC γ_DRC·B_mid, SWR-805 백분위(p0.1/p99.9), VOI [p_low, p_high] 프리셋 다수가 부록 A/A-2 미등재 또는 무등급이다. **가정 default**: 전부 Params로 외부화하고 부록 A 등재를 요청한다(튜닝값은 [T], GSDF 적합 임계는 [S]-인접 — PS3.14 표준이 적합 개념 정의; DENOISE ε_unbias·LNSG line_max_width 등재 요청 선례). 미등재 항목에 등재된 등급을 단정하지 않는다. 확인: 각 항목의 [T]/[S] 등재 등급·기본값 크기.
