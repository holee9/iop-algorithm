# CLAUDE.md — XDET 영상처리 SW P1 구현 핸즈오프

이 저장소는 X-ray FPD(CsI, 140µm, 3072×3072/3072×2560, 16-bit raw) 영상처리 SW의 P1(SW 레퍼런스/골든 모델) 구현이다. 본 문서가 작업 순서와 규칙의 단일 출처이며, 상세 사양은 docs/ 폴더의 문서를 따른다.

## 문서 지도 (docs/)

| 파일 | 역할 |
|---|---|
| XDET_SWR_spec_v1.2.md | **구현 사양의 단일 출처** — 모든 코드는 SWR ID 대응 |
| XDET_EVAL_criteria_v1.1.md | 합격 기준 (EV min/typ/max) |
| XDET_TestSpec_v1.0.md | 시험 케이스 (TC) — CI 등록 대상 |
| XDET_measurement_protocol_v1.0.md | 지표 산출 엔진 구현 사양 |
| XDET_FRD_v1.1 / PRD_v1.0 / MRD_v1.0 / RTM_v1.1 | 요구·추적 (변경 시 RTM 경유) |
| XDET_P1_dev_plan_v1.0.md | WP 정의 |
| 기타 (TRM/PRM/VV/로그/영상취득세트) | 배경·계획 참조 |

## 기술 스택 (P1)

- Python 3.11+, numpy/scipy 기반 **float 골든 모델** (속도 최적화 금지 — 정확도 단일 목표, P2에서 최적화)
- pytest + CI (모든 TC는 pytest 케이스로 등록)
- 데이터: raw 16-bit + 메타데이터 JSON. 골든 데이터셋은 data/ (LFS)

## 아키텍처 강제 규칙 (위반 시 머지 불가 — SWR-000-6~12)

1. 모든 모듈: `process(XFrame, CalibSet, Params) -> XFrame` 단일 시그니처, 순수함수형
2. XFrame = pixel(float32) + 마스크 스택(defect/포화/보간) + 노이즈모델(α,σ) + 처리 이력 체인. 사이드채널 금지
3. 모듈 간 직접 호출 금지 — 조합은 오케스트레이터(파이프라인 정의 파일)만
4. 공용 컴포넌트 5종(pyramid/히스토그램·조사야/FFT·PSD/강건통계/마스크연산)은 common/에 1회 구현, 중복 금지
5. CalibSet 공통 스키마 (패널 ID·해상도·유효기간·종류·데이터·이력)
6. 모듈마다 fixture 동봉 단위시험 (TC-000) — 통합 전 모듈 CI 통과 의무
7. 정수 경로 bit-동일, float 경로 최종 출력 ±1 LSB (TC-021 대비)

## 작업 우선순위 (이 순서대로 구현)

### T0 — 프레임워크 (최우선, 다른 모든 작업의 전제)
- repo 스캐폴드: `common/ modules/ pipeline/ metrics/ tests/ data/ docs/`
- XFrame, CalibSet, 오케스트레이터, 모듈 harness, 의존방향 정적검사, CI 골격
- 사양: SWR-000-1~12 | DoD: TC-000 통과

### T1 — 지표 산출 엔진 (metrics/)
- MTF(edge, 자동 각도추정→oversampled ESF→LSF→FFT), NPS/NNPS(256×256 ROI), DQE, first-frame lag, bad pixel 통계(E2597 분류), SNRn(=SNR×88.6µm/SRb), duplex wire 자동판독(20% dip)
- 사양: 측정프로토콜 전체 | DoD: 합성 팬텀 입력으로 기지값 재현 (TC-001~009, 018의 판정 엔진)
- 주의: 실측 영상 도착 전 — 합성 데이터(기지 MTF/노이즈 주입)로 엔진 자체를 검증

### T2 — WP1: offset/gain/defect (modules/)
- SWR-101~104, 201~204, 301~304 | DoD: TC-001~003 (합성+실측)
- noisy 6× median은 E2597-22 확정 [S], dead/over-under/non-uniform 임계는 [P] — Params로 외부화

### T3 — WP3+WP4: line noise, 포화/기하
- SWR-501~504 (reference 부재 시 503 대안 경로 우선 구현), 601~603 | DoD: TC-006~009

### T4 — WP2: lag
- SWR-401~404: 지수합 M=3~4 재귀 상태변수. IRF 피팅 도구 포함 (다중 노출 step-response 입력) | DoD: TC-004~005. IRF 파라미터는 2단계 실측 대기 — 합성 IRF로 선검증

### T5 — WP5: VST+BM3D
- SWR-701~706: GAT + exact unbiased inverse(LUT), BM3D(8×8/step3/N2=16/Ns=39/λ2.7/Haar) 또는 검증된 오픈 구현 래핑 + 마스크 가중 | DoD: TC-010~011 (VST 왕복 무편향 필수)

### T6 — WP6+WP7: MSE/DRC/자동윈도우/GSDF
- SWR-801~805 (Laplacian L=7, power law+선형 컷오프), 901~903 (조사야 인식→직접선 분리→VOI 3단계, GSDF LUT) | DoD: TC-012~014

### T7 — WP8: Grid line suppression
- SWR-1001~1006: **관측 스펙트럼 피크 직접 탐색 (aliasing 전제 — 명목 grid 주파수 사용 금지)**, 1D Gaussian notch, 저주파 접힘 시 경고, 미검출 시 무처리 통과 | DoD: TC-015~016 (grid 밀도 3부류 합성 데이터 포함)

### T8 — WP9: 커널 virtual grid
- SWR-1101~1103: SKS 다운샘플 반복. ⚠P — 구현하되 릴리스 전 특허 대조 플래그 유지 | DoD: TC-017

### T9 — WP10: NDT
- SWR-1201~1204: Welford 적산+실시간 SNRn, IQI 자동판독·리포트, 두께보정 | DoD: TC-018~019

### T10 — 티어/동일성 프레임
- SWR-1301~1303: 티어 판정·gating 구조 (수치 임계는 P2), diff 검증 훅 | DoD: TC-020~021 구조 통과 (절대 시간은 P2)

## 파라미터 정책

- TBD-[B] (실측 대기 9건) / TBD-[T] (튜닝 11건): 전부 Params/CalibSet로 외부화 — 하드코딩 금지. SWR 부록 A 레지스터 참조
- [P] 등급 수치는 기본값으로 넣되 config에서 주석으로 [P] 표기

## 금지 사항

- 파이프라인 순서 임의 변경 (SWR-000-2)
- 캘리브레이션 부재 시 기본값 무단 대체 (SWR-000-5)
- 포화 영역 "복원" (SWR-602)
- 점근 역 Anscombe 사용 (SWR-703)
- 명목 grid 주파수 기반 notch (SWR-1001)

## 완료 정의 (P1 전체)

Gen 1 대상 TC-000~021 CI 전체 통과 + 골든 모델 형상 동결. Gen 2 항목(DL, ADR)은 구현하지 않는다.
