# XDET 영상처리 SW P1 — 구조 개요

## 현재 상태

현재 저장소에는 `docs/`(사양·계획 문서)와 설정/메타 파일(`.moai/`, `.claude/`, `CLAUDE.md`, `.mcp.json` 등)만 존재하며, `common/ modules/ pipeline/ metrics/ tests/ data/` 등 구현 스캐폴드는 아직 생성되지 않았다. 아래 트리는 T0(프레임워크) 단계에서 구축할 계획된 구조이다.

## 계획된 디렉터리 트리 (T0 산출물)

```
iop-algorithm/
├── common/           # 공용 컴포넌트 5종 (1회만 구현, 중복 금지)
│   ├── pyramid/          # 이미지 피라미드 연산
│   ├── histogram/        # 히스토그램·조사야(FOV) 분석
│   ├── fft_psd/          # FFT/PSD 스펙트럼 분석
│   ├── robust_stats/     # 강건 통계(median, MAD 등)
│   └── mask_ops/         # 마스크 스택 연산
├── modules/          # 파이프라인 처리 모듈 (WP1~WP10, process() 단일 시그니처)
│   ├── offset/           # SWR-101~104
│   ├── gain/             # SWR-201~204
│   ├── defect/           # SWR-301~304
│   ├── lag/              # SWR-401~404
│   ├── line_noise/       # SWR-501~504
│   ├── saturation_geom/  # SWR-601~603
│   ├── vst_bm3d/         # SWR-701~706
│   ├── mse_drc/          # SWR-801~805
│   ├── auto_window_gsdf/ # SWR-901~903
│   ├── grid_suppress/    # SWR-1001~1006
│   ├── virtual_grid/     # SWR-1101~1103 (⚠ 특허 대조 플래그)
│   ├── ndt/              # SWR-1201~1204
│   └── tier_identity/    # SWR-1301~1303
├── pipeline/         # 오케스트레이터 — 모듈 조합 정의 (모듈 간 직접 호출 금지, 여기서만 조합)
├── metrics/          # 지표 산출 엔진 (T1) — MTF/NPS/NNPS/DQE/lag/bad pixel/SNRn/duplex wire
├── tests/            # pytest 케이스 (TC-000~021), 모듈별 fixture 동봉
├── data/             # raw 16-bit + JSON 메타데이터, 골든 데이터셋 (Git LFS)
└── docs/             # 사양·계획 문서 (현재 유일하게 존재하는 디렉터리)
```

## 디렉터리별 목적

- **common/**: 여러 모듈이 공유하는 알고리즘 컴포넌트를 단 한 곳에만 구현한다. pyramid(다중 해상도 처리), histogram/FOV(조사야 및 직접선 분석), FFT/PSD(주파수 영역 분석 — grid 억제·MTF 산출에 공용), robust_stats(강건 통계 — defect/line noise 등에 공용), mask_ops(불량/포화/보간 마스크 연산)의 5종으로 구성된다.
- **modules/**: 각 처리 단계를 독립 모듈로 구현한다. 모든 모듈은 `process(XFrame, CalibSet, Params) -> XFrame` 단일 시그니처의 순수함수로 작성되며, common/의 컴포넌트만 참조할 수 있다(모듈 간 직접 참조 금지).
- **pipeline/**: 모듈을 조합하는 오케스트레이터 정의 파일이 위치한다. 파이프라인 순서 결정과 모듈 조합은 오직 여기서만 이루어진다.
- **metrics/**: 영상 품질을 정량화하는 측정 엔진. MTF(edge 기반, 자동 각도추정 → oversampled ESF → LSF → FFT), NPS/NNPS(256×256 ROI), DQE, first-frame lag, E2597 기준 bad pixel 통계, SNRn(=SNR×88.6µm/SRb), duplex wire 자동판독(20% dip)을 포함한다.
- **tests/**: TC-000(모듈별 단위시험)부터 TC-021(정수/float 경로 동일성)까지 전체 시험 케이스를 pytest로 등록한다. 모듈 CI 통과가 파이프라인 통합의 선행 조건이다.
- **data/**: raw 16-bit 영상과 메타데이터(JSON), 골든 데이터셋을 Git LFS로 관리한다.
- **docs/**: SWR/EVAL/TestSpec/측정프로토콜 등 사양 문서의 단일 출처. 아래 "docs/ 문서 지도" 참고.

## 아키텍처 강제 규칙 (위반 시 머지 불가 — SWR-000-6~12)

1. **단일 시그니처**: 모든 모듈은 `process(XFrame, CalibSet, Params) -> XFrame`으로 구현하며 순수함수형이어야 한다(부작용 없음).
2. **XFrame 데이터 구조**: pixel(float32) + 마스크 스택(defect/포화/보간) + 노이즈모델(α, σ) + 처리 이력 체인으로 구성된다. 이 구조 밖의 사이드채널을 통한 데이터 전달은 금지된다.
3. **모듈 간 직접 호출 금지**: 모듈은 서로를 직접 호출할 수 없다. 조합은 오직 pipeline/ 오케스트레이터를 통해서만 이루어지며, 의존 방향은 module → common 단방향이다.
4. **공용 컴포넌트 중복 금지**: pyramid/히스토그램·조사야/FFT·PSD/강건통계/마스크연산의 5종은 common/에 1회만 구현하고 모든 모듈이 재사용한다.
5. **CalibSet 공통 스키마**: 패널 ID, 해상도, 유효기간, 종류, 데이터, 이력을 포함하는 공통 스키마를 모든 캘리브레이션 데이터에 적용한다.
6. **모듈별 fixture 동봉 단위시험(TC-000)**: 각 모듈은 자체 fixture와 단위시험을 포함해야 하며, 통합 전 모듈 CI 통과가 의무이다.
7. **정밀도 동일성**: 정수 경로는 bit-동일, float 경로는 최종 출력 기준 ±1 LSB 이내를 유지해야 한다(TC-021로 검증. 수치 기준의 원 출처는 SWR-1302, CLAUDE.md에서 승계).
8. **구현 교체 계약(SWR-000-12)**: golden model / 최적화 구현 / FPGA 구현이 동일한 시그니처를 공유하여 상호 교체 가능해야 한다.

## docs/ 문서 지도

| 파일 | 역할 |
|---|---|
| XDET_SWR_spec_v1.2.md | 구현 사양의 단일 출처 — 모든 코드는 SWR ID에 대응 |
| XDET_EVAL_criteria_v1.1.md | 합격 기준(EV min/typ/max) |
| XDET_TestSpec_v1.0.md | 시험 케이스(TC) — CI 등록 대상 |
| XDET_measurement_protocol_v1.0.md | 지표 산출 엔진 구현 사양 |
| XDET_FRD_v1.1 / PRD_v1.0 / MRD_v1.0 / RTM_v1.1 | 요구사항·추적 (변경 시 RTM 경유) |
| XDET_P1_dev_plan_v1.0.md | WP(Work Package) 정의 |
| 기타 (TRM/PRM/VV/crosscheck 로그/영상취득세트) | 배경·계획 참조 |

## 모듈 조직: T0~T10 작업 단계 매핑

| 단계 | 대상 | 산출물/DoD |
|---|---|---|
| T0 | 프레임워크(repo 스캐폴드, XFrame, CalibSet, 오케스트레이터, 모듈 harness, 의존방향 정적검사, CI 골격) | SWR-000-1~12, TC-000 통과 |
| T1 | metrics/ 지표 산출 엔진 (MTF/NPS/NNPS/DQE/lag/bad pixel/SNRn/duplex wire) | 합성 팬텀으로 기지값 재현 (TC-001~009, 018 판정 엔진) |
| T2 | WP1: offset/gain/defect | TC-001~003 (합성+실측) |
| T3 | WP3+WP4: line noise, 포화/기하 | TC-006~009 |
| T4 | WP2: lag (지수합 IRF, M=3~4) | TC-004~005 |
| T5 | WP5: VST+BM3D | TC-010~011 |
| T6 | WP6+WP7: MSE/DRC, 자동윈도우/GSDF | TC-012~014 |
| T7 | WP8: grid line suppression | TC-015~016 |
| T8 | WP9: 커널 virtual grid | TC-017 |
| T9 | WP10: NDT | TC-018~019 |
| T10 | 티어/동일성 프레임 | TC-020~021 구조 통과 (절대 시간은 P2) |

작업은 T0부터 순서대로 진행하며, T0(프레임워크)는 다른 모든 작업의 전제 조건이다.
