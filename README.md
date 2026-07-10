# iop-algorithm — XDET 영상처리 SW

## 프로젝트 개요

XDET은 X-ray FPD(CsI, 140µm, 3072×3072 / 3072×2560, 16-bit raw) 영상처리 소프트웨어이다. 본 저장소는 그 P1 단계 — SW 레퍼런스/골든 모델 구현을 담고 있다. 정수 최적화나 실시간 처리 성능이 아니라, float 정밀도 기준의 정확한 참조 동작을 정의하는 것이 P1의 유일한 목표이며, 속도 최적화는 의도적으로 P2 이후로 미뤄져 있다.

기술 스택은 Python 3.11+ 및 numpy/scipy 기반 골든 모델, pytest 기반 CI이다. 아키텍처는 `common/` · `modules/` · `pipeline/` · `metrics/` 4계층으로 구성되며, 모든 처리 모듈은 `process(XFrame, CalibSet, Params) -> XFrame` 단일 시그니처를 갖는 순수함수이다.

## 현재 상태

P1은 2026-07-10 완료되었다. 11개 SPEC(T0~T10)이 GitHub 이슈 #1~#12에 대응되어 전건 main 브랜치에 병합 완료되었으며, 최종 테스트 스위트는 **465 passed**이다.

상세 완료 이력(SPEC별 커밋, plan-audit 점수 추이, 독립 리뷰에서 발견된 critical/major 결함)은 다음 문서를 참조한다.

→ [`docs/P1_COMPLETION_REPORT.md`](docs/P1_COMPLETION_REPORT.md)

## 문서 지도

문서 지도의 단일 출처는 저장소 루트의 [`CLAUDE.md`](CLAUDE.md)이다(중복 방지를 위해 여기서는 목록을 재기술하지 않는다). `docs/` 디렉터리에는 SWR(사양), EVAL(합격기준), TestSpec(시험케이스), measurement protocol(지표산출 엔진 사양), FRD/PRD/MRD/RTM(요구·추적) 등이 있으며, 각 문서의 역할은 CLAUDE.md의 "문서 지도" 표에 정리되어 있다.

## 아키텍처 한눈에

- `common/` — XFrame·CalibSet 데이터 구조 및 5종 공용 컴포넌트(피라미드, FFT/PSD, 강건통계, 마스크연산, 동일성검증 등)
- `modules/` — 순수함수형 처리 모듈(offset·gain·defect·line_noise·saturation·geometry·lag·denoise·mse·window·grid·virtual_grid), 모듈 간 직접 호출 금지
- `pipeline/` — 조합 계층. `orchestrator.py`(CANONICAL_ORDER 기반), `sequence.py`(상태보유 모듈용 시퀀스 러너), `tier.py`(하드웨어 티어 게이팅)
- `metrics/` — T1 측정 엔진(MTF·NPS·DQE·lag IRF·defect 통계·NDT 등)

상세 아키텍처 설명은 [`docs/P1_COMPLETION_REPORT.md`](docs/P1_COMPLETION_REPORT.md)의 "아키텍처 개요" 절을 참조한다.

## 개발/테스트 실행

```bash
uv run pytest
```

## P2 착수 필요성 — 딥싱크 검토 (Deep-Sync Review)

이 섹션은 P1 산출물에 대해 합리적인 독자가 P2 착수 여부를 저울질할 때 참고할 사실들을 제시한다. **결론은 내리지 않는다.**

### 구조적으로 끝난 것

- CLAUDE.md 정의상 "Gen 1 대상 TC-000~021 CI 전체 통과 + 골든 모델 형상 동결"은 구조적으로 달성되었다 — 465 passed, 0 skipped, 캡스톤 테스트(`tests/test_tc_skeletons.py`)가 전 22개 TC ID의 실동작 존재를 강제 검증한다.
- 11개 SPEC(T0~T10) 전건이 plan-audit(EARS 준수 검증) 및 독립 코드 리뷰를 거쳐 main에 병합되었다.

### 실측/문서/특허 검토가 남은 것

- TC-020/021(티어/동일성 프레임)은 SPEC 설계 단계에서부터 절대 수치 판정이 P2로 명시 이연된 상태다. "형상 동결"은 골든모델 코드 자체의 동결을 의미하며, 하드웨어 티어별 실측 성능 기준의 확정을 의미하지 않는다.
- 미해결 문서 정합성 갭 2건이 존재한다.
  - DQE 측정 프로토콜 문서(`docs/XDET_measurement_protocol_v1.0.md` §1.4)가 코드와 불일치한다 — T5 리뷰에서 IEC 62220-1과의 공식 차원 오류가 발견되어 코드(`metrics/dqe.py`)만 수정되었고, 문서는 개정되지 않았다.
  - SWR 부록 A/A-2(TBD 레지스터·근거등급 총괄)가 11개 SPEC의 반복된 등재 요청에도 갱신되지 않았다.
- 특허 검토(⚠P 플래그 6개소 이상)가 "릴리스 게이트로 이연"된 상태로 남아있다. PRM v1.1이 요구하는 "상세설계 착수 전 변호사 검토 완료" 절차의 증적은 SWR 문서 상에서 확인되지 않는다. 이는 P1 범위 밖(정책상 의도된 이연)이지만 릴리스 전 반드시 클리어해야 할 게이트다.
- TBD-[B](실측 대기) 파라미터가 11개 SPEC 전반에 분포하며, 특히 LAG(IRF 파라미터)와 VGRID(SKS 산란커널)가 실측 의존도가 높다. 실제 패널 하드웨어 데이터 없이는 P1 골든모델이 "이론적으로 정확"할 뿐 "검증된 정확"이라 말하기 어려운 항목들이 남아있다.

### P2/Gen2 고유 범위

- Gen 2 항목(DL, ADR)은 CLAUDE.md 상 P1 범위에서 명시적으로 제외되어 있으며, 이번 P1 작업 범위에도 포함되지 않았다 — P2 시작 시 최초 논의 대상이다.

이 섹션은 사실관계 요약이며, 착수 여부는 프로젝트 오너의 판단에 달려 있다.
