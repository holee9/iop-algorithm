namespace Xdet.Engine.Contract;

// @MX:ANCHOR: [AUTO] `ProbeReadout.Read` is the sole display-tier pixel-probe readout
// shared by the WPF UI (CompareGroup hover) and the xUnit probe test.
// @MX:REASON: SPEC-VIEWER-001 C-03 requires the probe to read the STORED float32
// preview values (never a re-derived/rendered value); centralizing the read in one
// pure, CLR-only, testable function keeps the UI free of any array arithmetic (C-09)
// and lets the test assert "the value the UI shows == the stored array value".

/// <summary>
/// One probe reading: the integer pixel coordinate plus the STORED float32 value of
/// each preview (before / after / diff) at that pixel. Mirrors SPEC-VIEWER-001's
/// <c>ProbeReading</c> (apps/gui/probe.py) — the raw stored values, not the 8-bit
/// colormap-rendered values.
/// </summary>
public readonly record struct ProbeSample(
    int Row,
    int Col,
    bool InBounds,
    float Before,
    float After,
    float Diff);

/// <summary>
/// Pure display-tier probe readout (SPEC-VIEWER-001 C-03 analog of
/// <c>apps.gui.probe.probe_at</c>). Given the ENGINE-returned before/after/diff previews
/// (transport-form <see cref="FrameData"/>) and a pixel (row, col), it reads the STORED
/// float32 values directly from the preview buffers. No DSP, no colormap normalization —
/// a stored-array read exactly as VIEWER-001's probe reads <c>ImageLayer.array</c>. The UI
/// maps a plot coordinate to (row, col) via ScottPlot's own heatmap transform, then calls
/// this to obtain the values it displays; the same function is asserted headlessly in CI.
/// </summary>
public static class ProbeReadout
{
    /// <summary>True iff (row, col) is inside a (rows, cols) frame.</summary>
    public static bool InBounds(int row, int col, int rows, int cols)
        => row >= 0 && row < rows && col >= 0 && col < cols;

    /// <summary>The stored float32 value at (row, col) of a row-major preview.</summary>
    public static float ValueAt(FrameData frame, int row, int col)
        => frame.Pixels[row * frame.Cols + col];

    /// <summary>
    /// Read the stored before/after/diff values at (row, col). Bounds are taken from the
    /// <paramref name="before"/> preview (all three share the same preview shape). When
    /// out of range, <see cref="ProbeSample.InBounds"/> is false and the values are NaN.
    /// The diff value is read from the ENGINE-computed <paramref name="diff"/> preview
    /// (the stored signed value); it is never recomputed here when the preview is present.
    /// </summary>
    public static ProbeSample Read(FrameData before, FrameData after, FrameData? diff, int row, int col)
    {
        if (!InBounds(row, col, before.Rows, before.Cols))
            return new ProbeSample(row, col, false, float.NaN, float.NaN, float.NaN);

        float b = ValueAt(before, row, col);
        float a = InBounds(row, col, after.Rows, after.Cols) ? ValueAt(after, row, col) : float.NaN;
        float d = diff is not null && InBounds(row, col, diff.Rows, diff.Cols)
            ? ValueAt(diff, row, col)   // stored ENGINE-computed signed diff (C-03)
            : float.NaN;
        return new ProbeSample(row, col, true, b, a, d);
    }
}
