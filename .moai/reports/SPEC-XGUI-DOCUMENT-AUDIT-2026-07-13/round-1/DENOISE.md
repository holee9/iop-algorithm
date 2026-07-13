# SPEC Review Report: SPEC-XGUI-DENOISE

Iteration: 1/5
Verdict: PASS (2 minor advisories, no blocking defects)
Overall Score: 0.94

> Reasoning context ignored per M1 Context Isolation. Audit performed against spec.md + golden sources only.

## Must-Pass Results

- [PASS] MP-1 REQ number consistency — 6 REQ groups (INPUT/PARAM/APPLY/VIEW/IO/GUARD), grouped-prefix scheme `REQ-XGUI-DENOISE-{GROUP}-{N}` mirroring SPEC-XSEAM-002's `REQ-XSEAM-{GROUP}-{N}`. Sequential within each group: INPUT 1-3, PARAM 1-3, APPLY 1-3, VIEW 1-3, IO 1-2, GUARD 1-3 (spec.md:L41-74). No gaps, no duplicates.
- [PASS] MP-2 EARS compliance — all 17 REQs match a canonical EARS pattern with English keywords (WHEN/THEN/IF/WHILE) + Korean prose per language policy. Event-Driven (WHEN…THEN): INPUT-1/2, PARAM-1, APPLY-1/2, VIEW-1/2/3, IO-1. Unwanted (IF…THEN): INPUT-3, PARAM-3, APPLY-3, IO-2, GUARD-3. Ubiquitous: PARAM-2 (L50), GUARD-1 (L72). State-Driven (WHILE): GUARD-2 (L73).
- [PASS] MP-3 YAML frontmatter validity — id/version/status/created/updated/author/priority/issue_number/labels present, correct types (spec.md:L2-11). Uses `created`/`updated` (not generic `created_at`) which **correctly mirrors** SPEC-XSEAM-002:L5-6 per the explicit mirroring instruction — not a defect.
- [PASS] MP-4 language neutrality — N/A for 16-language tooling; single-language Python golden project. C-09 language-neutral seam (IXdetEngine `run_pipeline` mirror, SPEC-XSEAM-002 CONTRACT-6) is referenced accurately, not hardcoded to any tool.

## Golden-Source Fidelity (adversarial cross-check — every sampled citation verified accurate)

| SPEC claim | Golden evidence | Verdict |
|---|---|---|
| `process(frame, calib, params)->XFrame` @denoise.py:616, stateless | denoise.py:616 confirmed | ACCURATE |
| `required_params` @denoise.py:92, selector-dependent | denoise.py:92-114 | ACCURATE |
| Common Params keys `denoise_strength_ks`/`_inv_lut_lambda_max`/`_inv_lut_nodes`/`_inv_lut_gh_nodes` | P_STRENGTH/P_LUT_* @denoise.py:54,65-67,106 | ACCURATE (string values match) |
| BM3D keys (8): block/step/max_match/search_window/lambda3d/kaiser_beta/match_tau_hard/match_tau_wiener | denoise.py:56-63,108-111 | ACCURATE |
| NLM keys: nlm_h/nlm_patch/nlm_window | denoise.py:69-71,113 | ACCURATE |
| `NOISE_PAYLOAD_KEYS=("alpha","sigma")` @calibset.py:90-92 | confirmed | ACCURATE |
| `_resolve_noise` refuses absent/degenerate, never NoiseModel(0,0) fallback (SWR-000-5) | denoise.py:129-148 | ACCURATE |
| `_KIND_BY_STAGE["denoise"]="noise"`, `calib_kind_for_stage` | orchestrator.py:157,165-175 | ACCURATE |
| CANONICAL_ORDER …virtual_grid→denoise→mse→window→post | orchestrator.py:62-77 | ACCURATE |
| GAT radicand<0 clamp to 0; exact-inverse LUT only, no asymptotic (f/2)² | denoise.py:160-164,194 | ACCURATE |
| Saturation value preservation (SWR-602) | denoise.py:610-612 | ACCURATE |
| Output XFrame.noise write + HistoryEntry.extra {method,k_s,clamp_rate,resolved_alpha,resolved_sigma} | denoise.py:653,659-665 | ACCURATE |
| `make_synthetic_calibset(NOISE)` empty payload → hard fail | synth_calibset.py:24,48 (data={}) | ACCURATE |
| `fit_noise_model` needs ≥2 dose levels | noise_model.py:78,99 | ACCURATE |
| `run_module`/`run_partial_pipeline`/`load_raw_frame`/`guard_output_path`/`DataWriteRejectedError`/`compute_snr` | module_panel.py:38, pipeline_panel.py:104, io.py:35, io_panel.py:27/23, ndt.py:129 | ACCURATE |
| calib_map override "when absent, not always" @pipeline_panel.py:118 | verbatim match | ACCURATE |
| NPS/NNPS from metrics/nps.py | nps.py:83 compute_nps returns nps+nnps | ACCURATE |
| foundation G-1~G-9, §2 group4/5, §3 save, §4 open | foundation.md:28-36,77-93,142-160 | ACCURATE |

No invented Params/CalibSet keys, no wrong formulas, no fabricated citations detected.

## Category Scores (rubric-anchored)

| Dimension | Score | Band | Evidence |
|-----------|-------|------|----------|
| Clarity | 0.95 | 1.0 band | Every REQ single-interpretation; golden call sites disambiguate intent (L43-74). |
| Completeness | 0.90 | 0.75 band | HISTORY/Env/Requirements/Exclusions/결정필요 all present; acceptance.md + plan.md are referenced-but-absent siblings (Glob: only spec.md exists). |
| Testability | 0.92 | 0.75-1.0 | THEN clauses cite concrete golden errors (DenoiseError, DataWriteRejectedError) and recorded diagnostics; "sanity" operationalized as 유한·비퇴화·오류무발생 (L73). |
| Traceability | 0.95 | 1.0 band | Each REQ traces to SWR/golden line + foundation G-x + XSEAM-002 CONTRACT/COMPOSE; consistent. |

## Defects Found

D1. spec.md:L44,L73 (INPUT-2 path (b) / GUARD-2) — Minor. The "채워진 NOISE CalibSet"(declared scalar α,σ) procurement path has **no golden producer**: `fit_noise_model` requires ≥2 dose stacks (noise_model.py:99) and `make_synthetic_calibset(NOISE)` yields an empty payload (synth_calibset.py:48). Constructing `CalibSet(data={"alpha":..,"sigma":..})` inline is feasible but unspecified — and it raises which-layer question (a `common/` helper vs authoring the payload inside `apps/gui`, brushing C-09/C-11). 결정필요 2 frames this as a UI-choice but does not name the missing scalar-path builder. Pin the construction layer in run/acceptance. Severity: minor.

D2. spec.md:L63 (VIEW-3) — Minor. NPS/NNPS is delegated to `metrics/nps.py::compute_nps`, which computes "from a **stack** of uniform frames" (nps.py:90). A single denoise before/after pair is not a frame stack; the single-frame/ROI-ensemble convention for a before/after NPS panel is unspecified. Feasibility should be pinned (SNR via compute_snr is single-frame-OK; NPS is not). Severity: minor.

D3 (note, not a defect). Frontmatter `created`/`updated` vs generic `created_at`: correct per SPEC-XSEAM-002 mirroring instruction. Flagged only to preempt a false-positive downgrade.

## Chain-of-Verification Pass

Second-look findings: none new. Re-verified by re-reading: (a) all 17 REQ EARS patterns end-to-end (no skim) — all conform; (b) REQ numbering per group — no gap/dup; (c) Exclusions section (L78-84) — 6 specific entries (no golden edit / no bias-vs-λ golden / no asymptotic inverse / no DSP reimpl / no canonical numeric validation under QUARANTINE / no new stage-CalibKind / no save-schema expansion), all concrete; (d) contradiction sweep — INPUT-3 (reject empty synth) vs GUARD-2 (use *filled* synth) are consistent (empty forbidden, filled allowed); APPLY-2 override vs REQ-VIEW-CORE-3 "substitution when absent" consistent; (e) constraint sweep — C-09/C-11/C-20/QUARANTINE/SWR-000-2/-5, golden-FROZEN, save format, folder browser, seam mirror all present and correctly cited. No missed critical/major defect.

## Recommendation

PASS. Must-pass criteria all satisfied with concrete evidence: MP-1 (grouped sequential, L41-74), MP-2 (17/17 EARS), MP-3 (frontmatter L2-11 mirroring XSEAM-002), MP-4 (N/A single-language). Golden fidelity is exceptionally high — every sampled Params key, CalibSet key, error type, formula constraint, and line citation verified accurate against denoise.py/orchestrator.py/calibset.py/synth_calibset.py/noise_model.py/GUI infra/foundation.md. Address the 2 minor advisories (D1 populated-NOISE-CalibSet construction layer; D2 NPS single-frame vs stack feasibility) during acceptance.md authoring — neither blocks run.
