# X-ray FPD 영상처리 SW 제품 로드맵 (PRM v1.2 — 교차검증 보정 병합판)

기준 문서: TRM v2.0 (교차검증판). 본 PRM은 TRM의 기술 후보를 제품·SKU·세대에 매핑한다. 성능 수치 확정은 사양서(PR) 단계, FPGA 타깃 선정은 P3 단계의 산출물이며 본 문서는 방향과 구성을 정한다.

## 개정 이력 (HISTORY)

- v1.2 (issue #34): 범위(Medical + NDT) 유지. EOD/보안(ASTM F792) 미래 확장 후보를 **부록 A**로 추가(범위 밖 포인터 메모, 정식 사양 아님). 기존 내용 전부 보존(추가 편집). 파일명 유지(문서 맵·RTM 참조 보존).
- v1.1: 교차검증 보정 병합판.

---

## 1. 목적 및 범위

- 목적: X-ray FPD raw 영상 입력 기반 pre/post-processing SW 제품군의 라인 구성, 세대 계획, 기능 탑재 순서 정의.
- 범위: SW 제품(공용 코어 라이브러리, Medical DR post, NDT post). 검출기 HW·FPGA 펌웨어는 P3 이후 별도 문서.
- 원칙: 기술 탑재 여부는 제품 필요성으로 결정한다. 특허는 구현 방식(회피설계/라이선스/만료 활용)을 결정하는 리스크 관리 항목이며 탑재 가부의 게이트가 아니다.

## 2. 제품 라인 정의

| 제품 라인 | 형태 | 대상 |
|---|---|---|
| **Core Library** | 공용 pre-processing + 노이즈 저감 라이브러리 (Medical/NDT 공용) | 내부 컴포넌트 (두 제품에 내장) |
| **Medical DR Post** | 의료용 post-processing 엔진 + 파이프라인 | DR 시스템 (MFDS/FDA/CE MDR) |
| **NDT Post** | 산업용 post-processing 엔진 + ADR | NDT 시스템 (ISO 17636-2/ASTM) |

### SKU (Tier) 구성 — 잠정

| SKU | HW 전제 | 포지션 |
|---|---|---|
| Tier 1 | CPU only | 엔트리 — 결정론적 기능 전체 |
| Tier 2 | 보급형 GPU | **baseline SKU** — 딥러닝 기능 포함 |
| Tier 3 | 고성능 GPU | 프리미엄 — full 해상도 DL, 오프라인 고급처리 |

주: 티어별 기능 가용성은 TRM v2.0 §3의 잠정 매트릭스를 따르며, **확정은 사양서(PR) 단계의 실측 벤치마크 이후**. 진단 영향 기능은 티어 간 결과 동일(속도만 차이) 원칙 유지.

## 3. 세대(Generation) 계획

| 세대 | 기술 기반 | 규제 전략 | TRM 대응 |
|---|---|---|---|
| **Gen 1** | 결정론적 알고리즘 전체 (보정 코어, VST+BM3D/NLM, MSE+DRC, FFT GLS, auto windowing/GSDF, 커널 virtual grid, frame integration, 두께보정) | 표준 510(k)/CE — 검증 부담 최소 | TRM 단기 항목 (TRL 8~9) |
| **Gen 2** | 딥러닝 선택 탑재 (DL denoising, DL scatter, ADR) — 결정론적 fallback 동봉 | FDA PCCP 병행, IEC 62304 ML 문서화 | TRM 중기 항목 (TRL 6~8) |
| **Gen 3** | 확산모델·자가지도·지속학습 | PCCP 기반 지속 개선 | TRM 장기 항목 (TRL 4~6) |

## 4. TRM → 제품 기능 매핑 (교차검토 결과)

| TRM 기술 | 제품 | 세대 | SKU | 비고 (교차검토) |
|---|---|---|---|---|
| Offset/Gain/Defect/Lag 보정 | Core | Gen 1 | 전 Tier | TRM TRL 9 — 즉시 |
| Non-uniformity/기하왜곡/포화 처리 | Core | Gen 1 | 전 Tier | 교차검증 F4 보정 반영 (EV-106) |
| Line noise correction | Core | Gen 1 | 전 Tier | reference pixel 방식, 청구항 검토 병행 |
| VST+BM3D/NLM | Core | Gen 1 | T1 정지영상 / T2+ 준실시간 | TRM 검증: GPU 10~19배 근거 |
| DL denoising (U-Net) | Core | Gen 2 | T2+ | 공간상관노이즈 학습 필수 (TRM §1.6) |
| Diffusion/자가지도 | Core | Gen 3 | T3 오프라인 | TRL 4~6, 연구 병행 |
| MSE (다중스케일 대비강화) | Medical | Gen 1 | 전 Tier | 자체 pyramid 설계 (MUSICA 후속특허 회피 — 구현방식 이슈, 탑재는 확정) |
| DRC / tissue equalization | Medical | Gen 1 | 전 Tier | US 5,357,549 만료 확인 — 구현 제약 없음 |
| Auto windowing / GSDF | Medical | Gen 1 | 전 Tier | 표준 준수 항목 |
| Grid suppression (FFT/wavelet) | Medical | Gen 1 | 전 Tier | Kodak 특허 만료 확인 병행 |
| Virtual grid (커널) | Medical | Gen 1 후반 | 전 Tier | 산란 추정 방법론 자체 설계 |
| DL scatter | Medical | Gen 2 | T2 축소해상도 / T3 full | PCCP 대상, 다운샘플 추론 구조 |
| DL GLS | Medical | Gen 3 | T2+ | TRL 5~6 — 성숙도 대기 |
| Frame integration / 두께보정 | NDT | Gen 1 | 전 Tier | ISO 17636-2 SNRn 필수 요건 |
| ADR (결함 자동인식) | NDT | Gen 2 파일럿 → Gen 3 상용 | T2 소형모델 / T3 | POD 검증 필수, 데이터 확보가 게이트 |

교차검토 확인 사항: TRM의 전 기술 항목이 제품에 매핑됨(누락 없음). TRM 우선순위 순서(결정론 → DL → 생성모델)와 세대 구분이 일치함. TRM Caveats의 미확정 항목(벤치마크, 특허 유효성)은 본 문서에서 게이트가 아닌 병행 과제로 처리됨.

## 5. 화질 목표 (지표 정의)

수치 목표는 사양서(PR) 단계에서 실측 기반으로 확정. 본 단계에서는 지표와 원칙만 정의한다.

- Medical: IEC 62220-1 DQE, MTF/SRb, 저선량 조건 화질 유지율(무그리드+scatter correction 시 그리드 동등 화질 목표 — SimGrid 임상 근거 수준), DICOM GSDF 적합성.
- NDT: ISO 17636-2 SNRn/SRb Class A/B, duplex wire IQI, ASTM E2597 dSNRn. 원칙: 필터링이 SRb를 훼손하지 않을 것.
- 공통: 알고리즘 전후 정량지표 회귀시험 체계 (P1 골든 모델 기준).

## 6. 규제 전략

- Gen 1: 결정론적 구성으로 MFDS/FDA/CE MDR 동시 인허가 — 기존 3-Trace V-Model에 연결.
- Gen 2: DL 기능은 PCCP(FDA 2024.12 최종 가이던스) 전략 수립 후 탑재. 항상 결정론적 fallback 동봉으로 미승인 시장에서도 판매 가능 구조.
- NDT: 의료 인허가 불요 — Gen 2 기능(ADR)의 시장 선행 투입 채널로 활용 가능 (딥러닝 기술의 실전 검증장).

## 7. 리스크 및 병행 과제 (게이트 아님)

| 항목 | 처리 |
|---|---|
| 특허 유효성 (MUSICA 후속, Kodak GLS, Siemens DRZ, virtual grid 계열) | 상세설계(FR/SWR) 착수 전까지 변리사 검토 완료 — 구현 방식에만 영향 |
| Tier별 DL 실측 성능 | 사양서(PR) 단계 벤치마크 — 티어 매트릭스 확정 입력 |
| FPGA 타깃 디바이스 | P3 단계 산출물 — 본 PRM 범위 외 |
| ADR 학습 데이터 부족 | Gen 2 파일럿 기간 데이터 수집 체계 + 합성데이터 보강 |

## 8. 다음 단계

1. PRM v1.0 검토·승인 → 베이스라인 동결
2. MR 작성 (제품 라인별) → PR 전개 (이 단계에서 Tier 벤치마크 수행, 수치 확정)
3. P1 SW 레퍼런스 개발 정식 착수 (Gen 1 범위)

---

![PRM Roadmap](XDET_PRM_v1.0_roadmap.svg)

---

## 부록 A. EOD/보안 이미징 (미래 확장 후보 — 현 범위 밖)

> **범위 밖 포인터 메모 (issue #34).** 본 PRM의 정식 범위는 Medical + NDT이며, 아래는 향후 확장 검토용 참조일 뿐 정식 제품·평가 사양이 아니다. 채택 시 별도 MR/PR로 분기한다.

- **대상 표준**: ASTM F792 (보안 X선 이미징 성능) — 3분할(trifurcated) 체계: routine / human-perception / technical 3개 시험(각 별도 시험체·접미사; 정확한 접미사 표기는 F792 조문 대조 후 확정).
- **EOD 휴대형 특성**: 펄스형 X선, **이중에너지**(kV 스위칭 또는 중간-Z(Cu/황동) 분리판을 둔 적층 검출기)로 유기/무기물(Zeff) 판별.
- **지표 성격**: 침투도(penetration) / 와이어 가시성 / 재질 판별 중심 — **DQE 계열이 아님**. 따라서 포함 시 **F792 기반 별도 평가체계**가 필요하며 현 EVAL/측정 프로토콜(RQA5·ASTM E2597 계열)을 그대로 적용할 수 없다.
- **판단**: 현 세대(Gen 1~3) 계획에 미포함. 시장·규제 요건 확인 후에만 별도 요구·사양으로 전개.
