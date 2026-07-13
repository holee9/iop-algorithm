# XDET Test Spec — TC Table v1.0

기준: V&V Plan 골격 v1.0, 측정 프로토콜 v1.0, EVAL v1.1. VV별 TC 발번. 판정은 EV min 기준(자동), 데이터는 골든 데이터셋(GDS) 참조.

| TC ID | 상위 VV | 시험 내용 | 데이터 | 자동 판정 |
|---|---|---|---|---|
| XDET-TC-000 | VV-000 | 모듈 단위 CI: 각 모듈 fixture 입출력 일치 + 시그니처·의존 방향 정적 검사 (직접 호출 검출 시 실패) | 합성 fixture (모듈 동봉) | 계약 위반 0건 |
| XDET-TC-001 | VV-001 | 보정 전/후 DQE 3선량(XN/2, XN, 2XN) 측정, 열화율 산출 | GDS-RQA5 균일+edge 세트 | EV-101 min |
| XDET-TC-002 | VV-001 | 보정 전/후 MTF@3.57 lp/mm 유지율 | GDS-edge (W 2mm, 1.5~3°) | EV-102 min |
| XDET-TC-003 | VV-001 | Defect 보정: 검증 세트 전수 — 잔존 cluster 0건, 검출 누락률 | GDS-defect (주입 결함 포함 합성+실측) | EV-103 min |
| XDET-TC-004 | VV-002 | First-frame lag % (포화 근접 노출 시퀀스) | GDS-lag 시퀀스 | EV-104 min |
| XDET-TC-005 | VV-002 | Ghost 잔상 CNR (고대비 패턴 후 균일 조사) | GDS-ghost | EV-104 min |
| XDET-TC-006 | VV-003 | Line artifact 잔존 (균일 조사, 3단 window 자동 검사) | GDS-균일 선량 계단 | EV-105 min |
| XDET-TC-007 | VV-003 | 구조물 오염 오보정률 (금속 임플란트 모사 세트) | GDS-구조물 세트 | EV-105 min |
| XDET-TC-008 | VV-004 | 포화 경계 아티팩트 자동 검출 | GDS-포화 시나리오 | EV-106 min |
| XDET-TC-009 | VV-004 | 기하 잔차 (격자 팬텀) | GDS-격자 | EV-106 min |
| XDET-TC-010 | VV-005 | SNR 개선율 + SRb 열화 동시 판정 (선량 계단) | GDS-임상 모사 저선량 | EV-201, EV-102 min |
| XDET-TC-011 | VV-005 | VST 왕복 무편향성 (denoiser 우회 시 원신호 복원) | 합성 Poisson-Gaussian 세트 | 편차 임계 내 |
| XDET-TC-012 | VV-006 | 대비강화/DRC 자동 IQA 회귀 (기준 버전 대비 비열화) | GDS-임상 모사 | IQA 스코어 기준선 |
| XDET-TC-013 | VV-007 | 자동 윈도우 수용률 집계 | GDS-부위별 세트 | EV-205 min |
| XDET-TC-014 | VV-007 | GSDF LUT 적합성 자가검사 | LUT 산출물 | PS3.14 적합 |
| XDET-TC-015 | VV-008 | Grid 성분 검출 정확도 + 잔존 grid line — grid 밀도 3부류(f_grid < Nyquist / ≈ / > Nyquist, aliased 포함) 필수 | GDS-grid 세트 (SWR-1006 요건) | EV-203 min |
| XDET-TC-016 | VV-008 | Moiré/aliasing 발생 검사 + GLS 실패 시 무처리 통과 확인 | GDS-grid 경계 사례 | EV-203, FR-M007 |
| XDET-TC-017 | VV-009 | 무그리드+커널 보정 CNR 개선 (팬텀) | GDS-scatter 팬텀 | EV-202 min |
| XDET-TC-018 | VV-011 | SNRn/SRb 자동 산출 + IQI 자동 판독 정확도 | GDS-NDT 시편 (BAM5류 용접 시편 권장) | EV-301 min |
| XDET-TC-019 | VV-011 | 두께보정 후 CSa/SMTR + SRb 보호 | GDS-step wedge | EV-303, EV-102 min |
| XDET-TC-020 | VV-012 | Tier별 파이프라인 처리시간 (100회 중앙값, cold/warm) | GDS-표준 프레임 | EV-401 min |
| XDET-TC-021 | VV-012 | 티어 간 출력 diff (결정론 bit / 부동소수점 허용오차) | GDS-표준 프레임 | EV-402 min |
| XDET-TC-022 | VV-010 | 관찰자 연구 (인허가용 — 프로토콜 별도) | 임상/모사 세트 | EV-204 (인력) |
| XDET-TC-023~025 | VV-013/014/015 | (Gen 2 예약 — PCCP 동기 상세화) | — | — |

## GUI 사용·검증 시험 레지스트리 (v0.5.1 기준선 후보)

아래 `XDET-TC-096~167`는 `apps/xdet-console/` WPF가 저장소의 모든 대상 알고리즘을 실제 사용·검증하기 위한 중앙 할당이다. `PLANNED`는 SPEC과 인수 기준만 있고 자동 시험 증거는 아직 없다는 뜻이다. 사용자 승인·기준선 동결 전에는 구현 PR이나 신규 자동화 작성을 시작하지 않는다. 승인 뒤 실제 xUnit/integration/ViewModel/UI Automation test name과 TC ID를 1:1로 연결한 뒤에만 상태를 `AUTOMATED` 또는 `UI-AUTOMATED`로 변경한다.

문서 착수 게이트 `DOC-XGUI-GATE-001`은 제품 TC 번호와 분리한다. 이 게이트는 G0 12조건, 승인 버전·일시·범위, 승인 전 비문서 변경 0을 검증하며 통과 전 `XDET-TC-096~167`의 상태 전환을 금지한다.

| TC ID | GUI 그룹 | 상태 | 정본 인수 기준 | 구현 시 필수 증거 |
|---|---|---|---|---|
| XDET-TC-096~103 | Calibration | PLANNED | `SPEC-XGUI-CALIB/acceptance.md` | apply 3종, 모든 builder/import, pipeline fidelity, uint8 mask, artifact/manifest/evidence |
| XDET-TC-104~111 | Lag | PLANNED | `SPEC-XGUI-LAG/acceptance.md` | fresh sequence, snapshot/restore/reset, first-frame/ghost/IRF, frame hashes, cancel safety |
| XDET-TC-112~119 | Line/Saturation/Geometry | PLANNED | `SPEC-XGUI-LINESATGEO/acceptance.md` | 세 action 개별·조합, actual diag, uint8 mask, 오류·artifact/manifest |
| XDET-TC-120~127 | Denoise | PLANNED | `SPEC-XGUI-DENOISE/acceptance.md` | dynamic required Params, BM3D/NLM, NOISE gate, noise/NPS/SNR, user input/evidence |
| XDET-TC-128~135 | Enhancement | PLANNED | `SPEC-XGUI-ENHANCE/acceptance.md` | MSE/window, GSDF LUT, P-value remap, display-domain encoding, artifact/manifest |
| XDET-TC-136~143 | Grid/Virtual Grid | PLANNED | `SPEC-XGUI-GRID/acceptance.md` | analyze/notch/process, estimate/process, kernel build/fit, provenance/artifact |
| XDET-TC-144~151 | NDT | PLANNED | `SPEC-XGUI-NDT/acceptance.md` | 7 action, accumulator update/current/target/shot log, report/manifest/evidence |
| XDET-TC-152~159 | Metrics | PLANNED | `SPEC-XGUI-METRICS/acceptance.md` | MTF/NPS/line-noise/defect/DQE/scalar-at, typed DTO, report/manifest |
| XDET-TC-160 | Shared catalog | PLANNED | `SPEC-XGUI-MASTER/algorithm-catalog.md` | target 64 + SAMPLE helper 3 + common infrastructure 6 = qualified callable 73; 세 source 집합·catalog·manifest 차이와 집합 간 중복 0 |
| XDET-TC-161 | Shared Contract | PLANNED | `SPEC-XSEAM-002/acceptance.md` | catalog ACTION/SESSION − 9-family manifest/handler 집합 차이 0 |
| XDET-TC-162 | Shared orchestration | PLANNED | `SPEC-XGUI-MASTER/acceptance.md` | generic pipeline/sequence, canonical order, CalibMap/ParamsMap, state/intermediates fidelity |
| XDET-TC-163 | Shared tier | PLANNED | `SPEC-XSEAM-002/acceptance.md` | decide/select/run/time, forced upgrade 거부, downgrade 허용, structural timing |
| XDET-TC-164 | Shared DQE | PLANNED | `SPEC-XGUI-METRICS/acceptance.md` | `mtf_value_at`→`compute_dqe`, support bin, no extrapolation/clamp/UI DSP, provenance |
| XDET-TC-165 | Shared IO/calibration | PLANNED | `SPEC-XGUI-MASTER/acceptance.md` | builder validation, frame uint16/mask uint8, C-20, round-trip/reproducibility/hash |
| XDET-TC-166 | Shared state/evidence | PLANNED | `SPEC-XGUI-MASTER/acceptance.md` | availability/evidence 분리, strict user input, 무단 golden 승격 0 |
| XDET-TC-167 | Shared GUI reachability | PLANNED | `SPEC-XGUI-MASTER/acceptance.md` | 모든 ACTION/SESSION FeatureId에 enabled/typed-error GUI command와 AutomationId 존재 |

## 운용

1. TC-001~021은 기존 알고리즘 수치 회귀 스위트이며 GUI TC와 대체 관계가 아니다.
2. GDS 세트 ID는 golden dataset tag와 1:1이며 데이터 변경은 재베이스라인 절차를 따른다.
3. TC-022는 인허가 단계 실행이며 개발 게이트가 아니다.
4. GUI TC-096~167은 `PLANNED` 동안 CI 통과 수에 포함하지 않는다. 실제 test name·로그·artifact가 등록된 TC만 완료로 보고한다.
5. 새 public ACTION/SESSION이 추가되면 TC-160/161/167이 실패하고 catalog·seam·GUI·시험을 함께 갱신해야 한다.
