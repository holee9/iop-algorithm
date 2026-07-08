# XDET P1 아키텍처 개요 (플레이스홀더)

현재 소스 코드가 없는 문서 전용 상태입니다. T0(프레임워크 스캐폴드) 완료 후 `/moai codemaps`로 실제 아키텍처 문서를 생성하세요.

## 목표 구조 (계획)

```
common/    # 공용 컴포넌트 5종 (pyramid, histogram/FOV, FFT/PSD, robust stats, mask ops)
modules/   # 파이프라인 처리 모듈 (process(XFrame, CalibSet, Params) -> XFrame)
pipeline/  # 오케스트레이터 및 파이프라인 정의
metrics/   # 지표 산출 엔진 (MTF, NPS/NNPS, DQE, lag, bad pixel, SNRn, duplex wire)
tests/     # pytest TC-000~021
data/      # 골든 데이터셋 (Git LFS)
docs/      # 사양 문서 (SWR v1.2 = 단일 출처)
```

상세: `.moai/project/structure.md` 참조.
