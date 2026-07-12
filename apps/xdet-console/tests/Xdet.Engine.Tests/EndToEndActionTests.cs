using Xdet.Engine.Contract;
using Xdet.Engine.PythonNet;
using Xunit;

namespace Xdet.Engine.Tests;

/// <summary>
/// SPEC-XSEAM-001 per-UI-action end-to-end proof. Each test drives the exact seam
/// path that one MainWindow button invokes, through the REAL Python golden, and
/// asserts a real, correct result (not merely "non-null"):
///   - Offset button   -> MakeOffsetCase + RunOffset            (golden offset, delta 0)
///   - MTF button       -> MakeSlantedEdge + ComputeMtf          (golden MTF, delta 0 + sane)
///   - Pipeline button  -> MakePipelineCase + RunPipeline        (golden offset->gain, delta 0)
/// The synthetic INPUT builders are copied verbatim from the corresponding
/// MainWindow helpers so the tests exercise precisely what each button feeds across
/// the seam. Every test is deterministic and headless (no WPF window is created);
/// parallelization is disabled assembly-wide (see FidelityTests.cs).
/// </summary>
public sealed class EndToEndActionTests
{
    private static readonly PythonNetXdetEngine Engine = new();

    // SWR-601 [B] default raw saturation threshold — same constant the UI uses.
    private const double RawSaturationThreshold = 0.98 * 65535.0;

    // -- action INPUT builders (verbatim from MainWindow) ---------------------

    /// <summary>Mirror of MainWindow.MakeOffsetCase — the Offset button's stimulus.</summary>
    private static (FrameData input, OffsetCalibData calib) MakeOffsetCase(int rows = 32, int cols = 32)
    {
        var pixels = new float[rows * cols];
        var omap = new float[rows * cols];
        for (int r = 0; r < rows; r++)
        {
            for (int c = 0; c < cols; c++)
            {
                int i = r * cols + c;
                pixels[i] = 3000f + r * 3f + c * 1.5f;
                omap[i] = 200f + c * 0.5f;
            }
        }
        return (FrameData.FromPixels(pixels, rows, cols), new OffsetCalibData(omap, rows, cols));
    }

    /// <summary>Mirror of MainWindow.MakePipelineCase — the Pipeline button's stimulus.</summary>
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

    // -- Offset action --------------------------------------------------------

    [Fact]
    public void Offset_action_produces_the_real_golden_offset_result()
    {
        var (input, calib) = MakeOffsetCase();
        var offsetParams = new OffsetParams(RawSaturationThreshold);

        // Exactly what OffsetButton_Click runs across the seam.
        FrameData output = Engine.RunOffset(input, calib, offsetParams);

        // It is the real golden offset: dark subtraction actually lowered the pixels.
        Assert.All(Range(output.Pixels.Length), i =>
            Assert.True(output.Pixels[i] <= input.Pixels[i],
                "offset must not raise pixel values above the input"));
        Assert.False(input.Pixels.AsSpan().SequenceEqual(output.Pixels),
            "offset must actually change the frame");

        // And it is bit-identical to a Python-direct golden offset run (delta 0).
        EquivalenceResult diff = Engine.VerifyOffsetAgainstPython(output, input, calib, offsetParams);
        Assert.True(diff.StructurallyEqual, "offset seam output is not structurally equal to the golden");
        Assert.Equal(0.0, diff.MaxPixelAbsDiff);
    }

    // -- MTF action -----------------------------------------------------------

    [Fact]
    public void Mtf_action_produces_the_real_golden_mtf_curve()
    {
        var spec = new EdgePhantomSpec();   // golden defaults: 128x128, 2 deg, sigma 0.6
        var mtfParams = new MtfParams();

        // Exactly what MtfButton_Click runs: render the golden edge phantom, then
        // compute its presampled MTF across the seam.
        FrameData phantom = Engine.MakeSlantedEdge(spec);
        MtfResult seam = Engine.ComputeMtf(phantom, mtfParams);

        // Element-wise identical to the pure-Python golden compute_mtf (delta 0).
        MtfResult reference = Engine.ComputeMtfReference(spec, mtfParams);
        Assert.True(seam.Frequencies.AsSpan().SequenceEqual(reference.Frequencies),
            "frequencies_lpmm differ between seam and golden");
        Assert.True(seam.Mtf.AsSpan().SequenceEqual(reference.Mtf),
            "mtf differ between seam and golden");

        // Physically sane: finite, DC == 1, strictly-increasing frequency axis,
        // and the curve rolls off (a blurred edge attenuates high frequencies).
        Assert.True(seam.Frequencies.Length > 1);
        Assert.All(seam.Frequencies, f => Assert.True(double.IsFinite(f)));
        Assert.All(seam.Mtf, m => Assert.True(double.IsFinite(m)));
        Assert.Equal(1.0, seam.Mtf[0]);                       // MTF starts at 1 (normalized DC)
        for (int i = 1; i < seam.Frequencies.Length; i++)
            Assert.True(seam.Frequencies[i] > seam.Frequencies[i - 1],
                "frequency axis must be strictly increasing");
        Assert.True(seam.MtfAtNyquist < seam.Mtf[0] && seam.MtfAtNyquist > 0.0,
            "MTF must decrease from DC toward Nyquist and stay positive");
    }

    // -- Pipeline action ------------------------------------------------------

    [Fact]
    public void Pipeline_action_produces_the_real_golden_offset_then_gain_result()
    {
        var (input, offsetCalib, gainCalib) = MakePipelineCase();
        var offsetParams = new OffsetParams(RawSaturationThreshold);
        var gainParams = new GainParams();

        // Exactly what PipelineButton_Click runs across the seam.
        PipelineResult result = Engine.RunPipeline(input, offsetCalib, offsetParams, gainCalib, gainParams);

        // The golden orchestrator ran the minimal offset -> gain slice, in order.
        Assert.Equal(new[] { "offset", "gain" }, result.StagesRun);

        // The pipeline actually transformed the input (engine-reported and observed).
        Assert.True(result.MaxAbsChangeFromInput > 0.0, "pipeline must change the frame");
        Assert.False(input.Pixels.AsSpan().SequenceEqual(result.Output.Pixels),
            "pipeline output must differ from the input");
        Assert.All(result.Output.Pixels, p => Assert.True(float.IsFinite(p)));

        // Bit-identical to a Python-direct orchestrator run of the same pipeline (delta 0).
        EquivalenceResult diff = Engine.VerifyPipelineAgainstPython(
            result.Output, input, offsetCalib, offsetParams, gainCalib, gainParams);
        Assert.True(diff.StructurallyEqual, "pipeline seam output is not structurally equal to the golden");
        Assert.Equal(0.0, diff.MaxPixelAbsDiff);
    }

    // -- Negative control: the pipeline fidelity check is not vacuous ---------

    [Fact]
    public void Pipeline_fidelity_fails_when_one_path_input_is_perturbed()
    {
        var (input, offsetCalib, gainCalib) = MakePipelineCase();
        var offsetParams = new OffsetParams(RawSaturationThreshold);
        var gainParams = new GainParams();

        // Perturb the SEAM path input by >> 1 float32 LSB near 3000 (~2.4e-4).
        var perturbedPixels = (float[])input.Pixels.Clone();
        perturbedPixels[100] += 5.0f;
        var perturbedInput = FrameData.FromPixels(perturbedPixels, input.Rows, input.Cols);

        PipelineResult result = Engine.RunPipeline(perturbedInput, offsetCalib, offsetParams, gainCalib, gainParams);

        // Reference path keeps the UNPERTURBED input, so the outputs must differ.
        EquivalenceResult diff = Engine.VerifyPipelineAgainstPython(
            result.Output, input, offsetCalib, offsetParams, gainCalib, gainParams);
        Assert.False(diff.StructurallyEqual, "perturbed input must break structural equality");
        Assert.True(diff.MaxPixelAbsDiff > 0.0, "perturbed input must yield a nonzero pixel diff");
    }

    private static IEnumerable<int> Range(int n)
    {
        for (int i = 0; i < n; i++) yield return i;
    }
}
