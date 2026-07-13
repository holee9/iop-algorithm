---
id: SPEC-XGUI-CALIB
version: 0.5.1
status: completed
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-12
updated: 2026-07-13
author: drake.lee
---

# SPEC-XGUI-CALIB 리서치 기록

## 조사 범위와 사실

- 보정 실행: `modules.offset.process`, `modules.gain.process`, `modules.defect.process`
- 범용 builder: `metrics.defect_map.build_defect_map`, `metrics.defect_map.classify_morphology`, `metrics.defect_stats.classify_defects`, lag IRF, noise model, scatter kernel build/fit
- SAMPLE preset helper: `scripts.ingest_edrogi.build_offset_calibset`, `scripts.ingest_edrogi.build_gain_calibset`, `scripts.ingest_edrogi.build_defect_calibset`은 고정 SAMPLE panel/validity/domain을 사용하므로 등록 edrogi 구조 sanity 전용이며 범용 builder가 아니다.
- import: CalibSet schema/hash/shape/semantic validation
- XFrame mask는 `uint8` bitmask이고 DEFECT=1, SATURATION=2, INTERPOLATION=4, SATURATION_BAND=8이다.
- 등록 edrogi 자료는 builder와 offset→gain→defect 조합의 SAMPLE sanity에는 쓸 수 있지만 수치 golden은 아니다.

## 확정 결정

- Calibration GUI는 세 보정 stage와 모든 공개 calibration builder/import 검증 작업을 제공한다.
- defect 임계값은 별도 고급 패널에 두고 source Params schema와 동일한 이름·타입·제약을 사용한다.
- 검증 모드는 최종 결과와 모든 intermediate를 Python 직접 호출 결과와 대조한다.
- `XDET-TC-096~103` 전체를 사용하며 reserved 번호를 두지 않는다.

## v0.5 초기 문서 통제 재검토

- v0.5 초기 검토는 이 문서가 기록한 Python golden 사실이나 알고리즘 의미를 바꾸지 않는다.
- 구현 전제는 `../SPEC-XGUI-MASTER/baseline-control.md` G0, 요구사항·TC·증거 연결은 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따른다.
- 사용자 승인과 기준선 동결 전에는 이 조사 결과를 근거로 소스·XAML·테스트 구현을 시작하지 않는다.
