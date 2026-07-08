---
id: SPEC-INFRA-001
version: 0.1.1
status: draft
created: 2026-07-08
updated: 2026-07-08
author: drake.lee
priority: high
issue_number: 1
---

# SPEC-INFRA-001 — T0 프레임워크 스캐폴드

XDET 영상처리 SW P1의 최우선 작업 T0. 처리 알고리즘을 하나도 구현하지 않으면서, 13개 파이프라인 모듈과 지표 엔진이 준수해야 할 **공통 계약과 검증 기계장치(machinery)**를 확립한다.

- 근거: SWR-000-1~12 (XDET_SWR_spec_v1.2.md §0-A/0-B)
- 완료 정의(DoD): **XDET-TC-000 통과** — 모듈 fixture 입출력 일치 + 시그니처·의존 방향 정적 검사, 계약 위반 0건
- 근거 분석: [research.md](./research.md) · 구현 계획: [plan.md](./plan.md)

## HISTORY

- **v0.1.1 (2026-07-08)** — plan-audit iteration 1 (FAIL 0.74) 결함 6건 반영:
  - D4: DATA-1에 검증-모드 float64 병행 버퍼 명시, DATA-2·CI-3b와 상호 참조로 float64 채널 정책 폐합.
  - D2: DATA-2를 설계 규칙 + 자동 검출 가능 범위(계약/정적 검사)로 한정, acceptance.md EC-4 축소.
  - D1: CI-3을 CI-3a(Ubiquitous)/CI-3b(Optional)로 분리.
  - D3: CONTRACT-2에 구조적 확인 범위 + T4 런타임 검증 이연 명시, acceptance.md에 대응 구조 AC(S4) 추가.
  - D5: TC 표기를 XDET-TC-NNN으로 통일.
  - D6: DATA-3에서 직렬화 포맷(HOW) 제거, Environment/plan.md 참조로 이관.
- **v0.1.0 (2026-07-08)** — 초안 생성. 5개 요구 그룹(DATA/CONTRACT/ORCH/STATIC/CI) EARS 구조 확정. 사용자 승인 5개 결정 반영:
  1. 레퍼런스 passthrough 모듈은 `tests/` fixture 전용(모듈 트리 미포함)
  2. float64 병행 경로는 검증 모드 한정(기본은 float32 단일 경로)
  3. 의존 방향 정적 검사는 `import-linter`(선언적 레이어링 규칙) 채택
  4. CalibSet 저장 포맷은 npz + JSON sidecar 메타 기본값 — [P] 등급, T2에서 재검토 가능
  5. CI 진입점은 플랫폼 무관 pytest(Makefile/scripts), Gitea Actions를 유력 대상으로 TBD 표기
  - status: draft (run 단계 착수 전까지 유지)

## Environment / Assumptions

- Python 3.11+, numpy/scipy 기반 float 골든 모델 (tech.md). 속도 최적화 금지 — 정확도 단일 목표.
- 대상 프레임: 3072×3072 / 3072×2560, 16-bit unsigned raw, pitch 140µm.
- 정적 검사 도구: `import-linter` — 선언적 레이어 규칙으로 `module → common` 단방향, 모듈 간 import 금지를 강제.
- T0 시점에는 처리 모듈이 존재하지 않으므로, XDET-TC-000 판정은 `tests/` 동봉 **레퍼런스 passthrough(항등) 모듈**을 대상으로 성립시킨다(framework self-test).
- CalibSet 데이터 본체 저장 포맷은 npz(배열) + JSON sidecar(메타) 기본 — **[P]**, T2에서 재검토 가능.
- CI 실행 환경은 미확정(**TBD** — Gitea Actions 유력). T0는 플랫폼 무관 pytest 진입점(Makefile/scripts)만 제공.

## Requirements (EARS)

### REQ-INFRA-DATA — 데이터 계약: XFrame + CalibSet (SWR-000-6, -10, -3, -4)

- **REQ-INFRA-DATA-1 (Ubiquitous)** — XFrame은 pixel buffer(기본 float32; WHERE 검증 모드가 활성인 경우 동일 XFrame 인스턴스가 float64 병행 버퍼를 추가로 보유할 수 있음), 마스크 스택(defect/포화/보간 비트플래그), 노이즈 모델(α, σ), 처리 이력 체인을 담는 **유일한** 모듈 입출력 단위여야 한다. float64 병행 버퍼는 XFrame 내부 필드이므로 REQ-INFRA-DATA-2의 사이드채널에 해당하지 않으며, REQ-INFRA-CI-3b가 이 버퍼를 유일한 float64 전달 채널로 사용한다.
- **REQ-INFRA-DATA-2 (Unwanted)** — IF 모듈이 XFrame 컨테이너 외의 채널(전역 상태 · 부가 반환값 · 파일 우회 등)로 데이터를 전달하려 하면, THEN 시스템은 이를 계약 위반으로 취급해야 한다(사이드채널 금지). 이 금지 중 자동 검출 가능한 범위는 시그니처·부가 반환값 형태 위반(계약 검사)과 의존 방향 위반(import-linter 정적 검사)이며(acceptance.md EC-4의 검증 범위와 동일), 전역 상태·파일 우회는 테스트 가능 AC가 아닌 설계 규칙으로서 코드 리뷰 게이트로 다룬다(REQ-INFRA-CI 참조). XFrame 내부 필드(예: 검증-모드 float64 병행 버퍼)를 통한 전달은 컨테이너 내 전달이므로 위반이 아니다.
- **REQ-INFRA-DATA-3 (Ubiquitous)** — CalibSet은 단일 공통 스키마(패널 ID · 해상도 · 유효기간 · 종류 · 데이터 · 생성 이력)를 따르고 단일 직렬화 규약으로 저장되어야 한다(구체 저장 포맷은 Environment/Assumptions 및 plan.md 참조 — [P], T2 재검토 가능).
- **REQ-INFRA-DATA-4 (Event-Driven)** — WHEN 모듈이 출력 XFrame을 생성하면, THEN 시스템은 처리 메타(모듈 버전 · 파라미터 해시 · CalibSet ID)를 이력 체인에 결정론적으로 추가해야 한다(IEC 62304 추적).
- **REQ-INFRA-DATA-5 (State-Driven)** — WHILE 검증 모드가 활성인 동안, 시스템은 단계별 중간 XFrame 산출을 보존해야 한다.
- **REQ-INFRA-DATA-6 (Ubiquitous)** — 모듈은 입력 XFrame을 불변(immutable)으로 취급해야 한다(입력 원본 변경 금지).

### REQ-INFRA-CONTRACT — 모듈 계약 + harness (SWR-000-7, -11)

- **REQ-INFRA-CONTRACT-1 (Ubiquitous)** — 모든 처리 모듈은 단일 시그니처 `process(XFrame, CalibSet, Params) -> XFrame`을 노출하고 순수함수형이어야 한다.
- **REQ-INFRA-CONTRACT-2 (Optional)** — WHERE 모듈이 내부 상태를 선언하는 경우(예: lag), 그 상태는 XFrame 컨테이너로 직렬화 가능해야 한다. T0는 프로토콜에 상태 직렬화 인터페이스가 존재함을 구조적으로 확인하는 데 그치며, 상태 보유 모듈을 통한 런타임 검증은 T4(lag)로 이연한다.
- **REQ-INFRA-CONTRACT-3 (Ubiquitous)** — 각 모듈은 합성 입력 + 기대 출력 fixture로 harness를 통해 단독 시험 가능해야 한다. T0의 계약 검증 대상 레퍼런스 passthrough 모듈은 `tests/` fixture 전용으로 두며, `modules/` 트리에 포함하지 않는다.
- **REQ-INFRA-CONTRACT-4 (Event-Driven)** — WHEN harness가 모듈 fixture를 실행하면, THEN 시스템은 실제 대 기대 XFrame 출력을 비교(pixel · 마스크 · 노이즈 모델 · 이력 체인)하고 불일치를 리포트해야 한다.

### REQ-INFRA-ORCH — 오케스트레이터 + 순서 고정 (SWR-000-8, -2, -5)

- **REQ-INFRA-ORCH-1 (Ubiquitous)** — 오케스트레이터(파이프라인 정의 파일)만이 모듈 실행 순서 · 조합을 결정해야 한다.
- **REQ-INFRA-ORCH-2 (Unwanted)** — IF 처리 모듈이 다른 처리 모듈을 직접 호출하면, THEN 시스템은 이를 계약 위반으로 검출하여 실패시켜야 한다.
- **REQ-INFRA-ORCH-3 (Ubiquitous)** — 오케스트레이터는 고정 순서 offset → gain → defect → lag → line noise → (포화/기하) → post 를 강제해야 한다.
- **REQ-INFRA-ORCH-4 (Unwanted)** — IF 캘리브레이션 파일이 부재하거나 불일치(해상도 · 패널 ID)하면, THEN 시스템은 처리를 거부하고 명시 오류를 발생시켜야 한다(무단 기본값 대체 금지).

### REQ-INFRA-STATIC — 의존 방향 정적 검사 + 공용 컴포넌트 스캐폴드 (SWR-000-8, -9)

- **REQ-INFRA-STATIC-1 (Ubiquitous)** — 의존 방향은 `module → common` 단방향이어야 한다(역방향 · 수평 금지). 이 규칙은 `import-linter` 선언적 레이어링 계약으로 명시해야 한다.
- **REQ-INFRA-STATIC-2 (Event-Driven)** — WHEN 정적 검사기가 실행되면, THEN 시스템은 모듈→모듈 직접 import, common→module 역방향, 모듈 간 수평 의존을 검출하고 실패시켜야 한다.
- **REQ-INFRA-STATIC-3 (Ubiquitous)** — 공용 컴포넌트 5종(pyramid / histogram·FOV / fft_psd / robust_stats / mask_ops)은 각각 `common/`에 1회만 배치되고 참조로만 사용되어야 한다(중복 금지). T0는 디렉터리 + 최소 인터페이스 스텁만 제공한다.

### REQ-INFRA-CI — CI 골격 + 정밀도/동일성 훅 (SWR-000-1, -11, -12, XDET-TC-000, XDET-TC-021 훅)

- **REQ-INFRA-CI-1 (Ubiquitous)** — 모든 시험 케이스(XDET-TC-000~021)는 pytest 케이스로 등록되어야 한다. T0는 XDET-TC-000을 실동작시키고, 나머지는 skeleton(skip/placeholder)로 등록한다.
- **REQ-INFRA-CI-2 (Event-Driven)** — WHEN 코드가 커밋되면, THEN CI는 모듈 단위 게이트(XDET-TC-000)를 실행하고 계약 위반 시 머지를 차단해야 한다. CI 진입점은 플랫폼 무관 pytest(Makefile/scripts)로 제공하며, 실행 환경은 TBD(Gitea Actions 유력)이다.
- **REQ-INFRA-CI-3a (Ubiquitous)** — 골든 모델은 기본적으로 float32 단일 경로로 연산해야 한다(SWR-000-1).
- **REQ-INFRA-CI-3b (Optional)** — WHERE 검증 모드가 활성인 경우, 골든 모델은 수치 안정성 대조를 위한 float64 병행 산출 경로를 제공해야 한다. 이때 float64 산출물은 REQ-INFRA-DATA-1의 검증-모드 XFrame 내부 float64 병행 버퍼로만 전달되며, 이는 REQ-INFRA-DATA-2의 사이드채널에 해당하지 않는다(SWR-000-1).
- **REQ-INFRA-CI-4 (Ubiquitous)** — 프레임워크는 구현 교체 계약을 위한 등가성 diff 유틸 훅을 제공하여, 동일 시그니처를 공유하는 골든/최적화/FPGA 구현이 XDET-TC-021 계열로 비교될 수 있어야 한다. 수치 임계(±1 LSB / bit-동일)는 P2로 이연하며 T0는 훅 구조만 제공한다.

## Exclusions (What NOT to Build)

- **처리 알고리즘 구현 없음** — offset/gain/defect/lag/line noise/... 는 T2 이후. T0는 `tests/` 동봉 레퍼런스 passthrough(항등) 모듈만 사용한다.
- **지표 산출 엔진 없음** — MTF/NPS/NNPS/DQE/lag/bad pixel/SNRn/duplex wire 는 T1(metrics/).
- **실 캘리브레이션 데이터·골든 데이터셋 채우기 없음** — CalibSet 스키마 + 검증기 + npz/JSON sidecar 포맷 규약과 `data/` LFS 구조만 확립(실 데이터 미포함).
- **XDET-TC-021 수치 동일성 임계 없음** — ±1 LSB / bit-동일 수치 게이트는 P2. T0는 diff 유틸 훅과 float32/float64(검증 모드) 경로만 배치.
- **성능·처리시간 게이트 없음** — EV-401(Tier 처리시간)은 P2.
- **공용 컴포넌트 실 알고리즘 없음** — pyramid/histogram/fft_psd/robust_stats/mask_ops 의 실 구현은 첫 소비 WP(T1·T5·T6·T7 등)로 이연. T0는 스텁만.
- **Gen 2 항목 없음** — DL 기반 처리, ADR, observer study 는 P1 범위 밖.
- **모듈 트리 내 레퍼런스 모듈 없음** — passthrough 모듈은 `tests/` fixture 전용, `modules/`에 배치하지 않는다(사용자 결정 1).
