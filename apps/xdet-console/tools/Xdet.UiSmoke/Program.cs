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
/// select -> click -> assert the tab's info TextBlock updates to a non-error value.
/// Exit code 0 iff Offset, MTF and Pipeline all PASS. Requires an interactive desktop.
/// </summary>
internal static class Program
{
    // Poll cadence + budgets (see "FlaUI timing decisions" in the handoff report).
    private const int EngineReadyTimeoutSec = 60;   // embedded CPython bootstrap
    private const int ActionTimeoutSec = 30;        // one seam call round-trip
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
            Console.WriteLine();

            // 2) Drive each tab's button and assert its info TextBlock updates. Lookup
            //    is by AutomationId (order-independent; the XAML tab order is
            //    Offset, Pipeline, MTF but we key on ids, not position).
            bool offset = RunTab(window, cf, "OFFSET", "OffsetTab", "OffsetButton", "OffsetInfo", "offset error");
            bool mtf = RunTab(window, cf, "MTF", "MtfTab", "MtfButton", "MtfInfo", "MTF error");
            bool pipeline = RunTab(window, cf, "PIPELINE", "PipelineTab", "PipelineButton", "PipelineInfo", "pipeline error");

            Console.WriteLine();
            bool all = offset && mtf && pipeline;
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
        string label, string tabId, string buttonId, string infoId, string errorToken)
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
            while (sw.Elapsed.TotalSeconds < ActionTimeoutSec)
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
                    return true;
                }
                Thread.Sleep(PollMs);
            }
            Console.WriteLine($"{label}: FAIL timeout after {ActionTimeoutSec}s "
                              + $"(status: \"{ReadText(window, cf, "StatusText")}\")");
            return false;
        }
        catch (Exception ex)
        {
            Console.WriteLine($"{label}: FAIL exception {ex.GetType().Name}: {ex.Message}");
            return false;
        }
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
