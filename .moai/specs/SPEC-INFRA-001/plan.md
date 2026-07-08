---
id: SPEC-INFRA-001
title: T0 프레임워크 스캐폴드 (XFrame·CalibSet·오케스트레이터·harness·정적검사·CI)
version: 0.1.0
status: draft
created: 2026-07-08
updated: 2026-07-08
author: drake.lee
priority: high
issue_number: null
---

# SPEC-INFRA-001 구현 계획 (초안) — T0 프레임워크 스캐폴드

> 상태: **draft** (run 단계 착수 전까지 유지). EARS 확정본은 [spec.md](./spec.md), 인수 기준은 [acceptance.md](./acceptance.md), 근거 분석은 [research.md](./research.md) 참조.

## 0. 확정된 설계 결정 (사용자 승인 2026-07-08)

1. **레퍼런스 passthrough 모듈**: `tests/` fixture 전용 — `modules/` 트리에 포함하지 않는다.
2. **float64 병행 경로**: 검증 모드 한정. 기본은 float32 단일 경로.
3. **의존 방향 정적 검사**: `import-linter`(선언적 레이어링 규칙) — `module → common` 단방향, 모듈 간 import 금지.
4. **CalibSet 데이터 저장 포맷**: npz(배열) + JSON sidecar(메타) 기본값 — **[P]** 등급, T2에서 재검토 가능.
5. **CI 진입점**: 플랫폼 무관 pytest(Makefile/scripts). 실행 환경은 **TBD**(Gitea Actions 유력).

## 1. 개요

XDET P1의 최우선 작업 T0. 처리 알고리즘 없이 13개 파이프라인 모듈·지표 엔진이 준수할 **공통 계약과 검증 기계장치**를 확립한다. 근거: SWR-000-1~12. 완료 정의: **XDET-TC-000 통과**(모듈 fixture 입출력 일치 + 시그니처·의존 방향 정적 검사, 계약 위반 0건).

## 2. 기술 스택

| 항목 | 선택 | 근거 |
|---|---|---|
| 언어/런타임 | Python 3.11+ | tech.md |
| 수치 연산 | numpy, scipy (float32 기본 + float64 병행) | tech.md, SWR-000-1 |
| 시험 프레임워크 | pytest + CI | tech.md, SWR-000-11 |
| 데이터 관리 | raw 16-bit + JSON 메타, `data/` Git LFS. CalibSet 본체 npz + JSON sidecar [P] | tech.md, structure.md, 결정 4 |
| 정적 검사 | `import-linter` 선언적 레이어링(`module → common` 단방향) | SWR-000-8, TC-000, 결정 3 |
| CI 진입점 | 플랫폼 무관 pytest(Makefile/scripts), 실행 환경 TBD(Gitea Actions 유력) | 결정 5 |

원칙: **정확도 단일 목표, 속도 최적화 금지**. 파라미터는 Params/CalibSet 외부화, 하드코딩 금지.

## 3. 작업 분해 (요구 모듈 ≤5)

5개 요구 모듈로 분해. 각 모듈은 SWR-000 조항 집합에 대응하며 spec.md의 EARS 요구 그룹이 된다.

### M1 — 데이터 계약: XFrame + CalibSet (SWR-000-6, -10, -3, -4)
- `XFrame` 컨테이너: pixel(float32 기본 단일 경로) + 마스크 스택(defect/포화/보간 비트플래그) + 노이즈 모델(α,σ) + 처리 이력 체인. 불변 계약. float64 병행 산출은 **검증 모드 한정**(결정 2).
- `CalibSet` 공통 스키마 + 스키마 검증기: 패널 ID·해상도·유효기간·종류·데이터·생성 이력. 데이터 본체는 **npz + JSON sidecar** 직렬화([P], T2 재검토 — 결정 4).
- 처리 이력 해시 체인(모듈 버전·파라미터 해시·CalibSet ID) — IEC 62304 추적.
- 검증 모드 중간 산출 보존 옵션.

### M2 — 모듈 계약 + harness (SWR-000-7, -11)
- 단일 시그니처 계약 `process(XFrame, CalibSet, Params) -> XFrame` (추상 프로토콜/베이스).
- 레퍼런스 passthrough(항등) 모듈 + 합성 입력/기대 출력 fixture — **`tests/` 전용, `modules/` 미포함**(결정 1).
- 모듈 harness: fixture 로드 → `process()` 실행 → XFrame 단위 비교 → 불일치 리포트 (TC-000 판정 엔진 A).

### M3 — 오케스트레이터 + 순서 고정 (SWR-000-8, -2, -5)
- 파이프라인 정의 파일(오케스트레이터)이 순서·조합 단독 결정.
- 고정 순서 offset→gain→defect→lag→line noise→(포화/기하)→post를 passthrough 모듈로 골격 실증.
- 진입점 CalibSet 검증 게이트: 부재/불일치 시 처리 거부 + 명시 오류(무단 기본값 대체 금지).

### M4 — 의존 방향 정적 검사 + 공용 컴포넌트 스캐폴드 (SWR-000-8, -9)
- 정적 검사기: **`import-linter`** 선언적 레이어링 계약(`module → common` 단방향). module→module import, common→module 역방향, 모듈 간 수평 의존 검출 시 실패 (TC-000 판정 엔진 B — 결정 3).
- `common/` 5종(pyramid/histogram·FOV/fft_psd/robust_stats/mask_ops) 디렉터리 + 최소 인터페이스 스텁(중복 금지 계약).

### M5 — CI 골격 + 정밀도/동일성 훅 (SWR-000-1, -11, -12, TC-000, TC-021 훅)
- pytest 등록 구조: TC-000 실동작, TC-001~021 skeleton(skip/placeholder). 진입점은 **플랫폼 무관 Makefile/scripts**, 실행 환경 TBD(Gitea Actions 유력 — 결정 5).
- 커밋 트리거 → 모듈 단위 게이트(TC-000) → 계약 위반 시 머지 차단.
- float32 기본 단일 경로 + **float64 검증-모드 병행 경로**(결정 2) + 구현 교체 diff 유틸 훅(TC-021 계열 자리, 수치 임계 P2 이연).
- repo 스캐폴드(`common/ modules/ pipeline/ metrics/ tests/ data/`) + `.gitattributes`(LFS 트래킹).

## 4. EARS 구조 설계 (확정본은 spec.md)

확정 EARS 요구는 [spec.md](./spec.md)가 단일 출처이다. 아래는 5개 그룹 설계 요약(참조용). `[Ubiquitous]`/`[Event]`/`[State]`/`[Optional]`/`[Unwanted]`는 EARS 패턴 표기.

### REQ-INFRA-DATA (M1)
- `[Ubiquitous]` XFrame은 pixel buffer(기본 float32; 검증 모드 시 동일 인스턴스가 float64 병행 버퍼 보유 가능), 마스크 스택(defect/포화/보간 비트플래그), 노이즈 모델(α,σ), 처리 이력 체인을 담는 **유일한** 모듈 입출력 단위여야 한다. float64 병행 버퍼는 컨테이너 내부 필드로 CI-3b 전용 채널이다.
- `[Unwanted]` 모듈은 XFrame 컨테이너 외의 채널로 데이터를 전달해서는 안 된다(사이드채널 금지, 설계 규칙). 자동 검출 범위는 시그니처·반환값 형태(계약)+의존 방향(정적)이며, 전역 상태·파일 우회는 코드 리뷰 게이트.
- `[Ubiquitous]` CalibSet은 단일 공통 스키마(패널 ID·해상도·유효기간·종류·데이터·생성 이력)를 따라야 한다.
- `[Event]` 모듈이 출력 XFrame을 생성할 때, 시스템은 처리 메타(모듈 버전·파라미터 해시·CalibSet ID)를 이력 체인에 추가해야 한다.
- `[State]` 검증 모드가 활성인 동안, 시스템은 단계별 중간 XFrame 산출을 보존해야 한다.
- `[Ubiquitous]` 모듈은 입력 XFrame을 불변으로 취급해야 한다.

### REQ-INFRA-CONTRACT (M2)
- `[Ubiquitous]` 모든 처리 모듈은 단일 시그니처 `process(XFrame, CalibSet, Params) -> XFrame`을 노출하고 순수함수형이어야 한다.
- `[Optional]` 내부 상태를 선언하는 모듈(예: lag)에서는, 그 상태가 XFrame 컨테이너로 직렬화 가능해야 한다.
- `[Ubiquitous]` 각 모듈은 동봉된 합성 입력 + 기대 출력 fixture로 harness를 통해 단독 시험 가능해야 한다.
- `[Event]` harness가 모듈 fixture를 실행할 때, 시스템은 실제 대 기대 XFrame 출력을 비교하고 불일치를 리포트해야 한다.

### REQ-INFRA-ORCH (M3)
- `[Ubiquitous]` 오케스트레이터(파이프라인 정의)만이 모듈 실행 순서·조합을 결정해야 한다.
- `[Unwanted]` 처리 모듈은 다른 처리 모듈을 직접 호출해서는 안 된다.
- `[Ubiquitous]` 오케스트레이터는 고정 순서 offset→gain→defect→lag→line noise→(포화/기하)→post를 강제해야 한다.
- `[Unwanted]` 캘리브레이션 파일이 부재하거나 불일치(해상도/패널 ID)하면, 시스템은 처리를 거부하고 명시 오류를 발생시켜야 한다(무단 기본값 대체 금지).

### REQ-INFRA-STATIC (M4)
- `[Ubiquitous]` 의존 방향은 module → common 단방향이어야 한다(역방향·수평 금지).
- `[Event]` 정적 검사기가 실행될 때, 시스템은 모듈→모듈 직접 호출 및 역방향·수평 의존을 검출하고 실패시켜야 한다.
- `[Ubiquitous]` 공용 컴포넌트 5종(pyramid/histogram·FOV/fft_psd/robust_stats/mask_ops)은 각각 common/에 1회만 구현되고 참조로만 사용되어야 한다(중복 금지).

### REQ-INFRA-CI (M5)
- `[Ubiquitous]` 모든 시험 케이스(TC-000~021)는 pytest 케이스로 등록되어 CI에서 실행되어야 한다(T0는 TC-000 실동작 + 나머지 skeleton).
- `[Event]` 코드가 커밋될 때, CI는 모듈 단위 게이트(TC-000)를 실행하고 계약 위반 시 머지를 차단해야 한다.
- `[Ubiquitous]` (CI-3a) 골든 모델은 기본 float32 단일 경로로 연산해야 한다. `[Optional]` (CI-3b) 검증 모드 시 float64 병행 산출 경로를 제공하며, 산출물은 DATA-1의 검증-모드 XFrame 내부 float64 버퍼로만 전달한다(DATA-2 사이드채널 아님).
- `[Ubiquitous]` 프레임워크는 구현 교체 계약을 위한 등가성 diff 유틸 훅을 제공하여, 동일 시그니처를 공유하는 골든/최적화/FPGA 구현이 TC-021 계열로 비교될 수 있어야 한다(수치 임계는 P2 이연).

### Exclusions (What NOT to Build) — spec.md 필수 포함
- 처리 알고리즘 구현(offset/gain/defect/lag/... = T2 이후). T0는 레퍼런스 passthrough만.
- 지표 산출 엔진(MTF/NPS/NNPS/DQE 등 = T1).
- 실 캘리브레이션 데이터 내용·골든 데이터셋 채우기(스키마·LFS 구조만).
- TC-021 수치 동일성 임계(±1 LSB / bit-동일) — P2, T0는 훅만.
- 성능·처리시간 게이트(EV-401 = P2).
- 공용 컴포넌트 5종의 실제 알고리즘(첫 소비 WP로 이연).
- DL/ADR(Gen 2), observer study(P1 범위 밖).

## 5. 리스크 분석 (요약 — 상세 research.md §5)

| 리스크 | 완화 | 우선순위 |
|---|---|---|
| TC-000 순환 의존(검증 대상 부재) | 레퍼런스 passthrough 모듈 + fixture로 framework self-test 성립 | High |
| ±1 LSB/bit-동일 조기 확정 압박 | diff 훅·float64 병행 경로만, 수치 임계 P2 이연 | High |
| 사이드채널 누출 | 자동 검출(계약: 시그니처·반환값 / 정적: 의존 방향) + 코드 리뷰 게이트(전역 상태·파일 우회) | High |
| 공용 컴포넌트 조기 과설계 | 스텁만, 시그니처 확정은 첫 소비 WP | Medium |
| 정적 검사 우회(동적 import) | AST 분석 + 런타임 어서션 이중화 | Medium |
| 파라미터 하드코딩 유입 | Params/CalibSet 주입 필수화, [P] 주석 규약 | Medium |
| Git LFS 미설정 | `.gitattributes` 트래킹·구조만(실 데이터 미포함) | Low |

## 6. 마일스톤 (우선순위 기반, 시간 추정 없음)

- **Priority High**: M1(데이터 계약) → M2(모듈 계약·harness) → M3(오케스트레이터). 이 3개가 TC-000 판정 엔진 A(fixture 비교)의 전제.
- **Priority High**: M4(정적 검사) — TC-000 판정 엔진 B(의존 방향). M2/M3와 병행 가능.
- **Priority Medium**: M5(CI 골격·정밀도/동일성 훅) — M1~M4 완료 후 통합, TC-000 CI 실동작으로 DoD 판정.
- 순서 원칙: 데이터 계약(M1) 확정 후 나머지 착수. common/ 스텁(M4 일부)은 조기 배치 가능.

## 7. 검증 전략 — TC-000 fixtures

- **fixture 구성**: 레퍼런스 passthrough 모듈에 대한 합성 입력 XFrame + 기대 출력 XFrame(항등이므로 입력과 동일해야 함) 쌍.
- **판정 A (harness)**: `process()` 출력이 기대 XFrame과 일치(pixel·마스크·노이즈모델·이력 체인).
- **판정 B (정적검사)**: 스캐폴드 내 모듈→모듈 직접 호출·역방향/수평 의존 = 0건.
- **판정 C (계약)**: 시그니처·반환값 형태 위반 = 0건 (전역 상태·파일 우회는 자동 판정 범위 밖 — 코드 리뷰 게이트).
- **DoD**: 세 판정 모두 CI에서 자동 통과, 계약 위반 0건 → XDET-TC-000 PASS.
- acceptance.md에 Given-When-Then 시나리오(S1~S4)·엣지 케이스(CalibSet 부재/불일치, 잘못된 시그니처, 부가 반환값/직접 import 위반 fixture, 의존 위반)·품질 게이트를 상세화.
