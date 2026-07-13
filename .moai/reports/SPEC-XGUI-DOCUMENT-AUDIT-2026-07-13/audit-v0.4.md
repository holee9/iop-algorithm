---
id: SPEC-XGUI-MASTER-AUDIT-FINAL
version: 0.4.0
status: completed
created: 2026-07-13
updated: 2026-07-13
author: codex
labels: [xgui, final-audit, exhaustive-coverage, documentation, verification]
---

# SPEC-XGUI v0.4 최종 정합 감사

## 판정

**문서 기준선 PASS — 저장소의 대상 알고리즘 전체를 WPF GUI에서 실제 사용·검증하기 위한 구현 범위·계약·인수·시험 계획이 닫혔다.**

**애플리케이션 구현은 NOT COMPLETE다.** 현재 WPF는 4개 부분 탭과 offset→gain 고정 seam만 보유한다. 이 감사의 PASS는 코드 완료가 아니라, 구현자가 누락 범위를 임의로 축소하거나 DSP를 새로 만들지 않고 전체 기능을 구현할 수 있는 문서 완결성 판정이다.

## 소스 대 문서 전수 감사

| 검사 | 결과 |
|---|---|
| 구현 대상 | PASS — `apps/xdet-console/` .NET 9 WPF; Python `apps/gui/`는 역사적 선례 |
| core public callable | PASS — `modules/`, `metrics/`, `pipeline/`에서 추출한 64개 전부 분류 |
| SAMPLE helper | PASS — `scripts.ingest_edrogi.build_{offset,gain,defect}_calibset` 3개를 등록 edrogi preset 전용으로 분류 |
| operation closure | PASS — 총 67/67이 catalog, 그룹/shared spec, Given/When/Then acceptance에 qualified EntryPoint로 존재 |
| 문서 세트 | PASS — MASTER+8그룹+XSEAM의 spec/plan/acceptance/research 40개 모두 v0.4.0 |
| EARS/GWT | PASS — 10개 spec 모두 EARS 요구, 10개 acceptance 모두 Given/When/Then 보유 |
| Params/provenance | PASS — 소스에서 추출한 required/optional Params·provenance key 67/67이 활성 문서에 존재 |
| DTO | PASS — 9 family, `AlgorithmCatalogManifest`, typed value/error, input-set, result/run manifest 계약 존재 |
| 상태 정직성 | PASS — `AlgorithmAvailability`와 실행별 `EvidenceGrade`가 분리됨 |
| DQE | PASS — `NPS_BINS_WITHIN_MTF_SUPPORT_V1`, `metrics.mtf.mtf_value_at`→`metrics.dqe.compute_dqe`, no extrapolation/clamp/UI DSP 계약 존재 |
| calibration | PASS — 범용 defect/lag/noise/scatter builder, strict import, edrogi SAMPLE-only helper 경계가 분리됨 |
| session/tier | PASS — Lag snapshot/restore, NDT accumulator, tier decide/select/run/time 계약과 음성 대조 존재 |
| mask/export | PASS — frame encoding은 domain별 uint16, XFrame mask는 실제 `numpy.uint8` bitfield, C-20/run manifest/round-trip 계약 존재 |
| 중앙 TC | PASS — XDET-TC-096~167의 72개 번호가 빠짐·중복 없이 단일 배정되고 전부 `PLANNED`로 정직하게 표시됨 |
| 상대 링크 | PASS — 활성 대상 링크 82개 모두 존재; code-reference pseudo-link 4개는 링크 검사에서 분리 |
| Markdown diff | PASS — `git diff --check` 오류 0 |

정적 전수 검사는 현재 문서의 사실성을 확인한 감사다. 계획된 제품 시험 `AlgorithmCatalogCoverageTests` 자체가 구현됐다는 뜻은 아니다. 실제 코드에서는 같은 집합 비교를 xUnit/CI에 구현해야 XDET-TC-160/161/167을 완료할 수 있다.

## 구현 계약의 핵심

1. 카탈로그의 ACTION/SESSION/DERIVED/INFRASTRUCTURE 전부를 `AlgorithmCatalogManifest`에 싣는다.
2. 모든 ACTION/SESSION은 FRAME_PROCESS, PIPELINE, SEQUENCE, STACK_METRIC, PROFILE_METRIC, CALIBRATION_BUILD, METRIC_SERIES, NDT_SESSION, TIER 중 하나의 typed Contract handler를 가진다.
3. UI는 입력 수집·상태·렌더링만 담당하며 DSP·보간·지표·판정·스테이지 정렬은 Python engine 소유다.
4. strict 사용자 입력은 등록 fixture 부재와 무관하게 실행하고, 승인 전 `USER_SUPPLIED_UNVERIFIED`로 표시한다.
5. 모든 실행은 FeatureId, qualified EntryPoints, run id, input/Params/CalibSet/result hash, availability/evidence, warnings/error를 run manifest에 남긴다.
6. catalog→manifest→Contract handler→GUI command/AutomationId→TC의 집합 차이가 0이어야 구현 완료다.

## 중앙 GUI 시험 상태

| 범위 | 소유자 | 문서 상태 |
|---|---|---|
| 096~103 | Calibration | PLANNED |
| 104~111 | Lag | PLANNED |
| 112~119 | Line/Saturation/Geometry | PLANNED |
| 120~127 | Denoise | PLANNED |
| 128~135 | Enhancement | PLANNED |
| 136~143 | Grid/Virtual Grid | PLANNED |
| 144~151 | NDT | PLANNED |
| 152~159 | Metrics | PLANNED |
| 160~167 | catalog/seam/pipeline/tier/DQE/IO/evidence/reachability | PLANNED |

자동화 test name·로그·artifact가 중앙 TestSpec에 등록되기 전에는 어떤 GUI TC도 통과로 계산하지 않는다.

## 2026-07-13 fresh verification

- `uv run pytest -q`: **632 passed in 170.37s**, exit 0
- `uv run lint-imports`: **7 contracts kept, 0 broken**, exit 0
- `dotnet test apps/xdet-console/Xdet.sln --no-restore`: **21 passed, 0 failed, 0 skipped**, exit 0
- 문서 정적 감사: **67/67 operation closure, 72/72 TC, 67/67 Params/provenance, broken link 0, wrong mask dtype 0**

이 시험은 기존 코드의 무회귀를 증명한다. 아직 작성되지 않은 v0.4 GUI 자동화가 통과했다는 의미가 아니다.

## 현재 코드의 명시적 격차

1. `MainWindow.xaml`은 Viewer, registered offset→gain Pipeline, Real Image, synthetic MTF의 4개 탭뿐이며 8개 목적 그룹의 전체 command surface가 없다.
2. `IXdetEngine.RunPipeline`은 offset/gain 고정 signature이고 `AlgorithmCatalogManifest`와 9 family handler가 없다.
3. `RunSequence`, calibration build/import handler, Lag state, NDT session, DQE composition, tier handler가 없다.
4. 현재 C# source에는 `AlgorithmCatalogManifest`, `DqeCompose`, `RunSequence`, `SNRnAccumulator`, tier entry point가 없다.
5. 현재 저장은 Python GUI export helper의 npz+JSON 경로이며 목표 frame/mask artifact와 `xdet.run-manifest/1.0`을 구현하지 않았다.
6. XDET-TC-096~167은 전부 계획 상태이며 xUnit/integration/ViewModel/UIA 구현 증거가 없다.

## 구현 인계

문서를 다시 작성하면서 일부 코드만 임의 구현하는 방식이 아니다. v0.4 전체 범위는 이미 폐쇄형 worklist로 확정됐다. 코드는 마스터 plan의 M1/M2 공통 셸·9-family seam부터 단계적으로 구현할 수 있지만, 각 단계는 catalog와 중앙 TC에 의해 전체 목표에 계속 묶이며 67개 operation과 72개 GUI TC가 모두 닫히기 전에는 완료가 아니다.
