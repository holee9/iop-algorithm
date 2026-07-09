# SPEC-GRID-001 구현 계획 (plan.md)

T7(WP8 Grid line suppression). `modules/grid.py`(무상태 처리 모듈)를 구현하고, WP8(관측 스펙트럼 피크 직접 탐색 → 1D Gaussian notch 억제 → 저주파 접힘 moiré 경고 → 무검출 무처리 통과, SWR-1001~1006)을 T0 계약 `process(XFrame, CalibSet, Params) -> XFrame`으로 실현한다. 스펙트럼 추정은 공용 컴포넌트 `common/fft_psd.py`(③ FFT·PSD)를 SWR-000-9에 따라 소비·확장하며 재구현하지 않는다. 근거: [spec.md](./spec.md) · 인수 기준: [acceptance.md](./acceptance.md).

> **버전 0.1.1 (2026-07-09)** — plan-audit iteration 1 반영. GitHub 이슈 #8. 6개 요구 그룹(SEARCH/NOTCH/MOIRE/PASSTHROUGH/CONTRACT/VALIDATE). 결정 1(전용 `grid` 스테이지 배치: `geometry`↔`denoise` 사이)은 CANONICAL_ORDER 대조 검증 후 확정(RESOLVED).

## 선행 결정 (plan-audit 확정 대상)

「결정 필요/확인 사항」 1은 T0 표면(`CANONICAL_ORDER`)을 변경하는 run-blocking 항목으로 plan-audit에서 확정해야 한다(T5 SPEC-DENOISE-001·T6 SPEC-POST-001 결정 1과 동형의 부분수열-삽입 패턴). 나머지 2~5는 확인 대상(가정 default 제시).

- **결정 1(스테이지 배치, run-blocking)**: 전용 `grid` 스테이지를 `geometry`와 `denoise` **사이**에 신설(`CANONICAL_ORDER = … → saturation → geometry → grid → denoise → mse → window → post`). 등록 stages = `CANONICAL_ORDER` 부분수열 검증으로 하류 미등록 SPEC에 하위호환(T5·T6 선례). `post`는 예약 tail 유지. 검출기 캘리브레이션 없음 → `_KIND_BY_STAGE` 미등재, 진입 게이트 충족을 위해 CalibSet(OTHER) 소비(saturation/geometry/mse/window 선례). rationale: 기하 보정 후 축-정렬 영상에서 탐색(geometry 뒤) + BM3D 텍스처 오인·MSE 증폭 방지(denoise·mse 앞). 기각 대안: denoise 뒤(BM3D가 grid 패턴 왜곡 → notch 부정확).
- **확인 2(grid 메타데이터 소재·역할)**: 선택적 Params 필드, SWR-1005 대조 경고 전용, 피크 위치 산출 유입 금지(SWR-1001).
- **확인 3(EV-203 "비가시" 조작적 정의)**: notch 후 잔존 피크 전력 ≤ 유의성 임계(결정론 leg) + grid 직교축 MTF@Nyquist 유지율 ≥ EV-102 min 가드레일. 관찰자 비가시(EV-204)는 인허가 이연.
- **확인 4(방향 축-정렬 가정)**: 수평/수직만 지원, 대각선 범위 밖, 방향 모호 시 무검출 통과.
- **확인 5(파라미터 부록 A 등재)**: D_th·FWHM 계수 [T], 탐색 대역·moiré 컷오프·감쇠 상한·고조파 차수 무등급 등재 요청.

## 기술 접근 (WHAT — HOW 세부는 run 소관)

- **WP8 5단**: (1) grid 방향 추정(행/열 1D PSD 에너지 비교, `common/fft_psd.py` 소비) → (2) 해당 축 1D PSD(Welch)에서 탐색 대역 [0.3, f_N] 협대역 피크 탐색(유의성 ≥ D_th dB) + 접힘 고려 고조파 후보(f_a 정수배·f_s 접힘 조합) 검사(SWR-1001~1002) → (3) 검출 피크별 주파수 도메인 1D Gaussian notch(대역폭 = FWHM × 1.5, grid 직교축, 2D 등방 금지)(SWR-1003) → (4) 저주파 접힘(< 0.5/mm) 시 감쇠 상한 제한 + grid 교체 권고 경고(SWR-1004) → (5) 유의 피크 미검출 시 수치 동일 통과 + "grid 미검출" 로그(SWR-1005, FR-M007).
- **관측 스펙트럼 직접 탐색([HARD], SWR-1001)**: notch 대상 주파수는 오로지 관측 스펙트럼 피크에서 도출한다. 명목 grid 주파수·메타데이터 밀도값을 탐색·notch 산출 입력으로 쓰지 않는다(REQ-GRID-SEARCH-4 Unwanted). aliasing 전제: f_grid > f_N → f_a = |f_grid − k·f_s|. aliased 부류가 관측-탐색 부하의 핵심 negative control이다.
- **공용 컴포넌트 ③ FFT·PSD 소비(SWR-000-9)**: 스펙트럼 추정은 `common/fft_psd.py`(T1 구현, 헤더 @MX:ANCHOR가 T7 grid-suppression을 소비자로 명시)를 소비한다. SWR-1002의 "1D PSD(전 행 평균, Welch)" 추정기가 부재하면 `common/fft_psd.py`에 최초-소비자 확장으로 추가(POST-001의 `common/pyramid.py`·`common/histogram_fov.py` 확장 선례). FFT/PSD 모듈 내부 재구현 금지, `module → common` 단방향 유지.
- **line noise와 구별**: `metrics/nps.detect_line_noise`(T3, 판독 저주파 행/열 오프셋 밴딩, T1 엔진)와 현상·계층·소비 위치가 다르다. `grid`는 고주파(aliased 가능) 주기 변조를 주파수 notch로 억제하는 `modules/` 처리 모듈로 `metrics`를 import하지 않는다.
- **측정=판정 분리**: 모듈은 EV 임계·판정 로직을 내장하지 않는다. MTF 가드레일은 `tests/`에서 T1 지표 엔진(`metrics/mtf.compute_mtf`/`mtf_value_at`)을 소비하고, 검출 정확도·잔존 피크·moiré·통과는 `tests/`에서 기지 grid 주파수 대조 직접 측정으로 판정한다.

## 마일스톤 (우선순위 순 — 시간 추정 없음)

### M0 — 선행 결정 확정 (Priority: High, run-blocking)
- 「결정 필요/확인 사항」 1(전용 `grid` 스테이지 배치, `geometry`와 `denoise` 사이)을 plan-audit에서 확정하고 spec.md HISTORY에 반영(house style: 항목 번호 유지 + `[확정 — RESOLVED]` + rationale). 확인 2~5 default는 run 중 검토.
- 확정 산출: `CANONICAL_ORDER = … → geometry → grid → denoise → mse → window → post`, `_KIND_BY_STAGE` 미등재(OTHER 빈 placeholder 소비), grid 메타데이터 = 선택적 Params 대조 경고 전용.

### M1 — 공용 컴포넌트 확장 (Priority: High)
- `common/fft_psd.py`: SWR-1002 "1D PSD(전 행/열 평균, Welch)" 축 PSD 추정기가 부재하면 최초-소비자 확장으로 추가(SWR-000-9 ③, `grid` 소비). 기존 `compute_psd`/`nps_2d`/`radial_frequency_axes`와 정합 유지.
- 대응: REQ-GRID-SEARCH-1/2, REQ-GRID-CONTRACT-3.

### M2 — grid 모듈: 방향 추정 + 관측 스펙트럼 피크 탐색 (Priority: High)
- `modules/grid.py`: 행/열 1D PSD 에너지 비교 방향 추정(방향 마진 [T]) → 해당 축 1D PSD 탐색 대역 [0.3, f_N] 협대역 피크(유의성 ≥ D_th dB [T]) + 접힘 고려 고조파 후보(고조파 차수 [T]) 검사.
- 명목 주파수·메타데이터 밀도 유입 금지(REQ-GRID-SEARCH-4 Unwanted 단일 경로). f_N·f_s는 Params pitch 파생.
- 대응: REQ-GRID-SEARCH-1/2/3/4.

### M3 — grid 모듈: 1D Gaussian notch 억제 (Priority: High)
- 검출 피크별 주파수 도메인 1D Gaussian notch(대역폭 = FWHM × 1.5 [T])를 grid 직교축에만 적용(`common/fft_psd.py` 변환/역변환 소비). 2D 등방 notch 금지(REQ-GRID-NOTCH-2 Unwanted).
- 대응: REQ-GRID-NOTCH-1/2.

### M4 — grid 모듈: 저주파 접힘 moiré 경고 + 무검출 통과 (Priority: High)
- 저주파 접힘(< 0.5/mm [무등급]) 피크 → 감쇠 계수 상한([T]) 제한 + grid 교체 권고 경고 `HistoryEntry.extra` 기록(REQ-GRID-MOIRE-1).
- 유의 피크 미검출 → 수치 동일 통과 + "grid 미검출" 로그(REQ-GRID-PASSTHROUGH-1), 무단 억제 금지(REQ-GRID-PASSTHROUGH-2 Unwanted). grid 메타데이터 제공 시 대조 경고(REQ-GRID-PASSTHROUGH-3 Optional).
- 대응: REQ-GRID-MOIRE-1, REQ-GRID-PASSTHROUGH-1/2/3.

### M5 — 모듈 계약·오케스트레이터 통합 (Priority: High)
- `grid` 모듈 `process(XFrame,CalibSet,Params)->XFrame` 무상태 순수함수, 불변성·이력 체인(`HistoryEntry.extra` 진단)·의존 방향(`module → common`)·harness 단독 시험.
- 전용 `grid` 스테이지(`geometry`와 `denoise` 사이)를 `CANONICAL_ORDER`에 신설(결정 1), CalibSet(OTHER) 진입 게이트 충족, 마스크 substrate 불변·포화 미복원(REQ-GRID-CONTRACT-6).
- 대응: REQ-GRID-CONTRACT-1~6.

### M6 — 합성 검증 + TC 전환 (Priority: High)
- XDET-TC-015(검출 정확도 + 잔존 grid line, 하드 DoD): 밀도 3부류(f_grid < f_N / ≈ f_N / > f_N aliased) 합성 팬텀 → 올바른 피크 검출 + notch 후 잔존 피크 전력 ≤ 유의성 임계(비가시) + grid 직교축 MTF@Nyquist 유지율 ≥ EV-102 min 가드레일. aliased 부류 negative control(명목 위치 무피크).
- XDET-TC-016(moiré 발생 검사 + GLS 실패 통과): 표준 부류 moiré 0건 + 저주파 접힘 경계(감쇠 상한 + 경고) + 무피크 입력 수치 동일 통과 + 로그.
- pytest skeleton(skip) → 실동작 케이스 전환(REQ-GRID-VALIDATE-6).
- 대응: REQ-GRID-VALIDATE-1~6, acceptance 전 시나리오.

## 산출물

| 경로 | 역할 | 대응 REQ |
|---|---|---|
| `modules/grid.py` | Grid line suppression 처리 모듈(무상태) — 방향 추정·관측 스펙트럼 피크 탐색·1D Gaussian notch·moiré 경고·무검출 통과 | SEARCH, NOTCH, MOIRE, PASSTHROUGH, CONTRACT |
| `common/fft_psd.py` | ③ FFT·PSD 공용 컴포넌트 — 1D Welch 축 PSD 추정기 최초-소비자 확장(부재 시) | SEARCH-1/2 |
| `pipeline/orchestrator.py` | `grid` 스테이지 `CANONICAL_ORDER`(geometry와 denoise 사이) 신설(결정 1) | CONTRACT-5 |
| `tests/…` | XDET-TC-015/016 실동작 케이스 + 밀도 3부류 합성 팬텀 + harness fixture | VALIDATE |

> `pyproject.toml`은 변경 없음 — 방향 추정·1D PSD·Gaussian notch 전부 자체 numpy/scipy 구현으로 신규 의존성 미추가.
> `common/calibset.py`는 신규 CalibKind 미추가 — `grid`는 CalibSet(OTHER) 소비(검출기 캘리브레이션 없음, POST-001 선례).

## 리스크 및 완화

- **[High] 명목-주파수 shortcut 유혹(SWR-1001 위반)** — aliasing 전제를 무시하고 명목 grid 주파수로 notch하면 aliased grid를 놓쳐 잔존 grid line 발생. 완화: 관측 스펙트럼 직접 탐색([HARD], REQ-GRID-SEARCH-4 Unwanted), aliased 부류 negative control(REQ-GRID-VALIDATE-3)로 명목-탐색 실패를 시험측 대조로 증명.
- **[High] 스테이지 배치 T0 표면 변경** — `CANONICAL_ORDER` `grid` 스테이지 신설이 하류 SPEC 회귀. 완화: 결정 1(geometry와 denoise 사이), 등록 stages = 부분수열 검증 하위호환(T5·T6 선례), `post` 예약 tail 유지.
- **[High] 1D notch 해부 손실(EV-102 초과)** — notch 대역이 과대하거나 저주파 접힘 시 해부 신호 손실. 완화: grid 직교 1축만 적용(2D 등방 금지, REQ-GRID-NOTCH-2), 대역폭 = FWHM × 1.5 제한, 저주파 접힘 감쇠 상한(REQ-GRID-MOIRE-1), grid 직교축 MTF@Nyquist 유지율 EV-102 min 가드레일(REQ-GRID-VALIDATE-2).
- **[Medium] 무검출 무단 억제** — 잡음 피크를 grid로 오검출해 무단 notch. 완화: 유의성 임계 D_th 이상만 채택(REQ-GRID-SEARCH-2), 무검출 시 수치 동일 통과 단일 경로(REQ-GRID-PASSTHROUGH-2 Unwanted), 무피크 통과 수치 동일성 검증(REQ-GRID-VALIDATE-5).
- **[Medium] BM3D와의 순서 상호작용** — grid를 denoise 뒤에 두면 BM3D가 주기 패턴을 왜곡·확산시켜 notch 부정확. 완화: 결정 1(grid를 denoise 앞에 배치)으로 깨끗한 선처리 순서 확보.
- **[Medium] 방향 오추정(대각·교차 grid)** — 축-정렬 전제 밖 grid에서 방향 오추정. 완화: 방향 에너지비 마진([T]) 미만 시 무검출 통과(확인 4), 대각선 grid P1 범위 밖 명시(Exclusions), 방향·에너지비 진단 기록.
- **[Low] 실측 grid 세트 부재** — grid 취득 세트 도착 전. 완화: 밀도 3부류(aliased 포함) 합성 팬텀 선검증(SWR-1006), 실측 도착 후 치환은 게이트 아님(부록 A 정책).

## 검증 전략

- 모든 판정은 `tests/`에서 모듈 + T1 지표 엔진(MTF 가드레일)·기지 grid 주파수 대조로 수행(모듈은 `metrics` 미import — CONTRACT-3).
- EV 임계(EV-203/102)·D_th·잔존 피크 유의성 임계는 외부 주입(측정=판정 분리). 처리·판정 코드에 임계 내장 금지.
- harness 단독 시험(합성 입력 + 기대 출력 fixture)으로 모듈 격리 검증(XDET-TC-000 계승).
- 하드 DoD(XDET-TC-015: 관측 스펙트럼 검출 + 잔존 피크 유의성 이하 + MTF 가드레일)는 결정론 이진 게이트; PARTIAL(XDET-TC-016 moiré 경계·통과)은 합성 기지값·객관 대리 지표로 정직하게 부분 판정하고 관찰자 비가시(EV-204)는 인허가 이연으로 명시.
- aliased 부류(> f_N)를 필수 포함하고(SWR-1006), 명목-기반 탐색 실패를 테스트-로컬 대조 계산으로 확인하여 관측-스펙트럼 탐색이 부하 핵심임을 증명한다(REQ-GRID-VALIDATE-3).
