namespace Xdet.Engine.Contract;

/// <summary>
/// The durable XDET engine seam (SPEC-XSEAM-001). An engine transports a
/// <see cref="FrameData"/> through a golden processing stage / metric and returns
/// the result in the same transport form. This interface is Python-free so a
/// future native (C++/FPGA) engine can implement the identical contract; the
/// P1.5 implementation (<c>PythonNetXdetEngine</c>) fulfils it by calling the
/// frozen Python golden in-process via pythonnet.
/// </summary>
public interface IXdetEngine
{
    /// <summary>
    /// Run the offset-correction stage (dark subtraction + negative clamp,
    /// SWR-101~104) on <paramref name="input"/> and return the corrected frame.
    /// </summary>
    FrameData RunOffset(FrameData input, OffsetCalibData calib, OffsetParams parameters);

    /// <summary>
    /// Compute the presampled MTF (edge method, measurement protocol §1.2) of the
    /// edge-slab ROI carried by <paramref name="input"/>.
    /// </summary>
    MtfResult ComputeMtf(FrameData input, MtfParams parameters);

    /// <summary>
    /// Run a minimal valid golden pipeline — the <c>offset -&gt; gain</c> subsequence of
    /// the orchestrator's <c>CANONICAL_ORDER</c> — over <paramref name="input"/> through
    /// <c>pipeline.orchestrator.run_pipeline</c>. Composition, canonical stage order and
    /// the CalibSet entry gate are all decided by the golden orchestrator, never here.
    /// Returns the transported input/output frames plus engine-computed stage and
    /// statistic info (<see cref="PipelineResult"/>). Both stages are real transforming
    /// modules (offset subtracts the dark map; gain multiplies by the flat-field map),
    /// so the output genuinely differs from the input.
    /// </summary>
    PipelineResult RunPipeline(
        FrameData input,
        OffsetCalibData offsetCalib,
        OffsetParams offsetParams,
        GainCalibData gainCalib,
        GainParams gainParams);

    /// <summary>
    /// [HARD] QUARANTINE plumbing/sanity ONLY (SPEC-REALDATA-001). Run the golden OFFSET
    /// stage on a REAL edrogi acquisition frame to prove the pipeline EXECUTES on a real
    /// 3072x3072 frame and yields finite, non-degenerate output — this is NOT a numeric
    /// golden (no tolerance is fitted; no output is a reference). Reuses the frozen
    /// realdata sample arm verbatim: <c>scripts.ingest_edrogi.require_edrogi</c> /
    /// <c>_load_full</c> / <c>build_offset_calibset</c> plus <c>modules.offset.process</c>,
    /// then the <c>_assert_sane</c> checks (shape (3072,3072) / float32 / finite / std&gt;0).
    /// When the sample tree is absent, returns a <see cref="RealImageSanityResult"/> with
    /// <see cref="RealImageSanityResult.ImagesPresent"/> == false (no exception). All stats
    /// and the downsampled before/after previews are computed engine-side (SPEC-VIEWER-001:
    /// the UI does no DSP and no downsampling).
    /// </summary>
    RealImageSanityResult RunRealImageOffsetSanity();
}
