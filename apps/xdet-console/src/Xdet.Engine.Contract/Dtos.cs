namespace Xdet.Engine.Contract;

// SPEC-XSEAM-001 P1.5 thin-slice seam DTOs. Deliberately built only from CLR
// primitives + arrays so the contract carries no pythonnet (or any golden-model)
// type. A NativeXdetEngine must be able to produce/consume these unchanged.

/// <summary>
/// A frame in transport form: row-major float32 pixels plus the mask stack
/// (uint8 bit-flags) and the (alpha, sigma) noise model. Mirrors the load-bearing
/// state of the Python golden <c>XFrame</c> that the fidelity comparator inspects
/// (pixel / masks / noise); history is intentionally omitted (not compared by
/// <c>common.equivalence.diff_frames</c>).
/// </summary>
public sealed record FrameData(
    float[] Pixels,
    int Rows,
    int Cols,
    byte[] Masks,
    double NoiseAlpha,
    double NoiseSigma)
{
    /// <summary>Fresh frame: zeroed masks, zero noise model.</summary>
    public static FrameData FromPixels(float[] pixels, int rows, int cols)
        => new(pixels, rows, cols, new byte[pixels.Length], 0.0, 0.0);
}

/// <summary>CalibSet(OFFSET) payload: the static dark map O(x,y) (<c>O_map</c>).</summary>
public sealed record OffsetCalibData(float[] OffsetMap, int Rows, int Cols);

/// <summary>CalibSet(GAIN) payload: the single-point flat-field gain map G(x,y) (<c>G_map</c>).</summary>
public sealed record GainCalibData(float[] GainMap, int Rows, int Cols);

/// <summary>
/// Offset-stage parameters. Only the required raw saturation threshold S_th
/// (<c>raw_saturation_threshold</c>, SWR-601 [B]); the golden module refuses a
/// silent in-module default (SWR-000-5).
/// </summary>
public sealed record OffsetParams(double RawSaturationThreshold);

/// <summary>
/// Gain-stage validity bounds (<c>gain_min</c>/<c>gain_max</c>, SWR-201~204 [T]).
/// Externalized like every other tunable; the golden gain module refuses a silent
/// in-module default (SWR-000-5). Defaults mirror the golden test bounds
/// (<c>tests.modules.phantoms.corrections</c>: 0.5 .. 2.0).
/// </summary>
public sealed record GainParams(double GainMin = 0.5, double GainMax = 2.0);

/// <summary>
/// MTF-stage parameters (measurement protocol phantom defaults). All values are
/// externalized (REQ-METRICS-CORE-4); none is baked into the golden.
/// </summary>
public sealed record MtfParams(
    double PixelPitchMm = 0.14,
    int Oversample = 4,
    double AngleMinDeg = 1.5,
    double AngleMaxDeg = 3.0,
    double AngleMarginDeg = 0.2,
    string Direction = "vertical");

/// <summary>Presampled-MTF result: the frequency axis (lp/mm) and the MTF curve.</summary>
public sealed record MtfResult(
    double[] Frequencies,
    double[] Mtf,
    double EdgeAngleDeg,
    double NyquistLpmm,
    double MtfAtNyquist);

/// <summary>
/// Result of the golden <c>common.equivalence.diff_frames</c> comparator over two
/// candidate outputs. <see cref="StructurallyEqual"/> mirrors the Python property.
/// </summary>
public sealed record EquivalenceResult(
    bool PixelEqual,
    bool MasksEqual,
    bool NoiseEqual,
    double MaxPixelAbsDiff)
{
    public bool StructurallyEqual => PixelEqual && MasksEqual && NoiseEqual;
}

/// <summary>
/// Slanted-edge phantom spec forwarded to the golden generator
/// (<c>tests.metrics.phantoms.generators.make_slanted_edge</c>). No seed field:
/// the analytic (erf) edge is rendered noise-free and fully deterministic.
/// </summary>
public sealed record EdgePhantomSpec(
    int Rows = 128,
    int Cols = 128,
    double AngleDeg = 2.0,
    double SigmaPx = 0.6,
    double PitchMm = 0.14,
    double Low = 1000.0,
    double High = 5000.0);

/// <summary>
/// Result of a minimal valid golden pipeline run (SPEC-XSEAM-001 pipeline seam):
/// the ordered subset <c>offset -&gt; gain</c> of <c>CANONICAL_ORDER</c> executed by
/// <c>pipeline.orchestrator.run_pipeline</c> (the sole composition authority,
/// SWR-000-2/-8). Carries the transport-form <see cref="Input"/> and
/// <see cref="Output"/> frames plus stage/statistic info the ENGINE computed
/// (numpy over the golden output) — the UI performs no DSP (SPEC-VIEWER-001).
/// <see cref="StagesRun"/> is read from the golden history chain (module_name per
/// stage); <see cref="MaxAbsChangeFromInput"/> is the golden-computed proof the
/// pipeline actually transformed the input.
///
/// <see cref="DiffPreview"/> is the ENGINE-computed signed (output - input) diff
/// (numpy, adapter-side) in transport form; the UI renders it with a 0-centered
/// diverging colormap and never computes the subtraction itself (SPEC-VIEWER-001
/// C-09/C-11). <see cref="MaxAbsDiff"/> is max|diff| over that preview — the
/// symmetric ±range for the diff colormap.
/// </summary>
public sealed record PipelineResult(
    FrameData Input,
    FrameData Output,
    string[] StagesRun,
    double OutputMin,
    double OutputMax,
    double OutputMean,
    double MaxAbsChangeFromInput,
    FrameData? DiffPreview,
    double MaxAbsDiff);

/// <summary>
/// Result of the QUARANTINE plumbing/sanity run of the golden OFFSET stage on a REAL
/// edrogi acquisition frame (SPEC-REALDATA-001). [HARD] NON-AUTHORITATIVE: this is a
/// "does the pipeline EXECUTE on a real 3072x3072 frame and yield finite, non-degenerate
/// output" check ONLY — never a numeric golden. No tolerance is fitted and neither the
/// output nor any preview is a numeric reference. Every value here is computed ENGINE-side
/// (numpy over the golden output) and the previews are downsampled ENGINE-side; the UI
/// performs no DSP and no downsampling (SPEC-VIEWER-001).
///
/// <see cref="BeforePreview"/> / <see cref="AfterPreview"/> are engine-downsampled
/// (~512x512 block-mean) heatmap previews in the same transport form as any other frame
/// (float32 buffer + shape); dtype is implicitly float32. When the sample tree is absent
/// (<see cref="ImagesPresent"/> == false) the previews are null and the numeric fields are
/// zero — the engine returns cleanly rather than throwing.
/// </summary>
public sealed record RealImageSanityResult(
    bool ImagesPresent,
    bool Sane,
    string Status,
    string SignalName,
    int Rows,
    int Cols,
    string Dtype,
    bool Finite,
    double Std,
    double Min,
    double Max,
    double Mean,
    FrameData? BeforePreview,
    FrameData? AfterPreview)
{
    /// <summary>The sample acquisition tree is absent — a clean, non-throwing verdict.</summary>
    public static RealImageSanityResult Absent(string edrogiRoot)
        => new(false, false,
               "QUARANTINE 배관/sanity (수치 golden 아님): real images absent — " + edrogiRoot,
               "", 0, 0, "", false, 0.0, 0.0, 0.0, 0.0, null, null);
}

/// <summary>
/// Result of a QUARANTINE registered-arm run (SPEC-REALDATA-001, feat/xseam-ui-expand):
/// the golden OFFSET / GAIN / DEFECT stage executed on the REAL edrogi 아크릴 acquisition
/// frame using the REAL CalibSet built from the registered calibration source
/// (MasterDark / CalSet_19008 / BPM), mirroring <c>tests/test_tc_realdata_arms.py</c>
/// (<c>test_tc_001/002/003</c>) EXACTLY. [HARD] NON-AUTHORITATIVE plumbing/sanity: proves
/// the stage EXECUTES on a real 3072x3072 frame with its real calib and yields finite,
/// non-degenerate output — never a numeric golden (no tolerance fitted, no reference).
///
/// Because the calib is REAL (offset subtracts the real dark, gain scales by the real
/// flat-field, defect interpolates the real bad pixels), the correction is MEANINGFUL:
/// <see cref="MaxAbsChangeFromInput"/> (engine-computed max|output-input| over the full-res
/// golden output) is &gt; 0 — unlike a synthetic zero-dark no-op. Every value here is
/// computed ENGINE-side (numpy over the golden output); the previews are downsampled
/// ENGINE-side. The UI performs no DSP and no downsampling (SPEC-VIEWER-001). When the
/// sample tree is absent (<see cref="ImagesPresent"/> == false) the previews are null and
/// the numeric fields are zero — the engine returns cleanly rather than throwing.
///
/// <see cref="DiffPreview"/> is the ENGINE-computed signed (after - before) diff of the
/// two ~512x512 previews (numpy, adapter-side), in transport form; the UI renders it with
/// a 0-centered diverging colormap and never computes the subtraction itself (C-09/C-11).
/// <see cref="MaxAbsDiff"/> is max|diff| over that preview — the symmetric ±range for the
/// diff colormap (distinct from <see cref="MaxAbsChangeFromInput"/>, the full-res delta).
/// </summary>
public sealed record RegisteredArmResult(
    string Kind,
    string CalibName,
    bool ImagesPresent,
    bool Sane,
    string Status,
    string SignalName,
    int Rows,
    int Cols,
    string Dtype,
    bool Finite,
    double Std,
    double Min,
    double Max,
    double Mean,
    double MaxAbsChangeFromInput,
    FrameData? BeforePreview,
    FrameData? AfterPreview,
    FrameData? DiffPreview,
    double MaxAbsDiff)
{
    /// <summary>The sample acquisition tree is absent — a clean, non-throwing verdict.</summary>
    public static RegisteredArmResult Absent(string kind, string calibName, string edrogiRoot)
        => new(kind, calibName, false, false,
               $"QUARANTINE 배관/sanity (수치 golden 아님): real images absent — {edrogiRoot}",
               "", 0, 0, "", false, 0.0, 0.0, 0.0, 0.0, 0.0, null, null, null, 0.0);

    /// <summary>A clean, non-throwing arm-failure verdict (e.g. unknown kind, no signal raw).</summary>
    public static RegisteredArmResult Failed(string kind, string calibName, string status)
        => new(kind, calibName, true, false, status, "", 0, 0, "", false,
               0.0, 0.0, 0.0, 0.0, 0.0, null, null, null, 0.0);
}

/// <summary>
/// Result of a QUARANTINE registered MULTI-STAGE pipeline run (SPEC-REALDATA-001,
/// feat/xseam-ui-expand): the golden <c>offset -&gt; gain</c> subsequence of
/// <c>CANONICAL_ORDER</c> executed by <c>pipeline.orchestrator.run_pipeline</c> on the
/// REAL edrogi 아크릴 acquisition frame using a calib_map of the REAL CalibSets built from
/// the registered sources — offset from <c>MasterDark.raw</c> (<c>build_offset_calibset</c>)
/// and gain from the representative <c>CalSet_19008.raw</c> (<c>build_gain_calibset</c>).
/// Both carry panel_id <c>SAMPLE-EDROGI-16BIT</c> so the orchestrator's mutual-panel entry
/// gate passes. Mirrors how <c>tests/pipeline/</c> drives the orchestrator (a subsequence of
/// CANONICAL_ORDER + a validation-mode input frame so per-stage intermediates are preserved,
/// DATA-5). [HARD] NON-AUTHORITATIVE plumbing/sanity: proves the multi-stage chain EXECUTES
/// on a real 3072x3072 frame with real calibs and yields finite, non-degenerate output —
/// never a numeric golden (no tolerance fitted, no reference).
///
/// Because both calibs are REAL, the composed correction is MEANINGFUL:
/// <see cref="MaxAbsChangeFromInput"/> (engine-computed max|output-input| over the full-res
/// golden output) is &gt; 0. <see cref="StagesRun"/> is read from the golden history chain
/// (proving the canonical offset-then-gain order); <see cref="IntermediateCount"/> is the
/// number of per-stage intermediates the orchestrator preserved under validation_mode. Every
/// value here is computed ENGINE-side (numpy over the golden output); the ~512x512 before/after
/// previews and the signed (after - before) <see cref="DiffPreview"/> are computed ENGINE-side
/// (the UI performs no DSP and no downsampling, SPEC-VIEWER-001 C-09/C-11). When the sample
/// tree is absent (<see cref="ImagesPresent"/> == false) the previews are null and the numeric
/// fields are zero — the engine returns cleanly rather than throwing.
/// </summary>
public sealed record RegisteredPipelineResult(
    bool ImagesPresent,
    bool Sane,
    string Status,
    string SignalName,
    string OffsetCalibName,
    string GainCalibName,
    string[] StagesRun,
    int IntermediateCount,
    int Rows,
    int Cols,
    string Dtype,
    bool Finite,
    double Std,
    double OutputMin,
    double OutputMax,
    double OutputMean,
    double MaxAbsChangeFromInput,
    FrameData? BeforePreview,
    FrameData? AfterPreview,
    FrameData? DiffPreview,
    double MaxAbsDiff)
{
    /// <summary>The sample acquisition tree is absent — a clean, non-throwing verdict.</summary>
    public static RegisteredPipelineResult Absent(string edrogiRoot)
        => new(false, false,
               "QUARANTINE 배관/sanity (수치 golden 아님): real images absent — " + edrogiRoot,
               "", "MasterDark.raw", "CalSet_19008.raw", Array.Empty<string>(), 0,
               0, 0, "", false, 0.0, 0.0, 0.0, 0.0, 0.0, null, null, null, 0.0);

    /// <summary>A clean, non-throwing pipeline-failure verdict (e.g. no signal raw, gate refusal).</summary>
    public static RegisteredPipelineResult Failed(string status)
        => new(true, false, status, "", "MasterDark.raw", "CalSet_19008.raw",
               Array.Empty<string>(), 0, 0, 0, "", false,
               0.0, 0.0, 0.0, 0.0, 0.0, null, null, null, 0.0);
}

// -- Viewer P0 loop DTOs (SPEC-XSEAM-001 feat/xseam-ui-expand) ----------------
// The usable algorithm-verification loop: open an arbitrary test image -> process
// it -> view before/after -> save the result. All three DTOs are CLR-only (no
// pythonnet types) so a future native (C++) engine implements the same contract.
// Every stat + downsampled preview is computed ENGINE-side; the UI does no DSP
// and no downsampling (SPEC-VIEWER-001).

/// <summary>
/// Result of loading an ARBITRARY test image via the seam (Viewer P0 load step).
/// [HARD] QUARANTINE sanity: a loaded real acquisition is labeled, NEVER a numeric
/// golden (no tolerance/reference). <see cref="Preview"/> is an engine-downsampled
/// (~512x512 block-mean) heatmap preview in transport form; on failure (unreadable
/// file / unresolvable shape) <see cref="Loaded"/> is false, <see cref="Preview"/>
/// is null, and <see cref="Status"/> carries a clear message (the engine never
/// throws for a bad path/shape).
/// </summary>
public sealed record LoadedFrameInfo(
    bool Loaded,
    string Status,
    string SourceName,
    int Rows,
    int Cols,
    string Dtype,
    bool Finite,
    double Min,
    double Max,
    double Mean,
    FrameData? Preview)
{
    /// <summary>A clean, non-throwing load-failure verdict.</summary>
    public static LoadedFrameInfo Failed(string status)
        => new(false, status, "", 0, 0, "", false, 0.0, 0.0, 0.0, null);
}

/// <summary>
/// Result of processing the loaded frame through the golden OFFSET stage (Viewer P0
/// process step). The stage runs <c>modules.offset.process</c> with a synthetic
/// OFFSET CalibSet (<c>common.synth_calibset.make_synthetic_calibset</c>, kind via
/// <c>pipeline.orchestrator.calib_kind_for_stage</c>) carrying a ZERO dark map — no
/// measured calibration exists for an arbitrary loaded frame, so the golden offset
/// applies its subtract/clamp/saturation contract without inventing a fitted
/// correction. All stats + the ~512x512 before/after previews are engine-computed.
/// On failure <see cref="Processed"/> is false and <see cref="Status"/> explains why.
///
/// <see cref="DiffPreview"/> is the ENGINE-computed signed (after - before) diff of the
/// two ~512x512 previews (numpy, adapter-side), in transport form; the UI renders it with
/// a 0-centered diverging colormap and computes no subtraction itself (C-09/C-11).
/// <see cref="MaxAbsDiff"/> is max|diff| over that preview — the symmetric ±diff range.
/// </summary>
public sealed record ProcessedFrameInfo(
    bool Processed,
    string Status,
    string[] StagesRun,
    double OutputMin,
    double OutputMax,
    double OutputMean,
    double MaxAbsChangeFromInput,
    FrameData? BeforePreview,
    FrameData? AfterPreview,
    FrameData? DiffPreview,
    double MaxAbsDiff)
{
    /// <summary>A clean, non-throwing process-failure verdict.</summary>
    public static ProcessedFrameInfo Failed(string status)
        => new(false, status, Array.Empty<string>(), 0.0, 0.0, 0.0, 0.0, null, null, null, 0.0);
}

/// <summary>
/// Result of the ENGINE-side (after - before) diff preview computed on demand by
/// <see cref="IXdetEngine.ComputeDiffPreview"/> for a before/after pair the UI already
/// holds but whose seam call does not itself carry a diff (the synthetic Offset tab:
/// input vs <see cref="IXdetEngine.RunOffset"/> output). The subtraction is numpy,
/// adapter-side (SPEC-VIEWER-001 C-09/C-11: the UI renders <see cref="Diff"/>, never
/// computes it). <see cref="MaxAbsDiff"/> is max|diff| — the symmetric ±diff range.
/// </summary>
public sealed record DiffPreviewResult(
    FrameData Diff,
    double MaxAbsDiff);

/// <summary>
/// Result of saving the processed frame (Viewer P0 save step). The engine FIRST
/// applies the replicated C-20 write guard (mirror of
/// <c>apps.gui.io_panel.guard_output_path</c>: refuse any path resolving under
/// <c>&lt;repo&gt;/data</c>) and only then writes the npz + JSON sidecar
/// (<c>apps.gui.export.export_frame</c> schema). On a guard rejection
/// <see cref="GuardRejected"/> is true, <see cref="Success"/> is false, and NOTHING
/// is written. The seam never throws for a rejected/failed save.
/// </summary>
public sealed record SaveResult(
    bool Success,
    bool GuardRejected,
    string Path,
    string Message);
