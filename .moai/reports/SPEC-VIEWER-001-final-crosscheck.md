# SPEC-VIEWER-001 — 최종 교차검증 보고서 (커밋 전 마지막 게이트)

- 검증자: evaluator-active (독립 스켑틱 리뷰)
- 대상: `docs/GUI_CRITERIA.md`, `.moai/specs/SPEC-VIEWER-001/{spec.md,plan.md,acceptance.md}`(v0.1.2), `docs/GUI_REVIEW.md`, GitHub 이슈 #14~#19, `.moai/reports/plan-audit/SPEC-VIEWER-001-review-{1,2}.md`
- 범위: EARS 세부 재감사가 아니라(이미 plan-audit 2회, 최종 PASS 0.94, 12개 결함 해소 완료) **패키지 전체의 정합성·완결성·정직성**에 대한 홀리스틱 교차검증
- 검증 방법: 코드 사실 재대조(`common/contract.py` L131-152, `pyproject.toml` L17-42, `tests/fixtures/badlayers/`, `tests/test_tc000.py` L86-113, `tests/test_tc_skeletons.py` L79-115, `scripts/test.ps1`/`test.sh`), GitHub 이슈 5건 본문 원문 확인, 저장소 auto-memory lessons.md 대조

## 종합 판정: **READY-WITH-NOTES**

두 차례 plan-audit(iter1 FAIL 0.72 → iter2 PASS 0.94)가 인용한 코드 사실을 독립적으로 재확인한 결과 **왜곡·허위 인용 0건**이었다(아래 "재검증 결과" 참조). EARS 구조·추적성·D1~D10/N1~N2 해소는 견고하다. 다만 두 audit 라운드는 SPEC 3부작 내부 정합성에 집중했기 때문에 **패키지 외부(GUI_REVIEW.md 최신성)와 운영 실행 디테일(CI 인프라 부재, uv 전용 환경, 스파이크 리포트 산출물 위치)**에서 두 라운드 모두 놓친 신규 갭 5건을 발견했다. 전부 major/critical이 아니라 문서 정합·실행 디테일 수준이므로 SPEC 재설계는 불필요하지만, run 착수 전 처리를 권고한다.

---

## A. 문서 간 정합성 (Cross-Document Consistency)

### A-1. GUI_CRITERIA.md ↔ SPEC 3부작: 정합 확인
C-01~C-20·SG-1~3 전 항목이 spec.md의 REQ 그룹에 누락 없이 인용되며(plan-audit iter1의 "C-01~C-20 전수 매핑 확인"을 재검토), 약화되거나 조용히 삭제된 기준은 없다. 선행 코드 개선 의존표(§4)의 #15/#16/#18/#17/#19 처분도 spec.md Environment·Exclusions·결정 필요 섹션에 전건 반영되어 있다.

### A-2. [발견] GUI_REVIEW.md의 최신성 붕괴 — **신규, 중간 심각도**
`docs/GUI_REVIEW.md` §4 표 아래 각주(L38)와 §6 "다음 단계"(L60-64)는 다음과 같이 서술한다:

> *(2026-07-10 논의 시점 사용자 응답: "다시 디테일하게 작업할 예정" — 위 표는 그 시점까지의 검토 결과이며 옵션 선택은 아직 확정되지 않음)*
> ## 6. 다음 단계
> 1. 사용자가 §4 범위(A/B/C/D)를 확정
> 2. 확정되면 `manager-spec`에 위임해 EARS 형식 정식 SPEC 작성

그러나 같은 날짜(2026-07-10)로 작성된 `docs/GUI_CRITERIA.md` §1은 이미 "**옵션 C(A+B 통합)를 단계형으로 채택한다**"고 확정했고, SPEC-VIEWER-001(spec.md/plan.md/acceptance.md)까지 완성되어 plan-audit 2회를 거쳐 PASS 0.94에 도달했다. 즉 GUI_REVIEW.md는 spec.md 자신이 "근거" 문서로 인용하는(spec.md L19) 문서임에도, **그 문서를 그대로 읽으면 범위가 아직 미확정이라고 오독하게 된다** — 옵션 D("미정")가 실제로는 이미 지나간 단계인데 문서상 남아있는 상태.

- **왜 문제인가**: GUI_REVIEW.md는 "SPEC이 아니다"(L3)라고 명시하지만, spec.md가 이를 1차 근거로 인용하므로 독자(특히 향후 세션에서 컨텍스트 없이 재진입하는 에이전트)가 GUI_REVIEW.md만 읽고 "옵션이 아직 미정"이라 오판할 위험이 있다.
- **권고**: GUI_REVIEW.md는 이미 §4.5("운영 형태 결정 — 서브 프로젝트 확정")에서 날짜 있는 addendum 섹션을 추가한 선례가 있다. 동일한 패턴으로 **§4.6(또는 §4 각주 갱신)에 "2026-07-10 확정: 옵션 C 단계형 채택 — 근거는 GUI_CRITERIA.md §1, SPEC은 SPEC-VIEWER-001" 1단락**을 추가하고 §6 "다음 단계" 1번 항목에 완료 표시(취소선 또는 "완료 → GUI_CRITERIA.md §1 참조")를 다는 것을 권고한다. SPEC/CRITERIA 파일 자체는 수정하지 않음(범위 밖 지시 준수) — GUI_REVIEW.md만 대상.
- **심각도**: 중간(medium) — 차단 사유는 아니나, "이 패키지가 커밋되어 향후 참조될 단일 출처 세트"라는 목적에 비추어 방치하면 다음 세션에서 동일한 혼란이 재발할 것.

### A-3. 이슈 #18 vs SPEC 확정 — **divergence 아님, acceptable**
이슈 #18 본문은 "옵션 비교 후 택1 (SPEC-VIEWER-001 계획 단계에서 확정)"이라고 명시적으로 결정을 SPEC 단계로 위임했다. spec.md 결정 필요 2번과 plan.md §3(L64)이 `common/synth_calibset.py` 단일 배치로 확정한 것은 **이슈가 요청한 절차를 정확히 이행한 결과**이며 이슈 본문과 모순되지 않는다(이슈가 예시로 든 3개 옵션 중 옵션 1의 변형을 채택한 것도 이슈 본문 "옵션 1: 최소 합성 CalibSet 팩토리를 배포 코드로 승격(예: `common/synth.py`)"과 정합 — 파일명만 `synth_calibset.py`로 구체화됨).
- **권고**: 이슈 본문 자체를 지금 수정할 필요는 없다(오픈소스 관행상 이슈는 "문제+검토된 옵션"의 기록, PR/커밋이 "Closes #18"로 최종 결정을 반영). Phase 0.5 구현 PR이 머지될 때 커밋 메시지 또는 PR 본문에 "Closes #18 — `common/synth_calibset.py` 단일 배치 확정(SPEC-VIEWER-001 결정 필요 2)"을 남기는 것으로 충분. **지금 시점에 이슈를 닫거나 편집할 필요 없음** — 아직 코드가 존재하지 않으므로(§C-2 확인) 조기 종료는 부적절.

### A-4. 이슈 #15/#16 — SPEC과 정합
#15(`default_registry()`)·#16(`common/io.py`)는 spec.md REQ-VIEW-CORE-1/-2에 제안된 API 형태 그대로 반영되어 divergence 없음.

---

## B. 버전/추적 무결성 (Version/Trace Integrity)

| 항목 | 확인 결과 |
|---|---|
| spec.md frontmatter | `version: 0.1.2`, 8필드 전부 존재, `issue_number: 14` — GitHub #14 제목("[REVIEW] 단위 모듈/파이프라인 검증용 GUI 도입 검토")과 일치 |
| plan.md frontmatter | `version: 0.1.2` — spec.md와 동기화 확인 |
| acceptance.md | frontmatter 없음 — SPEC-TIER-001/SPEC-INFRA-001과 동일한 저장소 관행(review-2 확인 사항 재검증, 결함 아님) |
| HISTORY 완결성 | v0.1.0→v0.1.1(D1~D10)→v0.1.2(N1/N2) 3단계 전부 spec.md에 기록. **N1/N2 실제 반영 여부를 직접 재확인**: plan.md §5(fixture 표) "fixture → `process` 출력 XFrame(...) + MaskFlag 스택" — 구본 `run_harness 출력` 문구 소거 확인. plan.md §7 Phase 1 마일스톤 "모듈 1개 `ProcessModule.process` 실행..." — 구본 소거 확인. acceptance.md L8 코드리뷰 목록에 "W/L·줌/팬 무복사 경로(IMAGE-2: ... 프로파일러 확인 + 리뷰)" 추가 확인. **HISTORY의 "해소했다"는 주장은 허위가 아님** |
| plan-audit 참조 | spec.md HISTORY가 "plan-audit iter2 PASS 0.94"를 인용 — review-2.md의 실제 점수(0.94)·구조와 정확히 일치 |
| issue_number 정합 | 14로 고정, #15~#19는 본문에서 "(이슈 #15/#16/#18)" 등으로 정확히 상호 참조됨 |

**결론**: B 영역은 결함 없음. 두 차례 audit이 반복 재검증한 부분이라 견고성이 가장 높다.

---

## C. 실행 가능성 (Executability) — manager-tdd가 내일 Phase 0을 시작할 수 있는가

이 영역에서 **신규 갭 4건**을 발견했다. 두 plan-audit 라운드는 SPEC 3부작 "내부" 정합성(EARS 형식·추적성·코드 계약 일치)에 집중했기 때문에, "실제로 실행할 때 무엇이 없는가"라는 운영 디테일은 검사 범위 밖이었다.

### C-1. [발견] CI 인프라 자체가 저장소에 없음 — **중간 심각도**
`plan.md §8 "CI 잡 추가"`는 `core-no-gui`·`gui-offscreen`·`license-gate`·`import-linter(확장)` 4개의 "CI 잡"을 이름 붙여 정의한다. 그러나:
```
find .github -type f  →  No such file or directory
```
저장소에는 GitHub Actions 워크플로가 전혀 없다. 현재 유일한 "CI 진입점"은 `scripts/test.ps1`/`scripts/test.sh`(로컬 셸 스크립트, `uv run lint-imports` + `uv run pytest -q`만 실행)뿐이다. plan.md는 이 4개 잡이 **어디에 구현되어야 하는지**(신규 `.github/workflows/*.yml` 생성? 기존 `scripts/test.ps1`/`test.sh`를 잡 단위로 확장? 둘 다?) 명시하지 않는다.
- **영향**: manager-tdd가 Phase 0.5/아키텍처 게이트 작업을 시작할 때 "CI 잡"이라는 용어를 곧이곧대로 받아들이면 존재하지 않는 GitHub Actions 관행을 가정하고 새 인프라를 만들 수도 있고, 반대로 로컬 스크립트만 확장하고 끝낼 수도 있다 — 산출물 형태가 결정되지 않은 채 구현이 시작될 위험.
- **권고**: plan.md §8에 "본 SPEC의 'CI 잡'은 `scripts/test.ps1`/`test.sh`에 단계(스테이지)로 추가한다(GitHub Actions 워크플로는 범위 밖)" 또는 그 반대를 1줄로 확정.

### C-2. [발견] uv 전용 환경 규약이 plan.md §8 명령 예시에 반영되지 않음 — **중간 심각도**
저장소 auto-memory(`lessons.md` #4, environment)는 "**`python`이 PATH에 없음 — 모든 실행은 `uv run ...`**"이라고 명시한다. 실제로 `scripts/test.ps1`/`test.sh`는 예외 없이 `uv run lint-imports`, `uv run pytest -q` 형태다. 그러나 plan.md §8의 신규 CI 잡 명령 예시는 이 규약을 따르지 않는다:
- `core-no-gui`: `"pytest --ignore=tests/apps"` — `uv run` 접두어 없음
- `import-linter(확장)`: `"lint-imports --config <tmp>"` — 없음 (단, EC-2/acceptance.md L71은 `_run_lint_imports`라는 기존 테스트 헬퍼를 재사용하도록 되어 있어 실질 위험은 낮음 — `tests/test_tc000.py`의 `_run_lint_imports`가 내부적으로 올바른 실행 경로를 사용할 가능성이 높음)
- `license-gate`: `"pip-licenses"` — 없음
- **영향**: 이 문구를 그대로 셸 명령으로 옮기면 `python`/`pytest`가 PATH에 없어 즉시 실패한다(이미 한 번 저장소에서 관측되어 lesson으로 남은 실패 패턴과 동일 계열).
- **권고**: plan.md §8의 4개 명령 예시를 `uv run pytest --ignore=tests/apps`, `uv run pip-licenses`, `uv pip install .[gui]`(이미 uv 사용 중, 정정 불요)로 통일. 1줄 편집 수준.

### C-3. [발견] Phase 0 스파이크 리포트의 저장 위치·포맷 미지정 — **중간 심각도**
REQ-VIEW-SPIKE-1은 "시스템은 ... 스파이크 리포트를 산출해야 한다"고 요구하고, plan.md는 `tests/apps/gui/test_tc_viewer_spike.py`(XDET-TC-030)를 테스트 파일로 배치하지만, **리포트 자체가 어디에(파일 경로), 어떤 포맷으로(마크다운? JSON? 테스트 fixture 내 assert만?) 저장되는지는 spec.md·plan.md·acceptance.md 어디에도 없다.** 이는 프롬프트가 명시적으로 지적한 항목이자 사용자 지시가 강조한 "spike report는 어디로 가는가"에 정확히 해당하는 실질 갭이다.
- **비교**: `.moai/reports/plan-audit/`처럼 이 저장소는 산출물 저장 위치에 대한 명확한 관행이 있다. 스파이크 리포트도 예: `.moai/specs/SPEC-VIEWER-001/spike-report.md` 또는 `tests/apps/gui/artifacts/spike_report.json` 식으로 확정이 필요하다.
- **권고**: plan.md §7(Phase 0 마일스톤) 또는 §3(파일 레이아웃)에 스파이크 리포트 산출 경로 1줄 추가.

### C-4. [발견] SPIKE-1/SG-1·SG-2의 자동검출/코드리뷰 분류 누락 — **중간 심각도, 두 plan-audit 모두 미발견**
`acceptance.md`의 "자동 검출 vs 코드리뷰 설계 규칙" 분류표(L7-8)와 PARTIAL 섹션(L94-100)을 전수 대조한 결과:
- PARTIAL 섹션은 **C-17(콜드 스타트 10s, SG-3)**만 "스파이크에서 실측 + 하드 수치 CI 단정 아님"으로 명시적으로 완화 처리했다.
- 그러나 **C-01/SG-2("W/L 조작 응답 100ms")도 동일하게 실시간 타이밍 측정이라는 점에서 인식론적으로 동일 부류**임에도 PARTIAL 섹션에 없고, "자동 검출" 목록(L7)에도 "W/L 수치 적용"(값 적용의 정확성)만 있을 뿐 "100ms 이내 응답"이라는 타이밍 자체의 판정 주체가 명시되지 않는다.
- 또한 SPIKE-1(스파이크 리포트 자체의 산출 — SG-1/SG-2/SG-3 실측치를 담은 리포트 생성)과 SG-1(호버 프로브가 float32 원값을 노출하는지)은 L7/L8 분류표 어디에도 명시적으로 귀속되지 않는다. SG-1은 사실 순수 로직 검증(표시값이 아닌 저장값 반환 여부)이라 자동 검출이 충분히 가능하지만, 표에는 없다.
- **왜 두 plan-audit이 놓쳤는가(추정)**: iter1/iter2 모두 D5(SPIKE-3/CORE-4 분류 누락)를 발견해 해소했으나, "분류표 자체의 완전성"(35개 REQ 각각이 L7/L8/PARTIAL 셋 중 정확히 하나에 속하는가)을 항목 단위로 재귀 검증하지는 않았다 — SPIKE-1/SG-2는 REQ 자체는 아니고 C-NN/SG-N 기준이라 REQ 추적성 검사망(35 REQ 전수 재검사)에 걸리지 않았을 가능성이 높다.
- **권고**: acceptance.md PARTIAL 섹션에 "C-01(SG-2, 100ms)도 스파이크 SG-2 실측 + `[T]` 설정 외부화로 처리, 하드 수치 CI 단정 아님"을 C-17과 나란히 추가. L7 자동 검출 목록에 "SG-1 호버 프로브 저장값 검증(로직 레벨, 타이밍 아님)"을 명시 추가.

---

## D. 정직성 (Honesty)

### D-1. GUI_CRITERIA.md §2.1 가중 매트릭스 점수의 허위 정밀도 — **낮은 심각도, 정보성**
"가중 매트릭스(...): napari 4.23, pyqtgraph 4.28로 사실상 동률"이라는 문장은 소수점 둘째자리까지의 점수를 제시하지만, 그 산출에 쓰인 항목별 세부 점수표(6개 후보 × 6개 기준의 원점수)는 문서 어디에도 없다 — 결론 문장만 있고 계산 과정이 재현 불가능하다. "사실상 동률"이라는 정성적 결론 자체는 타당해 보이나(napari를 1순위로 확정한 근거가 "개발속도 체감" 정성 논리로 바로 이어짐), 소수점 둘째자리 수치는 실제로는 검증 불가능한 근사치를 사실인 것처럼 제시하는 셈이다.
- **판단**: [T] 튜닝 값이나 EARS 요구 수치가 아니라 스택 선정 **근거 문서의 리서치 서술**이므로 SPEC 품질 게이트에는 영향 없음. 다만 "이 결정이 재현 가능한 리서치에 기반했다"는 신뢰를 주는 문장이 실제로는 재현 불가능한 요약이라는 점에서 과잉 정밀도(false precision) 사례로 기록해 둔다. 차단 사유 아님.

### D-2. 그 외 항목: 과잉 확신 발견 안 됨
- `[T]` 태그가 붙은 모든 수치(100ms/10s/2GB/200ms/±max|diff|)는 spec.md 규범 본문에 하드코딩되지 않고 일관되게 괄호+`[T]` 표기로 격리되어 있다(review-1/2가 이미 전수 확인했고, 본 재검증에서도 spec.md 재열람으로 재확인) — 연구 파생 수치를 사실처럼 단정한 사례 없음.
- MaskFlag/HistoryEntry/run_harness 시그니처 등 코드 인용은 전부 실제 소스와 바이트 단위로 일치(본 보고서 상단 "검증 방법"에서 직접 재확인) — 검증되지 않은 주장을 사실처럼 기술한 사례 없음.
- HISTORY의 "D1~D10/N1~N2 해소" 주장은 실제 파일 내용과 대조해 허위 없음(§B 참조).

---

## 신규 결함 요약 (Findings List)

| # | 심각도 | 위치 | 내용 |
|---|---|---|---|
| F1 | Medium | `docs/GUI_REVIEW.md` L38, L60-64 | §4 각주·§6 "다음 단계"가 이미 확정된 옵션 C 채택(GUI_CRITERIA.md §1)과 모순되는 미확정 서술을 유지 |
| F2 | Medium | `.moai/specs/SPEC-VIEWER-001/plan.md` §8 | "CI 잡" 구현 대상(GitHub Actions vs `scripts/test.ps1`/`test.sh` 확장)이 명시되지 않음 |
| F3 | Medium | `plan.md` §8 명령 예시(4곳) | `uv run` 접두 누락 — 저장소 uv 전용 환경 규약(lessons.md #4)과 불일치, 문언 그대로 실행 시 실패 |
| F4 | Medium | `spec.md`/`plan.md`/`acceptance.md` 전체 | Phase 0 스파이크 리포트(REQ-VIEW-SPIKE-1 산출물)의 저장 경로·포맷 미지정 |
| F5 | Medium | `acceptance.md` L7-8, L94-100(PARTIAL) | C-01/SG-2(100ms)가 C-17/SG-3(10s)과 동일 부류의 타이밍 측정임에도 PARTIAL 처리 비대칭; SPIKE-1 리포트 산출·SG-1 호버 로직이 자동검출/코드리뷰 분류표 어디에도 명시적으로 귀속되지 않음 |
| F6 | Low(정보성) | `docs/GUI_CRITERIA.md` §2.1 | 가중 매트릭스 점수(4.23/4.28)가 세부 산출 근거 없이 소수점 둘째자리로 제시되어 과잉 정밀도 |

없음(No divergence): 이슈 #15/#16/#18 본문과 SPEC 확정 내용 사이에 수정이 필요한 실질적 모순은 발견되지 않았다(§A-3/A-4).

---

## #18 이슈-SPEC divergence에 대한 권고 (요청 사항)

**divergence 아님, acceptable.** 이슈 #18은 결정을 SPEC 계획 단계로 명시적으로 위임했고, SPEC은 이슈가 제시한 옵션 1의 구체화(`common/synth_calibset.py`)로 정확히 응답했다. **이슈 본문을 지금 편집할 필요 없음.** Phase 0.5 구현이 머지되는 시점에 PR/커밋에서 "Closes #18"로 자연스럽게 정리하면 충분하다. 지금 이슈를 닫거나 옵션 목록을 수정하면 오히려 "왜 그런 결정을 내렸는가"라는 논의 기록이 손실된다.

## GUI_REVIEW.md 갱신 필요성에 대한 권고 (요청 사항)

**갱신 필요, 단 SPEC/CRITERIA는 그대로 두고 GUI_REVIEW.md만.** §4.5 addendum과 동일한 패턴으로 짧은 날짜 있는 단락을 추가해 §4/§6의 미확정 서술이 이미 지나간 단계임을 명시할 것을 권고한다(F1). 이는 문서 편집자(사용자 또는 manager-docs)가 처리할 수 있는 1~2문단 수준의 작업이며, SPEC 재작성이나 재감사를 요구하지 않는다.

---

## 결론

패키지는 두 차례의 엄격한 EARS/코드-사실 대조 audit(PASS 0.94)을 통과했고, 본 독립 재검증에서 그 판정의 정직성(허위 인용 0건)을 확인했다. 다만 "커밋되어 다음 세션/에이전트가 그대로 실행할 단일 출처 세트"라는 최종 게이트 기준에서 보면, **문서 최신성(F1)과 실행 운영 디테일(F2~F5)** 5건이 아직 정리되지 않았다. 전부 1문단~1줄 수준의 수정으로 해소 가능하며 SPEC 재설계나 3차 plan-audit을 요구하지 않는다.

**권고 조치(권장 순서)**:
1. F3(uv run 접두) — plan.md §8 4곳 1줄씩 수정
2. F4(스파이크 리포트 경로) — plan.md §7 또는 §3에 1줄 추가
3. F2(CI 잡 구현 대상 명확화) — plan.md §8 서두에 1줄 추가
4. F5(PARTIAL 분류 비대칭) — acceptance.md PARTIAL 섹션에 C-01/SG-2 1줄 추가, L7에 SG-1 로직 검증 귀속 추가
5. F1(GUI_REVIEW.md 최신화) — GUI_REVIEW.md에 addendum 단락 추가 (SPEC 파일은 미변경)
6. F6은 정보성 기록으로 충분, 수정 불요

**Overall Verdict: READY-WITH-NOTES**
