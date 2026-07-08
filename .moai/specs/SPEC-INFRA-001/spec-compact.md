# SPEC-INFRA-001 (compact) — T0 프레임워크 스캐폴드

근거: SWR-000-1~12 · DoD: XDET-TC-000 통과(계약 위반 0건) · status: draft

## REQ 요약

### REQ-INFRA-DATA (SWR-000-6, -10, -3, -4)
- DATA-1 (Ubiq): XFrame = pixel(기본 float32; 검증 모드 시 동일 인스턴스가 float64 병행 버퍼 보유 가능) + 마스크 스택(defect/포화/보간 비트플래그) + 노이즈 모델(α,σ) + 이력 체인, 유일 입출력 단위. float64 병행 버퍼는 XFrame 내부 필드(DATA-2 사이드채널 아님, CI-3b가 사용).
- DATA-2 (Unwanted): 컨테이너 외 채널 전달 금지(설계 규칙). 자동 검출 범위 = 시그니처·반환값 형태(계약 검사) + 의존 방향(정적 검사); 전역 상태·파일 우회는 위반 fixture 검출 시연 + 코드 리뷰. XFrame 내부 필드 전달은 위반 아님.
- DATA-3 (Ubiq): CalibSet 공통 스키마(패널ID·해상도·유효기간·종류·데이터·이력) + 단일 직렬화 규약(포맷은 Environment/plan.md 참조, [P]).
- DATA-4 (Event): 출력 생성 시 처리 메타(버전·파라미터 해시·CalibSet ID) 이력 체인 결정론적 추가.
- DATA-5 (State): 검증 모드 중 단계별 중간 XFrame 보존.
- DATA-6 (Ubiq): 입력 XFrame 불변.

### REQ-INFRA-CONTRACT (SWR-000-7, -11)
- CONTRACT-1 (Ubiq): 단일 시그니처 `process(XFrame, CalibSet, Params) -> XFrame` 순수함수.
- CONTRACT-2 (Opt): 내부 상태 모듈(lag)은 상태를 XFrame으로 직렬화 가능. T0는 프로토콜에 직렬화 인터페이스 존재만 구조 확인, 런타임 검증은 T4 이연.
- CONTRACT-3 (Ubiq): fixture 기반 단독 시험 가능. 레퍼런스 passthrough는 tests/ 전용(modules/ 미포함).
- CONTRACT-4 (Event): harness 실행 시 실제/기대 XFrame 비교·불일치 리포트.

### REQ-INFRA-ORCH (SWR-000-8, -2, -5)
- ORCH-1 (Ubiq): 오케스트레이터만 순서·조합 결정.
- ORCH-2 (Unwanted): 모듈→모듈 직접 호출 검출·실패.
- ORCH-3 (Ubiq): 고정 순서 offset→gain→defect→lag→line noise→(포화/기하)→post 강제.
- ORCH-4 (Unwanted): CalibSet 부재/불일치(해상도·패널ID) 시 처리 거부+명시 오류(기본값 대체 금지).

### REQ-INFRA-STATIC (SWR-000-8, -9)
- STATIC-1 (Ubiq): module→common 단방향, import-linter 선언적 규칙.
- STATIC-2 (Event): 정적 검사 시 모듈→모듈 import·역방향·수평 의존 검출·실패.
- STATIC-3 (Ubiq): 공용 5종(pyramid/histogram·FOV/fft_psd/robust_stats/mask_ops) common/ 1회, 스텁만.

### REQ-INFRA-CI (SWR-000-1, -11, -12, XDET-TC-000, XDET-TC-021 훅)
- CI-1 (Ubiq): XDET-TC-000~021 pytest 등록, XDET-TC-000 실동작·나머지 skeleton.
- CI-2 (Event): 커밋 시 XDET-TC-000 게이트·위반 시 머지 차단. 진입점 플랫폼 무관(Makefile/scripts), 환경 TBD(Gitea Actions 유력).
- CI-3a (Ubiq): 골든 모델 기본 float32 단일 경로.
- CI-3b (Opt): 검증 모드 시 float64 병행 산출, 산출물은 DATA-1 검증-모드 XFrame 내부 float64 버퍼로만 전달(DATA-2 사이드채널 아님).
- CI-4 (Ubiq): 구현 교체 등가성 diff 유틸 훅(XDET-TC-021 계열 자리), 수치 임계(±1 LSB/bit-동일) P2 이연.

## Acceptance 요약
- S1: passthrough harness — pixel/마스크/노이즈모델/이력체인 일치, 불일치 0.
- S2: 고정 순서 오케스트레이션 — 순서 준수·입력 불변·직접호출 없음·검증모드 중간산출 보존.
- S3: import-linter + XDET-TC-000 CI PASS — 의존 위반 0, 계약 위반 0.
- S4: 상태 직렬화 인터페이스 구조 확인(CONTRACT-2) — 프로토콜에 인터페이스 존재, 런타임 검증 T4 이연.
- EC-1: CalibSet 부재 → 처리 거부+오류. EC-2: 불일치 → 거부+필드 명시. EC-3: 잘못된 시그니처 → FAIL. EC-4: 자동 검출 한정 — 시그니처·부가 반환값(계약)·직접 import(정적) FAIL; 전역 상태·파일 우회는 범위 밖(코드 리뷰). EC-5: 의존 위반 → 열거·FAIL·머지 차단.
- DoD: XDET-TC-000 PASS(계약 위반 0건).

## Files (T0 산출 대상)
- `common/{pyramid,histogram,fft_psd,robust_stats,mask_ops}/` — 5종 스텁
- `modules/` — 처리 모듈 트리(스캐폴드만, 레퍼런스 모듈 미포함)
- `pipeline/` — 오케스트레이터(파이프라인 정의 + CalibSet 진입 검증 게이트)
- `metrics/` — 지표 엔진 자리(T1)
- `tests/` — 레퍼런스 passthrough 모듈 + fixture, XDET-TC-000 실동작·XDET-TC-001~021 skeleton
- `data/` + `.gitattributes` — LFS 트래킹 구조(실 데이터 미포함)
- XFrame / CalibSet 자료구조 + 스키마 검증기 + npz/JSON sidecar 직렬화
- 단일 시그니처 계약(추상 프로토콜) + harness + import-linter 계약 파일
- pytest 진입점(Makefile/scripts) + float32/float64(검증모드) + diff 유틸 훅

## Exclusions
- 처리 알고리즘(T2+)·지표 엔진(T1)·실 CalibSet/골든 데이터·XDET-TC-021 수치 임계(P2)·성능 게이트(P2)·공용 컴포넌트 실 알고리즘(첫 소비 WP)·DL/ADR/observer study(Gen 2)·modules/ 내 레퍼런스 모듈(tests/ 전용)·전역 상태/파일 우회 일반 자동 검출(코드 리뷰 게이트).
