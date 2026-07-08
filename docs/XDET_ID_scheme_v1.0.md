# XDET ID 체계 정의서 (v1.0)

기존 XDET-* 문서 체계 및 ME 접두어 원칙(MERS 등과 충돌 회피)과 정합.

## ID 형식

| 유형 | 형식 | 예 | 부여 문서 |
|---|---|---|---|
| Market Requirement | XDET-MR-### | XDET-MR-001 | MRD |
| Product Requirement | XDET-PR-{CORE\|MED\|NDT}-### | XDET-PR-MED-003 | PRD |
| 평가 지표 | XDET-EV-### | XDET-EV-101 | EVAL |
| V&V 항목 | XDET-VV-### | (예약) | V&V Plan |
| Test Case | XDET-TC-### | (예약) | Test Spec |

## EV 번호 대역

- 1xx: Common Core 물리 지표
- 2xx: Medical post 지표
- 3xx: NDT post 지표
- 4xx: 성능·운영(Tier) 지표

## 규칙

1. ID는 삭제 후 재사용 금지 (결번 유지).
2. PR의 acceptance criteria는 EV ID 참조형으로만 기술 ("XDET-EV-201 min 이상"). 지표 수치 개정 시 PR 문서 무수정.
3. 하위 문서(FR/SWR)는 기존 3-Trace 체계에 연결 — 본 문서는 MR/PR/EV/VV/TC 계층만 정의.
4. RTM은 MR→PR→EV→VV→TC 5열 추적을 기본으로 한다.
