# SPEC-INFRA-001 — 인수 기준 (Acceptance Criteria)

DoD: **XDET-TC-000 통과** — 모듈 fixture 입출력 일치 + 시그니처·의존 방향 정적 검사, 계약 위반 0건. 모든 기준은 관측 가능(테스트 출력·정적 검사 결과·오류 발생)해야 한다.

## Given-When-Then 시나리오

### Scenario 1 — 레퍼런스 passthrough 모듈 harness 통과 (REQ-INFRA-CONTRACT, DATA)
- **Given** `tests/` fixture에 레퍼런스 passthrough(항등) 모듈과, 합성 입력 XFrame + 기대 출력 XFrame(항등이므로 입력과 동일) 쌍이 동봉되어 있다.
- **When** harness가 passthrough 모듈의 `process(XFrame, CalibSet, Params)`를 실행하고 결과를 기대 XFrame과 비교한다.
- **Then** pixel(float32) · 마스크 스택 · 노이즈 모델(α, σ) · 처리 이력 체인이 모두 일치하고, 이력 체인에는 모듈 버전 · 파라미터 해시 · CalibSet ID가 결정론적으로 추가되어 있다. 불일치 0건.

### Scenario 2 — 고정 파이프라인 순서 오케스트레이션 (REQ-INFRA-ORCH)
- **Given** 오케스트레이터(파이프라인 정의)가 레퍼런스 passthrough 모듈들을 고정 순서 offset → gain → defect → lag → line noise → (포화/기하) → post 로 조립하도록 정의되어 있고, 유효한 CalibSet이 주어져 있다.
- **When** 오케스트레이터가 파이프라인을 실행한다.
- **Then** 모듈이 정의된 순서대로 실행되며, 각 단계 입력 XFrame은 불변으로 보존되고, 모듈 간 직접 호출 없이 오케스트레이터만이 조합을 수행한다. 검증 모드가 활성이면 단계별 중간 XFrame이 보존된다.

### Scenario 3 — 정적 의존 방향 검사 통과 (REQ-INFRA-STATIC, CI)
- **Given** 스캐폴드(`common/ modules/ pipeline/ metrics/ tests/`)와 `import-linter` 선언적 레이어링 계약(`module → common` 단방향, 모듈 간 import 금지)이 설정되어 있다.
- **When** CI가 `import-linter` + pytest(XDET-TC-000)를 플랫폼 무관 진입점(Makefile/scripts)으로 실행한다.
- **Then** 모듈→모듈 직접 import, common→module 역방향, 모듈 간 수평 의존이 0건으로 검출되고 계약 위반 0건으로 XDET-TC-000이 PASS 한다.

### Scenario 4 — 상태 직렬화 인터페이스 구조 확인 (REQ-INFRA-CONTRACT-2)
- **Given** 모듈 계약(추상 프로토콜)이 정의되어 있다.
- **When** 구조 테스트가 프로토콜 인터페이스를 검사한다.
- **Then** 내부 상태를 XFrame 컨테이너로 직렬화/역직렬화하는 인터페이스(계약 자리)가 프로토콜에 존재함이 확인된다. 상태 보유 모듈(lag)을 통한 런타임 왕복 검증은 T4로 이연하며 본 T0 범위 밖이다.

## Edge Cases (부정/경계 케이스)

### EC-1 — CalibSet 부재 (REQ-INFRA-ORCH-4)
- **Given** 오케스트레이터에 CalibSet 파일이 주어지지 않았다.
- **When** 파이프라인 진입 검증 게이트가 실행된다.
- **Then** 시스템은 처리를 거부하고 명시 오류를 발생시킨다. 무단 기본값 대체가 발생하지 않는다.

### EC-2 — CalibSet 불일치 (해상도/패널 ID) (REQ-INFRA-ORCH-4, DATA-3)
- **Given** CalibSet의 해상도 또는 패널 ID가 입력 XFrame과 불일치한다.
- **When** 진입 검증 게이트가 스키마·정합성을 확인한다.
- **Then** 시스템은 처리를 거부하고 불일치 필드를 명시한 오류를 발생시킨다.

### EC-3 — 잘못된 시그니처 (REQ-INFRA-CONTRACT-1)
- **Given** 시그니처가 `process(XFrame, CalibSet, Params) -> XFrame`을 따르지 않는 모듈(예: 인자 누락, 반환 타입 상이)이 존재한다.
- **When** harness/계약 검사가 실행된다.
- **Then** 계약 위반으로 검출되어 XDET-TC-000이 FAIL 한다.

### EC-4 — 사이드채널: 자동 검출 가능 범위 한정 (REQ-INFRA-DATA-2)
- **Given** 시그니처를 위반하거나 계약 외 부가 반환값을 추가한 위반 fixture 모듈이 `tests/`에 동봉되어 있다.
- **When** 계약 검사(시그니처·반환값 형태)와 import-linter 정적 검사가 실행된다.
- **Then** 시그니처 위반·부가 반환값은 계약 검사로, 모듈 간 직접 import는 정적 검사로 검출되어 FAIL 한다.
- **범위 밖(설계 규칙 — 테스트 가능 AC 아님)**: 전역 상태 기록·파일 우회 등 임의의 사이드채널에 대한 일반 자동 검출은 XDET-TC-000 범위에 포함되지 않으며(TestSpec:L7 검사 범위 = fixture 입출력 일치 + 시그니처·의존 방향 정적 검사), REQ-INFRA-DATA-2의 금지는 코드 리뷰 게이트로 강제한다.

### EC-5 — 의존 방향 위반 검출 (REQ-INFRA-STATIC-2)
- **Given** 한 모듈이 다른 모듈을 직접 import 하거나, `common/`이 `modules/`를 역참조하거나, 모듈 간 수평 의존이 존재한다.
- **When** `import-linter` 정적 검사가 실행된다.
- **Then** 해당 위반이 열거되어 검사가 FAIL 하고 머지가 차단된다.

## 품질 게이트 / Definition of Done

- [ ] repo 스캐폴드(`common/ modules/ pipeline/ metrics/ tests/ data/`) + `.gitattributes`(LFS 트래킹) 생성
- [ ] XFrame(4구성요소·불변·검증모드 중간산출) + CalibSet(공통 스키마·검증기·npz/JSON sidecar) 구현
- [ ] 단일 시그니처 계약(추상 프로토콜) + 모듈 harness 구현
- [ ] 오케스트레이터(고정 순서 강제 + CalibSet 진입 검증 게이트) 구현
- [ ] `import-linter` 레이어링 계약 + 공용 컴포넌트 5종 디렉터리/스텁 배치
- [ ] pytest 진입점(Makefile/scripts) + XDET-TC-000 실동작, XDET-TC-001~021 skeleton 등록
- [ ] 단일 시그니처 프로토콜에 상태 직렬화 인터페이스 존재(구조 확인, Scenario 4). 상태 보유 모듈 런타임 검증은 T4 이연.
- [ ] float32 기본 단일 경로 + float64 검증-모드 병행 버퍼(검증-모드 XFrame 내부 필드, DATA-1) + 구현 교체 diff 유틸 훅
- [ ] Scenario 1~4 통과, EC-1~5 정상 거부/검출
- [ ] **XDET-TC-000 PASS (계약 위반 0건)** — DoD
