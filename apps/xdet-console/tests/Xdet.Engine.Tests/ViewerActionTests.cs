using Xdet.Engine.Contract;
using Xdet.Engine.PythonNet;
using Xunit;

namespace Xdet.Engine.Tests;

/// <summary>
/// SPEC-XSEAM-001 (feat/xseam-ui-expand) Viewer P0-loop end-to-end proof. Drives the
/// exact seam path the three Viewer buttons invoke, through the REAL Python golden:
///   - Open image...  -> LoadRawFrame   (load a REAL edrogi 3072x3072 raw, assert sane)
///   - Run offset     -> ProcessLoadedFrame (golden offset, assert sane output)
///   - Save output... -> SaveProcessedFrame  (npz+JSON, assert written + pixel round-trip)
/// plus the C-20 write-guard negative: a save under &lt;repo&gt;/data MUST be rejected
/// with NOTHING written. A REAL image is QUARANTINE plumbing/sanity only (no numeric
/// golden). The suite skips cleanly when images/에드로지16BIT/ is absent. Headless and
/// deterministic; parallelization is disabled assembly-wide (see FidelityTests.cs).
/// </summary>
public sealed class ViewerActionTests
{
    private static readonly PythonNetXdetEngine Engine = new();

    private static string? RepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "pyproject.toml")))
            dir = dir.Parent;
        return dir?.FullName;
    }

    /// <summary>The real edrogi MasterDark raw, or null when the sample tree is absent.</summary>
    private static string? EdrogiMasterDark()
    {
        string? root = RepoRoot();
        if (root is null) return null;
        string p = Path.Combine(root, "images", "에드로지16BIT", "16bit cal", "MasterDark.raw");
        return File.Exists(p) ? p : null;
    }

    // -- Load -> Process -> Save round-trip on a REAL 3072x3072 frame ---------

    [Fact]
    public void Viewer_load_process_save_roundtrips_on_a_real_edrogi_frame()
    {
        string? masterdark = EdrogiMasterDark();
        if (masterdark is null) return;   // clean skip: sample tree absent

        // LOAD — a real 3072x3072 acquisition (no sidecar -> perfect-square inference).
        LoadedFrameInfo loaded = Engine.LoadRawFrame(masterdark);
        Assert.True(loaded.Loaded, loaded.Status);
        Assert.Equal(3072, loaded.Rows);
        Assert.Equal(3072, loaded.Cols);
        Assert.Equal("float32", loaded.Dtype);
        Assert.True(loaded.Finite, "loaded frame must be finite");
        Assert.NotNull(loaded.Preview);
        Assert.Contains("QUARANTINE", loaded.Status);   // real image is labeled, not a golden

        // PROCESS — the golden offset actually ran, output is sane.
        ProcessedFrameInfo processed = Engine.ProcessLoadedFrame();
        Assert.True(processed.Processed, processed.Status);
        Assert.Equal(new[] { "offset" }, processed.StagesRun);
        Assert.NotNull(processed.BeforePreview);
        Assert.NotNull(processed.AfterPreview);
        Assert.True(double.IsFinite(processed.OutputMin));
        Assert.True(double.IsFinite(processed.OutputMax));
        Assert.True(double.IsFinite(processed.OutputMean));
        Assert.True(processed.OutputMax >= processed.OutputMin);

        // SAVE (OUTSIDE data/) + reload -> saved pixels equal the processed output.
        string tmp = Path.Combine(Path.GetTempPath(),
            "xdet_viewer_test_" + Guid.NewGuid().ToString("N") + ".npz");
        string tmpJson = Path.ChangeExtension(tmp, ".json");
        try
        {
            SaveResult save = Engine.SaveProcessedFrame(tmp);
            Assert.True(save.Success, save.Message);
            Assert.False(save.GuardRejected);
            Assert.True(File.Exists(tmp), "npz was not written: " + tmp);
            Assert.True(File.Exists(tmpJson), "json sidecar was not written: " + tmpJson);

            FrameData processedFull = Engine.GetProcessedFrame();
            FrameData reloaded = Engine.LoadExportedFrame(tmp);
            Assert.Equal(processedFull.Rows, reloaded.Rows);
            Assert.Equal(processedFull.Cols, reloaded.Cols);
            Assert.Equal(processedFull.Pixels.Length, reloaded.Pixels.Length);
            Assert.True(processedFull.Pixels.AsSpan().SequenceEqual(reloaded.Pixels),
                "reloaded pixels differ from the processed output — export round-trip is broken");
        }
        finally
        {
            TryDelete(tmp);
            TryDelete(tmpJson);
        }
    }

    // -- C-20 write guard: a save under <repo>/data is REJECTED, nothing written --

    [Fact]
    public void Viewer_save_under_data_is_rejected_by_the_c20_guard()
    {
        string? masterdark = EdrogiMasterDark();
        if (masterdark is null) return;   // clean skip: sample tree absent
        string? root = RepoRoot();
        Assert.NotNull(root);

        Engine.LoadRawFrame(masterdark);
        Engine.ProcessLoadedFrame();

        // A path resolving under <repo>/data must be refused BEFORE any write.
        string under = Path.Combine(root!, "data",
            "xdet_should_not_write_" + Guid.NewGuid().ToString("N") + ".npz");
        string underJson = Path.ChangeExtension(under, ".json");

        SaveResult save = Engine.SaveProcessedFrame(under);

        Assert.False(save.Success, "a write under data/ must not succeed");
        Assert.True(save.GuardRejected, "the C-20 guard must flag the rejection");
        Assert.False(File.Exists(under), "guard-rejected npz must NOT be written under data/");
        Assert.False(File.Exists(underJson), "guard-rejected json must NOT be written under data/");
    }

    private static void TryDelete(string path)
    {
        try { if (File.Exists(path)) File.Delete(path); } catch { /* best-effort cleanup */ }
    }
}
