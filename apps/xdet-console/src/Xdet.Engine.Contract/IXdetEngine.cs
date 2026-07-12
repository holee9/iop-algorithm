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
    /// Compute the signed (after - before) diff preview ENGINE-side (numpy, adapter) for a
    /// before/after pair the UI already holds but whose own seam call carries no diff — the
    /// synthetic Offset tab (input vs <see cref="RunOffset"/> output). Returns the diff in
    /// transport form plus max|diff|. Pure element-wise subtraction: the UI never computes
    /// the diff itself (SPEC-VIEWER-001 C-09/C-11), it only renders <see cref="DiffPreviewResult.Diff"/>
    /// with a 0-centered diverging colormap over ±<see cref="DiffPreviewResult.MaxAbsDiff"/>.
    /// </summary>
    DiffPreviewResult ComputeDiffPreview(FrameData before, FrameData after);

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

    /// <summary>
    /// [HARD] QUARANTINE plumbing/sanity ONLY (SPEC-REALDATA-001). Run the golden
    /// OFFSET / GAIN / DEFECT stage (<paramref name="kind"/> ∈ {"offset","gain","defect"})
    /// on the REAL edrogi 아크릴 acquisition frame using the REAL CalibSet built from the
    /// registered calibration source — mirroring <c>tests/test_tc_realdata_arms.py</c>
    /// (<c>test_tc_001/002/003</c>) EXACTLY:
    /// <list type="bullet">
    ///   <item>signal := first non-<c>_result</c> raw under <c>아크릴</c> (via <c>_load_full</c>);</item>
    ///   <item>offset: <c>build_offset_calibset(_load_full("16bit cal/MasterDark.raw"))</c> -&gt; <c>modules.offset.process</c>;</item>
    ///   <item>gain:   <c>build_gain_calibset(_load_full("16bit cal/CalSet_19008.raw"))</c> -&gt; <c>modules.gain.process</c>;</item>
    ///   <item>defect: <c>build_defect_calibset(_load_full("16bit cal/BPM.raw"))</c> -&gt; <c>modules.defect.process</c>;</item>
    /// </list>
    /// each with <c>tests.modules.phantoms.corrections.corr_params()</c>. Because the
    /// calib is REAL, the correction is MEANINGFUL (output differs from input,
    /// <see cref="RegisteredArmResult.MaxAbsChangeFromInput"/> &gt; 0) — unlike the synthetic
    /// zero-dark no-op. Returns the sanity verdict (shape/dtype/finite/std) + engine-computed
    /// stats (min/max/mean + max|delta|) + engine-downsampled ~512x512 before/after previews.
    /// The corrected output is ALSO held as adapter state so <see cref="SaveProcessedFrame"/>
    /// can persist it (C-20 guard intact). When the sample tree is absent, returns a result
    /// with <see cref="RegisteredArmResult.ImagesPresent"/> == false (no exception). All DSP +
    /// downsampling happen engine-side (SPEC-VIEWER-001). NON-AUTHORITATIVE — never a numeric golden.
    /// </summary>
    RegisteredArmResult RunRegisteredArm(string kind);

    // -- Viewer P0 loop: open arbitrary image -> process -> save (usable) ------
    // The adapter holds the loaded / processed frame as state ACROSS these three
    // calls (LoadRawFrame sets it, ProcessLoadedFrame consumes+updates it,
    // SaveProcessedFrame persists it). All DSP + downsampling happen engine-side.

    /// <summary>
    /// Load an ARBITRARY 16-bit raw test image via the golden and hold it as adapter
    /// state. When a <c>&lt;name&gt;.json</c> sidecar exists next to the raw, the golden
    /// <c>common.io.load_raw_frame</c> is used (the sidecar's <c>resolution</c> governs
    /// the shape). Otherwise the shape is inferred from the payload: element count =
    /// bytes/2 (uint16); if <paramref name="rows"/>*<paramref name="cols"/> is supplied
    /// and matches it is used, else a perfect square (edrogi 3072x3072) then 3072x2560
    /// is tried; if none matches a clear error verdict is returned (no crash). Real
    /// images are QUARANTINE sanity — labeled, never a numeric golden. Returns a DTO
    /// with stats (shape/dtype/min/max/mean/finite) + an engine-downsampled ~512x512
    /// preview (the UI does zero DSP).
    /// </summary>
    LoadedFrameInfo LoadRawFrame(string path, int rows = 0, int cols = 0);

    /// <summary>
    /// Run the golden OFFSET stage (<c>modules.offset.process</c>) on the frame most
    /// recently loaded by <see cref="LoadRawFrame"/>, using a synthetic OFFSET CalibSet
    /// (<c>make_synthetic_calibset(shape, calib_kind_for_stage("offset"))</c> populated
    /// with a ZERO dark map) + default Params, and hold the output as adapter state.
    /// Returns before/after ~512x512 previews + engine-computed output stats. Returns a
    /// clean failure verdict (no crash) when no frame is loaded.
    /// </summary>
    ProcessedFrameInfo ProcessLoadedFrame();

    /// <summary>
    /// Persist the frame most recently produced by <see cref="ProcessLoadedFrame"/> to
    /// <paramref name="outputPath"/>. FIRST applies the replicated C-20 guard (refuse any
    /// path under <c>&lt;repo&gt;/data</c>), then writes the npz (pixel float32 + masks
    /// uint8) + JSON sidecar (noise / validation_mode / history / array_keys) in the
    /// <c>apps.gui.export.export_frame</c> schema. Returns the written path + success, or
    /// a clean guard-rejected / failed verdict (never throws).
    /// </summary>
    SaveResult SaveProcessedFrame(string outputPath);
}
