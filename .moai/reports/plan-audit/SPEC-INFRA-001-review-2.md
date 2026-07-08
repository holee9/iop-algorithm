# SPEC Review Report: SPEC-INFRA-001
Iteration: 2/3
Verdict: PASS
Overall Score: 0.94

> Reasoning context ignored per M1 Context Isolation — 조정자(coordinator)의 "6건 모두 해결" 주장은 증거로 취급하지 않고, 개정된 spec.md(v0.1.1) / acceptance.md 전문을 재독하여 독립 검증함.

## Must-Pass Results

- [PASS] **MP-1 REQ 번호 일관성**: 총 18개 REQ 전수 확인 — DATA-1~6 (spec.md:L50-55), CONTRACT-1~4 (L59-62), ORCH-1~4 (L66-69), STATIC-1~3 (L73-75), CI-1, CI-2, CI-3a, CI-3b, CI-4 (L79-83). 갭 0건, 중복 0건. CI-3의 3a/3b 분할은 iteration 1 결함 D1의 수정 결과로, 원 번호에 접미 문자를 부여하는 개정 관행(프로젝트 생태계의 REQ-LC-001a와 동일 방식)에 부합 — 추적성 보존 목적의 유효한 번호 체계로 판정.
- [PASS] **MP-2 EARS 형식 준수**: 18건 전수 재검사. Ubiquitous 10건, Event-Driven 4건(DATA-4 L53, CONTRACT-4 L62, STATIC-2 L74, CI-2 L80 — 모두 "WHEN …, THEN …해야 한다" 형식 부합), State-Driven 1건(DATA-5 L54 WHILE), Unwanted 라벨 3건(DATA-2 L51, ORCH-2 L67, ORCH-4 L69 — 이 중 L67/L69는 IF/THEN 형식 완전 부합), Optional 2건(CONTRACT-2 L60, CI-3b L82 — 모두 "WHERE …해야 한다" 형식 부합). 비형식 문장 0건. 단, DATA-2(L51)의 라벨-본문 불일치는 신규 결함 N1로 기록(본문은 형식적 "shall not" 문형이므로 EARS 위반 아님 — 하단 참조).
- [PASS] **MP-3 YAML 프론트매터 유효성**: spec.md:L2-9 — 8필드(id, version, status, created, updated, author, priority, issue_number) 전부 존재, 타입 유효. version이 0.1.0 → **0.1.1**로 승급되어(L3) 개정 이력 규약 준수. HISTORY에 v0.1.1 엔트리 추가(L22-28) 확인.
- [N/A] **MP-4 언어 중립성**: Python 단일 언어 SPEC — N/A: single-language SPEC.

## Regression Check — Iteration 1 결함 6건 해소 검증

- **D4 (major, float64 채널 모순)** — [RESOLVED]: spec.md:L50 DATA-1이 "pixel buffer(기본 float32; WHERE 검증 모드가 활성인 경우 동일 XFrame 인스턴스가 float64 병행 버퍼를 추가로 보유할 수 있음)"로 개정되고, "float64 병행 버퍼는 XFrame 내부 필드이므로 REQ-INFRA-DATA-2의 사이드채널에 해당하지 않으며, REQ-INFRA-CI-3b가 이 버퍼를 유일한 float64 전달 채널로 사용한다"는 폐합 문장 추가. L51 DATA-2 말미("XFrame 내부 필드…를 통한 전달은 컨테이너 내 전달이므로 위반이 아니다")와 L82 CI-3b("float64 산출물은 …XFrame 내부 float64 병행 버퍼로만 전달")가 상호 참조로 삼각 폐합. DATA-1↔DATA-2↔CI-3b 간 모순 해소 확인. DoD(acceptance.md:L64)도 "float64 검증-모드 병행 버퍼(검증-모드 XFrame 내부 필드, DATA-1)"로 정합 갱신.
- **D2 (major, EC-4 구현 불가)** — [RESOLVED]: acceptance.md:L44-48 EC-4가 "자동 검출 가능 범위 한정"으로 재작성 — Given이 구체 위반 fixture(시그니처 위반·부가 반환값, L45)로 특정되고, Then(L47)이 검출 메커니즘별로 이진 판정 가능. 범위 밖 항목(전역 상태·파일 우회 일반 검출)은 L48에서 "설계 규칙 — 테스트 가능 AC 아님"으로 명시 분리되고 근거(TestSpec:L7의 XDET-TC-000 검사 범위)를 정확히 인용. spec.md:L51 DATA-2도 자동 검출 가능 범위를 계약 검사 + import-linter로 한정. 과잉 약속 제거 확인.
- **D1 (minor, CI-3 라벨 불일치)** — [RESOLVED]: spec.md:L81 CI-3a(Ubiquitous — "기본적으로 float32 단일 경로로 연산해야 한다"), L82 CI-3b(Optional — "WHERE 검증 모드가 활성인 경우 …제공해야 한다")로 분리. 각 라벨-본문 일치 확인.
- **D3 (minor, CONTRACT-2 AC 부재)** — [RESOLVED]: spec.md:L60에 "T0는 …구조적으로 확인하는 데 그치며, 런타임 검증은 T4(lag)로 이연" 명시 추가. acceptance.md:L22-25에 Scenario 4(상태 직렬화 인터페이스 구조 확인) 신설 — Then이 이진 판정 가능("인터페이스가 프로토콜에 존재함이 확인된다") + T4 이연 명시. DoD 체크리스트 L63 대응 항목 추가. 커버리지 갭 해소.
- **D5 (minor, TC 표기 혼용)** — [RESOLVED]: spec.md L17, L42, L77, L79-80, L83, L90 및 acceptance.md L3, L19-20, L42, L47-48, L62, L66 전수 확인 — 접두어 없는 "TC-NNN" 단독 표기 잔존 0건, XDET-TC-NNN으로 통일.
- **D6 (minor, DATA-3 HOW 포함)** — [RESOLVED]: spec.md:L52 DATA-3이 "단일 직렬화 규약으로 저장되어야 한다(구체 저장 포맷은 Environment/Assumptions 및 plan.md 참조)"로 개정 — npz+JSON sidecar는 Environment(L43)에만 잔류. WHAT/HOW 분리 확인. (Exclusions L89의 포맷 언급은 범위 서술이므로 무해.)

**6/6 RESOLVED. 정체(stagnation) 결함 없음.**

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 | 신규 minor 모호성 N2(하단) 1건 — 합리적 구현자가 일관되게 해소 가능한 수준. 그 외 요구는 단일 해석. float64 정책은 3중 상호 참조로 명확화(L50/L51/L82) |
| Completeness | 1.00 | 1.0 | HISTORY(L20-35, 개정 이력 포함), Environment(L37-44), Requirements 18건, Exclusions 8건(L85-94), AC(Scenario 4건 + EC 5건 + DoD 10항), 프론트매터 8필드 + 버전 승급 |
| Testability | 1.00 | 1.0 | 전 AC 이진 판정 가능. EC-4는 검출 가능 범위로 축소되고 비검증 항목은 "테스트 가능 AC 아님"으로 명시 분리(acceptance.md:L48). Scenario 4 구조 테스트 판정 가능(L25). 위즐 워드 0건 |
| Traceability | 1.00 | 1.0 | 18개 REQ 전건 AC 커버(CONTRACT-2→Scenario 4, CI-3a/3b→DoD L64, DATA-2→EC-4 등 전수 대조). AC의 REQ 참조 전건 실재. SWR/TC/EV ID 참조는 iteration 1에서 근거 문서 실재 확인 완료, 개정으로 변경 없음 |

## Defects Found (신규)

**N1.** spec.md:L51 — REQ-INFRA-DATA-2의 라벨은 "(Unwanted)"이나, 개정 후 본문은 IF/THEN 구조가 아닌 금지형 Ubiquitous("모듈은 …전달해서는 안 된다", shall-not 문형)로 변경됨. iteration 1의 "IF …하면, THEN …실패시켜야 한다"에서 형식이 바뀌었으므로 라벨을 "(Ubiquitous)"로 정정하거나 IF/THEN 문형 복원 필요. EARS 형식 자체는 준수(형식적 shall-not)하므로 MP-2 비저촉. — Severity: **minor**

**N2.** spec.md:L51 ↔ acceptance.md:L44-48 — DATA-2는 전역 상태·파일 우회에 대해 "지정된 위반 fixture에 대한 검출 시연 및 코드 리뷰 게이트로 다룬다"고 서술하나, EC-4의 위반 fixture(L45)는 시그니처 위반·부가 반환값만 포함하며 전역 상태·파일 우회는 L48에서 코드 리뷰 게이트 전담으로 규정. DATA-2의 "검출 시연" 언급이 EC-4에 대응물이 없음 — DATA-2 문구를 "코드 리뷰 게이트로 다룬다"로 정리하거나 EC-4에 전역 상태 위반 fixture 1건을 추가하여 정합시킬 것. — Severity: **minor**

## Chain-of-Verification Pass

2차 재검토 수행:
- **개정 전파 누락 검사**: D4 수정이 Scenario 1(acceptance.md:L10 "pixel(float32)")과 충돌하는지 확인 — Scenario 1은 기본 모드(검증 모드 비활성) 시나리오이므로 float32 비교가 정합. 충돌 없음.
- **CONTRACT-4(L62) 비교 항목**: float64 병행 버퍼가 비교 대상에 미포함 — T0 기본 경로 범위에서 정당(검증 모드 비교는 CI-3b/DoD 소관). 결함 아님.
- **DATA-1의 괄호 내 WHERE 절**: "보유할 수 있음"은 허용(permission)으로 자료구조 정의의 일부이며, 규범적 의무는 CI-3b(Optional)에 위치 — D1과 달리 라벨 불일치로 보지 않음(관찰 사항).
- **Exclusions 재검사**: L90(XDET-TC-021 임계 없음) ↔ CI-4(L83), L94(모듈 트리 내 레퍼런스 없음) ↔ CONTRACT-3(L61) — 개정 후에도 충돌 없음.
- **TC 표기 전수 재스캔**: 접두어 누락 잔존 0건 재확인.

2차 재검토 신규 발견: N2는 2차 패스에서 발견됨(1차 패스에서는 D2 해소 확인에 집중하여 DATA-2 본문의 "검출 시연" 문구와 EC-4 fixture 범위의 미세 불일치를 지나쳤음). 상기 결함 목록에 반영 완료.

## Recommendation

**PASS.** 근거:
- MP-1: 18개 REQ 번호 갭/중복 0건 (spec.md:L50-83 전수).
- MP-2: 18건 전수 EARS 형식 부합 — 예: L54 "WHILE 검증 모드가 활성인 동안, 시스템은 …보존해야 한다", L69 "IF 캘리브레이션 파일이 부재하거나 불일치하면, THEN 시스템은 처리를 거부하고 명시 오류를 발생시켜야 한다".
- MP-3: 8필드 완비 + version 0.1.1 승급 (L2-9).
- MP-4: N/A (Python 단일 언어).
- Iteration 1 결함 6/6 RESOLVED (증거 상기), major 결함 0건, 종합 0.94 ≥ 0.75.

신규 minor 2건(N1: DATA-2 라벨 정정, N2: DATA-2↔EC-4 문구 정합)은 차단 사유가 아니며, run 착수 전 annotation 사이클에서 한 줄 수정으로 처리 권고. 패턴 경고: 라벨-본문 불일치(D1 → N1)가 개정 과정에서 재발하는 경향이 있으므로, manager-spec은 요구 문형 변경 시 라벨 재검을 체크리스트화할 것.

---
감사자: plan-auditor | 대상: spec.md v0.1.1 / acceptance.md (개정본) | 이전 보고서: SPEC-INFRA-001-review-1.md (FAIL 0.74)
