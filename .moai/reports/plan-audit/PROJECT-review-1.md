# SPEC Review Report: PROJECT (.moai/project/ — product.md, structure.md, tech.md)
Iteration: 1/3
Verdict: PASS
Overall Score: 0.92

문서 유형: project (제품/구조/기술 스티어링 문서 3종)
근거(Ground Truth): 저장소 CLAUDE.md, docs/XDET_SWR_spec_v1.2.md, docs/XDET_EVAL_criteria_v1.1.md, docs/XDET_TestSpec_v1.0.md
비고: Reasoning context ignored per M1 Context Isolation — 감사에는 최종 문서와 근거 문서만 사용함.

## Must-Pass Results

- [PASS] MP-1 ID 참조 일관성 (project 문서 유형에 맞게 REQ → SWR/TC/EV ID로 적용): 세 문서에서 참조된 모든 SWR ID 범위(SWR-101~104, 201~204, 301~304, 401~404, 501~504, 601~603, 701~706, 801~805, 901~903, 1001~1006, 1101~1103, 1201~1204, 1301~1303, SWR-000-1~12)가 CLAUDE.md 및 XDET_SWR_spec_v1.2.md와 전수 일치. 간극/중복/오타 0건. 증거: product.md:L30~L44, structure.md:L18~L30, XDET_SWR_spec_v1.2.md:L13~L19, L53~L56, L145~L147.
- [N/A] MP-2 EARS 형식: project 스티어링 문서는 수용 기준(AC)을 포함하지 않는 문서 유형이므로 해당 없음.
- [N/A] MP-3 YAML frontmatter: project 문서(product/structure/tech.md) 스키마는 frontmatter를 요구하지 않음. 세 문서 모두 frontmatter 없이 제목부터 시작 — 유형에 부합.
- [N/A] MP-4 Section 22 언어 중립성: 단일 언어(Python 3.11+) 프로젝트로 명시적 범위 한정(tech.md:L5) — 자동 통과.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity (명확성) | 0.90 | 0.75~1.0 | 대부분 단일 해석. 예외 2건: product.md:L42 "결과 등급 판정"(SWR-1301 오독 소지, D1), product.md:L32 "7-class" 출처 불명(D3) |
| Completeness (완전성) | 0.95 | 1.0 | 3개 문서가 제품/구조/기술 축을 모두 커버. 13 모듈 + T0~T10 + 파라미터 정책 + 금지 사항 + DoD 전부 포함 (product.md:L26~L69, structure.md:L71~L87, tech.md:L18~L57) |
| Accuracy (사실 정확성, Testability 대체) | 0.85 | 0.75 | 수치 전수 대조 결과 오류 0건 (아래 검증 목록). 단, 특성화 오류 2건(D1, D2) + 저장소 상태 기술 부정확 1건(D4) |
| Traceability (추적성) | 1.00 | 1.0 | SWR/TC/EV 참조 전수 원본 일치. TC-000~021 DoD는 TestSpec의 TC-022(observer study) 제외와 정합 — product.md:L11, L64, tech.md:L41에서 observer study 제외를 3중 명시 |

## 수치 교차 검증 결과 (전수 대조)

| 문서 주장 | 근거 원문 | 판정 |
|---|---|---|
| MTF@Nyquist(3.57 lp/mm) min 0.25 / typ 0.30 (tech.md:L36) | XDET_EVAL_criteria_v1.1.md:L37 "MTF@Nyquist(3.57) \| 0.25 \| 0.30 \| 0.35" | 일치 |
| SRb 저하율 ≤10%, MTF 유지율 ≥90% (tech.md:L37) | EVAL v1.1:L38 "알고리즘 후 SRb 열화 ≤10%", L39 "MTF@Nyquist 유지율 ≥90%" | 일치 |
| DQE @ RQA5 (tech.md:L38) | EVAL v1.1:L14 "IEC 62220-1 RQA5", L20 "XDET-EV-101 — DQE @ RQA5" | 일치 |
| Grid: 잔여 패턴 비가시, Moiré/aliasing 0건 (tech.md:L39) | EVAL v1.1:L93~L94 (EV-203) "잔존 grid line 비가시 / Moiré/aliasing 0건·0건·0건" | 일치 |
| NDT SNRn typ ≥130 (tech.md:L40) | EVAL v1.1:L118 "SNRn (처리 후) \| Class A 충족 \| ≥130 \| ≥250" | 일치 |
| SNRn = SNR×88.6µm/SRb (structure.md:L43) | CLAUDE.md T1 | 일치 |
| BM3D 8×8/step3/N2=16/Ns=39/λ2.7/Haar (product.md:L36) | CLAUDE.md T5 | 일치 |
| Laplacian L=7 (product.md:L37) | CLAUDE.md T6 | 일치 |
| TBD-[B] 9건 / TBD-[T] 11건 (tech.md:L22~L23) | CLAUDE.md 파라미터 정책 | 일치 |
| noisy 6× median E2597-22 [S] (tech.md:L23 예시 맥락) | SWR spec:L53 "noisy: dark 영상 노이즈 median의 6× 초과 [S]" | 일치 |
| Nyquist 3.57 lp/mm (140µm 피치) | SWR spec:L5 "f_N = 3.571 lp/mm" — 반올림 표기는 crosscheck log:L13에서 허용 편차로 판정됨 | 일치 |
| SWR-000-12 = 구현 교체 계약 (structure.md:L57, tech.md:L16) | SWR spec:L19 "P1/P2/P4 구현 교체 계약: 골든(float)·최적화(SIMD/GPU)·FPGA ... TC-021 계열로만 교체 승인" | 일치 |
| duplex wire 20% dip, NPS 256×256 ROI (structure.md:L43) | CLAUDE.md T1 | 일치 |

## Defects Found

D1. product.md:L42 — "Tier/동일성 프레임 ... **결과 등급 판정** 및 golden/optimized/FPGA 구현 간 동일성 검증 구조"에서 "결과 등급 판정"은 오독 소지. SWR spec:L145의 SWR-1301 티어 판정은 영상 결과의 등급이 아니라 **실행 하드웨어 역량 티어**(CPU 코어·AVX 지원, GPU 모델·VRAM) 판정임. "실행 티어(HW 역량) 판정"으로 수정 필요 — Severity: minor

D2. structure.md:L48, L56 — 제목 "아키텍처 강제 규칙 (SWR-000-6~12)" 아래 8개 규칙 중 규칙 7(정밀도 동일성: 정수 bit-동일, float ±1 LSB)은 SWR-000-6~12에 존재하지 않음. SWR spec 대조 결과 SWR-000-6~12는 7개 항목(XFrame/시그니처/직접호출금지/공용컴포넌트/CalibSet/harness/교체계약)이며, 정밀도 동일성 규칙의 원출처는 SWR-1302(SWR spec:L146)임. 단, 이 묶음 표기는 CLAUDE.md에서 승계된 것으로 문서 자체 창작 오류는 아님 — Severity: minor

D3. product.md:L32 — "E2597 **7-class** 불량 픽셀 분류"의 "7"이 docs/ 어디에도 명시적으로 없음. SWR spec:L53 열거(dead/over/under/non-uniform/noisy/persistence·lag/bad-neighborhood)로 7종 해석이 성립하지만, over/under를 1종으로 계수하면 6종이 되어 계수 기준이 모호함. 클래스 목록 병기 또는 "E2597-22 분류"로 완화 권장 — Severity: minor

D4. structure.md:L5 — "현재 저장소에는 docs/와 .moai/**만** 존재"는 부정확. 저장소에는 .claude/, CLAUDE.md, .gitignore, .mcp.json도 존재함(git status 확인). "구현 스캐폴드는 미생성" 취지는 옳으나 "만 존재" 표현은 사실과 불일치 — Severity: minor

## Chain-of-Verification Pass

2차 재검토 수행 항목:
- SWR ID 전 구간 재대조(간극/중복 스팟체크가 아닌 전수): 이상 없음.
- SWR-000-6~12 원문 7항목 재확인 → D2를 1차 패스의 "표기 의문"에서 확정 결함으로 승격.
- TestSpec 상·하한 TC(TC-000, TC-021, TC-022) 확인 → TC-022(observer study)의 P1 제외가 세 문서와 정합함을 확인 — 모순 없음.
- 문서 간 상호 모순 검사(product ↔ structure ↔ tech): DoD, 금지 사항, TBD 건수, 파이프라인 순서 기술 모두 상호 일치. 모순 0건.
- 저장소 실상태 대조 → D4 발견(2차 패스 신규).

## Regression Check (Iteration 2+ only)

해당 없음 (iteration 1).

## Recommendation

Verdict PASS 근거: (1) MP-1 — 참조 ID 전수 일치, 증거 상기 표. (2) MP-2/3/4 — project 문서 유형 특성상 N/A. (3) 근거 문서와의 수치 대조 13건 전건 일치, 사실 오류(수치)는 0건. 발견된 결함 4건은 모두 minor 특성화/표현 수준으로 must-pass에 저촉되지 않음.

차기 개정 시 권장 수정 (차단 아님):
1. product.md:L42 — "결과 등급 판정" → "실행 티어(HW 역량: CPU/AVX/GPU/VRAM) 판정"으로 교체 (D1).
2. structure.md:L48 — 제목을 "SWR-000-6~12 + SWR-1302"로 정정하거나 규칙 7에 "(SWR-1302)" 출처 병기 (D2).
3. product.md:L32 — E2597 클래스 목록을 열거하거나 "7-class" 계수 근거 명시 (D3).
4. structure.md:L5 — ".claude/, CLAUDE.md 등 워크플로우 설정 파일 포함" 반영 (D4).
