using System;
using System.Threading.Tasks;
using System.Windows;
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

            RenderRow(OffsetPlot, input, output);

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

    // -- rendering (pure display: array selection + float->double cast only) ------

    private static void RenderRow(ScottPlot.WPF.WpfPlot view, FrameData input, FrameData output)
    {
        int row = input.Rows / 2;
        var xs = new double[input.Cols];
        var before = new double[input.Cols];
        var after = new double[input.Cols];
        for (int c = 0; c < input.Cols; c++)
        {
            int idx = row * input.Cols + c;
            xs[c] = c;
            before[c] = input.Pixels[idx];
            after[c] = output.Pixels[idx];
        }

        view.Plot.Clear();
        var s1 = view.Plot.Add.Scatter(xs, before);
        s1.LegendText = "input";
        var s2 = view.Plot.Add.Scatter(xs, after);
        s2.LegendText = "offset-corrected";
        view.Plot.ShowLegend();
        view.Plot.Title($"Offset (SWR-101~104) - row {row}");
        view.Plot.XLabel("column");
        view.Plot.YLabel("pixel value");
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
        return true;
    }

    private void EndWork()
    {
        _busy = false;
        OffsetButton.IsEnabled = true;
        MtfButton.IsEnabled = true;
    }
}
