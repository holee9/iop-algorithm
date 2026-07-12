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
/// </summary>
public sealed record PipelineResult(
    FrameData Input,
    FrameData Output,
    string[] StagesRun,
    double OutputMin,
    double OutputMax,
    double OutputMean,
    double MaxAbsChangeFromInput);

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
    FrameData? AfterPreview)
{
    /// <summary>A clean, non-throwing process-failure verdict.</summary>
    public static ProcessedFrameInfo Failed(string status)
        => new(false, status, Array.Empty<string>(), 0.0, 0.0, 0.0, 0.0, null, null);
}

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
