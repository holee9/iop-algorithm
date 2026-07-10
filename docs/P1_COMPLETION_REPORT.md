# XDET P1 완료 보고서

**대상**: X-ray FPD(CsI, 140µm, 3072×3072 / 3072×2560, 16-bit raw) 영상처리 SW P1(레퍼런스/골든 모델)
**완료일**: 2026-07-10
**연관 이슈**: GitHub #1 ~ #12 (전건 CLOSED)

---

## 1. 개요

P1은 11개 SPEC(T0~T10)으로 구성되며, 각 SPEC은 GitHub 이슈 #1~#12에 1:1 대응되어(마지막 #12는 SPEC이 아닌 사용자 요청 E2E 스모크 통합 테스트) 전건 CLOSED 상태로 main 브랜치에 순차 병합 완료되었다.

CLAUDE.md가 정의하는 P1 완료 기준 원문은 다음과 같다.

> Gen 1 대상 TC-000~021 CI 전체 통과 + 골든 모델 형상 동결. Gen 2 항목(DL, ADR)은 구현하지 않는다.

이 기준의 충족 여부를 최종 수치로 요약하면 다음과 같다 (상세는 4절 품질 스냅샷 참조).

- 테스트: **465 passed, 0 skipped**
- XDET-TC-000~021 전 22개 ID가 `tests/` 내 실동작 형태로 존재함을 캡스톤 테스트가 강제 검증 (이연된 TC 없음)
- import-linter 아키텍처 계약: **6건 KEPT**

즉 "TC-000~021 CI 전체 통과 + 골든 모델 형상 동결"은 **구조적으로 충족**되었다. 다만 TC-020/021(티어·동일성 프레임)은 SPEC 설계 단계에서부터 절대 수치 판정이 P2로 명시 이연되어 있어, P1 범위는 구조 검증까지였다는 점은 별도로 유의해야 한다 (4절, README 딥싱크 섹션에서 재론).

Gen 2 항목(DL, ADR)은 CLAUDE.md 상 P1 범위에서 명시적으로 제외되어 있으며, 본 보고서가 다루는 작업 범위에도 포함되지 않는다.

---

## 2. 아키텍처 개요

P1 골든 모델은 4개 계층으로 구성된다. 모든 처리 모듈은 `process(XFrame, CalibSet, Params) -> XFrame` 단일 시그니처를 갖는 순수함수이며, 모듈 간 직접 호출은 금지되고 조합은 오케스트레이터에서만 이루어진다(SWR-000-6~12).

- **`common/`** — 전 모듈이 공유하는 데이터 구조 및 5종 공용 컴포넌트: `xframe.py`(XFrame), `calibset.py`(CalibSet), `contract.py`, `pyramid.py`(피라미드), `fft_psd.py`(FFT/PSD), `robust_stats.py`(강건통계), `mask_ops.py`(마스크 연산), `equivalence.py`(동일성 검증), `histogram_fov.py`(히스토그램/조사야)
- **`modules/`** — 순수함수형 처리 모듈: `offset.py`, `gain.py`, `defect.py`, `line_noise.py`, `saturation.py`, `geometry.py`, `lag.py`, `denoise.py`, `mse.py`, `window.py`, `grid.py`, `virtual_grid.py`
- **`pipeline/`** — 조합 계층: `orchestrator.py`(CANONICAL_ORDER 기반 모듈 조합), `sequence.py`(lag 등 상태보유 모듈을 위한 시퀀스 러너), `tier.py`(하드웨어 티어 게이팅)
- **`metrics/`** — T1 측정 엔진: `mtf.py`, `nps.py`, `dqe.py`, `lag_irf.py`, `defect_stats.py`, `defect_map.py`, `noise_model.py`, `scatter_kernel.py`, `ndt.py`, `result.py`

T9(NDT)과 T10(tier)은 CANONICAL_ORDER/CalibKind를 건드리지 않는 별도 계층(측정/인프라)이다. 두 SPEC 모두 독립 리뷰에서 T0가 정의한 오케스트레이터 표면(CANONICAL_ORDER, CalibKind)이 무변경임을 명시적으로 확인했다.

---

## 3. SPEC별 완료 이력

### #1 SPEC-INFRA-001 (T0, 프레임워크 스캐폴드)

- v0.1.0 초안 → plan-audit iter.1 **FAIL 0.74**(결함 D1~D6) → v0.1.1 → Run 완료(커밋 `64137f3`, 마일스톤 M1~M5)
- 독립 리뷰: 33에이전트 투입, 31건 검증, **확정 결함 10건**(게이트가 panel_id/kind/유효기간을 미검사, CalibSet 경로 절단, `with_pixel`이 float64 stale 상태 유지, `params_hash`가 비단사 등)
- 전량 수정 + 회귀 테스트 13건 추가 → 커밋 `23f1b42` → main 머지 `227be2c`
- 최종: **46 passed / 21 skipped**(이연 skeleton), import-linter 계약 4건

### #2 SPEC-METRICS-001 (T1, 측정엔진)

- v0.1.0 → plan-audit iter.1 **FAIL 0.71**(결함 D1~D12, critical: TC-005 ghost CNR이 의무/Optional 모순) → v0.1.1 → iter.2 **PASS 0.93**
- Run 완료(커밋 `bab37f5`: mtf/nps/dqe/lag/defect_stats/ndt/result + common 3종 첫 실구현)
- 독립 리뷰: 31에이전트, **확정 결함 10건**
  - **critical**: DQE 공식 차원 역전 — 원인은 `docs/XDET_measurement_protocol_v1.0.md` §1.4 공식 자체가 IEC 62220-1과 상충(코드는 문서를 충실 재현했을 뿐). IEC 표준형으로 코드 수정 + `@MX:WARN` 부착. **문서 자체는 개정되지 않음(미해결 — 5절 및 README 딥싱크 섹션에서 재론)**
  - **critical**: TC-001~003이 T2의 DoD인데 T1 테스트로 오용되어 미구현 보정 모듈이 green으로 표시됨(수정: skeleton 복원)
- 전량 수정 → 커밋 `c3f207a`까지 반영 → main 머지
- 최종: 80 → **90 passed**, import-linter 계약 4건

### #3 SPEC-CORR-001 (T2, offset/gain/defect)

- plan-audit iter.1 **FAIL 0.77**(결함 D1~D8 + BLOCK 2건: defect맵 생성기의 T2 포함 여부 결정, gain 범위밖 픽셀 처리 방식 결정) → iter.2 **PASS 0.93**
- Run 완료(커밋 `4451875`: `modules/offset·gain·defect` + `metrics/defect_map.py`, 테스트 28건)
- 독립 리뷰: **확정 결함 10건**
  - **critical**: 대형 블롭이 LINE으로 오분류되어 C_max 게이트를 우회(품질 미보증 영역이 조용히 보정되는 결함)
- 전량 수정 + 회귀 7건 → 커밋 `daa442e` → main 머지
- 최종: **118 passed / 18 skipped**, import-linter 계약 5건(modules 상호독립 구조 신설)

### #4 SPEC-LNSG-001 (T3, line noise + 포화/기하)

- plan-audit iter.1 **PASS 0.89**(결함 D1 + BLOCK: raw 포화 검출을 offset 모듈 소관으로 결정, SPEC-CORR-001에 REQ-CORR-OFFSET-4 소급 신설)
- Run 완료(커밋 `7ab0338`: `modules/line_noise·saturation·geometry` + `offset` v1.1.0)
- 독립 리뷰: **확정 결함 10건**
  - **critical**: geometry가 마스크 스택을 미수송(워프된 픽셀인데 SATURATION/DEFECT 플래그는 원좌표에 남아있어 하류 T5가 포화 픽셀을 유효 데이터로 오인)
- 전량 수정 → main 머지
- 최종: **148 passed / 14 skipped**, import-linter 계약 5건

### #5 SPEC-LAG-001 (T4, lag 보정)

- plan-audit iter.1 **PASS 0.89**(결함 D1~D7 + BLOCK: `pipeline/sequence.py`를 신규 러너로 도입해 시퀀스 처리, orchestrator 무수정 결정)
- Run 완료(커밋 `3d74e8e`: `modules/lag.py`(상태보유) + `sequence.py` + `metrics/lag_irf.py`)
- 독립 리뷰: **major만, critical 없음**
  - FB `confirm()` 반환값 폐기(핸드셰이크 실패가 무시됨) → 명시 오류로 수정
  - IRF 피팅 수렴 미검사
  - TC-005 게이트 약화(상대감소만 단언)
  - `pixel_f64`가 float32 양자화로 오염
- 전량 수정 → main 머지
- 최종: **174 passed / 12 skipped**, import-linter 계약 5건

### #6 SPEC-DENOISE-001 (T5, VST + BM3D)

- plan-audit iter.1 **FAIL 0.78**(결함 D1~D8 + BLOCK 3건: denoise 전용 스테이지 신설, `CalibKind.NOISE` 신설, **BM3D는 PyPI 패키지 대신 자체 numpy/scipy 구현 채택** — bm3d PyPI는 비상업 한정 라이선스+폐쇄 바이너리로 감사 불가/P2 상업 승계 리스크가 있기 때문. 오케스트레이터가 감사자 권고를 승인한 결정) → iter.2 **PASS 0.90**
- Run 완료(커밋 `0c2927b`)
- 독립 리뷰: **확정 결함 10건, critical 2건**
  - 역변환 LUT의 λ_max 클램프 초과 시 조용한 포스터화 → 도메인 검증 + 명시 오류로 수정
  - `PipelineDefinition.full()` 하드 회귀(denoise 스테이지 추가로 기존 호출자 전부 깨짐)
- 전량 수정 → main 머지
- TC-011(VST 왕복 무편향, 하드 DoD): exact-inverse 0.0017 / 출하경로 0.008 ≤ ε 달성(점근 역변환 음성대조 0.11 FAIL로 대조 검증)
- import-linter 계약 5건

### #7 SPEC-POST-001 (T6, MSE/DRC/자동윈도우/GSDF)

- plan-audit iter.1 **FAIL 0.76**(결함 D1~D7, 전부 국소적) → iter.2 **PASS 0.93**
- Run 완료(커밋 `ec9c7c0`: `pyramid.py` 최초 구현 + `mse.py` + `window.py`)
- 독립 리뷰: **확정 결함 10건**
  - **critical**: 포화 '값보존'이 정규화 출력 `[0,1]`에 raw DN(수천)을 그대로 주입 → 도메인 최댓값 보존으로 수정
  - σ_ℓ 독립잡음 가정 오류(ACF 전파로 교체)
  - GSDF 적합 자가검사가 순환검증(PS3.14 계수 오류 불검출) → 표준참조표 테스트로 교체
- 전량 수정 → main 머지
- 최종: **288 passed / 7 skipped**, import-linter 계약 5건

### #8 SPEC-GRID-001 (T7, grid line suppression)

- plan-audit iter.1 사실상 통과(프론트매터 스키마만 보정)
- Run 완료(커밋 `830d53d`: 관측 스펙트럼 협대역 피크 직접 탐색 — **명목 grid 주파수 절대 미사용**, aliasing negative control로 실증)
- 독립 리뷰: **major만, 5건**
  - 방향 선택이 빈-피크축 배경잡음 최댓값과 진짜 피크를 오비교
  - Nyquist 빈이 탐색에서 누락
  - 접힘 고조파 미구현
  - `notch_gain_1d`가 실제 notch 대비 1-term만 계산(과소보고)
  - TC-015(b) 하드 DoD가 조건문에 걸려 항상 통과하던 결함 → 무조건 검증으로 수정
- 전량 수정 → main 머지
- 최종: **327 passed / 5 skipped**, import-linter 계약 5건

### #9 SPEC-VGRID-001 (T8, 커널 virtual grid)

- plan-audit **PASS 0.85**(⚠P 특허플래그 US 11,911,202 원문 대조 검증 완료, 6개소 명시, 릴리스 게이트로 이연)
- Run 완료(커밋 `c5e2720`: SKS 산란추정 + 이중 Gaussian 커널 + `CalibSet(SCATTER)` REJECT 무기본값)
- 독립 리뷰: 결함 1건(정확도 무영향 cleanup) → main 머지
- TC-017(하드 DoD, EV-202 ≥ +20% CNR): 실측 약 57% 개선
- 최종: **367 passed / 4 skipped**, import-linter 계약 5건

### #10 SPEC-NDT-001 (T9, NDT)

- plan-audit iter.1 **FAIL 0.55**(**critical: EARS 비정형 서술** + Ambiguity 1 — 두께보정 출력 성격에 대해 FRD 문구 충돌 가능성 지적, 오케스트레이터가 사용자에게 확인 요청 → "내부 측정 전용, 하류 미노출"로 확정) → iter.2 **PASS 0.90**
- Run 완료(커밋 `fb6c4f0`: `common/robust_stats.py` `WelfordAccumulator` 첫 온라인누적기 + `metrics/ndt.py`)
- ⚠ 구현 중 명시 이탈 보고: TC-019 하드게이트 테스트가 기본값(`morphological_opening`) 대신 `gaussian` 메서드 사용 → 독립 리뷰가 이 편차를 조사 → **이 이탈이 실제 결함(과대 스케일 가드가 `morphological_opening`의 실제 커널크기(2*scale+1)를 미반영, 기본값 사용 시 조용히 손상된 출력)을 은폐하고 있었음을 확인**
- 그 외 **critical**: SNRn 누적기가 검증 전에 뮤테이션(거부된 zero-noise 프레임이 Welford 상태를 영구 오염)
- 전량 수정 + TC-019 게이트 정직성 재검증 → main 머지
- 최종: **405 passed / 2 skipped**, import-linter 계약 5건. T0 표면(CANONICAL_ORDER/CalibKind) 무변경 확인

### #11 SPEC-TIER-001 (T10, 티어/동일성 프레임 — P1 최종 SPEC)

- plan-audit iter.1 **FAIL 0.75**(D3: EC-3 이접조항 → 단일결정론 경로로 정정) → PASS
- 독립감사가 SWR/EVAL 원문에서 "tier=하드웨어 실행경로 분류이며 EV 화질등급이 아님"을 직접 재도출 검증
- Run 완료(커밋 `4e67292`: `pipeline/tier.py`의 `decide_tier`/`select_pipeline`/`run_tier`/`time_tier`(구조만) + `common/equivalence.py` 확장)
- 독립 리뷰: **critical 없음**, major 3건
  - `decide_tier`가 `params=None`일 때 미문서화 `AttributeError`
  - `INTEGER_PATH_STAGES`가 orchestrator `CANONICAL_ORDER`와 별도로 손수 복제(드리프트 시 조용히 FLOAT로 강등되어도 무감지)
  - capstone `_SKELETONS==[]` 단언의 공허통과 가능성(TC ID가 실동작 전환 없이 삭제돼도 무검출)
- 전량 수정 → main 머지
- 최종: **454 passed / 0 skipped**, import-linter 계약 5건. TC-020/021은 구조 DoD 통과, 수치 절대판정은 P2로 명시 이연(CLAUDE.md T10 항목: "절대 시간은 P2")

### #12 [TEST] E2E 스모크 통합 테스트

- P1 완료 후 사용자가 실제 구동 점검을 요청 → 표준 스크립트로 프로덕션 코드 전경로(오케스트레이터 + 실제 모듈 + 실제 CalibSet) 구동 확인
- `tests/test_e2e_smoke.py` 7개 테스트로 정식화: 6단계 보정체인 참값복원, MTF 엔진, T9 Welford SNRn √N 선량적산, T10 티어판정, T10 동일성 diff
- main 머지
- 최종: **465 passed**(신규 7건), import-linter 계약 **6건 KEPT**

---

## 4. 품질 스냅샷 (최종, 2026-07-10 기준 재확인됨)

| 항목 | 값 |
|---|---|
| 테스트 | **465 passed, 0 skipped** (실측 재실행, `uv run pytest -q` 146.52초) |
| import-linter 계약 | **6건 KEPT** (`pyproject.toml` `[[tool.importlinter.contracts]]` 6개) |
| TODO/FIXME/XXX | `modules/` `pipeline/` `metrics/` `common/` 전역 **0건** |
| XDET-TC 커버리지 | 전 22개 ID(TC-000~021) 전건이 `tests/` 소스에 실동작 형태로 존재함을 캡스톤 테스트(`tests/test_tc_skeletons.py::test_all_gen1_tc_skeletons_are_live`)가 강제 검증. `_SKELETONS=[]`, `_DEFERRED_GEN1_TC={}`(둘 다 공백 — 이연된 TC 없음) |

CLAUDE.md 완료정의 "TC-000~021 CI 전체 통과 + 골든 모델 형상 동결"은 **구조적으로 충족**되었다. 단, TC-020/021은 절대 수치 판정이 SPEC 자체에서 P2로 명시 이연되어 있음(구조 DoD만 P1 대상)이라는 뉘앙스는 정확히 전달되어야 한다: "전건 CI 통과"는 참이지만, 그중 2건(TC-020/021)은 애초 SPEC 설계상 절대 임계 판정이 아니라 구조 검증까지가 P1 범위였다.

---

## 5. 아키텍처/기술부채 메모

**⚠P 특허 플래그**: SWR 문서 내 8절(grid), 11절(virtual grid/kernel), 5절 일부(denoise 인접 — MSE/Laplacian pyramid, FRD FR-M001 "특허 회피 확인 후 SWR 확정" 미해결 상태로 존재) 등 다수 개소에 존재한다. 전역 정책은 "특허 검토는 릴리스 게이트로 이연"(PRM v1.1 원칙 — 특허는 탑재가부 게이트가 아니라 HOW의 리스크관리 항목)이다. TRM v2.1은 일부(Fuji DRC 특허 US 5,357,549, 2011년 만료 확인)는 해소했으나, 2010년대 virtual-grid 세대 특허군(Kodak US 6,269,176 / US 7,050,618, Siemens DRZ 계열, Carestream US 7,832,928)은 "유효 추정, 개별 검증 미완, 법률검토 필요" 상태로 남아있다. PRM v1.1의 79행은 "상세설계(FR/SWR) 착수 전까지" 특허 변호사 검토를 요구하나, SWR 문서에는 ⚠P 플래그만 있을 뿐 완료된 검토의 증적은 확인되지 않는다 — 프로세스 준수 갭으로 기록한다.

**DQE 측정 프로토콜 문서 불일치**: `docs/XDET_measurement_protocol_v1.0.md` §1.4의 공식이 IEC 62220-1과 차원이 맞지 않는 오류가 T1(SPEC-METRICS-001, 이슈 #2) 리뷰에서 발견되어 코드(`metrics/dqe.py`, 커밋 `41ec640`)는 올바른 형태로 수정되었으나, **문서 자체는 한 번도 개정되지 않았다**(생성 이후 커밋 이력 1건 = 최초 작성). 코드와 원본 사양서가 불일치 상태로 남아있다.

**SWR 부록 A/A-2 미갱신**: SWR 부록 A(TBD 레지스터) · 부록 A-2(근거등급 총괄)는 T0 최초 작성 이후 갱신 이력이 전무하다(문서 커밋 이력 1건). 11개 SPEC 각각의 plan-audit 결함 코멘트에서 "신규 TBD 파라미터를 부록 A/A-2에 등재 요청"이 반복적으로 언급되었으나 실제 등재는 이뤄지지 않았다. 부록 A는 여전히 SWR ID 범위 요약(2줄)만 존재하고, 개별 파라미터별 세부 항목은 없다.

**실측([B]) 의존 밀도**: SPEC별 "실측" 언급 횟수(대략적 척도) — INFRA 0, METRICS 6, CORR 6, LNSG 7, LAG 15, DENOISE 8, POST 6, GRID 4, VGRID 13, NDT 5, TIER 0. LAG와 VGRID가 가장 실측 의존적(전자는 IRF 파라미터, 후자는 SKS 산란커널)이다. 이는 P2 진입 전 실제 패널 데이터 확보의 우선순위 신호로 읽을 수 있다(판단은 독자에게 맡긴다 — 본 문서는 사실만 기술한다).

---

## 6. 다음 단계 안내

본 문서는 "완료" 보고서이며 권고 문서가 아니다 — P1 산출물의 사실관계를 기록하는 데 목적이 있고, 여기서 결론을 내리지 않는다. P2 착수 필요성에 대한 검토는 저장소 루트 `README.md`의 별도 섹션("P2 착수 필요성 — 딥싱크 검토")에서 다룬다.
