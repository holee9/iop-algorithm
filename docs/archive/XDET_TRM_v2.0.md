# X-ray FPD 영상처리 알고리즘 TRM 개정판 (v2.0 — 교차검증 반영)

문서 상태: 1차 리서치 결과를 원문 출처로 교차검증하여 정정·보강. Phase(SW→HW) 및 PC Tier 축 신규 반영.

---

## 0. 사실 검증 결과 요약 (1차 대비 정정 사항)

| # | 1차 기술 내용 | 검증 결과 | 판정 |
|---|---|---|---|
| 1 | US 5,357,549 = "Fuji DRC 특허" | **정정**: 원 출원인은 U.S. Philips Corporation (발명자 Neitzel, Maack), 2005년 Fuji Photo Film으로 양도. 1991년 출원 → **존속기간 만료(약 2011년)**. 리스크 해제 | ⚠️ 부분 정정 |
| 2 | SimGrid 임상연구 수치 (Ahn et al., Korean J Radiol 2018;19(3):526-533) | **확인**: 38명 병상 흉부, median DAP grid 1.48 (1.37–2.17) vs grid-like 1.22 (1.11–1.78) dGy·cm², p<0.001. SimGrid = "딥러닝 기반 scatter correction" 명시 확인. 결론: grid-like 영상이 grid 영상과 동등 화질을 더 낮은 선량으로 달성 | ✅ 확인 |
| 3 | DSE (Maier et al., Med Phys 2019;46(1):238-249) 오차 <1.8%, 10-20 ms | **정정**: mean error **1.7%**, 속도 **≈10 ms/projection** (MC 대비 수십 배 이상 고속). DL 추정치는 MC 대비 <3% 편차 | ⚠️ 수치 정밀화 |
| 4 | FDA PCCP 최종 가이던스 2024.12.03 | **확인**: Federal Register 공고 2024.12.04. 적용범위가 draft(ML 한정) → 최종본에서 **전체 AI-DSF로 확대** 확인. 2025.08 FDA/Health Canada/MHRA 공동 PCCP 5원칙(Focused, Risk-based 등) 확인 | ✅ 확인 |
| 5 | BM3D의 CPU/GPU 성능 격차 | **확인**: 원저 CUDA 구현은 4MP 영상에서 CPU 대비 4~5배(1MP 이하는 GPU가 오히려 저속), 최적화 구현(Honzátko, GTX980)에서 약 10배, exact CUDA 구현 19배 사례. 최신 GPU 최적화 구현(Davy et al., J Real-Time Image Processing)은 실시간 시나리오 사용 가능 수준 | ✅ 확인 (Tier 매트릭스 근거 확보) |
| 6 | FDA 승인 AI 기기 중 radiology 76% (1,104/1,451) | **검증 불가**: 이번 검증에서 원출처 미확인. 참고 수치로 강등, 인용 금지 권장 | ❓ 미검증 |
| 7 | Kodak US 6,269,176 / US 7,050,618 (GLS), Siemens DRZ 특허군, Carestream US 7,832,928 | 특허 존재는 1차에서 확인, **만료/유효 여부는 개별 미검증**. 2000년대 초 출원분은 만료 가능성 높으나 법률검토 필요 | ❓ 부분 검증 |

핵심 시사점: **1990년대 초 DRC 계열 특허(US 5,357,549 등)는 만료 확정으로, DRC 자체 구현의 특허 리스크가 크게 낮아졌다.** 반면 Virtual Grid/SimGrid 등 2010년대 특허는 유효 추정으로 회피설계 대상 유지.

---

## 1. 3계층 기술 분류 및 검증 반영 평가 매트릭스

### 1계층: Common Core (의료/산업 공용)

| 기술 | 성능 근거 (검증 상태) | 구현난이도 | 특허리스크 | 규제부담 | TRL |
|---|---|---|---|---|---|
| Offset/Gain/Defect 보정 | Seibert et al. SPIE 3336 (1998) 표준 파이프라인, ASTM E2597 bad pixel 7종 정의 | 낮음 | 낮음 | 낮음 | 9 |
| Lag/Ghost 보정 (SW deconvolution / forward bias) | Starman et al. Med Phys 2011/2012 | 중간~높음 | 중간 (Varian) | 낮음~중간 | 8~9 |
| Line noise correction (reference pixel) | Siemens DRZ 특허군 (존재 확인, 유효성 미검증) | 낮음 | 중간 | 낮음 | 9 |
| VST(Anscombe)+BM3D/NLM | Mäkitalo & Foi, IEEE TIP 2011 (exact unbiased inverse) | 중간 | 낮음 | 낮음 | 9 |
| 딥러닝 denoising (U-Net/Noise2Noise) | FPD 공간상관노이즈 이슈 유효 (SPIE 12925) — 백색잡음 학습 모델은 실기 부적합 | 높음 | 중간 | 높음 | 7~8 |
| Diffusion/self-supervised denoising | 연구 단계, 추론 저속 | 매우높음 | 중간 | 높음 | 4~6 |

### 2계층: Medical Post-processing

| 기술 | 성능 근거 | 특허리스크 (검증 반영) | 규제부담 | TRL |
|---|---|---|---|---|
| 멀티스케일 대비강화 (MUSICA/UNIQUE 유형) | 임상 ICC 0.76~0.86 (skeletal radiography) | **높음 유지** — 원 특허 만료 추정이나 MUSICA2/3 후속 특허군 유효 추정 | 중간 | 9 |
| DRC / tissue equalization | Philips→Fuji 특허 계열 | **낮음으로 하향** — US 5,357,549 만료 확정, 1990년대 계열 만료 추정 | 중간 | 9 |
| Auto windowing / DICOM GSDF | DICOM PS3.14 표준 | 낮음 | 낮음 | 9 |
| Grid line suppression (FFT notch/wavelet) | PMC5352826 등 | 중간 (Kodak 특허 만료 개별확인 필요) | 낮음 | 9 |
| Virtual Grid (커널/MC 기반) | Fuji Virtual Grid, Philips SkyFlow 상용 | 높음 (유효 추정) | 중간 | 9 |
| 딥러닝 scatter correction | **DSE: mean error 1.7%, ≈10 ms/projection (검증)**. SimGrid 임상: DAP 1.48→1.22 dGy·cm², grid 동등 화질 (검증) | 높음 | 높음 (PCCP 필요) | 6~8 |
| 딥러닝 GLS | 연구 단계 | 중간 | 높음 | 5~6 |

### 3계층: NDT Post-processing

| 기술 | 근거 | 특허리스크 | TRL |
|---|---|---|---|
| Frame averaging/integration | ISO 17636-2 SNRn 요구 — integrated 영상 필수 | 낮음 | 9 |
| 두께보정 / weld seam 강조 | ISO 17636-2 compensation principle | 낮음 | 8~9 |
| ADR (딥러닝 결함검출/segmentation) | YOLO/SegNet 계열, 데이터 부족이 병목 | 중간 | 6~7 |

---

## 2. 구현 Phase 로드맵 (SW 우선 → HW 이관)

| Phase | 기간(안) | 내용 | 게이트 기준 |
|---|---|---|---|
| **P1: SW 레퍼런스 (골든 모델)** | 0~9개월 | 전 알고리즘 C++/Python float 구현, 정확도 우선. IEC 62220-1 DQE, ASTM E2597 SRb/bad pixel, ISO 17636-2 SNRn 정량 검증 체계 확립 | 정량지표 목표 달성 + 골든 모델 형상 동결 |
| **P2: SW 최적화 (파이프라인 실시간화)** | 6~15개월 (P1과 중첩) | 파이프라인 실시간화를 독립 기술 과제로 수행: CPU SIMD/OpenMP, GPU CUDA + ONNX Runtime(TensorRT/OpenVINO EP), Tier별 파이프라인 실측 프로파일링 (EV-401 대응) | Tier 2 기준 실시간 목표 충족 |
| **P3: FPGA 이관 판단** | 12~18개월 | 병목 프로파일링 → 이관 후보 선별. 후보: offset/gain 감산·제산, static defect 보간, reference-pixel line noise correction (프레임 동기 필수 블록). Artix-7 35T 잔여 리소스(LUT/BRAM/DSP) 실측 합성 기반 타당성 평가. **주의: 35T급에서 offset+gain+defect 동시 탑재 가능 여부는 문헌 확정 근거 없음 — 실측 필수** | 이관 대상 확정 보고서 |
| **P4: FPGA 구현·검증** | 18~30개월 | 고정소수점 RTL 구현. P1 골든 모델과 bit-accurate(또는 정의된 허용오차) 등가성 검증. IEC 62304 관점에서 골든 모델이 검증 기준(reference) 역할 | 등가성 검증 통과 + DQE 회귀시험 무열화 |

원칙: FPGA 이관은 "전부"가 아닌 프레임레이트 종속 전처리만 선별. Post-processing은 PC 측 유지.

---

## 3. PC Tier별 기능 가용성 매트릭스 (검증 근거 반영)

검증 근거: BM3D는 GPU 최적화 구현에서 실시간 시나리오 사용 가능 수준(CPU 대비 약 10~19배 사례). 단 원저 CUDA 구현은 1MP 이하 소형 영상에서 GPU 이득이 없었다는 보고가 있어, **FPD급 대형 영상(6~16MP)에서 GPU 이득이 크고 소형 ROI는 CPU가 유리**할 수 있다는 점을 설계에 반영.

| 기능 | Tier 1: CPU only | Tier 2: 보급형 GPU | Tier 3: 고성능 GPU |
|---|---|---|---|
| Offset/Gain/Defect/Lag | ✅ | ✅ | ✅ |
| Line noise correction (ref. pixel) | ✅ | ✅ | ✅ |
| NLM/BM3D denoising | ⚠️ 정지영상 (FPD 해상도에서 수 초~수십 초) | ✅ 준실시간 (GPU 최적화 구현 전제) | ✅ 실시간 |
| 멀티스케일 대비강화 | ✅ | ✅ | ✅ |
| DRC / Auto windowing / GSDF | ✅ | ✅ | ✅ |
| Grid suppression (FFT) | ✅ | ✅ | ✅ |
| 딥러닝 denoising (U-Net) | ❌ | ✅ (INT8/TensorRT 양자화 전제, 실측 필요) | ✅ full 해상도 |
| 딥러닝 scatter | ❌ (커널 기반만 ⚠️) | ⚠️ 다운샘플 추론 — scatter는 저주파이므로 저해상도 추론 + 업샘플 적용이 표준 관행. DSE의 ≈10 ms/projection(CT 기준)을 볼 때 보급형에서 현실적 | ✅ |
| NDT ADR | ❌ | ⚠️ 소형 모델 (YOLOv8n급) | ✅ |
| Diffusion 계열 | ❌ | ❌ | ⚠️ 오프라인 처리만 |

주의: U-Net급 모델의 FPD full 해상도 기준 티어별 실측 추론시간은 공개 벤치마크가 희소 — **P2 필수 실측 과제**. 딥러닝 항목의 티어 판정은 잠정.

### 티어 설계 원칙 (규제 반영)
1. **결과 동일성 우선**: 진단 영향 기능은 티어 간 결과 동일(속도만 차이) 설계. CPU/GPU 부동소수점 비결정성은 허용오차 기준을 정의하여 문서화.
2. **Tier 2 = baseline SKU**. 티어 자동 감지 + graceful degradation.
3. **추론 런타임 ONNX Runtime 단일화** — IEC 62304 SOUP 1종 관리로 문서화 부담 최소화.

---

## 4. 특허 리스크 최종 평가

| 특허/특허군 | 상태 | 리스크 판정 |
|---|---|---|
| US 5,357,549 (DRC, Philips→Fuji 양도) | **만료 확정** (1991 출원, 존속기간 종료) | **해제** — DRC 기본 기법 자체 구현 가능 |
| US 5,471,987 / 5,991,457 / 5,493,622 (DRC 계열) | 1990년대 출원, 만료 추정 | 낮음 (개별 확인 권장) |
| Agfa MUSICA 계열 | 원 특허 만료 추정, MUSICA2/3 후속 특허군 유효 추정 | **중간~높음 유지** — 최신 구현 모방 금지, 고전 Laplacian pyramid 기반 자체 설계 |
| Kodak US 6,269,176 / 7,050,618 (GLS) | 만료 가능성 높음, 미확정 | 중간 → 법률검토 후 낮음 전환 예상 |
| Siemens DRZ (line noise) | 유효성 미검증 | 중간 — reference pixel 방식 자체는 일반 기법, 청구항 범위 검토 필요 |
| Fuji Virtual Grid / Samsung SimGrid / Philips SkyFlow | 2010년대, 유효 추정 | **높음** — scatter 추정 방법론 차별화 필수 |

---

## 5. 우선순위 로드맵 (개정)

한눈에 보는 로드맵: `XDET_TRM_v2.0_roadmap.svg` (3계층 × 단기/중기/장기 × P1~P4 phase) — 본 문서와 동일 폴더에 첨부.

![TRM Roadmap](XDET_TRM_v2.0_roadmap.svg)

**단기 (0~12개월, P1~P2 초기)**
1. Common Core 완비 + 정량 검증 체계 (DQE/SRb/SNRn)
2. VST+BM3D/NLM (Tier 1 정지영상, Tier 2+ 준실시간)
3. 멀티스케일 대비강화 자체 엔진 + **DRC — 만료 특허 기반으로 리스크 부담 없이 착수 가능 (이번 검증의 실질 효익)**
4. FFT/wavelet grid line suppression

**중기 (1~2년, P2~P3)**
5. 딥러닝 denoising (ONNX/TensorRT, 티어별 실측) + PCCP 전략 수립
6. 커널 Virtual Grid → 딥러닝 scatter (다운샘플 추론 구조, DSE 방법론 참조하되 청구항 회피)
7. NDT ADR 파일럿 (합성데이터 보강, POD 검증)
8. FPGA 이관 판단 (P3 게이트)

**장기 (2~4년, P4+)**
9. FPGA 전처리 IP + 골든 모델 등가성 검증
10. Diffusion/self-supervised, PCCP 기반 지속 개선 인프라

---

## 6. Caveats (검증 한계 명시)

- **FDA radiology AI 76% 수치**: 원출처 미확인 — 인용 금지. FDA 공식 AI-enabled device list에서 직접 재산출 필요.
- **Kodak/Siemens/Carestream 특허 만료 여부**: Google Patents의 법적 상태는 "assumption"으로 명시됨 — 변리사 법률검토 필수.
- **Artix-7 35T 리소스 적합성**: 문헌 확정 근거 없음, 자체 합성 실측 필요.
- **U-Net/diffusion의 FPD full 해상도 티어별 추론시간**: 공개 벤치마크 부재, P2 실측 과제.
- **DSE ≈10 ms/projection은 CT projection(상대적 저해상도) 기준**: 정지 radiography full 해상도 직접 적용 수치 아님. scatter 저주파 특성상 다운샘플 추론으로 완화 가능하나 자체 검증 필요.
- **벤더 알고리즘 세부는 영업비밀**: MUSICA/UNIQUE/Virtual Grid 수식 비공개, 성능 수치 일부는 벤더 발표 기반.
- **BM3D 벤치마크의 하드웨어 세대**: 인용 벤치마크는 Titan Xp/GTX980 세대. 현세대 GPU에서 여유가 더 크나 절대 수치 재실측 필요.
