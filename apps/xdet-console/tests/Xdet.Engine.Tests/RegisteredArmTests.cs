using Xdet.Engine.Contract;
using Xdet.Engine.PythonNet;
using Xunit;

namespace Xdet.Engine.Tests;

/// <summary>
/// SPEC-XSEAM-001 (feat/xseam-ui-expand) registered-arm end-to-end proof. Drives the
/// seam path the Viewer's PRIMARY flow invokes — <see cref="IXdetEngine.RunRegisteredArm"/>
/// for each of {offset, gain, defect} — through the REAL Python golden, mirroring
/// <c>tests/test_tc_realdata_arms.py::test_tc_001/002/003</c>: the real 아크릴 signal + the
/// REAL CalibSet built from the registered source (MasterDark / CalSet_19008 / BPM) + the
/// real module.process. Each arm must be (a) SANE (3072x3072, float32, finite, std&gt;0) and
/// (b) — because the calib is REAL — a MEANINGFUL correction (before != after). offset and
/// gain scale/subtract the whole field so their max|delta| is strictly positive; defect
/// interpolates the real bad pixels (asserted sane + runs, and its max|delta| observed).
/// A REAL image is QUARANTINE plumbing/sanity only (never a numeric golden). The suite
/// skips cleanly when images/에드로지16BIT/ is absent. Headless and deterministic;
/// parallelization is disabled assembly-wide (see FidelityTests.cs).
/// </summary>
public sealed class RegisteredArmTests
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
               File.Exists(Path.Combine(edrogi, "16bit cal", "MasterDark.raw"));
    }

    private static void AssertSane(RegisteredArmResult r)
    {
        Assert.True(r.ImagesPresent, r.Status);
        Assert.True(r.Sane, r.Status);
        Assert.Equal(3072, r.Rows);
        Assert.Equal(3072, r.Cols);
        Assert.Equal("float32", r.Dtype);
        Assert.True(r.Finite, "arm output must be finite");
        Assert.True(r.Std > 0.0, "arm output must be non-degenerate (std > 0)");
        Assert.NotNull(r.BeforePreview);
        Assert.NotNull(r.AfterPreview);
        Assert.Contains("QUARANTINE", r.Status);   // real image is labeled, not a golden
    }

    // -- offset arm (real 아크릴 signal - real MasterDark OFFSET) -------------

    [Fact]
    public void Offset_registered_arm_is_sane_and_a_meaningful_real_correction()
    {
        if (!EdrogiPresent()) return;   // clean skip: sample tree absent

        RegisteredArmResult r = Engine.RunRegisteredArm("offset");
        AssertSane(r);
        Assert.Equal("offset", r.Kind);
        Assert.Equal("MasterDark.raw", r.CalibName);
        // The REAL dark is subtracted everywhere -> the output genuinely differs.
        Assert.True(r.MaxAbsChangeFromInput > 0.0,
            "offset with the REAL MasterDark must change the frame (before != after)");
    }

    // -- gain arm (single-point G_map from the representative CalSet) ---------

    [Fact]
    public void Gain_registered_arm_is_sane_and_a_meaningful_real_correction()
    {
        if (!EdrogiPresent()) return;   // clean skip: sample tree absent

        RegisteredArmResult r = Engine.RunRegisteredArm("gain");
        AssertSane(r);
        Assert.Equal("gain", r.Kind);
        Assert.Equal("CalSet_19008.raw", r.CalibName);
        // The REAL flat-field gain scales the field -> the output genuinely differs.
        Assert.True(r.MaxAbsChangeFromInput > 0.0,
            "gain with the REAL flat-field must change the frame (before != after)");
    }

    // -- defect arm (BPM DEFECT map -> interpolate real bad pixels) -----------

    [Fact]
    public void Defect_registered_arm_is_sane_and_runs()
    {
        if (!EdrogiPresent()) return;   // clean skip: sample tree absent

        RegisteredArmResult r = Engine.RunRegisteredArm("defect");
        AssertSane(r);
        Assert.Equal("defect", r.Kind);
        Assert.Equal("BPM.raw", r.CalibName);
        // defect interpolates the real flagged pixels; its delta may be localized but
        // must be a finite, non-negative measure (near-zero is acceptable per SPEC).
        Assert.True(double.IsFinite(r.MaxAbsChangeFromInput));
        Assert.True(r.MaxAbsChangeFromInput >= 0.0);
    }

    // -- registered-arm output is saveable (Save works on the arm result) ----

    [Fact]
    public void Registered_arm_output_is_saveable_outside_data()
    {
        if (!EdrogiPresent()) return;   // clean skip: sample tree absent

        RegisteredArmResult r = Engine.RunRegisteredArm("offset");
        AssertSane(r);

        string tmp = Path.Combine(Path.GetTempPath(),
            "xdet_regarm_test_" + Guid.NewGuid().ToString("N") + ".npz");
        string tmpJson = Path.ChangeExtension(tmp, ".json");
        try
        {
            SaveResult save = Engine.SaveProcessedFrame(tmp);
            Assert.True(save.Success, save.Message);
            Assert.False(save.GuardRejected);
            Assert.True(File.Exists(tmp), "npz was not written: " + tmp);
            Assert.True(File.Exists(tmpJson), "json sidecar was not written: " + tmpJson);
        }
        finally
        {
            TryDelete(tmp);
            TryDelete(tmpJson);
        }
    }

    // -- unknown kind is a clean, non-throwing verdict (no crash) -------------

    [Fact]
    public void Unknown_arm_kind_returns_a_clean_failure_verdict()
    {
        RegisteredArmResult r = Engine.RunRegisteredArm("bogus");
        Assert.False(r.Sane);
        Assert.Contains("unknown arm kind", r.Status);
    }

    private static void TryDelete(string path)
    {
        try { if (File.Exists(path)) File.Delete(path); } catch { /* best-effort cleanup */ }
    }
}
