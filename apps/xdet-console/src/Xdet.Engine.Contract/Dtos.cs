namespace Xdet.Engine.Contract;

// SPEC-XSEAM-001 P1.5 thin-slice seam DTOs. Deliberately built only from CLR
// primitives + arrays so the contract carries no pythonnet (or any golden-model)
// type. A NativeXdetEngine must be able to produce/consume these unchanged.

/// <summary>
/// A frame in transport form: row-major float32 pixels plus the mask stack
/// (uint8 bit-flags) and the (alpha, sigma) noise model. Mirrors the load-bearing
/// state of the Python golden <c>XFrame</c> that the fidelity comparator inspects
/// (pixel / masks / noise); history is intentionally omitted (not compared by
/// <c>common.equivalence.diff_frames</c>).
/// </summary>
public sealed record FrameData(
    float[] Pixels,
    int Rows,
    int Cols,
    byte[] Masks,
    double NoiseAlpha,
    double NoiseSigma)
{
    /// <summary>Fresh frame: zeroed masks, zero noise model.</summary>
    public static FrameData FromPixels(float[] pixels, int rows, int cols)
        => new(pixels, rows, cols, new byte[pixels.Length], 0.0, 0.0);
}

/// <summary>CalibSet(OFFSET) payload: the static dark map O(x,y) (<c>O_map</c>).</summary>
public sealed record OffsetCalibData(float[] OffsetMap, int Rows, int Cols);

/// <summary>
/// Offset-stage parameters. Only the required raw saturation threshold S_th
/// (<c>raw_saturation_threshold</c>, SWR-601 [B]); the golden module refuses a
/// silent in-module default (SWR-000-5).
/// </summary>
public sealed record OffsetParams(double RawSaturationThreshold);

/// <summary>
/// MTF-stage parameters (measurement protocol phantom defaults). All values are
/// externalized (REQ-METRICS-CORE-4); none is baked into the golden.
/// </summary>
public sealed record MtfParams(
    double PixelPitchMm = 0.14,
    int Oversample = 4,
    double AngleMinDeg = 1.5,
    double AngleMaxDeg = 3.0,
    double AngleMarginDeg = 0.2,
    string Direction = "vertical");

/// <summary>Presampled-MTF result: the frequency axis (lp/mm) and the MTF curve.</summary>
public sealed record MtfResult(
    double[] Frequencies,
    double[] Mtf,
    double EdgeAngleDeg,
    double NyquistLpmm,
    double MtfAtNyquist);

/// <summary>
/// Result of the golden <c>common.equivalence.diff_frames</c> comparator over two
/// candidate outputs. <see cref="StructurallyEqual"/> mirrors the Python property.
/// </summary>
public sealed record EquivalenceResult(
    bool PixelEqual,
    bool MasksEqual,
    bool NoiseEqual,
    double MaxPixelAbsDiff)
{
    public bool StructurallyEqual => PixelEqual && MasksEqual && NoiseEqual;
}

/// <summary>
/// Slanted-edge phantom spec forwarded to the golden generator
/// (<c>tests.metrics.phantoms.generators.make_slanted_edge</c>). No seed field:
/// the analytic (erf) edge is rendered noise-free and fully deterministic.
/// </summary>
public sealed record EdgePhantomSpec(
    int Rows = 128,
    int Cols = 128,
    double AngleDeg = 2.0,
    double SigmaPx = 0.6,
    double PitchMm = 0.14,
    double Low = 1000.0,
    double High = 5000.0);
