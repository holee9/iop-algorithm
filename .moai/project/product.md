# XDET 영상처리 SW P1 — 제품 개요

## 프로젝트명

XDET 영상처리 SW P1 (SW Reference / Golden Model)

## 설명

X-ray FPD(Flat Panel Detector, CsI 섬광체, 픽셀 피치 140µm, 해상도 3072×3072 / 3072×2560, 16-bit raw 출력)로부터 취득한 원본 영상을 물리적으로 검증 가능한 방식으로 보정·강화하는 영상처리 소프트웨어이다.

P1 단계의 목표는 "SW 레퍼런스/골든 모델" 확립이다. raw 16-bit 프레임을 입력으로 받아 보정/강화된 영상을 출력하되, DQE(Detective Quantum Efficiency), MTF(Modulation Transfer Function), NPS(Noise Power Spectrum) 등 영상 품질 지표가 파이프라인 전 구간에서 훼손되지 않음을 **수치적으로 증명**하는 것이 핵심이다. P1에서는 모든 품질 판정이 자동화된 지표 엔진으로 이루어지며, 사람이 영상을 직접 판독하는 observer study는 범위에 포함되지 않는다.

## 대상 사용자

- **의료 방사선 도메인**: 진단용 X-ray 영상 판독 워크플로우를 사용하는 방사선사·의료영상 엔지니어
- **NDT(비파괴검사) 도메인**: 산업용 방사선 검사(ISO 17636-2, ASTM E2597 기준) 담당 엔지니어

## 3개 도메인 구조

| 도메인 | 목적 |
|---|---|
| **Common Core** | 검출기 물리 특성 보정 (offset/gain/defect/lag/line noise/saturation/geometry) — 모든 응용 도메인의 공통 기반 |
| **Medical Post** | 진단 목적 영상 강화 (노이즈 억제 VST+BM3D, 계조 압축 MSE/DRC, 자동 윈도우/GSDF, grid line 억제, virtual grid) |
| **NDT Post** | 산업용 방사선 검사 특화 처리 (SNRn 실시간 산출, IQI 자동판독, 두께 보정) — ISO 17636-2 / ASTM E2597 준거 |

## 핵심 기능: 파이프라인 13 모듈

| 순서 | 모듈 | SWR ID | 설명 |
|---|---|---|---|
| WP1-1 | Offset correction | SWR-101~104 | 암전류/오프셋 보정 |
| WP1-2 | Gain correction | SWR-201~204 | 감도 불균일 보정 |
| WP1-3 | Defect correction | SWR-301~304 | E2597 기반 불량 픽셀 분류(7-class, over/under 계수 방식에 따라 6~7종 — 원문 docs에 계수 기준 미명시) + edge-directed 보간 |
| WP2 | Lag correction | SWR-401~404 | 지수합 IRF 재귀 모델 (M=3~4) |
| WP3 | Line noise suppression | SWR-501~504 | 라인 노이즈 억제 |
| WP4 | Saturation/geometry | SWR-601~603 | 포화 영역 처리(복원 금지) + 기하 보정 |
| WP5 | VST + BM3D | SWR-701~706 | GAT(분산안정화)+정확 무편향 역변환, BM3D(8×8/step3/N2=16/Ns=39/λ2.7/Haar) 마스크 가중 노이즈 억제 |
| WP6 | MSE/DRC | SWR-801~805 | Laplacian(L=7) 다중스케일 에지 강화 + power-law/linear cutoff 동적범위 압축 |
| WP7 | 자동 윈도우/GSDF | SWR-901~903 | FOV 인식 → 직접선 분리 → 3단계 VOI → GSDF LUT 적용 |
| WP8 | Grid line suppression | SWR-1001~1006 | 관측 스펙트럼 피크 직접 탐색(aliasing-aware) + 1D Gaussian notch, 명목 grid 주파수 사용 금지 |
| WP9 | Virtual grid | SWR-1101~1103 | SKS 다운샘플 반복 (⚠ 특허 대조 플래그 유지) |
| WP10 | NDT | SWR-1201~1204 | Welford 알고리즘 실시간 SNRn, IQI 자동판독, 두께 보정 |
| — | Tier/동일성 프레임 | SWR-1301~1303 | HW 실행 역량(CPU/AVX/GPU/VRAM) 기반 티어 판정·gating 및 golden/optimized/FPGA 구현 간 동일성 검증 구조 |

프레임워크 공통 규칙: SWR-000-1~12

## 유스케이스

1. **의료 진단 영상 파이프라인**: raw 프레임 취득 → 공통 보정(offset/gain/defect/lag) → line noise/saturation/geometry 보정 → VST+BM3D 노이즈 억제 → MSE/DRC 계조 처리 → 자동 윈도우/GSDF → (필요 시) grid 억제·virtual grid → 최종 진단용 영상 출력
2. **NDT 검사 파이프라인**: 공통 보정 이후 SNRn 실시간 계산, IQI 자동판독으로 이미지 품질 지수 확인, 두께 보정 적용 → 검사 리포트 생성
3. **지표 검증 워크플로우**: 합성 팬텀(기지 MTF/노이즈 프로파일)을 입력으로 지표 산출 엔진(MTF/NPS/DQE 등)의 정확도를 자체 검증

## P1 범위

- Python 기반 float 정밀도 골든 모델 구현 (WP1~WP10, T0~T10)
- 13개 파이프라인 모듈 + 지표 산출 엔진 구현
- TC-000~021 전체 pytest 케이스 CI 통과
- 합성 팬텀 기반 지표 엔진 자체 검증 + 실측 데이터 기반 모듈별 검증

## P1 비범위 (Gen 2 — 구현하지 않음)

- DL(딥러닝) 기반 처리 모듈
- ADR(Adaptive Dose Reduction) 등 적응형 알고리즘
- 속도 최적화 (P1은 정확도 단일 목표, 최적화는 P2에서 수행)
- Observer study(인간 판독 기반 품질 평가)
- 절대 처리 시간 성능 기준 (T10에서 구조만 통과, 수치 임계는 P2)

## 완료 정의 (Definition of Done)

Gen 1 대상 TC-000~021 CI 전체 통과 + 골든 모델 형상 동결(config freeze). Gen 2 항목(DL, ADR)은 P1에서 구현하지 않는다.

## 참고 문서 지도

| 파일 | 역할 |
|---|---|
| XDET_SWR_spec_v1.2.md | 구현 사양의 단일 출처(SSOT) |
| XDET_EVAL_criteria_v1.1.md | 합격 기준(EV min/typ/max) 단일 출처 |
| XDET_TestSpec_v1.0.md | 시험 케이스(TC) 정의 — CI 등록 대상 |
| XDET_measurement_protocol_v1.0.md | 지표 산출 엔진 구현 사양 |
| XDET_FRD/PRD/MRD/RTM | 요구사항·추적 매트릭스 |
| XDET_P1_dev_plan_v1.0.md | WP(Work Package) 정의 |
