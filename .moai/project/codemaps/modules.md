# 모듈 카탈로그

패키지별 파일 상세 목록. 전체 아키텍처는 [overview.md](./overview.md), 의존성 규칙은 [dependencies.md](./dependencies.md) 참조.

---

## common/ (12개) — 기반 계층, 공용 컴포넌트 5종 + 코어 데이터모델

### 공용 컴포넌트 5종 (CLAUDE.md 강제 규칙 4 — 1회 구현, 중복 금지)

| # | 컴포넌트 | 파일 | 책임 |
|---|---|---|---|
| ① | pyramid | `pyramid.py` | Burt-Adelson Laplacian 피라미드 (5×5 `[1 4 6 4 1]/16` 커널) build/reconstruct/reduce_once |
| ② | histogram/FOV | `histogram_fov.py` | 히스토그램 산출 + FOV(조사야)/직접노출 검출 |
| ③ | FFT/PSD | `fft_psd.py` | 2D FFT/PSD 기본 연산 (fftshift 중심 정렬) — **@MX:ANCHOR** |
| ④ | robust-stats | `robust_stats.py` | median, MAD→std(×1.4826), robust mean/std — **@MX:ANCHOR** |
| ⑤ | mask-ops | `mask_ops.py` | 마스크 형태학 연산 + 연결요소 + `DefectMorphology` 클래스맵(NORMAL/SINGLE/LINE/CLUSTER) — **@MX:ANCHOR** |

### 코어 데이터모델 및 인프라

| 파일 | 책임 |
|---|---|
| `xframe.py` | `XFrame`(pixel/masks/noise/history), `NoiseModel(alpha,sigma)`, `HistoryEntry`, `MaskFlag` — **@MX:ANCHOR** |
| `calibset.py` | `CalibSet` 스키마, `CalibKind`, `CalibDomain` — **@MX:ANCHOR** |
| `contract.py` | `Params` 컨테이너, `ProcessModule`/`StatefulModule` Protocol, `run_harness` — **@MX:ANCHOR** |
| `io.py` | `load_raw_frame`: 헤더 없는 16-bit raw + JSON 사이드카 → float32 XFrame — **@MX:ANCHOR**, 유일한 raw 진입점 |
| `synth_calibset.py` | `make_synthetic_calibset`: 스키마 유효 합성 CalibSet 팩토리 (GUI/테스트용; 패키징 편의상 common/에 배치) |
| `equivalence.py` | TC-021 구조적 XFrame 필드 diff (골든/최적화/FPGA 스왑 비교), `INTEGER_PATH_STAGES` |
| `__init__.py` | 패키지 마커 |

---

## modules/ (14개) — 처리 계층, 수평 독립 필터

모든 처리 파일은 `process(XFrame, CalibSet, Params) -> XFrame` 계약을 노출한다(예외: lag는 stateful, 아래 참조).

### WP1 — offset/gain/defect (T2, SWR-101~304)

| 파일 | SWR | 책임 |
|---|---|---|
| `offset.py` | SWR-101~104 | dark 감산(I−O), clamp |
| `gain.py` | SWR-201~204 | flat-field 보정(I·G), 16-bit clamp, out-of-range → `DEFECT` 마스크 |
| `defect.py` | SWR-301~304 | 결함맵 기반 보간, `INTERPOLATION` 마스크 표기 |

### WP2 — lag (T4, SWR-401~404)

| 파일 | 책임 |
|---|---|
| `lag.py` | `LagCorrector.process` — 지수합(M=3~4) 상태변수 재귀. **stateful 예외(SWR-000-7)**, XFrame 직렬화로 시퀀스 간 상태 전달 |

### WP3 — line noise (T3, SWR-501~504)

| 파일 | 책임 |
|---|---|
| `line_noise.py` | row/col 밴딩 억제. reference 부재 시 고역통과 프로파일 감산, reference 존재 시 k·MAD 경로 |

### WP4 — saturation/geometry (T3, SWR-601~603)

| 파일 | 책임 |
|---|---|
| `saturation.py` | `SATURATION` 마스크 소비, `SATURATION_BAND` 팽창, **값 복원 없음**(SWR-602) |
| `geometry.py` | 다항 왜곡보정 역변위장 + 스플라인 보간. EV-106 미만 시 항등 통과 |

### WP5 — VST+BM3D denoise (T5, SWR-701~706)

| 파일 | 책임 |
|---|---|
| `denoise.py` | GAT(VST) → 2단계 BM3D → exact unbiased inverse(LUT), `CalibSet(NOISE)` 소비, `XFrame.noise` 갱신 |

### WP6 — MSE/DRC (T6, SWR-801~805)

| 파일 | 책임 |
|---|---|
| `mse.py` | Laplacian 피라미드(L=7) 다중스케일 강조 + 노이즈게이트 밴드 변조 + DRC(power law+선형 컷오프) + 백분위 정규화 |

### WP7 — 자동윈도우/GSDF (T6, SWR-901~903)

| 파일 | 책임 |
|---|---|
| `window.py` | 조사야/직접노출 분리 → VOI 3단계 윈도잉 → DICOM PS3.14 GSDF JND LUT |

### WP8 — grid line suppression (T7, SWR-1001~1006)

| 파일 | 책임 |
|---|---|
| `grid.py` | **관측 스펙트럼 피크 직접 탐색**(aliasing 전제, 명목 grid 주파수 금지) → 1D Gaussian notch. `CalibSet(OTHER)` 소비, 미검출 시 무처리 통과 |

### WP9 — kernel virtual grid (T8, SWR-1101~1103)

| 파일 | 책임 |
|---|---|
| `virtual_grid.py` | SKS 산란추정(×8 다운샘플 고정소수점, dual-Gaussian) + 감산. `CalibSet(SCATTER)` 소비. ⚠P 특허 대조 플래그 유지 |

### 인프라

| 파일 | 책임 |
|---|---|
| `registry.py` | `default_registry()` — 스테이지명→`ProcessModule` 매핑. lag는 항상 `LagCorrector()` fresh 인스턴스 생성. **modules/ 내에서 모든 모듈을 import하는 유일한 파일** |
| `__init__.py` | 패키지 마커 |

### 처리 모듈이 없는 WP

WP10(NDT)과 티어/동일성 프레임(T10)은 `modules/`에 처리 모듈을 두지 않는다. NDT는 `metrics/ndt.py`(지표 산출), 티어는 `pipeline/tier.py`(게이팅)에 구현된다.

---

## pipeline/ (4개) — 오케스트레이션 계층

| 파일 | 책임 |
|---|---|
| `orchestrator.py` | **@MX:ANCHOR** — `run_pipeline`(유일한 모듈 조합 권한), `CANONICAL_ORDER`, `PipelineDefinition`(subsequence 검증), `_calibration_gate`, `calib_kind_for_stage`. 모듈을 정적 import하지 않고 `registry` 매개변수로 주입받음 |
| `sequence.py` | `run_sequence` — 연속 캡처마다 `run_pipeline` 래핑, lag 상태 스레딩, 시퀀스별 fresh-registry 리셋 + forward-bias(FB) 트리거 핸드셰이크(SWR-404) |
| `tier.py` | `decide_tier`/`select_pipeline`/`run_tier`/`time_tier` — 하드웨어 연산능력 티어 게이팅(SWR-1301). 주입된 `TierRule` 정책에 따른 강제 다운그레이드 전용 |
| `__init__.py` | 패키지 마커 |

---

## metrics/ (12개) — 지표 산출 엔진, `MetricResult` 공통 반환

| 파일 | 책임 |
|---|---|
| `mtf.py` | MTF — edge법 자동각도추정 → oversampled ESF → LSF → FFT → presampled MTF(lp/mm) |
| `nps.py` | NPS/NNPS — 256² half-overlap ROI → detrend → 2D-FFT 앙상블 → 1D축. NNPS=NPS/signal² |
| `dqe.py` | DQE(f)=MTF²/(q·Ka·NNPS), IEC 62220-1. **@MX:WARN** — 측정프로토콜 §1.4 차원 불일치 플래그(issue #2) |
| `lag.py` | first-frame lag(%), ghost CNR (ASTM E2597) |
| `lag_irf.py` | (오프라인 빌더) `CalibSet(LAG)`: ≥2 다중노출 step response → 지수합 IRF(a_i, b_i) 피팅 |
| `defect_stats.py` | bad-pixel 7분류(ASTM E2597). noisy = temporal-std > 6×median |
| `defect_map.py` | (오프라인 빌더) `CalibSet(DEFECT)`: `defect_stats` + 공간 형태학 → class_map |
| `noise_model.py` | (오프라인 빌더) `CalibSet(NOISE)`: var = α·mean + σ² 선형회귀(다중선량 flat) |
| `scatter_kernel.py` | (오프라인 빌더) `CalibSet(SCATTER)`: dual-Gaussian 산란 PSF vs 두께/kV |
| `ndt.py` | duplex-wire SRb(ISO 20% dip 자동판독), SNRn=SNR×88.6µm/SRb |
| `result.py` | **@MX:ANCHOR** — `MetricResult` 공통 컨테이너 |
| `__init__.py` | 패키지 마커 |

---

## apps/gui/ (14개) — qtpy → PySide6 + pyqtgraph (napari는 Phase-0에서 기각)

| 파일 | 책임 |
|---|---|
| `app.py` | **@MX:ANCHOR** — `MainWindow`(+`CompareDisplay`), 유일한 실행 애플리케이션. 3탭(module/pipeline/metrics) 비교뷰어, 백그라운드 `CallableWorker` 스레드 |
| `config.py` | GUI 전용 [T] 임계값(W/L latency, cold-start, RSS, LRU cap) |
| `io_panel.py` | 파일선택 + `guard_output_path` 쓰기 초크포인트 — **@MX:ANCHOR** |
| `export.py` | `export_frame`/`import_frame` — XFrame 왕복 직렬화 |
| `layers.py` | pyqtgraph input/output/diff/mask-overlay 레이어 — **@MX:ANCHOR** |
| `module_panel.py` | `run_module` — 단일 모듈 실행 → 입출력 XFrame 쌍 — **@MX:ANCHOR** |
| `pipeline_panel.py` | `run_partial_pipeline` — 부분/전체 CANONICAL_ORDER 스테이지별 before/after |
| `metrics_panel.py` | `plot_mtf`/`recompute_mtf_for_roi` (GUI는 지표를 직접 계산하지 않고 metrics/ 위임) |
| `history_panel.py` | 처리 이력(HistoryEntry 체인) 표시 |
| `probe.py` | hover 픽셀 프로브 — `probe_at`/`scene_pos_to_pixel`/`make_hover_proxy` |
| `worker.py` | `CallableWorker` — off-GUI-thread 실행 래퍼 + progress + cancel |
| `help_dialog.py` | 사용법 도움말 QDialog + `ABOUT_TEXT` |
| `__init__.py` (apps/gui) | 패키지 마커 |
| `__init__.py` (apps) | 패키지 마커 |

---

## scripts/ (3개) — 골든 모델 패키지 외부 도구

| 파일 | 책임 |
|---|---|
| `ingest_edrogi.py` | argparse CLI. `images/에드로지16BIT/` 3072² 16-bit raw → `data/edrogi` JSON 사이드카+manifest+256² ROI fixture+비권위 샘플 CalibSet. **[HARD] QUARANTINE**: 배관(plumbing) 테스트 전용, [B]/[T]/[P] 파라미터 유도 금지, `process` 시그니처 없음 |
| `spike_gui_probe.py` | Phase-0 napari 헤드리스 스파이크(SG-1 hover-float, SG-2 W/L≤100ms, SG-3 cold-start≤10s). 골든모델 패키지 외부, import-linter 대상 아님 |
| `__init__.py` | 패키지 마커 |

---

## @MX:ANCHOR 허브 정리 (fan-in 높은 계약 지점)

`common/{xframe, calibset, contract, fft_psd, robust_stats, pyramid, mask_ops, io}`, `pipeline/{orchestrator, sequence, tier}`, `metrics/result`, `apps/gui/{layers, module_panel, io_panel, app}`

## 확인된 예외 사항 (모두 승인됨)

- **lag stateful**: `modules/lag.py`의 `LagCorrector.process`는 순수함수형 원칙의 승인된 예외(SWR-000-7).
- **dqe @MX:WARN**: `metrics/dqe.py`는 측정프로토콜 §1.4 차원 불일치가 플래그되어 있음(issue #2).
- **CalibKind 확장**: `NOISE`, `SCATTER`가 WP5/WP9 지원을 위해 `CalibKind`에 추가됨.
- **GUI 프레임워크 우회**: GUI는 `qtpy` 경유로 PySide6/pyqtgraph에 접근(직접 의존 없음).
- **synth_calibset 배치**: 테스트/GUI 전용이지만 패키징 편의상 `common/`에 위치.
- **WP10/티어 무처리모듈**: NDT와 티어/동일성 프레임은 `modules/`에 대응 처리 모듈이 없음(의도된 설계, 위 "처리 모듈이 없는 WP" 참조).
