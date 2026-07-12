using System.Diagnostics;
using FlaUI.Core;
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Conditions;
using FlaUI.UIA3;

namespace Xdet.UiSmoke;

/// <summary>
/// SPEC-XSEAM-001 P1.5 end-to-end GUI smoke driver. Launches the REAL WPF app and
/// exercises every tab's button through the Windows UI Automation tree (FlaUI/UIA3):
/// wait for the embedded-Python engine to reach "ready", then for each tab
/// select -> click -> assert the tab's info TextBlock updates to a non-error value,
/// and CAPTURE a PNG screenshot of the window AFTER each action completes. Exit code 0
/// iff Offset, MTF, Pipeline and Real Image all PASS. Requires an interactive desktop.
///
/// The Real Image tab runs the QUARANTINE plumbing/sanity offset on a REAL edrogi
/// 3072x3072 frame (SPEC-REALDATA-001) — it loads a ~18M-pixel raw, so it gets a
/// generous per-action budget. Screenshots (offset/mtf/pipeline/realimage + a ready
/// overview) are written to apps/xdet-console/_screens/ (a build artifact, gitignored).
/// </summary>
internal static class Program
{
    // Poll cadence + budgets (see "FlaUI timing decisions" in the handoff report).
    private const int EngineReadyTimeoutSec = 60;   // embedded CPython bootstrap
    private const int ActionTimeoutSec = 30;        // one seam call round-trip
    private const int RealImageTimeoutSec = 120;    // loads a real 3072² raw + offset
    private const int PollMs = 250;
    private const int TabRealizeMs = 400;           // let WPF realize the tab content

    private static int Main(string[] args)
    {
        string exePath = args.Length > 0 ? args[0] : DefaultExePath();
        Console.WriteLine("=== XDET UI smoke (FlaUI/UIA3) — SPEC-XSEAM-001 P1.5 ===");
        Console.WriteLine("exe: " + exePath);

        if (!File.Exists(exePath))
        {
            Console.WriteLine("FATAL: app exe not found. Build Xdet.Console.App (Release) first.");
            return 3;
        }

        // Viewer P0-loop file paths, injected into the app via env presets
        // (XDET_VIEWER_OPEN_PATH / XDET_VIEWER_SAVE_PATH) BEFORE launch so the child
        // inherits them. The app then bypasses the native Open/Save dialogs and uses
        // these paths directly — a DELIBERATE decision: automating the native Win32
        // file dialogs through UIA is unreliable/non-deterministic, so we drive the
        // full Load->Process->Save flow deterministically (and still capture the three
        // viewer screenshots). The real native dialogs remain in place for end users.
        string repoRoot = RepoRoot();
        string viewerOpenPath = Path.Combine(repoRoot, "images", "에드로지16BIT", "16bit cal", "MasterDark.raw");
        string viewerSavePath = Path.Combine(Path.GetTempPath(),
            "xdet_viewer_smoke_" + Guid.NewGuid().ToString("N") + ".npz");
        Environment.SetEnvironmentVariable("XDET_VIEWER_OPEN_PATH", viewerOpenPath);
        Environment.SetEnvironmentVariable("XDET_VIEWER_SAVE_PATH", viewerSavePath);

        Application? app = null;
        UIA3Automation? automation = null;
        try
        {
            automation = new UIA3Automation();
            app = Application.Launch(exePath);

            Window? window = app.GetMainWindow(automation, TimeSpan.FromSeconds(30));
            if (window is null)
            {
                Console.WriteLine("FATAL: could not obtain the app main window (UIA could not attach). "
                                  + "An interactive desktop session is required.");
                return 3;
            }
            Console.WriteLine("main window: \"" + window.Title + "\"");
            var cf = automation.ConditionFactory;

            // 1) Wait for the engine to finish its embedded-interpreter bootstrap.
            if (!WaitEngineReady(window, cf))
            {
                Console.WriteLine("FATAL: engine never reached ready. last status: \""
                                  + ReadText(window, cf, "StatusText") + "\"");
                return 2;
            }
            Console.WriteLine("engine ready — status: \"" + ReadText(window, cf, "StatusText") + "\"");

            // Screenshot sink (absolute, gitignored build artifact). Capture a
            // full-window overview on the ready screen before driving any tab.
            string screensDir = ScreensDir();
            Directory.CreateDirectory(screensDir);
            Console.WriteLine("screens dir: " + screensDir);
            CaptureWindow(window, Path.Combine(screensDir, "overview.png"));
            Console.WriteLine();

            // 2) Drive each tab's button, assert its info TextBlock updates, and capture
            //    a screenshot AFTER the action completes. Lookup is by AutomationId
            //    (order-independent; we key on ids, not XAML tab position). The Real
            //    Image tab loads a real 3072² raw so it gets the generous budget.
            bool offset = RunTab(window, cf, "OFFSET", "OffsetTab", "OffsetButton", "OffsetInfo",
                "offset error", ActionTimeoutSec, Path.Combine(screensDir, "offset.png"));
            bool mtf = RunTab(window, cf, "MTF", "MtfTab", "MtfButton", "MtfInfo",
                "MTF error", ActionTimeoutSec, Path.Combine(screensDir, "mtf.png"));
            bool pipeline = RunTab(window, cf, "PIPELINE", "PipelineTab", "PipelineButton", "PipelineInfo",
                "pipeline error", ActionTimeoutSec, Path.Combine(screensDir, "pipeline.png"));
            bool realImage = RunTab(window, cf, "REALIMAGE", "RealImageTab", "RealImageButton", "RealImageInfo",
                "real image error", RealImageTimeoutSec, Path.Combine(screensDir, "realimage.png"));

            // 3) Drive the Viewer P0 loop end-to-end: Open image -> Run offset -> Save
            //    output, capturing a screenshot after each step and asserting the saved
            //    npz exists. File paths are injected via the env presets set above.
            bool viewer = RunViewer(window, cf, screensDir, viewerOpenPath, viewerSavePath);

            Console.WriteLine();
            bool all = offset && mtf && pipeline && realImage && viewer;
            Console.WriteLine("=== RESULT: " + (all ? "ALL PASS" : "FAIL") + " ===");
            return all ? 0 : 1;
        }
        catch (Exception ex)
        {
            Console.WriteLine("FATAL: unhandled exception: " + ex.GetType().Name + ": " + ex.Message);
            Console.WriteLine(ex.StackTrace);
            return 3;
        }
        finally
        {
            try { app?.Close(); } catch { /* best-effort */ }
            try { if (app is not null && !app.HasExited) app.Kill(); } catch { /* best-effort */ }
            automation?.Dispose();
            Console.Out.Flush();
        }
    }

    private static bool WaitEngineReady(Window window, ConditionFactory cf)
    {
        var sw = Stopwatch.StartNew();
        while (sw.Elapsed.TotalSeconds < EngineReadyTimeoutSec)
        {
            string status = ReadText(window, cf, "StatusText");
            if (status.Contains("failed", StringComparison.OrdinalIgnoreCase) ||
                status.Contains("error", StringComparison.OrdinalIgnoreCase))
            {
                Console.WriteLine("engine init FAILED — status: \"" + status + "\"");
                return false;
            }
            // Ready line is exactly "engine: ready" (before any action runs).
            if (status.Contains("ready", StringComparison.OrdinalIgnoreCase))
                return true;
            Thread.Sleep(PollMs);
        }
        return false;
    }

    private static bool RunTab(
        Window window, ConditionFactory cf,
        string label, string tabId, string buttonId, string infoId, string errorToken,
        int timeoutSec, string screenshotPath)
    {
        try
        {
            var tab = window.FindFirstDescendant(cf.ByAutomationId(tabId));
            if (tab is null)
            {
                Console.WriteLine($"{label}: FAIL tab '{tabId}' not found");
                return false;
            }
            tab.AsTabItem().Select();
            Thread.Sleep(TabRealizeMs);   // WPF realizes the newly selected tab's content

            string infoBefore = ReadText(window, cf, infoId);

            var button = window.FindFirstDescendant(cf.ByAutomationId(buttonId));
            if (button is null)
            {
                Console.WriteLine($"{label}: FAIL button '{buttonId}' not found");
                return false;
            }
            button.AsButton().Invoke();

            var sw = Stopwatch.StartNew();
            while (sw.Elapsed.TotalSeconds < timeoutSec)
            {
                string status = ReadText(window, cf, "StatusText");
                if (status.Contains(errorToken, StringComparison.OrdinalIgnoreCase) ||
                    status.Contains("error", StringComparison.OrdinalIgnoreCase))
                {
                    Console.WriteLine($"{label}: FAIL {status}");
                    return false;
                }
                string info = ReadText(window, cf, infoId);
                if (info.Length > 0 && info != infoBefore)
                {
                    Console.WriteLine($"{label}: PASS {info}");
                    // Capture AFTER the action completed and the tab shows its result.
                    Thread.Sleep(TabRealizeMs);   // let the plots/heatmaps paint first
                    CaptureWindow(window, screenshotPath);
                    return true;
                }
                Thread.Sleep(PollMs);
            }
            Console.WriteLine($"{label}: FAIL timeout after {timeoutSec}s "
                              + $"(status: \"{ReadText(window, cf, "StatusText")}\")");
            return false;
        }
        catch (Exception ex)
        {
            Console.WriteLine($"{label}: FAIL exception {ex.GetType().Name}: {ex.Message}");
            return false;
        }
    }

    /// <summary>
    /// Drive the Viewer P0 loop end-to-end (feat/xseam-ui-expand): select the Viewer
    /// tab, then Open image... -> Run offset -> Save output..., capturing a screenshot
    /// (viewer_loaded / viewer_processed / viewer_saved) after each step and asserting
    /// the saved npz exists. The Open/Save file paths are injected via env presets
    /// (set in Main before launch), so the native dialogs are bypassed and the full
    /// flow is deterministic. Skips cleanly (PASS) when the edrogi sample is absent.
    /// </summary>
    private static bool RunViewer(
        Window window, ConditionFactory cf, string screensDir, string openPath, string savePath)
    {
        Console.WriteLine();
        Console.WriteLine("VIEWER: P0 loop (open -> run offset -> save)");
        if (!File.Exists(openPath))
        {
            Console.WriteLine("VIEWER: SKIP — edrogi sample absent: " + openPath);
            return true;   // clean skip when images are absent (matches the xUnit suite)
        }
        Console.WriteLine("VIEWER: open preset = " + openPath);
        Console.WriteLine("VIEWER: save preset = " + savePath);
        Console.WriteLine("VIEWER: file dialogs bypassed via env presets "
            + "(XDET_VIEWER_OPEN_PATH / XDET_VIEWER_SAVE_PATH) for a deterministic flow.");
        try
        {
            var tab = window.FindFirstDescendant(cf.ByAutomationId("ViewerTab"));
            if (tab is null) { Console.WriteLine("VIEWER: FAIL tab 'ViewerTab' not found"); return false; }
            tab.AsTabItem().Select();
            Thread.Sleep(TabRealizeMs);

            // 1) Open image... (preset path). The real edrogi 3072² raw loads, so use
            //    the generous budget. Wait until ViewerStatus reports "loaded".
            if (!ClickAndWait(window, cf, "OpenImageButton", "ViewerStatus", "loaded",
                    RealImageTimeoutSec, "VIEWER/open")) return false;
            Thread.Sleep(TabRealizeMs);
            CaptureWindow(window, Path.Combine(screensDir, "viewer_loaded.png"));

            // 2) Run offset (golden offset on the 3072² frame). Wait until "processed".
            if (!ClickAndWait(window, cf, "ViewerProcessButton", "ViewerStatus", "processed",
                    RealImageTimeoutSec, "VIEWER/process")) return false;
            Thread.Sleep(TabRealizeMs);
            CaptureWindow(window, Path.Combine(screensDir, "viewer_processed.png"));

            // 3) Save output... (preset path, outside data/). Wait until "saved".
            if (!ClickAndWait(window, cf, "ViewerSaveButton", "ViewerStatus", "saved",
                    ActionTimeoutSec, "VIEWER/save")) return false;
            Thread.Sleep(TabRealizeMs);
            CaptureWindow(window, Path.Combine(screensDir, "viewer_saved.png"));

            // Assert the saved npz exists (SaveProcessedFrame writes exactly the preset
            // path: a trailing '.npz' is stripped then re-appended -> 'foo.npz').
            if (!File.Exists(savePath))
            {
                Console.WriteLine("VIEWER: FAIL saved npz not found: " + savePath);
                return false;
            }
            long size = new FileInfo(savePath).Length;
            Console.WriteLine($"VIEWER: PASS saved npz exists: {savePath} ({size} bytes)");
            return true;
        }
        catch (Exception ex)
        {
            Console.WriteLine($"VIEWER: FAIL exception {ex.GetType().Name}: {ex.Message}");
            return false;
        }
    }

    /// <summary>
    /// Click the button <paramref name="buttonId"/> and poll the TextBlock
    /// <paramref name="watchId"/> until its text contains <paramref name="successToken"/>
    /// (PASS) or an error/failed/refused token (FAIL). Case-insensitive.
    /// </summary>
    private static bool ClickAndWait(
        Window window, ConditionFactory cf,
        string buttonId, string watchId, string successToken, int timeoutSec, string label)
    {
        var button = window.FindFirstDescendant(cf.ByAutomationId(buttonId));
        if (button is null)
        {
            Console.WriteLine($"{label}: FAIL button '{buttonId}' not found");
            return false;
        }
        button.AsButton().Invoke();

        var sw = Stopwatch.StartNew();
        while (sw.Elapsed.TotalSeconds < timeoutSec)
        {
            string watch = ReadText(window, cf, watchId);
            if (watch.Contains(successToken, StringComparison.OrdinalIgnoreCase))
            {
                Console.WriteLine($"{label}: PASS {watch}");
                return true;
            }
            if (watch.Contains("error", StringComparison.OrdinalIgnoreCase) ||
                watch.Contains("failed", StringComparison.OrdinalIgnoreCase) ||
                watch.Contains("refused", StringComparison.OrdinalIgnoreCase))
            {
                Console.WriteLine($"{label}: FAIL {watch}");
                return false;
            }
            Thread.Sleep(PollMs);
        }
        Console.WriteLine($"{label}: FAIL timeout after {timeoutSec}s "
                          + $"(watch: \"{ReadText(window, cf, watchId)}\")");
        return false;
    }

    /// <summary>Walk up from this runner's base dir to the repo root (pyproject.toml).</summary>
    private static string RepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "pyproject.toml")))
            dir = dir.Parent;
        return dir?.FullName ?? AppContext.BaseDirectory;
    }

    /// <summary>
    /// Capture the whole app window to a PNG via FlaUI's UIA-driven element capture and
    /// report the saved path + byte size. Best-effort: a capture failure is logged but
    /// does not fail the tab (the functional assertion already passed).
    /// </summary>
    private static void CaptureWindow(Window window, string path)
    {
        try
        {
            using FlaUI.Core.Capturing.CaptureImage image =
                FlaUI.Core.Capturing.Capture.Element(window);
            image.ToFile(path);
            long size = new FileInfo(path).Length;
            Console.WriteLine($"  screenshot: {path} ({size} bytes)");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"  screenshot FAILED for {path}: {ex.GetType().Name}: {ex.Message}");
        }
    }

    /// <summary>Absolute screenshots sink under the repo: apps/xdet-console/_screens/.</summary>
    private static string ScreensDir()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "pyproject.toml")))
            dir = dir.Parent;
        string root = dir?.FullName ?? AppContext.BaseDirectory;
        return Path.Combine(root, "apps", "xdet-console", "_screens");
    }

    /// <summary>Read a WPF TextBlock's text: its automation Name equals its Text content.</summary>
    private static string ReadText(Window window, ConditionFactory cf, string automationId)
    {
        var el = window.FindFirstDescendant(cf.ByAutomationId(automationId));
        return el?.Name ?? string.Empty;
    }

    private static string DefaultExePath()
    {
        // Walk up from this runner's base dir to the repo root (pyproject.toml), then
        // resolve the built WPF app exe under its Release output.
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "pyproject.toml")))
            dir = dir.Parent;
        string root = dir?.FullName ?? AppContext.BaseDirectory;
        return Path.Combine(root, "apps", "xdet-console", "src", "Xdet.Console.App",
            "bin", "Release", "net9.0-windows", "Xdet.Console.App.exe");
    }
}
