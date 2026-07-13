# SPEC Review Report: SPEC-XGUI-GRID (그룹 6 Grid/VGrid 검증 탭)
Iteration: 1/5
Verdict: **PASS** (must-pass firewall 전부 통과; 잔여는 minor 권고 3건)
Overall: 골든 대조 무결점, EARS 준수, 제약 위반 없음

M1 고지: 저작자 추론 컨텍스트는 무시함(Context Isolation). spec.md + 동결 골든 소스만으로 감사함.

## Must-Pass 결과

- **[PASS] MP-1 REQ 넘버링** — 명명 그룹 스킴(형제 SPEC-XSEAM-002 미러): INPUT-1/2/3, BUILD-1/2, APPLY-1/2/3, VIEW-1/2/3, EXPORT-1/2, GUARD-1/2/3/4. 그룹 내 순차, 갭·중복 없음(spec.md:83-114).
- **[PASS] MP-2 EARS 준수** — 16개 REQ 전부 유효 패턴: Ubiquitous(INPUT-1/BUILD-1/GUARD-2/3/4), Event-Driven(WHEN/THEN: INPUT-2/3, APPLY-1/2/3, VIEW-1/2/3, EXPORT-1), Unwanted(IF/THEN: BUILD-2, EXPORT-2, GUARD-1). 비정형·혼합 없음.
- **[PASS] MP-3 YAML frontmatter** — id/version/status/created/updated/author/priority/issue_number/labels 전부 존재·타입 정합(spec.md:2-11). `created`(≠`created_at`)는 형제 SPEC-XSEAM-002(spec.md:5) 규약을 정확히 미러 → 프로젝트 규약상 정상, 결함 아님.
- **[N/A] MP-4 언어 중립성** — 단일 언어(Python 골든) 프로젝트 SPEC. 16개 언어 다국어 툴링 대상 아님 → 자동 통과.

## 골든 대조 검증 (§9 근거표 file:line 전수 재확인)

| SPEC 주장 | 골든 실측 | 판정 |
|---|---|---|
| grid REQUIRED 정확히 8키 (grid.py:83-92) | 8키 튜플 확인, bg_window/meta_* 제외 | ✅ 정확 |
| grid 선택키 3종(meta_mounted/meta_nominal/bg_window) | grid.py:72-76, REQUIRED 부재 | ✅ 정확 |
| grid_bg_window_bins 기본 11 | grid.py:255 `params.get(...,11)` | ✅ 정확(비지어냄) |
| virtual_grid REQUIRED 정확히 5키 (vg.py:82-88) | 5키 튜플 확인 | ✅ 정확 |
| grid=CalibKind.OTHER(_KIND_BY_STAGE 부재) | orch.py:148-162 grid 부재, :165 accessor→OTHER | ✅ 정확 |
| virtual_grid=SCATTER (orch.py:158-161) | orch.py:161 `"virtual_grid":"scatter"` | ✅ 정확 |
| 빈 payload SCATTER 함정(진입 통과·_resolve_kernel 하드실패) | synth_calibset.py:48 `data={}`; vg.py:121-126 VirtualGridError | ✅ 정확(미묘·핵심 함정 검증됨) |
| dual-Gaussian amp[2]/sigma[2]/SPR<1 | vg.py:129-150 | ✅ 정확 |
| build_scatter_kernel→CalibKind.SCATTER (sk.py:144) | sk.py:128 kind=SCATTER, :144 def | ✅ 정확 |
| grid analyze:243 / notch_gain_1d:327 / process:409 | 실측 일치 | ✅ 정확 |
| grid 미검출 수치 동일 통과 :434-446 | 실측 일치 | ✅ 정확 |
| grid 이력필드(peak_freq/significance/notch_bw/dir_ratio/n_peaks/moire_cap) | grid.py:426-479 전부 존재 | ✅ 정확 |
| vg estimate_scatter:202 / process:302 / 진단 :345-351 / 특허 :352-356 | 실측 일치 | ✅ 정확 |
| vg 비음수 클램프 :283-287 / tanh 저신호 :229-240 | vg.py:285-287 / :239 | ✅ 정확 |
| CANONICAL_ORDER 부분수열 grid→vg→denoise→mse | orch.py:31-67 순서 확인 | ✅ 정확 |
| guard_output_path data/ 거부 (io_panel.py:27) | io_panel.py:27-44 DataWriteRejectedError | ✅ 정확 |
| XFrame validation_mode→intermediates 단일패스 | xframe.py:161/163/219 | ✅ 정확 |
| f_N=1/(2·pitch), 밀도 30~85 lines/cm | grid.py:5-7 | ✅ 정확 |

지어낸 Params·CalibSet 키 없음. 틀린 수식 없음. 그룹 고유 뷰어 특성(grid=주파수도메인 PSD+1D notch |H(f)|; vg=공간 산란맵 S_hat+⚠P 배너) 골든 소스와 정합. 제약(FROZEN/C-09/C-11/C-20/QUARANTINE/SWR-000-2/-5/저장·열기 포맷/시임 CONTRACT-6) 위반 없음.

## Defects Found (전부 minor, run 비차단)

D1. spec.md:45,137 — 섹션 넘버링 불일치: `## 3. 정확한 Params 키 목록`·`## 9. 골든 대조 근거표`만 번호가 있고 HISTORY/Environment/Requirements/Exclusions/결정사항은 무번호. 잔여 번호(3/9)가 형제 SPEC 편집 흔적으로 보임. — Severity: minor
D2. spec.md:25,26,132 — dangling 참조: `acceptance.md`·`plan.md`를 DoD(1) 인수 기준 출처로 지목하나 디렉터리에 미존재(현재 spec.md 단독). plan 단계상 정상이나, 인수 기준을 acceptance.md에 위임한 만큼 다음 라운드 전 생성 필요. — Severity: minor
D3. spec.md:134 (결정사항 3) — grid+virtual_grid 동시 조합을 "취득 컨텍스트상 상호 배타 → 비권장"으로 특징화하나, 골든 오케스트레이터(orchestrator.py:49-56)는 grid→virtual_grid 순서를 "저비율 물리그리드의 잔여 산란(residual scatter of a low-ratio physical grid)"을 커버하는 **정당한 결합 시나리오**로 명시 문서화함. SPEC이 골든의 결합-사용 근거를 인용하지 않아 배타성을 과대표현. 상호배타(vg.py:7-9)와 결합타당(orch.py:49-56)은 양립하므로, 결정사항에 골든의 결합근거를 병기 권고. — Severity: minor

## Chain-of-Verification Pass
2차 재독으로 확인: (a) §9 근거표 20개 file:line 전수 대조(스킴 아닌 실독) — 전부 정확, 갭 없음. (b) REQ 서브넘버링 그룹별 끝까지 재점검(INPUT~GUARD 16건) — 갭·중복 없음. (c) 각 REQ EARS 키워드 개별 확인 — 위반 없음. (d) Exclusions 8항 구체성 확인 — 골든변경/명목주파수/커널합성/포화복원/특허게이팅/정본검증/CalibKind신설/C++ 각 항 구체적. (e) 그룹내 모순 스캔: grid=OTHER↔vg=SCATTER 뷰어·CalibKind·저장도메인(둘다 raw-DN) 일관. 신규 결함: D3(배타성 과대표현) 1차에서 포착·기록함. 지어낸 키/수식 재탐색 — 없음.

## Regression Check
해당 없음(라운드 1).

## 권고 (Recommendation)
must-pass 4/4 및 실질 감사축(무지어냄·정확수식·뷰어특성·EARS·제약·검증가능성·그룹정합) 전부 통과. run 착수 가능. 마감 전 polish:
1. D1: `## 3.`/`## 9.` 번호 제거하여 무번호 헤딩으로 통일(또는 전 섹션 일관 번호 부여).
2. D2: acceptance.md/plan.md 생성 또는 DoD(1)의 acceptance.md 위임을 spec 내 인수문구로 대체.
3. D3: 결정사항 3에 orchestrator.py:49-56(저비율 그리드 잔여산란) 결합근거 병기 — 배타는 "통상 취득"이고 결합은 "저비율 물리그리드"임을 구분.
