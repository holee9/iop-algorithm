using Xdet.Engine.Contract;
using Xdet.Engine.PythonNet;
using Xunit;

// Embedded CPython is a single interpreter guarded by one GIL; serialize tests.
[assembly: CollectionBehavior(DisableTestParallelization = true)]

namespace Xdet.Engine.Tests;

/// <summary>
/// SPEC-XSEAM-001 P1.5 thin-slice fidelity proof. Each test drives the C# seam and
/// an independent pure-Python reference over the SAME golden code, then asserts the
/// two agree bit-identically. The engine is shared across tests (the interpreter is
/// initialized once per process).
/// </summary>
public sealed class FidelityTests
{
    private static readonly PythonNetXdetEngine Engine = new();

    private const double RawSaturationThreshold = 0.98 * 65535.0; // SWR-601 [B] default

    /// <summary>Deterministic C#-originated offset input: signal well above the raw
    /// floor (no clamping) and below S_th (no saturation), with an O_map to subtract.</summary>
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

    // -- FIDELITY-2: offset module bit-identical + lossless input marshaling ---

    [Fact]
    public void Offset_seam_reproduces_python_golden_bit_identically()
    {
        var (input, calib) = MakeOffsetCase();
        var offsetParams = new OffsetParams(RawSaturationThreshold);

        // output_A: produced by the C# seam (C# -> numpy -> XFrame -> offset.process -> C#).
        FrameData outputA = Engine.RunOffset(input, calib, offsetParams);

        // output_B built Python-side from identical values; compared via the golden
        // common.equivalence.diff_frames comparator.
        EquivalenceResult diff = Engine.VerifyOffsetAgainstPython(outputA, input, calib, offsetParams);

        Assert.True(diff.StructurallyEqual, "offset seam output is not structurally equal to the golden");
        Assert.True(diff.PixelEqual);
        Assert.True(diff.MasksEqual);
        Assert.True(diff.NoiseEqual);
        Assert.Equal(0.0, diff.MaxPixelAbsDiff); // EXACTLY zero: P1.5 is pure transport
    }

    [Fact]
    public void Offset_input_marshaling_round_trips_bit_identically()
    {
        var (input, _) = MakeOffsetCase();

        float[] roundTripped = Engine.RoundTripPixels(input.Pixels, input.Rows, input.Cols);

        Assert.Equal(input.Pixels.Length, roundTripped.Length);
        Assert.True(input.Pixels.AsSpan().SequenceEqual(roundTripped),
            "C# -> numpy -> C# float32 transport was not bit-identical");
    }

    // -- FIDELITY-3: MTF metric element-wise EXACTLY equal -------------------

    [Fact]
    public void Mtf_seam_reproduces_python_golden_exactly()
    {
        var spec = new EdgePhantomSpec(); // golden defaults: 128x128, 2 deg, sigma 0.6
        var mtfParams = new MtfParams();

        // Seam path: golden generator -> C# pixels -> back through the seam -> compute_mtf.
        FrameData phantom = Engine.MakeSlantedEdge(spec);
        MtfResult seam = Engine.ComputeMtf(phantom, mtfParams);

        // Reference path: build the phantom + compute_mtf entirely in Python.
        MtfResult reference = Engine.ComputeMtfReference(spec, mtfParams);

        Assert.Equal(reference.Frequencies.Length, seam.Frequencies.Length);
        Assert.Equal(reference.Mtf.Length, seam.Mtf.Length);
        Assert.True(seam.Frequencies.AsSpan().SequenceEqual(reference.Frequencies),
            "frequencies_lpmm differ between seam and golden");
        Assert.True(seam.Mtf.AsSpan().SequenceEqual(reference.Mtf),
            "mtf differ between seam and golden");
        // Sanity: a real MTF curve was produced (DC == 1, curve rolls off).
        Assert.Equal(1.0, seam.Mtf[0]);
        Assert.True(seam.Frequencies.Length > 1);
    }

    // -- Negative control: the fidelity check is not vacuous -----------------

    [Fact]
    public void Offset_fidelity_fails_when_one_path_input_is_perturbed()
    {
        var (input, calib) = MakeOffsetCase();
        var offsetParams = new OffsetParams(RawSaturationThreshold);

        // Perturb the SEAM path input by >> 1 float32 LSB (LSB near 3000 is ~2.4e-4).
        var perturbedPixels = (float[])input.Pixels.Clone();
        perturbedPixels[100] += 5.0f;
        var perturbedInput = FrameData.FromPixels(perturbedPixels, input.Rows, input.Cols);

        FrameData outputA = Engine.RunOffset(perturbedInput, calib, offsetParams);

        // Reference path keeps the UNPERTURBED input, so the two outputs must differ.
        EquivalenceResult diff = Engine.VerifyOffsetAgainstPython(outputA, input, calib, offsetParams);

        Assert.False(diff.StructurallyEqual, "perturbed input must break structural equality");
        Assert.False(diff.PixelEqual);
        Assert.True(diff.MaxPixelAbsDiff > 0.0, "perturbed input must yield a nonzero pixel diff");
    }
}
