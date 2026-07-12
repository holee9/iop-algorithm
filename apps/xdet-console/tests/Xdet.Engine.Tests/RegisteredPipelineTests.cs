using Xdet.Engine.Contract;
using Xdet.Engine.PythonNet;
using Xunit;

namespace Xdet.Engine.Tests;

/// <summary>
/// SPEC-XSEAM-001 (feat/xseam-ui-expand) registered MULTI-STAGE pipeline end-to-end proof.
/// Drives the seam path the Pipeline tab now invokes — <see cref="IXdetEngine.RunRegisteredPipeline"/>
/// — through the REAL Python golden orchestrator: the <c>offset -&gt; gain</c> subsequence of
/// CANONICAL_ORDER on the REAL 아크릴 3072x3072 frame with a calib_map of the REAL CalibSets
/// (MasterDark offset + CalSet_19008 gain), mirroring <c>tests/pipeline/</c> +
/// <c>tests/test_tc_realdata_arms.py</c>. The run must be (a) SANE (3072x3072, float32, finite,
/// std&gt;0), (b) a MEANINGFUL real correction (max|delta|&gt;0, since both calibs are real),
/// (c) ordered offset-then-gain (from the golden history chain), and (d) accompanied by an
/// ENGINE-computed diff preview that equals (after - before) element-wise. A REAL image is
/// QUARANTINE plumbing/sanity only (never a numeric golden). Skips cleanly when
/// images/에드로지16BIT/ is absent. Headless and deterministic; parallelization is disabled
/// assembly-wide (see FidelityTests.cs).
/// </summary>
public sealed class RegisteredPipelineTests
{
    private static readonly PythonNetXdetEngine Engine = new();

    private static string? RepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "pyproject.toml")))
            dir = dir.Parent;
        return dir?.FullName;
    }

    /// <summary>True only when the real edrogi acrylic signal + 16bit cal dir are present.</summary>
    private static bool EdrogiPresent()
    {
        string? root = RepoRoot();
        if (root is null) return false;
        string edrogi = Path.Combine(root, "images", "에드로지16BIT");
        return Directory.Exists(Path.Combine(edrogi, "아크릴")) &&
               File.Exists(Path.Combine(edrogi, "16bit cal", "MasterDark.raw")) &&
               File.Exists(Path.Combine(edrogi, "16bit cal", "CalSet_19008.raw"));
    }

    // -- the registered offset->gain pipeline is sane and a real composed correction --

    [Fact]
    public void Registered_pipeline_is_sane_and_a_meaningful_real_offset_then_gain_correction()
    {
        if (!EdrogiPresent()) return;   // clean skip: sample tree absent

        RegisteredPipelineResult r = Engine.RunRegisteredPipeline();

        // (a) present + sane on the REAL 3072x3072 frame.
        Assert.True(r.ImagesPresent, r.Status);
        Assert.True(r.Sane, r.Status);
        Assert.Equal(3072, r.Rows);
        Assert.Equal(3072, r.Cols);
        Assert.Equal("float32", r.Dtype);
        Assert.True(r.Finite, "pipeline output must be finite");
        Assert.True(r.Std > 0.0, "pipeline output must be non-degenerate (std > 0)");
        Assert.Contains("QUARANTINE", r.Status);   // real image is labeled, not a golden

        // (b) the golden orchestrator ran the minimal offset -> gain slice, in canonical order.
        Assert.Equal(new[] { "offset", "gain" }, r.StagesRun);
        Assert.Equal("MasterDark.raw", r.OffsetCalibName);
        Assert.Equal("CalSet_19008.raw", r.GainCalibName);

        // validation_mode preserved one intermediate per stage (DATA-5).
        Assert.Equal(2, r.IntermediateCount);

        // (c) both REAL calibs transform the field, so the composed correction is meaningful.
        Assert.True(r.MaxAbsChangeFromInput > 0.0,
            "the REAL offset->gain pipeline must change the frame (before != after)");
        Assert.True(double.IsFinite(r.OutputMin));
        Assert.True(double.IsFinite(r.OutputMax));
        Assert.True(double.IsFinite(r.OutputMean));
        Assert.True(r.OutputMax >= r.OutputMin);
    }

    // -- the engine diff preview equals (after - before) element-wise (real ~512² previews) --

    [Fact]
    public void Registered_pipeline_diff_preview_equals_after_minus_before()
    {
        if (!EdrogiPresent()) return;   // clean skip: sample tree absent

        RegisteredPipelineResult r = Engine.RunRegisteredPipeline();
        Assert.True(r.Sane, r.Status);
        Assert.NotNull(r.BeforePreview);
        Assert.NotNull(r.AfterPreview);
        Assert.NotNull(r.DiffPreview);

        FrameData b = r.BeforePreview!;
        FrameData a = r.AfterPreview!;
        FrameData d = r.DiffPreview!;
        Assert.Equal(b.Rows, d.Rows);
        Assert.Equal(b.Cols, d.Cols);
        Assert.Equal(a.Rows, d.Rows);
        Assert.Equal(a.Cols, d.Cols);

        double maxAbs = 0.0;
        for (int i = 0; i < b.Pixels.Length; i++)
        {
            float expected = a.Pixels[i] - b.Pixels[i];
            Assert.Equal(expected, d.Pixels[i]);   // the ENGINE subtracted the ~512² previews (C-09)
            maxAbs = Math.Max(maxAbs, Math.Abs(expected));
        }
        Assert.Equal(maxAbs, r.MaxAbsDiff, 3);
        Assert.True(r.MaxAbsDiff > 0.0,
            "the REAL offset->gain pipeline changes the field, so the preview diff is non-zero");
    }
}
