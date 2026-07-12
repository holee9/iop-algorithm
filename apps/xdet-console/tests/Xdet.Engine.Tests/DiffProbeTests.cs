using Xdet.Engine.Contract;
using Xdet.Engine.PythonNet;
using Xunit;

namespace Xdet.Engine.Tests;

/// <summary>
/// SPEC-XSEAM-001 (feat/xseam-ui-expand) "compare and inspect" proof: the diff preview is
/// computed ENGINE-side and the pixel probe reads the STORED preview values (SPEC-VIEWER-001
/// C-03/C-06/C-09). Two facts are asserted through the REAL Python golden / adapter:
/// <list type="number">
///   <item>the engine diff preview equals (after - before) element-wise — proving the ENGINE
///   (not the UI) computes the subtraction (via both <see cref="IXdetEngine.ComputeDiffPreview"/>
///   and the DTO-embedded <see cref="PipelineResult.DiffPreview"/> / registered-arm diff);</item>
///   <item>the probe readout the UI uses (<see cref="ProbeReadout"/>) returns the stored
///   before/after/diff array values at a (row,col).</item>
/// </list>
/// The synthetic cases are deterministic and headless (no WPF, no edrogi); the registered-arm
/// case skips cleanly when images/에드로지16BIT/ is absent. Parallelization is disabled
/// assembly-wide (see FidelityTests.cs).
/// </summary>
public sealed class DiffProbeTests
{
    private static readonly PythonNetXdetEngine Engine = new();
    private const double RawSaturationThreshold = 0.98 * 65535.0;

    /// <summary>Mirror of MainWindow.MakePipelineCase — a deterministic offset->gain stimulus.</summary>
    private static (FrameData input, OffsetCalibData offset, GainCalibData gain)
        MakePipelineCase(int rows = 32, int cols = 32)
    {
        var pixels = new float[rows * cols];
        var omap = new float[rows * cols];
        var gmap = new float[rows * cols];
        for (int r = 0; r < rows; r++)
        {
            for (int c = 0; c < cols; c++)
            {
                int i = r * cols + c;
                pixels[i] = 3000f + r * 3f + c * 1.5f;
                omap[i] = 200f + c * 0.5f;
                gmap[i] = 1.1f;
            }
        }
        return (FrameData.FromPixels(pixels, rows, cols),
                new OffsetCalibData(omap, rows, cols),
                new GainCalibData(gmap, rows, cols));
    }

    private static string? RepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "pyproject.toml")))
            dir = dir.Parent;
        return dir?.FullName;
    }

    private static bool EdrogiPresent()
    {
        string? root = RepoRoot();
        if (root is null) return false;
        string edrogi = Path.Combine(root, "images", "에드로지16BIT");
        return Directory.Exists(Path.Combine(edrogi, "아크릴")) &&
               File.Exists(Path.Combine(edrogi, "16bit cal", "MasterDark.raw"));
    }

    // -- the engine computes the diff = after - before (not the UI) -----------

    [Fact]
    public void ComputeDiffPreview_equals_after_minus_before_elementwise()
    {
        // Two deterministic frames; the engine must return after - before EXACTLY (float32
        // IEEE subtraction is deterministic, so numpy and a C# reference agree bit-for-bit).
        const int rows = 8, cols = 8;
        var before = new float[rows * cols];
        var after = new float[rows * cols];
        for (int i = 0; i < before.Length; i++)
        {
            before[i] = 100f + i;
            after[i] = 100f + 2f * i - 3f;
        }
        var b = FrameData.FromPixels(before, rows, cols);
        var a = FrameData.FromPixels(after, rows, cols);

        DiffPreviewResult d = Engine.ComputeDiffPreview(b, a);

        Assert.Equal(rows, d.Diff.Rows);
        Assert.Equal(cols, d.Diff.Cols);
        double maxAbs = 0.0;
        for (int i = 0; i < before.Length; i++)
        {
            float expected = after[i] - before[i];
            Assert.Equal(expected, d.Diff.Pixels[i]);   // ENGINE subtracted, bit-identical
            maxAbs = Math.Max(maxAbs, Math.Abs(expected));
        }
        Assert.Equal(maxAbs, d.MaxAbsDiff, 3);   // engine-reported peak == max|diff|
    }

    [Fact]
    public void Pipeline_diff_preview_is_the_engine_computed_output_minus_input()
    {
        var (input, offsetCalib, gainCalib) = MakePipelineCase();

        PipelineResult result = Engine.RunPipeline(
            input, offsetCalib, new OffsetParams(RawSaturationThreshold), gainCalib, new GainParams());

        Assert.NotNull(result.DiffPreview);
        FrameData diff = result.DiffPreview!;
        Assert.Equal(result.Input.Rows, diff.Rows);
        Assert.Equal(result.Input.Cols, diff.Cols);

        double maxAbs = 0.0;
        for (int i = 0; i < result.Input.Pixels.Length; i++)
        {
            float expected = result.Output.Pixels[i] - result.Input.Pixels[i];
            Assert.Equal(expected, diff.Pixels[i]);   // the ENGINE did the subtraction (C-09)
            maxAbs = Math.Max(maxAbs, Math.Abs(expected));
        }
        Assert.Equal(maxAbs, result.MaxAbsDiff, 3);
        Assert.True(result.MaxAbsDiff > 0.0, "the offset->gain pipeline must change the frame");
    }

    // -- the probe reads the STORED preview values (C-03) --------------------

    [Fact]
    public void Probe_readout_returns_the_stored_preview_values()
    {
        var (input, offsetCalib, gainCalib) = MakePipelineCase();
        PipelineResult result = Engine.RunPipeline(
            input, offsetCalib, new OffsetParams(RawSaturationThreshold), gainCalib, new GainParams());
        FrameData before = result.Input;
        FrameData after = result.Output;
        FrameData diff = result.DiffPreview!;

        // The exact readout the UI shows on hover: the stored array values at (row,col).
        foreach ((int row, int col) in new[] { (0, 0), (3, 7), (31, 31), (10, 20) })
        {
            ProbeSample s = ProbeReadout.Read(before, after, diff, row, col);
            Assert.True(s.InBounds);
            Assert.Equal(row, s.Row);
            Assert.Equal(col, s.Col);
            int idx = row * before.Cols + col;
            Assert.Equal(before.Pixels[idx], s.Before);
            Assert.Equal(after.Pixels[idx], s.After);
            Assert.Equal(diff.Pixels[idx], s.Diff);   // stored engine diff, NOT recomputed
        }

        // Out-of-range coordinates are a clean, non-throwing verdict.
        Assert.False(ProbeReadout.Read(before, after, diff, -1, 0).InBounds);
        Assert.False(ProbeReadout.Read(before, after, diff, 0, before.Cols).InBounds);
    }

    // -- registered offset arm: DTO diff preview == after - before (real data) --

    [Fact]
    public void Registered_offset_arm_diff_preview_equals_after_minus_before()
    {
        if (!EdrogiPresent()) return;   // clean skip: sample tree absent

        RegisteredArmResult r = Engine.RunRegisteredArm("offset");
        Assert.True(r.Sane, r.Status);
        Assert.NotNull(r.BeforePreview);
        Assert.NotNull(r.AfterPreview);
        Assert.NotNull(r.DiffPreview);

        FrameData b = r.BeforePreview!;
        FrameData a = r.AfterPreview!;
        FrameData d = r.DiffPreview!;
        Assert.Equal(b.Rows, d.Rows);
        Assert.Equal(b.Cols, d.Cols);

        double maxAbs = 0.0;
        for (int i = 0; i < b.Pixels.Length; i++)
        {
            float expected = a.Pixels[i] - b.Pixels[i];
            Assert.Equal(expected, d.Pixels[i]);   // engine subtracted the ~512² previews
            maxAbs = Math.Max(maxAbs, Math.Abs(expected));
        }
        Assert.Equal(maxAbs, r.MaxAbsDiff, 3);
        Assert.True(r.MaxAbsDiff > 0.0, "the REAL offset changes the field, so the diff is non-zero");
    }
}
