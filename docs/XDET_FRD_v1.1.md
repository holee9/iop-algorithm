# XDET FRD — Functional Requirements + FR Table v1.1

기준: PRD v1.0, EVAL v1.1, TRM v2.1. PR 17건을 기능 요구로 전개. 수치는 EV 참조, 미확정 파라미터는 TBD-[B]. SWR(상세 SW 요구)은 본 FR의 하위로 발번(XDET-SWR-###) — 특허 검토는 사용자 결정에 따라 **릴리스 게이트로 이연** (SWR 작성은 진행하되 ⚠P 표기 절은 릴리스 전 대조).

## Core

| FR ID | 기능 요구 | 상위 PR | VV |
|---|---|---|---|
| XDET-FR-C001 | 다중 dark frame 평균 기반 offset map 생성 및 픽셀별 감산. 온도·경과시간 의존 offset 갱신 정책(주기/트리거) 포함 | PR-CORE-001 | VV-001 |
| XDET-FR-C002 | Flat-field 기반 gain map 생성·제산. 비선형 대응 multi-point(piecewise linear) gain, 선량 계단 취득 절차 내장 | PR-CORE-001 | VV-001 |
| XDET-FR-C003 | ASTM E2597 7종 분류 기반 static defect map 생성(dark/flat 스택 통계) + 주기적 adaptive 재검출 | PR-CORE-001 | VV-001 |
| XDET-FR-C004 | Defect 보간: 단일점 이웃 보간, line/cluster는 방향성(edge-directed) 보간. cluster 크기 상한 초과 시 경고 리포트 | PR-CORE-001 | VV-001 |
| XDET-FR-C005 | Lag 보정: 지수합 IRF 모델 재귀 deconvolution. IRF 파라미터는 자사 패널 실측 캘리브레이션(TBD-[B]) | PR-CORE-002 | VV-002 |
| XDET-FR-C006 | Ghost 관리: forward bias 시퀀스 연동 인터페이스(패널 FW 협조) + 잔존 ghost SW 감쇠 옵션 | PR-CORE-002 | VV-002 |
| XDET-FR-C007 | Line noise 보정: 라인별 기준영역(비조사/reference 영역) 신호로 행 단위 offset 감산. 임계 초과·급변 라인 오염 배제 로직(구조물 오보정 방지) | PR-CORE-003 | VV-003 |
| XDET-FR-C008 | 포화 처리: 포화 픽셀 검출·마킹, 경계 아티팩트 억제, 포화 영역 메타데이터 하류 전달 | PR-CORE-005 | VV-004 |
| XDET-FR-C009 | 기하 보정: 왜곡 모델 캘리브레이션(격자 팬텀) 및 잔차 EV-106 이내 리샘플링 | PR-CORE-005 | VV-004 |
| XDET-FR-C010 | 노이즈 저감: Poisson-Gaussian 모델 파라미터 추정 → Generalized Anscombe VST → Gaussian denoiser(BM3D 기본/NLM 대체) → exact unbiased inverse | PR-CORE-004 | VV-005 |
| XDET-FR-C011 | 노이즈 저감 강도 프리셋(부위/용도별) + SRb 보호 제약(EV-102 연동 강도 상한) | PR-CORE-004 | VV-005 |
| XDET-FR-C012 | 실행 HW 자동 감지(CPU/GPU/VRAM) → 티어 판정 → 기능 gating. 판정 결과 로그·UI 노출 | PR-CORE-007 | VV-012 |
| XDET-FR-C013 | 진단 영향 기능의 티어 간 결과 동일성: 결정론 경로 bit 동일, 부동소수점 경로 허용오차 정의·검증 훅 | PR-CORE-008 | VV-012 |
| XDET-FR-C014 | (Gen 2 예약) DL denoising 추론 모듈: ONNX Runtime 단일 런타임, 결정론적 fallback 자동 전환 | PR-CORE-006 | VV-013 |
| XDET-FR-C015 | 공통 프레임워크: XFrame 컨테이너·CalibSet 스키마·공용 컴포넌트 5종·오케스트레이터 — 전 모듈의 기반 (SWR-000-6~12) | 전 PR 공통 기반 (MR-003) | VV-000 |

## Medical

| FR ID | 기능 요구 | 상위 PR | VV |
|---|---|---|---|
| XDET-FR-M001 | 다중스케일 분해(Laplacian pyramid, 레벨 수 TBD) 기반 대역별 대비 변조. 자체 설계 — 특허 회피 확인 후 SWR 확정 | PR-MED-001 | VV-006/010 |
| XDET-FR-M002 | 대역별 노이즈 게이팅(저신호 대역 증폭 억제) 및 부위별 파라미터 프리셋 | PR-MED-001 | VV-006 |
| XDET-FR-M003 | DRC: 저주파 마스크 기반 dynamic range 압축, 골/연부 동시 가시화. 마스크 크기·압축 곡선 파라미터화 | PR-MED-002 | VV-006/010 |
| XDET-FR-M004 | 히스토그램 분석 기반 자동 VOI LUT(부위 인식 프리셋) — 수용률 EV-205 판정 연동 | PR-MED-003 | VV-007 |
| XDET-FR-M005 | DICOM GSDF(PS3.14) 출력 LUT 및 적합성 자가검사 | PR-MED-003 | VV-007 |
| XDET-FR-M006 | Grid 성분 자동 검출: 관측 스펙트럼 피크 직접 탐색 — 140µm 피치에서 상용 grid(30~85 lines/cm) 대부분이 Nyquist(3.57 lp/mm) 초과로 **aliasing되어 접힌 주파수로 나타남**을 전제. 검출 피크별 1D notch/band-stop, moiré(저주파 접힘) 대응 포함 | PR-MED-004 | VV-008 |
| XDET-FR-M007 | GLS 실패 감지(주파수 미검출·비정상 스펙트럼) 시 무처리 통과 + 경고 | PR-MED-004 | VV-008 |
| XDET-FR-M008 | 커널 기반 산란 추정: 두께/부위 파라미터화 scatter kernel, 다운샘플 추정 + 업샘플 감산, SW grid ratio 선택 UI | PR-MED-005 | VV-009 |
| XDET-FR-M009 | (Gen 2 예약) DL scatter 추정 모듈: 저해상도 추론 구조, PCCP 경계 정의 | PR-MED-006 | VV-014 |

## NDT

| FR ID | 기능 요구 | 상위 PR | VV |
|---|---|---|---|
| XDET-FR-N001 | Frame integration: N매 적산/평균, 목표 SNRn 도달 자동 판정·중단, shot별 SNRn/SRb 자동 기록(ISO 17636-2 요구) | PR-NDT-001 | VV-011 |
| XDET-FR-N002 | 두께 보정: 저주파 두께 프로파일 추정·보상, weld seam 고역 강조(SRb 보호 제약) | PR-NDT-002 | VV-011 |
| XDET-FR-N003 | IQI 자동 판독 리포트: duplex wire/단선 IQI 검출·판독·합부 자동 판정 | PR-NDT-001 | VV-011 |
| XDET-FR-N004 | (Gen 2 예약) ADR: 결함 검출·segmentation, POD 산출 리포트 | PR-NDT-003 | VV-015 |

## 공통 규칙

1. 각 FR의 acceptance는 상위 PR의 EV 참조를 상속. FR 고유 판정 필요 시 EV 추가 발번.
2. TBD-[B] 파라미터는 베이스라인 실측/벤치마크 후 SWR에서 확정.
3. Gen 2 FR(C014, M009, N004)은 구조만 정의 — 상세화는 PCCP 전략 문서와 동기.
4. SWR 전개 시 3-Trace 체계 연결 (SW 단독 제품이므로 HW/ME trace는 인터페이스 항목만).
