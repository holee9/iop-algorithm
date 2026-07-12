using System;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using Xdet.Engine.Contract;
using Xdet.Engine.PythonNet;

namespace Xdet.Console.App;

/// <summary>
/// SPEC-XSEAM-001 P1.5 UI skeleton. Inherits SPEC-VIEWER-001 C-09/C-11/C-20: the UI
/// computes NO DSP. Every numeric result comes from the durable engine seam
/// (<see cref="IXdetEngine"/>, fulfilled by <see cref="PythonNetXdetEngine"/> calling
/// the frozen Python golden); this class only builds deterministic synthetic INPUT,
/// forwards it across the seam, and plots what the engine returns. It never writes any
/// golden fixture (read-only toward the golden).
/// </summary>
public partial class MainWindow : Window
{
    // Concrete engine: needed for the diagnostic slanted-edge phantom path that feeds
    // ComputeMtf (the durable interface intentionally omits phantom generation).
    private PythonNetXdetEngine? _engine;

    // The durable seam surface. Offset + MTF are driven exclusively through this
    // interface, keeping the UI dependent on the contract, not the Python adapter.
    private IXdetEngine? Seam => _engine;

    private bool _busy;

    // SWR-601 [B] default raw saturation threshold (0.98 of the 16-bit full scale).
    private const double RawSaturationThreshold = 0.98 * 65535.0;

    public MainWindow()
    {
        InitializeComponent();
    }

    private async void Window_Loaded(object sender, RoutedEventArgs e)
    {
        StatusText.Text = "engine: initializing embedded interpreter...";
        try
        {
            // Embedded-CPython bootstrap can take a moment; run it off the UI thread.
            // Initialized exactly once and reused for every seam call thereafter.
            _engine = await Task.Run(() => new PythonNetXdetEngine());
            StatusText.Text = "engine: ready";
        }
        catch (Exception ex)
        {
            StatusText.Text = "engine: init failed - " + ex.Message;
        }
    }

    private async void OffsetButton_Click(object sender, RoutedEventArgs e)
    {
        if (!TryBeginWork()) return;
        try
        {
            var (input, calib) = MakeOffsetCase();
            var offsetParams = new OffsetParams(RawSaturationThreshold);

            // Seam call: C# -> golden offset.process -> C#. The correction happens in
            // the golden; the UI receives the corrected frame back.
            FrameData output = await Task.Run(() => Seam!.RunOffset(input, calib, offsetParams));

            // Upgraded from a single-row line plot to full 2-D before/after heatmaps.
            RenderHeatmap(OffsetInputPlot, input, "Offset input");
            RenderHeatmap(OffsetOutputPlot, output, "Offset-corrected (SWR-101~104)");

            OffsetInfo.Text =
                $"frame {input.Rows}x{input.Cols}  S_th={RawSaturationThreshold:F0}  " +
                $"out noise(alpha={output.NoiseAlpha:G4}, sigma={output.NoiseSigma:G4})";
            StatusText.Text = "engine: ready (offset done)";
        }
        catch (Exception ex)
        {
            StatusText.Text = "offset error: " + ex.Message;
        }
        finally
        {
            EndWork();
        }
    }

    private async void MtfButton_Click(object sender, RoutedEventArgs e)
    {
        if (!TryBeginWork()) return;
        try
        {
            var spec = new EdgePhantomSpec();   // golden defaults: 128x128, 2 deg, sigma 0.6
            var mtfParams = new MtfParams();

            // Adapter renders the golden edge phantom; the seam computes its MTF.
            MtfResult result = await Task.Run(() =>
            {
                FrameData phantom = _engine!.MakeSlantedEdge(spec);
                return Seam!.ComputeMtf(phantom, mtfParams);
            });

            RenderMtf(MtfPlot, result);

            MtfInfo.Text =
                $"edge angle={result.EdgeAngleDeg:F2} deg  " +
                $"Nyquist={result.NyquistLpmm:F2} lp/mm  " +
                $"MTF@Nyquist={result.MtfAtNyquist:F3}";
            StatusText.Text = "engine: ready (MTF done)";
        }
        catch (Exception ex)
        {
            StatusText.Text = "MTF error: " + ex.Message;
        }
        finally
        {
            EndWork();
        }
    }

    private async void PipelineButton_Click(object sender, RoutedEventArgs e)
    {
        if (!TryBeginWork()) return;
        try
        {
            var (input, offsetCalib, gainCalib) = MakePipelineCase();
            var offsetParams = new OffsetParams(RawSaturationThreshold);
            var gainParams = new GainParams();

            // Seam call: C# -> golden orchestrator (offset -> gain) -> C#. The
            // orchestrator owns stage order + the CalibSet entry gate; the UI only
            // supplies synthetic input/calibs and renders what comes back.
            PipelineResult result = await Task.Run(() =>
                Seam!.RunPipeline(input, offsetCalib, offsetParams, gainCalib, gainParams));

            RenderHeatmap(PipelineInputPlot, result.Input, "Pipeline input");
            RenderHeatmap(PipelineOutputPlot, result.Output, "After offset -> gain");

            // All numbers are engine-computed (golden/numpy), not derived in the UI.
            PipelineInfo.Text =
                $"stages: {string.Join(" -> ", result.StagesRun)}  " +
                $"out[min={result.OutputMin:F1}, max={result.OutputMax:F1}, mean={result.OutputMean:F1}]  " +
                $"max|delta|={result.MaxAbsChangeFromInput:F1}";
            StatusText.Text = "engine: ready (pipeline done)";
        }
        catch (Exception ex)
        {
            StatusText.Text = "pipeline error: " + ex.Message;
        }
        finally
        {
            EndWork();
        }
    }

    private async void RealImageButton_Click(object sender, RoutedEventArgs e)
    {
        if (!TryBeginWork()) return;
        try
        {
            // [HARD] QUARANTINE 배관/sanity ONLY (SPEC-REALDATA-001). The seam runs the
            // golden offset on a REAL edrogi frame and returns engine-computed sanity
            // stats + engine-downsampled before/after previews. The UI performs no DSP
            // and never touches full-res pixels (SPEC-VIEWER-001).
            RealImageSanityResult result = await Task.Run(() => Seam!.RunRealImageOffsetSanity());

            if (!result.ImagesPresent)
            {
                // Honest, non-error verdict when the sample tree is absent.
                RealImageInfo.Text = result.Status;
                StatusText.Text = "engine: ready (real image: images absent)";
                return;
            }

            if (result.BeforePreview is not null)
                RenderHeatmap(RealImageInputPlot, result.BeforePreview,
                    "REAL signal (QUARANTINE, ~512² preview)");
            if (result.AfterPreview is not null)
                RenderHeatmap(RealImageOutputPlot, result.AfterPreview,
                    "REAL offset-corrected (QUARANTINE, ~512² preview)");

            // All numbers are engine-computed (golden/numpy) — the UI derives nothing.
            RealImageInfo.Text =
                $"{result.Status}  file={result.SignalName}  " +
                $"[shape {result.Rows}x{result.Cols}, dtype {result.Dtype}, finite={result.Finite}, " +
                $"std={result.Std:G4}, min={result.Min:G4}, max={result.Max:G4}, mean={result.Mean:G4}]  " +
                $"sane={result.Sane}";
            StatusText.Text = "engine: ready (real image sanity done)";
        }
        catch (Exception ex)
        {
            StatusText.Text = "real image error: " + ex.Message;
        }
        finally
        {
            EndWork();
        }
    }

    // -- Viewer P0 loop: open arbitrary image -> process -> save ------------------
    // The usable algorithm-verification loop. The UI drives 3 buttons; the engine
    // loads/downsamples/processes/exports. Every number + preview comes from the
    // seam (SPEC-VIEWER-001: the UI does no DSP and no downsampling). File paths may
    // be injected via env presets (XDET_VIEWER_OPEN_PATH / XDET_VIEWER_SAVE_PATH) so
    // the UI smoke can drive the full flow deterministically without automating the
    // native file dialogs; when unset, the real native dialogs are used.

    private bool _viewerLoaded;
    private bool _viewerProcessed;

    /// <summary>
    /// PRIMARY Viewer flow (feat/xseam-ui-expand): run the selected REGISTERED arm
    /// (Offset/MasterDark, Gain/CalSet_19008, Defect/BPM) on the REAL edrogi 아크릴 frame
    /// with its REAL CalibSet via <see cref="IXdetEngine.RunRegisteredArm"/>. The engine
    /// returns sanity + stats (incl. max|delta|, proving the REAL correction) + downsampled
    /// before/after previews; the corrected output is held engine-side so 'Save output...'
    /// persists it. The UI performs no DSP (SPEC-VIEWER-001) and labels the result QUARANTINE.
    /// </summary>
    private async void RunRegisteredArmButton_Click(object sender, RoutedEventArgs e)
    {
        // Resolve the selected arm kind from the ComboBoxItem Tag (offset|gain|defect).
        string kind = (ArmSelector.SelectedItem as ComboBoxItem)?.Tag as string ?? "offset";

        if (!TryBeginWork()) return;
        try
        {
            RegisteredArmResult result = await Task.Run(() => Seam!.RunRegisteredArm(kind));

            if (!result.ImagesPresent)
            {
                // Honest, non-error verdict when the sample tree is absent.
                _viewerProcessed = false;
                ViewerInfo.Text = result.Status;
                ViewerStatus.Text = "viewer: registered arm — images absent";
                StatusText.Text = "engine: ready (registered arm: images absent)";
                return;
            }

            if (result.BeforePreview is not null)
                RenderHeatmap(ViewerBeforePlot, result.BeforePreview,
                    $"REAL {result.Kind} signal (QUARANTINE, ~512² preview)");
            if (result.AfterPreview is not null)
                RenderHeatmap(ViewerAfterPlot, result.AfterPreview,
                    $"REAL {result.Kind}-corrected (QUARANTINE, ~512² preview)");

            // All numbers are engine-computed (golden/numpy) — the UI derives nothing.
            ViewerInfo.Text =
                $"{result.Status}  file={result.SignalName}  calib={result.CalibName}  " +
                $"[shape {result.Rows}x{result.Cols}, dtype {result.Dtype}, finite={result.Finite}, " +
                $"std={result.Std:G4}, min={result.Min:G4}, max={result.Max:G4}, mean={result.Mean:G4}]  " +
                $"max|delta|={result.MaxAbsChangeFromInput:G4}  sane={result.Sane}";
            // The corrected output is held engine-side; enable Save when the arm was sane.
            _viewerProcessed = result.Sane;
            _viewerLoaded = false;   // registered arm supersedes any arbitrary-loaded frame
            ViewerStatus.Text = result.Sane
                ? $"viewer: {result.Kind} arm done (real correction, max|delta|={result.MaxAbsChangeFromInput:G4}) — click 'Save output...'"
                : $"viewer: {result.Kind} arm ran but SANITY FAILED";
            StatusText.Text = "engine: ready (registered arm done)";
        }
        catch (Exception ex)
        {
            StatusText.Text = "registered arm error: " + ex.Message;
        }
        finally
        {
            EndWork();
        }
    }

    private async void OpenImageButton_Click(object sender, RoutedEventArgs e)
    {
        // Resolve the path FIRST (env preset or native dialog), off the busy guard so
        // a cancelled dialog leaves state untouched.
        string? path = Environment.GetEnvironmentVariable("XDET_VIEWER_OPEN_PATH");
        if (string.IsNullOrWhiteSpace(path))
        {
            var dlg = new Microsoft.Win32.OpenFileDialog
            {
                Title = "Open 16-bit raw test image",
                Filter = "Raw 16-bit (*.raw)|*.raw|All (*.*)|*.*",
            };
            if (dlg.ShowDialog() != true) return;
            path = dlg.FileName;
        }

        if (!TryBeginWork()) return;
        try
        {
            string p = path!;
            LoadedFrameInfo info = await Task.Run(() => Seam!.LoadRawFrame(p));

            if (!info.Loaded)
            {
                _viewerLoaded = false;
                _viewerProcessed = false;
                ViewerInfo.Text = info.Status;
                ViewerStatus.Text = "viewer: load failed";
                StatusText.Text = "viewer: load failed";
                return;
            }

            if (info.Preview is not null)
                RenderHeatmap(ViewerBeforePlot, info.Preview, "loaded (QUARANTINE, ~512² preview)");
            // Clear any stale "after" from a previous frame.
            ViewerAfterPlot.Plot.Clear();
            ViewerAfterPlot.Refresh();

            ViewerInfo.Text =
                $"{info.Status}  min={info.Min:G4} max={info.Max:G4} mean={info.Mean:G4}";
            ViewerStatus.Text = "viewer: loaded — click 'Run offset'";
            _viewerLoaded = true;
            _viewerProcessed = false;
            StatusText.Text = "engine: ready (image loaded)";
        }
        catch (Exception ex)
        {
            StatusText.Text = "viewer load error: " + ex.Message;
        }
        finally
        {
            EndWork();
        }
    }

    private async void ViewerProcessButton_Click(object sender, RoutedEventArgs e)
    {
        if (!TryBeginWork()) return;
        try
        {
            ProcessedFrameInfo result = await Task.Run(() => Seam!.ProcessLoadedFrame());

            if (!result.Processed)
            {
                _viewerProcessed = false;
                ViewerStatus.Text = result.Status;
                StatusText.Text = "viewer: process failed";
                return;
            }

            if (result.BeforePreview is not null)
                RenderHeatmap(ViewerBeforePlot, result.BeforePreview, "before (QUARANTINE, ~512² preview)");
            if (result.AfterPreview is not null)
                RenderHeatmap(ViewerAfterPlot, result.AfterPreview, "after offset (QUARANTINE, ~512² preview)");

            ViewerInfo.Text =
                $"{result.Status}  out[min={result.OutputMin:G4}, max={result.OutputMax:G4}, mean={result.OutputMean:G4}]";
            ViewerStatus.Text = "viewer: processed — click 'Save output...'";
            _viewerProcessed = true;
            StatusText.Text = "engine: ready (offset done)";
        }
        catch (Exception ex)
        {
            StatusText.Text = "viewer process error: " + ex.Message;
        }
        finally
        {
            EndWork();
        }
    }

    private async void ViewerSaveButton_Click(object sender, RoutedEventArgs e)
    {
        string? path = Environment.GetEnvironmentVariable("XDET_VIEWER_SAVE_PATH");
        if (string.IsNullOrWhiteSpace(path))
        {
            var dlg = new Microsoft.Win32.SaveFileDialog
            {
                Title = "Save processed frame",
                Filter = "XFrame npz (*.npz)|*.npz|All (*.*)|*.*",
                DefaultExt = ".npz",
                FileName = "processed.npz",
            };
            if (dlg.ShowDialog() != true) return;
            path = dlg.FileName;
        }

        if (!TryBeginWork()) return;
        try
        {
            string p = path!;
            SaveResult result = await Task.Run(() => Seam!.SaveProcessedFrame(p));

            // A guard rejection or error is reported in the status line, never a crash.
            ViewerStatus.Text = result.Success
                ? $"viewer: saved -> {result.Path}"
                : (result.GuardRejected ? "viewer: save refused (C-20) — " : "viewer: save failed — ") + result.Message;
            StatusText.Text = result.Success
                ? "engine: ready (saved)"
                : (result.GuardRejected ? "viewer: save refused (C-20 guard)" : "viewer: save failed");
        }
        catch (Exception ex)
        {
            StatusText.Text = "viewer save error: " + ex.Message;
        }
        finally
        {
            EndWork();
        }
    }

    // -- rendering (pure display: array selection + float->double cast only) ------

    /// <summary>Render a frame as a 2-D ScottPlot heatmap (row-major -> [row, col]).</summary>
    private static void RenderHeatmap(ScottPlot.WPF.WpfPlot view, FrameData frame, string title)
    {
        var grid = new double[frame.Rows, frame.Cols];
        for (int r = 0; r < frame.Rows; r++)
            for (int c = 0; c < frame.Cols; c++)
                grid[r, c] = frame.Pixels[r * frame.Cols + c];

        view.Plot.Clear();
        var heatmap = view.Plot.Add.Heatmap(grid);
        view.Plot.Add.ColorBar(heatmap);
        view.Plot.Title(title);
        view.Plot.XLabel("column");
        view.Plot.YLabel("row");
        view.Refresh();
    }

    private static void RenderMtf(ScottPlot.WPF.WpfPlot view, MtfResult result)
    {
        view.Plot.Clear();
        var curve = view.Plot.Add.Scatter(result.Frequencies, result.Mtf);
        curve.LegendText = "MTF";
        view.Plot.ShowLegend();
        view.Plot.Title("Presampled MTF (edge method)");
        view.Plot.XLabel("spatial frequency (lp/mm)");
        view.Plot.YLabel("MTF");
        view.Refresh();
    }

    // -- deterministic synthetic offset INPUT (mirrors the fidelity test) ---------
    // Building test INPUT is not DSP; it is the stimulus fed across the seam.
    private static (FrameData input, OffsetCalibData calib) MakeOffsetCase(int rows = 32, int cols = 32)
    {
        var pixels = new float[rows * cols];
        var omap = new float[rows * cols];
        for (int r = 0; r < rows; r++)
        {
            for (int c = 0; c < cols; c++)
            {
                int i = r * cols + c;
                pixels[i] = 3000f + r * 3f + c * 1.5f; // above raw floor, below S_th
                omap[i] = 200f + c * 0.5f;              // static dark map to subtract
            }
        }
        return (FrameData.FromPixels(pixels, rows, cols), new OffsetCalibData(omap, rows, cols));
    }

    // Synthetic INPUT + calibs for the minimal offset -> gain golden pipeline. Same
    // frame/O_map as the offset case, plus a flat gain map inside [gain_min, gain_max]
    // so both stages apply cleanly (no clamp / no invalid-gain flag). Not DSP — the
    // stimulus fed across the seam.
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
                pixels[i] = 3000f + r * 3f + c * 1.5f; // above raw floor, below S_th
                omap[i] = 200f + c * 0.5f;              // static dark map (offset)
                gmap[i] = 1.1f;                         // flat gain in [0.5, 2.0] (gain)
            }
        }
        return (FrameData.FromPixels(pixels, rows, cols),
                new OffsetCalibData(omap, rows, cols),
                new GainCalibData(gmap, rows, cols));
    }

    // -- UI busy-state guard ------------------------------------------------------

    private bool TryBeginWork()
    {
        if (_engine is null)
        {
            StatusText.Text = "engine: not ready yet";
            return false;
        }
        if (_busy) return false;
        _busy = true;
        OffsetButton.IsEnabled = false;
        MtfButton.IsEnabled = false;
        PipelineButton.IsEnabled = false;
        RealImageButton.IsEnabled = false;
        RunRegisteredArmButton.IsEnabled = false;
        OpenImageButton.IsEnabled = false;
        ViewerProcessButton.IsEnabled = false;
        ViewerSaveButton.IsEnabled = false;
        return true;
    }

    private void EndWork()
    {
        _busy = false;
        OffsetButton.IsEnabled = true;
        MtfButton.IsEnabled = true;
        PipelineButton.IsEnabled = true;
        RealImageButton.IsEnabled = true;
        // Viewer buttons follow the loop state: the registered-arm and Open buttons are
        // always available; Run offset needs an arbitrary-loaded frame; Save needs a
        // processed frame (from either the registered arm or the arbitrary offset).
        RunRegisteredArmButton.IsEnabled = true;
        OpenImageButton.IsEnabled = true;
        ViewerProcessButton.IsEnabled = _viewerLoaded;
        ViewerSaveButton.IsEnabled = _viewerProcessed;
    }
}
