# SPEC Review Report: SPEC-INFRA-001
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.74

> 참고: 호출 프롬프트에 SPEC 작성자의 reasoning context는 포함되지 않았음. 원칙 명시 — Reasoning context ignored per M1 Context Isolation. 감사는 spec.md / acceptance.md 파일과 근거 문서(docs/)만으로 수행함.

## Must-Pass Results

- [PASS] **MP-1 REQ 번호 일관성**: 그룹형 체계 REQ-INFRA-{GROUP}-{N} 사용. DATA-1~6 (spec.md:L43-48), CONTRACT-1~4 (L52-55), ORCH-1~4 (L59-62), STATIC-1~3 (L66-68), CI-1~4 (L72-75). 각 그룹 내 번호 연속(1부터 시작, 갭 없음)·중복 없음·표기 일관. 총 **17개 REQ**(6+4+4+3+4) 전수 확인. 갭 0건, 중복 0건.
- [PASS] **MP-2 EARS 형식 준수**: 17개 REQ 전수 검사. Ubiquitous 9건(예: L43 "…유일한 모듈 입출력 단위여야 한다"), Event-Driven 4건(예: L46 "WHEN 모듈이 출력 XFrame을 생성하면, THEN…"), State-Driven 1건(L47 "WHILE 검증 모드가 활성인 동안…"), Unwanted 3건(예: L60 "IF 처리 모듈이 다른 처리 모듈을 직접 호출하면, THEN…"), Optional 1건(L53 "WHERE 모듈이 내부 상태를 선언하는 경우…"). 비형식 문장("~하면 좋다", "가능하면") 0건. 단, CI-3(L74)의 패턴 라벨 불일치는 결함 D1로 기록(문장 자체는 EARS 형식 준수 — Ubiquitous+Optional 복합).
- [PASS] **MP-3 YAML 프론트매터 유효성**: 프로젝트 규약(.claude/agents/moai/manager-spec.md:L113 — "8 fields: id, version, status, created, updated, author, priority, issue_number") 기준으로 8필드 전수 대조. spec.md:L2-9 — id: SPEC-INFRA-001(문자열, SPEC-{DOMAIN}-{NUM} 패턴 부합), version: 0.1.0, status: draft(유효 enum), created/updated: 2026-07-08(ISO 날짜), author: drake.lee, priority: high(유효 enum), issue_number: 0(plan.md 워크플로우 L378 규약상 "0 if --no-issue" 유효). 누락 0건, 타입 불일치 0건. (일반 MP-3의 created_at/labels 필드명은 본 프로젝트의 8필드 스키마로 대체 적용 — 프로젝트 템플릿이 구속력 있는 스키마임.)
- [N/A] **MP-4 언어 중립성**: 본 SPEC은 Python 3.11+ 단일 언어 프로젝트(spec.md:L32, repo CLAUDE.md 기술 스택)로 다중 언어 툴링을 다루지 않음. N/A: single-language SPEC — auto-pass.

**must-pass 4/4 통과. 그러나 아래 major 결함 2건(D2, D4)으로 인해 Consistency(CN-1)·Testability(AC-2) 체크리스트가 FAIL이며, 종합 점수 0.74 < 0.75로 전체 판정 FAIL.**

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.60 | 0.50~0.75 사이 | D4: spec.md:L43(DATA-1 "pixel buffer(float32)") + L44(DATA-2 사이드채널 금지) + L74(CI-3 float64 병행 산출)의 상호작용이 미해소 — 합리적 구현자마다 다르게 해석 가능. 그 외 요구는 단일 해석 가능 |
| Completeness | 1.00 | 1.0 | HISTORY(L20), 배경/가정(L14-18, L30-37), Requirements(L39, 17건), Exclusions(L77-86, 구체 항목 8건), AC 별도 파일(acceptance.md, Scenario 3 + EC 5 + DoD 체크리스트 9항). 프론트매터 8필드 완비 |
| Testability | 0.60 | 0.50~0.75 사이 | D2: acceptance.md:L39-42 EC-4가 작성된 그대로는 구현·판정 불가(하단 상술). 나머지 Scenario 1~3(L7-20), EC-1~3/5, DoD 항목은 이진 판정 가능("불일치 0건", "0건으로 검출", "PASS/FAIL"). 위즐 워드("적절한", "합리적인") 0건 |
| Traceability | 0.75 | 0.75 | SWR 매핑 전수 검증: DATA↔SWR-000-6/-10/-3/-4, CONTRACT↔-7/-11, ORCH↔-8/-2/-5, STATIC↔-8/-9, CI↔-1/-11/-12 — 모두 XDET_SWR_spec_v1.2.md:L13-19, L25-29와 정확히 일치. AC의 REQ 참조 전건 실재. TC-021(TestSpec:L28), EV-401(EVAL:L137) 실재 확인. 단 REQ-INFRA-CONTRACT-2는 대응 AC 부재(D3) — 1건 미커버 |

## Defects Found

**D1.** spec.md:L74 — REQ-INFRA-CI-3의 라벨은 "(Ubiquitous)"이나 본문은 "float32 기본 단일 경로로 연산하되(Ubiquitous 절) + WHERE 검증 모드가 활성인 경우 float64 병행 산출 경로를 제공(Optional 절)"의 복합 요구. 라벨-본문 불일치. — Severity: **minor**

**D2.** acceptance.md:L39-42 (EC-4) — "어떤 모듈이 XFrame 컨테이너 외의 채널(전역 상태·부가 반환값·파일 우회)로 데이터를 전달하려 하면 → 계약 검사/정적 검사가 검출하여 FAIL"을 약속. 그러나 근거 문서 XDET_TestSpec_v1.0.md:L7의 XDET-TC-000 검사 범위는 "fixture 입출력 일치 + **시그니처·의존 방향 정적 검사**(직접 호출 검출 시 실패)"뿐. 임의의 전역 상태 변경·파일 우회를 일반적으로 검출하는 정적/계약 검사는 존재하지 않으며 SPEC 어디에도 검출 메커니즘이 명세되지 않음. EC-4는 작성된 그대로는 구현 불가능한 과잉 약속 — TC-000 DoD 판정을 오염시킴. — Severity: **major**

**D3.** spec.md:L53 (REQ-INFRA-CONTRACT-2) — "내부 상태의 XFrame 직렬화 가능성" 요구에 대응하는 AC가 acceptance.md 어디에도 없음(Scenario 1~3, EC-1~5, DoD 체크리스트 전수 확인). T0에 상태 보유 모듈(lag, T4)이 없다는 사정은 있으나, SPEC 내 명시적 이연 표기도 없음. — Severity: **minor**

**D4.** spec.md:L43 + L44 + L74 — 요구 간 정합성 미해소: DATA-1은 XFrame pixel buffer를 float32로 고정하고 "유일한 모듈 입출력 단위"로 선언, DATA-2는 XFrame 외 모든 채널을 계약 위반으로 규정. 그런데 CI-3의 float64 병행 산출물은 (a) float32 XFrame에 담을 수 없고 (b) XFrame 외 채널로 전달하면 DATA-2 위반. float64 산출물의 합법적 전달 채널/자료형 정책이 미정의 — 문자 그대로 읽으면 CI-3 이행이 DATA-1 또는 DATA-2와 충돌. (근거 SWR-000-1 자체가 가진 긴장이지만, 이를 해소하는 것이 SPEC의 역할.) — Severity: **major**

**D5.** spec.md:L17 "XDET-TC-000" vs L72-75 "TC-000~021" — TC ID 접두어 표기 혼용. TestSpec 공식 표기는 XDET-TC-NNN(TestSpec:L7). 단 repo CLAUDE.md도 축약형을 관용적으로 사용하므로 표기 통일 권고 수준. — Severity: **minor**

**D6.** spec.md:L45 (REQ-INFRA-DATA-3) — 요구사항 본문에 직렬화 포맷(npz + JSON sidecar)이라는 구현 방법(HOW)이 포함됨. [P] 태그 + "T2 재검토 가능" + HISTORY의 사용자 결정 4(L26)로 완화되어 있으나, 원칙적으로 WHAT과 분리하여 Environment/Assumptions 또는 plan.md로 이동이 바람직. — Severity: **minor**

## Chain-of-Verification Pass

2차 재검토 수행 항목:
- **REQ 전수 재확인**: 17건(DATA 6 + CONTRACT 4 + ORCH 4 + STATIC 3 + CI 4)을 처음부터 끝까지 재열람 — 번호 갭/중복 없음 재확인.
- **SWR 매핑 재대조**: ORCH-3의 고정 순서 "offset → gain → defect → lag → line noise → (포화/기하) → post"(spec.md:L61)가 SWR-000-2(SWR spec:L26)와 문자 단위 일치 확인. STATIC-3의 공용 컴포넌트 5종(L68)이 SWR-000-9(L16)의 ①~⑤와 대응 확인 — SWR ②의 "직접선 분리"가 SPEC 표기에서 생략되었으나 T0 스텁 범위에서 무해.
- **Exclusions-요구 충돌 검사**: L86(모듈 트리 내 레퍼런스 모듈 없음) ↔ CONTRACT-3 2문장(L54) 일치. L82(TC-021 임계 없음) ↔ CI-4 "훅 구조만 제공"(L75) 일치. 충돌 없음.
- **CONTRACT-1 "순수함수형" vs CONTRACT-2 "내부 상태 허용"**: 표면상 긴장이나 SWR-000-7(SWR spec:L14) 원문이 동일 구조("순수함수형(내부 상태는 lag 등 명시 선언 모듈만 허용)")이므로 근거 계승으로 판단 — 결함 아님.
- **DoD 스캐폴드 목록**(acceptance.md:L51)에서 `docs/` 생략: repo CLAUDE.md T0 목록에는 docs/ 포함이나 docs/는 기존 존재 — 결함 아님(관찰 사항).

2차 재검토 신규 결함: **없음** — 1차에서 식별한 D1~D6이 전부이며, D2/D4의 심각도 판단을 재확인함(특히 D4는 "모듈이 아닌 프레임워크 수준 대조 산출물"로 해석하면 회피 가능하다는 반론을 검토했으나, float64 **연산 경로**를 통과하는 모듈 입출력 자체가 XFrame(float32) 계약과 충돌하는 문제는 해석으로 해소되지 않음 — major 유지).

## Regression Check (Iteration 2+ only)

해당 없음 — iteration 1.

## Recommendation

manager-spec은 다음을 수정한 뒤 재감사를 요청할 것 (수정 필수: 1, 2 / 권고: 3~6):

1. **[필수, D4]** float64 병행 경로의 자료형·채널 정책을 명시하라. 권장안: REQ-INFRA-DATA-1을 "pixel buffer(기본 float32; WHERE 검증 모드가 활성인 경우 float64 병행 버퍼/XFrame 변형 허용)"로 개정하거나, CI-3에 "float64 산출물은 검증-모드 XFrame(또는 프레임워크 수준 대조 아티팩트)으로 전달되며 이는 DATA-2의 사이드채널에 해당하지 않는다"는 해소 문장을 추가할 것. spec.md:L43, L44, L74 3개 요구가 상호 참조로 닫히게 할 것.
2. **[필수, D2]** acceptance.md EC-4(L39-42)를 검출 가능한 범위로 축소하라. 권장안: TC-000의 실제 검사 범위(시그니처 검사 + import-linter 의존 방향 + 반환값 타입/개수 검사)에 맞춰 "부가 반환값·시그니처 위반은 계약 검사로 검출"로 한정하고, 전역 상태·파일 우회는 "레퍼런스 위반 fixture(예: 전역 변수 기록 모듈) 1건에 대한 검출 시연" 수준의 구체 테스트로 명세하거나 코드 리뷰 게이트로 이관할 것.
3. **[권고, D1]** spec.md:L74 CI-3를 CI-3a(Ubiquitous: float32 기본 단일 경로) / CI-3b(Optional: WHERE 검증 모드 시 float64 병행)로 분리하거나 라벨을 복합(Ubiquitous+Optional)으로 정정.
4. **[권고, D3]** REQ-INFRA-CONTRACT-2에 대응 AC를 추가(예: "상태 직렬화 인터페이스가 프로토콜에 존재함을 확인하는 구조 테스트")하거나 "T4에서 검증(이연)" 명시.
5. **[권고, D5]** TC ID 표기를 XDET-TC-NNN 또는 TC-NNN 중 하나로 통일.
6. **[권고, D6]** DATA-3의 npz+JSON sidecar 포맷 지정을 Environment/Assumptions(L36에 이미 존재) 참조로 대체하고 요구 본문은 "공통 스키마 준수 + 단일 직렬화 규약"의 WHAT 수준으로 유지.

---
감사자: plan-auditor | 근거 문서: repo CLAUDE.md, docs/XDET_SWR_spec_v1.2.md(L13-19, L25-29), docs/XDET_TestSpec_v1.0.md(L7, L28), docs/XDET_EVAL_criteria_v1.1.md(L137), .claude/agents/moai/manager-spec.md(L113)
