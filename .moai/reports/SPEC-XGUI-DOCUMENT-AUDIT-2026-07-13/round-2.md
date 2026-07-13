# SPEC-XGUI v0.5 문서 교차검증 — Round 2

Date: 2026-07-13
Scope: MASTER, XSEAM, 8개 그룹, GUI 기준, 중앙 TestSpec, 현행 Python/WPF source
Implementation changes: 0

## 1. 1차 개정에서 닫은 구조 결함

1. 사용자 승인·기준선 동결·구현 착수 차단을 `baseline-control.md` G0로 신설했다.
2. EARS 요구사항→acceptance→TC→증거를 `traceability-matrix.md`로 중앙화했다.
3. GUI 성능 임시 임계를 제거하고 측정 환경·반복·p95/최대·메모리·취소 기준을 고정했다.
4. source 공개 예외형 17개를 typed `EngineError` code에 매핑했다.
5. Calibration 102~103, Denoise 124~127, NDT 150~151의 개별 시나리오를 추가했다.
6. `audit-r1.md`와 v0.4 감사를 SPEC 디렉터리에서 본 reports 디렉터리로 분리했다.

## 2. Round 2에서 새로 발견하고 수정한 결함

| 결함 | 영향 | 수정 |
|---|---|---|
| 8개 그룹 acceptance 추적표에 literal `\\n` 삽입 | Markdown 표 파손, 사람/도구 추적 불가 | 실제 줄바꿈 표로 전수 교체 |
| Lag acceptance의 strict 사용자 입력 evidence 누락 | 등록 데이터 부재 시 실제 사용 계약 약화 | XDET-TC-111 시나리오 추가 |
| Line/Sat/Geo acceptance의 사용자 evidence 누락 | 실측 입력 실행과 정본 승격 경계 불명확 | XDET-TC-119 시나리오 추가 |
| Enhancement acceptance의 사용자 evidence 누락 | display artifact와 evidence 연결 약화 | XDET-TC-135 시나리오 추가 |
| MASTER에 Qt 제품화 금지 명시 부족 | 과거 Python GUI 문서와 충돌 가능 | Exclusions에 Qt/PySide/napari 금지 추가 |
| foundation의 `MASK_DTYPE` 단일 권위 문장 부족 | mask dtype 회귀 가능 | `numpy.uint8`와 bit flag를 명시 |
| Markdown pseudo-link 3건 | 링크 감사 실패 | 등급/범위 표기를 일반 텍스트로 교정 |

## 3. 재계산 결과

| 검사 | 결과 |
|---|---:|
| 필수 문서 세트 | 10세트 × 4파일, 누락 0 |
| EARS 요구사항→acceptance | 287/287 |
| 그룹 GUI TC | 8그룹 × 8 = 64/64 |
| 중앙 GUI TC | XDET-TC-096~167 = 72/72 |
| catalog qualified EntryPoint | 67/67 source symbol 존재 |
| 실행 family | 9/9 |
| source 공개 예외형→typed error | 17/17 |
| Params authority key | 106/106 문서 존재 |
| Calib payload key | 16/16 문서 존재 |
| 상대 링크 | 89/89 존재 |
| SPEC 내부 audit 파일 | 0 |
| 비문서 worktree 변경 | 0 |
| `git diff --check` | PASS |

## 4. 정량 기준 확인

- W/L 100회: p95 100 ms 이하, 최대 200 ms 이하.
- cold start: 새 프로세스 5회 각각 10 s 이하.
- peak RSS: 2 GiB 이하; full-frame LRU 8, thumbnail LRU 256.
- 50-frame 두 번째 순회 후 RSS 증가: 64 MiB 이하.
- heartbeat 최대 공백: 200 ms 이하; Canceled 표시: 250 ms 이하; late result commit: 0.
- normalized artifact 재열기 절대오차: 0.5/65535 이하.
- 반복 실행: result/hash bit-identical; 20회 RSS 기울기 1 MiB/run 이하.

알고리즘 Params의 `[T]`는 임시 GUI 임계가 아니라 외부화된 튜닝 provenance 등급이므로 유지한다. 값 권위는 Params/config이며 UI 하드코딩은 금지한다.

## 5. 현재 판정

구조·추적·계약의 Round 2 결함은 수정됐다. 최종 상태 전환 전에는 3차 독립 정적 감사가 필요하다. 사용자 승인과 구현 착수 허가는 별도 G0 조건이므로 현재도 `pending_user/false`를 유지한다.
