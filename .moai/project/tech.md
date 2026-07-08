# XDET 영상처리 SW P1 — 기술 스택 및 정책

## 기술 스택

- **언어/런타임**: Python 3.11+
- **수치 연산**: numpy, scipy 기반 float 골든 모델
- **시험 프레임워크**: pytest + CI 파이프라인 (모든 TC는 pytest 케이스로 등록)
- **데이터 관리**: raw 16-bit 영상 + JSON 메타데이터, 골든 데이터셋은 `data/`에 Git LFS로 관리

## float 골든 모델 원칙

P1 단계에서는 **정확도가 유일한 목표**이며, 속도 최적화는 명시적으로 금지된다. 최적화(성능 튜닝, FPGA 이식 등)는 P2 단계에서 별도로 수행한다. 이는 다음을 의미한다:

- 모든 모듈은 numpy/scipy를 이용한 float32/float64 연산으로 구현하며, 벡터화나 저수준 최적화보다 사양 대비 정확성을 우선한다.
- 정밀도 검증은 정수 경로 bit-동일, float 경로 ±1 LSB 기준(TC-021)으로 이루어진다.
- 구현 교체 계약(SWR-000-12)에 따라 golden model 구현은 이후 최적화 구현·FPGA 구현과 동일한 `process(XFrame, CalibSet, Params) -> XFrame` 시그니처를 공유해야 하며, 이를 통해 P2 최적화 시 알고리즘 동일성을 검증할 수 있다.

## 파라미터 외부화 정책

모든 조정 가능한 수치는 하드코딩하지 않고 Params 또는 CalibSet으로 외부화한다. SWR 부록 A 레지스터가 전체 목록의 단일 출처이다.

- **TBD-[B] (9건)**: 실측(Bench measurement) 대기 파라미터. 실제 패널/시스템 측정값이 도착하기 전까지는 잠정값을 사용하며, 반드시 Params/CalibSet 외부 설정으로 관리한다. (예: WP2 lag의 IRF 파라미터는 2단계 실측 대기 중이며, 그 전까지는 합성 IRF로 엔진을 선검증한다.)
- **TBD-[T] (11건)**: 튜닝(Tuning) 대기 파라미터. 알고리즘 동작을 좌우하는 임계값 등으로, 검증 과정에서 조정될 수 있으므로 하드코딩을 금지한다. (예: defect 분류의 dead/over-under/non-uniform 임계값)
- **[P]-grade 값**: 잠정(Provisional) 등급의 기본값. config에 기본값을 넣되 반드시 `[P]`로 주석 표기하여 확정값이 아님을 명시한다.

## 데이터 형식

- **입력**: raw 16-bit 영상 (3072×3072 또는 3072×2560), 픽셀 피치 140µm, CsI 섬광체 FPD 출력
- **메타데이터**: JSON 포맷으로 패널/취득 조건/캘리브레이션 참조 정보를 기록
- **골든 데이터셋**: `data/` 디렉터리, 대용량 바이너리이므로 Git LFS로 버전 관리

## CI/품질 게이트

- **TC ↔ pytest 매핑**: XDET_TestSpec_v1.0.md에 정의된 모든 시험 케이스(TC-000~021)는 1:1로 pytest 케이스로 등록되어야 하며, CI에서 자동 실행된다.
- **EV 회귀 게이트**: 회귀 게이트는 XDET_EVAL_criteria_v1.1.md의 EV(Evaluation criteria) min/typ/max 수치를 산출하여 병합을 차단(block)하는 역할을 한다. 예시 판정 항목:
  - MTF@Nyquist(3.57 lp/mm): min 0.25 / typ 0.30
  - 후처리 알고리즘 적용 시 SRb(Spatial Resolution) 저하율 ≤10%, MTF 유지율 ≥90% (노이즈 억제 강도의 상한 결정 기준)
  - DQE @ RQA5 조건
  - Grid suppression: 잔여 패턴 비가시(invisible), Moiré/aliasing 발생 0건
  - NDT SNRn: typ ≥130, SRb는 duplex-wire IQI로 산출
  - observer study는 P1 범위 밖 (자동 지표 판정만 사용)
- **모듈 단위 CI**: 각 모듈은 fixture 동봉 단위시험(TC-000)을 통과해야 파이프라인 통합 대상이 된다.
- **정적 검사**: 모듈 간 의존 방향(module → common 단방향)을 위반하는지 정적으로 검사하여 CI에서 차단한다.

## 금지 사항

- 파이프라인 순서 임의 변경 (SWR-000-2)
- 캘리브레이션 부재 시 기본값 무단 대체 (SWR-000-5)
- 포화 영역 "복원" 시도 — 포화는 정보 손실 영역으로 간주하고 복원하지 않는다 (SWR-602)
- 점근(asymptotic) 역 Anscombe 변환 사용 — 반드시 정확 무편향(exact unbiased) 역변환(LUT 기반)을 사용해야 한다 (SWR-703)
- 명목(nominal) grid 주파수 기반 notch 필터링 — grid 억제는 반드시 관측 스펙트럼에서 직접 피크를 탐색해야 하며, 명목 주파수를 가정한 notch는 aliasing 상황에서 부정확하므로 금지된다 (SWR-1001)
- P1 단계에서의 속도 최적화 (정확도가 유일한 목표)
- Gen 2 항목(DL 기반 처리, ADR) 구현 — P1 범위 밖

## 완료 정의와의 연결

TC-000~021 전체가 pytest로 등록되어 CI에서 통과하고, 골든 모델의 설정(config)이 동결(freeze)되는 시점이 P1의 완료 정의이다. 이 시점까지 모든 신규/변경 파라미터는 반드시 위 외부화 정책을 따라야 하며, EV 회귀 게이트를 통과해야 병합할 수 있다.
