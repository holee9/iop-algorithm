# SPEC 감사 리포트: SPEC-XGUI-NDT (그룹 7 NDT 검증 탭)

라운드: 1/5
판정: **PASS (NO PRIORITY DEFECTS)**
감사자: plan-auditor (적대적 교차검증)

> M1 컨텍스트 격리: 저자 추론 컨텍스트는 무시했다. `spec.md` + 동결 골든 소스만으로 판정한다.

## 대조검증 범위 (골든 = 권위)

`metrics/ndt.py`(638줄), `common/robust_stats.py`, `common/io.py`, `metrics/result.py`, `scripts/ingest_edrogi.py`, `apps/gui/io_panel.py`, `SPEC-XGUI-MASTER/foundation.md`, `SPEC-XSEAM-002/spec.md`를 Read로 직접 대조.

## Must-Pass 결과

- **[PASS] MP-1 REQ 번호 일관성** — 명명 그룹 스킴(형제 SPEC-XSEAM-002 미러 요구). INPUT-1~5 / ACCUM-1~4 / IQI-1~4 / THICK-1~3 / EXPORT-1~2 / GUARD-1~4 = 22개, 그룹 내 순차·무결번·무중복. HISTORY "22개" 주장과 일치(5+4+4+3+2+4=22).
- **[PASS] MP-2 EARS 준수** — 22개 전부 EARS 라벨+패턴 준수(Ubiquitous/Event-Driven/Unwanted/State-Driven). 경미: THICK-2(spec.md:92) State-Driven이 `WHILE ... THEN`로 THEN 혼용(정준 State-Driven은 THEN 없음). 비차단.
- **[PASS] MP-3 Frontmatter 유효성** — id/version/status/created/updated/author/issue_number/priority/labels 전원 존재·타입 정상. `created_at` 대신 `created`/`updated` 사용은 형제 SPEC-XSEAM-002(spec.md:5-6) 미러 요구를 정확히 준수한 것(프로젝트 권위 우선).
- **[N/A] MP-4 언어 중립성** — 단일 언어(Python 골든) 프로젝트. 다국어 LSP 툴링 아님 → 자동 통과.

## 골든 대조: 지어낸/틀린 키·수식·시그니처 = 0건

**§3 Params 키 12종 + beam_quality — 12/12 정확** (하드코딩 리터럴 없음, 전부 `require_param`/`params.get` 경유):

| SPEC 주장 | 골든 확인 |
|---|---|
| `ndt_dip_threshold` @ndt.py:93 `[S]` (주석 `[P]`→NDT-001 교정) | ndt.py:29 정의, :93 소비, 주석 `[P]` 실재 ✓ |
| `ndt_srb_norm_um` @:162/:240 (88.6 [S]) | :30 정의, :162·:240 소비 ✓ |
| `ndt_target_snrn` @:245 | :245 소비 ✓ |
| `ndt_min_roi_pixels` @:241 | :241 소비 ✓ |
| `ndt_thickness_method` @:405 (기본 morphological_opening) | :405 기본값 일치 ✓ |
| `ndt_thickness_scale_px` @:406 | :406 ✓ |
| `ndt_thickness_gradient_min_frac` @:407 | :407 ✓ |
| `ndt_wire_visibility_threshold` @:514 | :514 ✓ |
| `ndt_class_a_snrn_min`/`_required_wire` @:601/:602 | :601 float·:602 int ✓ |
| `ndt_class_b_snrn_min`/`_required_wire` @:603/:604 | :603·:604 ✓ |
| `beam_quality`(선택 서술자) @:177 | MetricCondition `params.get("beam_quality")` ✓ |

**수식·시그니처·거부계약 — 전부 정확:**
- SNRn = SNR × 88.6 / SRb_image → ndt.py:163 `snrn = snr * norm_um / srb_um` ✓
- `_dip` = 1 − valley/mean(peaks) → ndt.py:61-67 ✓
- 공개 진입점 7종 라인(70/129/144/206/383/495/583) 정확; 데이터클래스 라인(WirePair:45, ShotLogEntry:187, ThicknessResult:340, WireElement:482, IqiShot:553, ShotVerdict:570) ±1(@dataclass 데코레이터 라인 인용 일관) ✓
- MetricResult values 키(srb_um/dips/first_unresolved_pair @119-123, min_visible_wire/contrasts/visible @543-547) 정확 ✓
- peek-후-commit 거부=no-op(@273-301), 정규화 단일출처 compute_snrn 재호출(@283-299), target_reached/index(@309-311/320-327) 정확 ✓
- passthrough 이중가드(@430-464), 미지 method→MetricReadError(@425-428) 정확 ✓
- 엔진 내부 DSP는 grey_opening/gaussian_filter(@22/445/447)뿐 — read_duplex_srb/read_single_wire_iqi는 필터링 없음 → "UI 순수 샘플링" 경계 주장 정합 ✓

**교차 소스 — 전부 실재 확인:** robust_stats.py WelfordAccumulator:62/robust_mean:22/robust_std:30 ✓; io.py load_raw_frame:35, 사이드카 `resolution:[rows,cols]`/`dtype:"uint16"` = EXPORT-1 주장과 일치 ✓; result.py 4심볼 ✓; ingest_edrogi.py nps_flat:88/acrylic_step:89 ✓; io_panel.py guard_output_path:27 ✓; foundation G-1~G-9·§4 상주 브라우저·그룹7 표 실재 ✓.

## 제약 준수

- **골든 FROZEN(G-1)**: Exclusions에서 metrics/ndt.py·result.py·robust_stats.py·xframe.py 무편집 명시, "호출만" ✓
- **C-09 DSP 0(G-2)**: GUARD-1 + 전 REQ에서 SNR/SNRn/dip/contrast/verdict 자체계산·로컬 공식 재구현 금지 ✓
- **C-11 단방향(G-3)**: GUARD-2 metrics/ndt.py는 apps/gui 미의존 ✓
- **C-20 내보내기(G-4)**: EXPORT-2 guard_output_path 단일 choke point, data/ 하위 거부 ✓
- **QUARANTINE(G-5)**: GUARD-4 nps_flat sanity/acrylic 표시전용·임계화 금지, SRb·IQI는 #33 대기 ✓
- **SWR-000-2/-5**: NDT는 CalibKind 미소비 → 구조적 N/A 명시(지표 엔진 정당), 그럼에도 FROZEN/DSP-0/단방향/가드/QUARANTINE 전면 적용 선언 ✓
- **저장 규약**: `<name>_result.raw`(16-bit headerless little-endian <u2, 입력 동일 포맷)+`.json` 사이드카, float→clip[0,65535]→rint 변환 — 태스크 HARD 제약과 정확 일치 ✓
- **열기 규약**: INPUT-1이 상주 폴더 브라우저(폴더트리+가상화 썸네일+형제 필름스트립+이전/다음, 단일파일 지정 시 부모폴더 형제표시) foundation §4 완전 반영 ✓
- **시임 미러(CONTRACT-6)**: NDT는 run_pipeline/IXdetEngine 미경유(지표 엔진)임을 정당하게 구분 — XSEAM-002와 충돌 없음 ✓

## 그룹 고유 뷰어 특성 · 그룹간 정합

foundation 그룹7 요구(리포트/판정 테이블 중심, 실시간 적산 UI) 완전 포착: 실시간 SNRn 곡선+shot 로그(ACCUM) / duplex SRb dip 곡선+single-wire 판독 테이블+Class A/B verdict(IQI) / 두께보정 전후 프로필+passthrough(THICK). 모듈실행 그룹(1~6, run_pipeline)과의 축 구분 명확, before/after diff·CalibSet 조합을 Exclusions에서 배제 — 형제 SPEC-XSEAM-002(module-execution)와 무모순.

## 결함 목록

우선순위(critical/major) 결함: **없음.**

경미(minor, 비차단) 관찰:
- **M-1** spec.md:92 THICK-2 — State-Driven이 `WHILE...THEN` THEN 혼용(EARS 순도 경미 흠). 권고: THEN 제거하거나 Event-Driven 재분류.
- **M-2** spec.md:86/158 — `IqiShot` 필드 나열이 shot_index 누락(snrn/srb_um/min_visible_wire만; 실제 4필드). 지어냄 아님, 열거 불완전. 권고: shot_index 추가 표기.
- **M-3** 저장 산출물 명명 표류 — 본문(DoD:25, EXPORT-1:97) `<name>_report.json` vs 결정필요4(:125) `<입력명>_ndt_report.json`. 열린 결정으로 명시되어 비차단이나 run 전 확정 권고.
- **M-4** acceptance.md 부재 — 본 SPEC이 참조하나 미작성. 결정필요1(:122)에서 spec.md-only 커밋 범위임을 정직히 공개. 3-file HARD 규칙 충족 위해 후속 필요(플래닝 흠결 아닌 범위 공개).

## Chain-of-Verification (2차 자기비판)

1차에서 놓친 것 재점검: (a) 12 Params 키를 스킴하지 않고 12/12 라인 개별 대조 — 전부 실재. (b) REQ 22개 EARS 라벨 종단 점검 — THICK-2 1건 경미 흠 외 clean. (c) 전 REQ의 심볼(WirePair/WireElement/ShotLogEntry/IqiShot/ShotVerdict/values 딕셔너리 키)을 골든 정의와 대조 — 지어낸 심볼 0. (d) Exclusions 특이성 점검 — 7개 항목 전부 구체적(골든무변경/모듈아님/HW제어없음/판정없음/CSa·ADR없음/lag러너없음/QUARANTINE/최적화없음). (e) 그룹간 모순 재탐색 — XSEAM-002의 run_pipeline 조합 경로와 NDT 지표엔진 경로가 상충 없이 축분리. 신규 결함 없음.

## 권고

PASS. run 착수 가능. 형제 SPEC-XSEAM-002 미러 준수, 골든 대조 근거(§9) 전 항목 실측 정확, 지어내기 0건. run 전 선택 정리: M-1(EARS 순도), M-3(저장 명명 확정), 후속으로 plan.md/acceptance.md 작성(M-4). 어느 것도 차단 아님.
