using System;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
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

    // The durable seam surface. The registered arms, the registered offset->gain pipeline,
    // the MTF metric and the Viewer P0 loop are all driven exclusively through this
    // interface, keeping the UI dependent on the contract, not the Python adapter.
    private IXdetEngine? Seam => _engine;

    private bool _busy;

    // SWR-601 [B] default raw saturation threshold (0.98 of the 16-bit full scale).
    private const double RawSaturationThreshold = 0.98 * 65535.0;

    // The two before/after/diff comparison groups (feat/xseam-ui-expand). Each owns its
    // tab's before/after/diff heatmaps + shared W/L inputs + hover probe (SPEC-VIEWER-001
    // C-01/C-03/C-06). Constructed after InitializeComponent so the named XAML elements
    // exist; the engine-computed diff is passed IN — the group never computes DSP (C-09).
    // The Viewer group renders the registered arms; the Pipeline group renders the
    // registered offset->gain pipeline. (The old synthetic Offset tab/group was removed —
    // its bit-exact seam path is still exercised headlessly by the fidelity tests.)
    private readonly CompareGroup _viewerGroup;
    private readonly CompareGroup _pipelineGroup;

    public MainWindow()
    {
        InitializeComponent();
        _viewerGroup = new CompareGroup(
            ViewerBeforePlot, ViewerAfterPlot, ViewerDiffPlot,
            ViewerWlMin, ViewerWlMax, ViewerWlAuto, ViewerProbeLabel);
        _pipelineGroup = new CompareGroup(
            PipelineInputPlot, PipelineOutputPlot, PipelineDiffPlot,
            PipelineWlMin, PipelineWlMax, PipelineWlAuto, PipelineProbeLabel);
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
                $"SYNTHETIC edge phantom (등록 세트 슬랜티드 엣지 없음, 실측 MTF는 지침 취득세트 #33 대기)  " +
                $"edge angle={result.EdgeAngleDeg:F2} deg  " +
                $"Nyquist={result.NyquistLpmm:F2} lp/mm  " +
                $"MTF@Nyquist={result.MtfAtNyquist:F3}";
            StatusText.Text = "engine: ready (MTF done, synthetic phantom)";
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

    /// <summary>
    /// Pipeline tab (feat/xseam-ui-expand): run the REAL <c>offset -&gt; gain</c> subsequence of
    /// CANONICAL_ORDER on the REGISTERED edrogi 아크릴 3072x3072 frame with a calib_map of the
    /// REAL CalibSets (MasterDark offset + CalSet_19008 gain) via
    /// <see cref="IXdetEngine.RunRegisteredPipeline"/>. The engine returns engine-downsampled
    /// before/after previews + the engine-computed signed diff + stage/stat info (incl. max|delta|,
    /// proving the REAL composed correction). The UI renders before / after / diff with the shared
    /// W/L + hover probe and performs no DSP (SPEC-VIEWER-001). QUARANTINE-labeled — never a golden.
    /// </summary>
    private async void PipelineButton_Click(object sender, RoutedEventArgs e)
    {
        if (!TryBeginWork()) return;
        try
        {
            // Seam call: C# -> golden orchestrator (REAL offset -> gain over the registered
            // 아크릴 frame + REAL calibs) -> C#. The orchestrator owns stage order + the CalibSet
            // entry gate; the UI supplies nothing but the click and renders what comes back.
            RegisteredPipelineResult result = await Task.Run(() => Seam!.RunRegisteredPipeline());

            if (!result.ImagesPresent)
            {
                // Honest, non-error verdict when the sample tree is absent.
                PipelineInfo.Text = result.Status;
                StatusText.Text = "engine: ready (registered pipeline: images absent)";
                return;
            }

            // The diff preview (after - before) is engine-computed (numpy) over the ~512² previews;
            // the UI renders before / after / diff with a diverging colormap and subtracts nothing (C-09).
            if (result.BeforePreview is not null && result.AfterPreview is not null)
                _pipelineGroup.Render(result.BeforePreview, result.AfterPreview,
                    result.DiffPreview, result.MaxAbsDiff,
                    "REAL signal (QUARANTINE, ~512² preview)",
                    "After REAL offset → gain (QUARANTINE, ~512² preview)");

            // All numbers are engine-computed (golden/numpy) — the UI derives nothing.
            PipelineInfo.Text =
                $"{result.Status}  file={result.SignalName}  calibs={result.OffsetCalibName}+{result.GainCalibName}  " +
                $"stages: {string.Join(" → ", result.StagesRun)} (intermediates={result.IntermediateCount})  " +
                $"out[min={result.OutputMin:G4}, max={result.OutputMax:G4}, mean={result.OutputMean:G4}]  " +
                $"max|delta|={result.MaxAbsChangeFromInput:G4}  sane={result.Sane}";
            StatusText.Text = result.Sane
                ? $"engine: ready (registered pipeline done, max|delta|={result.MaxAbsChangeFromInput:G4})"
                : "engine: ready (registered pipeline ran but SANITY FAILED)";
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

            // The diff preview is engine-computed (numpy, after-before on the ~512² previews);
            // the UI renders before / after / diff with a shared W/L + hover probe (C-09).
            if (result.BeforePreview is not null && result.AfterPreview is not null)
                _viewerGroup.Render(result.BeforePreview, result.AfterPreview,
                    result.DiffPreview, result.MaxAbsDiff,
                    $"REAL {result.Kind} signal (QUARANTINE, ~512² preview)",
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

            // Loaded-only state: render just the before preview; clear any stale after/diff.
            if (info.Preview is not null)
                _viewerGroup.RenderSingle(info.Preview, "loaded (QUARANTINE, ~512² preview)");

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

            // Engine-computed diff preview (numpy); the UI renders before / after / diff.
            if (result.BeforePreview is not null && result.AfterPreview is not null)
                _viewerGroup.Render(result.BeforePreview, result.AfterPreview,
                    result.DiffPreview, result.MaxAbsDiff,
                    "before (QUARANTINE, ~512² preview)", "after offset (QUARANTINE, ~512² preview)");

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

    /// <summary>Row-major FrameData -> ScottPlot [row, col] grid (display cast only, no DSP).</summary>
    private static double[,] ToGrid(FrameData frame)
    {
        var grid = new double[frame.Rows, frame.Cols];
        for (int r = 0; r < frame.Rows; r++)
            for (int c = 0; c < frame.Cols; c++)
                grid[r, c] = frame.Pixels[r * frame.Cols + c];
        return grid;
    }

    /// <summary>
    /// Fully reset a plot before a re-render: clear the plottables (the heatmap) AND remove
    /// every existing ColorBar. A ScottPlot ColorBar is an edge <c>IPanel</c>, NOT a
    /// plottable, so <c>Plot.Clear()</c> leaves it in place — without this, repeatedly
    /// rendering the same plot (e.g. the Viewer's offset/gain/defect arms) stacks colorbars
    /// that squeeze the heatmap to nothing.
    /// </summary>
    private static void ResetPlot(ScottPlot.WPF.WpfPlot view)
    {
        view.Plot.Clear();
        foreach (var bar in view.Plot.Axes.GetPanels().OfType<ScottPlot.Panels.ColorBar>().ToList())
            view.Plot.Remove(bar);
    }

    /// <summary>
    /// Render a frame as a 2-D ScottPlot heatmap (row-major -> [row, col]) and return the
    /// heatmap so callers can set a shared Window/Level color range (C-01). Pure display.
    /// </summary>
    private static ScottPlot.Plottables.Heatmap RenderHeatmap(
        ScottPlot.WPF.WpfPlot view, FrameData frame, string title)
    {
        ResetPlot(view);
        var heatmap = view.Plot.Add.Heatmap(ToGrid(frame));
        view.Plot.Add.ColorBar(heatmap);
        view.Plot.Title(title);
        view.Plot.XLabel("column");
        view.Plot.YLabel("row");
        view.Plot.Axes.AutoScale();   // fit the spatial axes to the frame every re-render
        view.Refresh();
        return heatmap;
    }

    /// <summary>
    /// Render the ENGINE-computed diff preview with a 0-centered diverging colormap over a
    /// SYMMETRIC ±max|diff| range (SPEC-VIEWER-001 C-06). Pure render: the diff array is
    /// engine-produced (numpy after-before); this only maps values to colors (blue negative,
    /// white 0, red positive). Returns the heatmap for the hover probe.
    /// </summary>
    private static ScottPlot.Plottables.Heatmap RenderDiffHeatmap(
        ScottPlot.WPF.WpfPlot view, FrameData diff, double maxAbsDiff, string title)
    {
        ResetPlot(view);
        var heatmap = view.Plot.Add.Heatmap(ToGrid(diff));
        heatmap.Colormap = MakeDivergingColormap();
        double peak = maxAbsDiff > 0.0 ? maxAbsDiff : 1.0;   // guard the all-zero-diff case
        heatmap.ManualRange = new ScottPlot.Range(-peak, peak);   // symmetric, 0 -> white
        view.Plot.Add.ColorBar(heatmap);
        view.Plot.Title(title);
        view.Plot.XLabel("column");
        view.Plot.YLabel("row");
        view.Plot.Axes.AutoScale();   // fit the spatial axes to the diff frame every re-render
        view.Refresh();
        return heatmap;
    }

    /// <summary>
    /// Blue-white-red diverging colormap mirroring SPEC-VIEWER-001's <c>_diverging_colormap</c>
    /// (apps/gui/layers.py): blue for negative, white at the 0 midpoint, red for positive.
    /// Paired with a symmetric ±range so 0 maps to white (C-06).
    /// </summary>
    private static ScottPlot.IColormap MakeDivergingColormap()
        => new ScottPlot.Colormaps.Custom(
            new[]
            {
                new ScottPlot.Color((byte)30, (byte)60, (byte)220, (byte)255),   // negative -> blue
                new ScottPlot.Color((byte)255, (byte)255, (byte)255, (byte)255), // zero -> white
                new ScottPlot.Color((byte)220, (byte)30, (byte)30, (byte)255),   // positive -> red
            },
            smooth: true);

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

    // -- before/after/diff comparison group (C-01/C-03/C-06) ----------------------

    /// <summary>
    /// A before/after/diff heatmap comparison group (feat/xseam-ui-expand), mirroring
    /// SPEC-VIEWER-001's <c>WindowLevelControl</c> + <c>CompareView</c> + hover probe
    /// (apps/gui/layers.py, apps/gui/probe.py). It owns one tab's three heatmaps and:
    /// <list type="bullet">
    ///   <item><b>Shared W/L (C-01):</b> two numeric inputs set the SAME color range on the
    ///   before AND after heatmaps (so they are visually comparable — fixing the old
    ///   independent auto-scale); 'Auto' resets to the before-preview min/max.</item>
    ///   <item><b>Diff heatmap (C-06):</b> the ENGINE-computed diff rendered with a 0-centered
    ///   diverging colormap over its own symmetric ±max|diff| range.</item>
    ///   <item><b>Pixel probe (C-03):</b> on hover, map the plot coordinate to a preview
    ///   (row,col) via ScottPlot's own heatmap transform, then read the STORED float32
    ///   before/after/diff values (via <see cref="ProbeReadout"/>) into a label.</item>
    /// </list>
    /// Pure render: it sets ScottPlot color ranges/colormaps and reads stored values; it
    /// computes NO DSP (the diff is engine-produced and passed in, C-09/C-11).
    /// </summary>
    private sealed class CompareGroup
    {
        private readonly ScottPlot.WPF.WpfPlot _beforePlot;
        private readonly ScottPlot.WPF.WpfPlot _afterPlot;
        private readonly ScottPlot.WPF.WpfPlot _diffPlot;
        private readonly TextBox _wlMin;
        private readonly TextBox _wlMax;
        private readonly TextBlock _probe;

        private FrameData? _before;
        private FrameData? _after;
        private FrameData? _diff;
        private ScottPlot.Plottables.Heatmap? _beforeHeat;
        private ScottPlot.Plottables.Heatmap? _afterHeat;
        private ScottPlot.Plottables.Heatmap? _diffHeat;
        private bool _suppressWl;      // ignore programmatic textbox writes (no feedback loop)
        private long _lastProbeTick;   // hover throttle timestamp

        public CompareGroup(
            ScottPlot.WPF.WpfPlot beforePlot, ScottPlot.WPF.WpfPlot afterPlot, ScottPlot.WPF.WpfPlot diffPlot,
            TextBox wlMin, TextBox wlMax, Button wlAuto, TextBlock probe)
        {
            _beforePlot = beforePlot;
            _afterPlot = afterPlot;
            _diffPlot = diffPlot;
            _wlMin = wlMin;
            _wlMax = wlMax;
            _probe = probe;

            _wlMin.TextChanged += (_, _) => OnWlChanged();
            _wlMax.TextChanged += (_, _) => OnWlChanged();
            wlAuto.Click += (_, _) => AutoWindowLevel();

            _beforePlot.MouseMove += OnHeatmapMouseMove;
            _afterPlot.MouseMove += OnHeatmapMouseMove;
            _diffPlot.MouseMove += OnHeatmapMouseMove;
        }

        /// <summary>
        /// Render before + after + the engine diff, seed the shared W/L from the before-preview
        /// min/max, and apply it to both before/after. The diff keeps its own symmetric range.
        /// </summary>
        public void Render(
            FrameData before, FrameData after, FrameData? diff, double maxAbsDiff,
            string titleBefore, string titleAfter)
        {
            _before = before;
            _after = after;
            _diff = diff;
            _beforeHeat = RenderHeatmap(_beforePlot, before, titleBefore);
            _afterHeat = RenderHeatmap(_afterPlot, after, titleAfter);

            (double lo, double hi) = MinMax(before);
            SetInputs(lo, hi);
            ApplyWindowLevel(lo, hi);

            if (diff is not null)
            {
                _diffHeat = RenderDiffHeatmap(_diffPlot, diff, maxAbsDiff, "diff (after - before)");
            }
            else
            {
                _diffHeat = null;
                ResetPlot(_diffPlot);
                _diffPlot.Refresh();
            }
            _probe.Text = "probe (row,col): move mouse over a heatmap";
        }

        /// <summary>
        /// Render a single before-only frame (the loaded-but-not-processed state): clear the
        /// after/diff heatmaps and seed the shared W/L from this frame.
        /// </summary>
        public void RenderSingle(FrameData frame, string title)
        {
            _before = frame;
            _after = null;
            _diff = null;
            _beforeHeat = RenderHeatmap(_beforePlot, frame, title);
            _afterHeat = null;
            ResetPlot(_afterPlot);
            _afterPlot.Refresh();
            _diffHeat = null;
            ResetPlot(_diffPlot);
            _diffPlot.Refresh();

            (double lo, double hi) = MinMax(frame);
            SetInputs(lo, hi);
            ApplyWindowLevel(lo, hi);
            _probe.Text = "probe (row,col): move mouse over a heatmap";
        }

        private void OnWlChanged()
        {
            if (_suppressWl) return;
            if (double.TryParse(_wlMin.Text, out double lo) && double.TryParse(_wlMax.Text, out double hi))
                ApplyWindowLevel(lo, hi);
        }

        private void AutoWindowLevel()
        {
            if (_before is null) return;
            (double lo, double hi) = MinMax(_before);
            SetInputs(lo, hi);
            ApplyWindowLevel(lo, hi);
        }

        /// <summary>Apply the SAME color range to the before AND after heatmaps (C-01, pure render).</summary>
        private void ApplyWindowLevel(double low, double high)
        {
            if (high <= low) high += 1.0;
            var range = new ScottPlot.Range(low, high);
            if (_beforeHeat is not null) { _beforeHeat.ManualRange = range; _beforePlot.Refresh(); }
            if (_afterHeat is not null) { _afterHeat.ManualRange = range; _afterPlot.Refresh(); }
        }

        private void SetInputs(double lo, double hi)
        {
            _suppressWl = true;
            _wlMin.Text = lo.ToString("G6");
            _wlMax.Text = hi.ToString("G6");
            _suppressWl = false;
        }

        /// <summary>
        /// Hover probe (C-03): map the mouse pixel to a plot coordinate, then to a preview
        /// (row,col) via ScottPlot's OWN heatmap inverse transform (C-02 analog — never a
        /// re-derived pan/zoom transform), and show the STORED before/after/diff values.
        /// Throttled to ~30 Hz to avoid spamming the label on every raw mouse-move.
        /// </summary>
        private void OnHeatmapMouseMove(object sender, MouseEventArgs e)
        {
            if (_before is null) return;
            long now = Environment.TickCount64;
            if (now - _lastProbeTick < 33) return;
            _lastProbeTick = now;

            var plot = (ScottPlot.WPF.WpfPlot)sender;
            ScottPlot.Plottables.Heatmap? hm =
                ReferenceEquals(plot, _beforePlot) ? _beforeHeat :
                ReferenceEquals(plot, _afterPlot) ? _afterHeat : _diffHeat;
            if (hm is null) return;

            ScottPlot.Pixel px = plot.GetPlotPixelPosition(e);
            ScottPlot.Coordinates coord = plot.Plot.GetCoordinates(px);
            (int col, int row) = hm.GetIndexes(coord);   // ScottPlot's own inverse transform

            ProbeSample s = ProbeReadout.Read(_before, _after ?? _before, _diff, row, col);
            if (!s.InBounds)
            {
                _probe.Text = $"probe (row,col)=({row},{col}): out of range";
                return;
            }
            string after = _after is null ? "-" : s.After.ToString("G6");
            string diff = _diff is null ? "-" : s.Diff.ToString("G6");
            _probe.Text = $"probe (row,col)=({s.Row},{s.Col}): before={s.Before:G6} after={after} diff={diff}";
        }

        /// <summary>
        /// Min/max of a preview for the default display window (mirrors SPEC-VIEWER-001
        /// <c>make_image_layer</c>: float(np.min)/float(np.max)) — a display-range selection,
        /// not pipeline DSP. The engine still owns all real numeric processing (C-09).
        /// </summary>
        private static (double lo, double hi) MinMax(FrameData f)
        {
            if (f.Pixels.Length == 0) return (0.0, 1.0);
            float lo = f.Pixels[0], hi = f.Pixels[0];
            foreach (float v in f.Pixels)
            {
                if (v < lo) lo = v;
                if (v > hi) hi = v;
            }
            return (lo, hi);
        }
    }
}
