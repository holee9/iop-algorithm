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
}
