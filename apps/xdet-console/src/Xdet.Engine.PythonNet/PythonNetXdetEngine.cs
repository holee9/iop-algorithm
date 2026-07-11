using Python.Runtime;
using Xdet.Engine.Contract;

namespace Xdet.Engine.PythonNet;

/// <summary>
/// <see cref="IXdetEngine"/> backed by the frozen Python golden, embedded in-process
/// via pythonnet (SPEC-XSEAM-001 P1.5). The interop configuration is copied verbatim
/// from the proven diagnostic probe (apps/xdet-console/interop-probe/Program.cs):
/// the CPython that owns python312.dll is resolved from the uv .venv pyvenv.cfg, and
/// the repo root + site-packages are placed on sys.path.
///
/// Lifecycle: the interpreter is initialized exactly once per process (shared across
/// all engine instances and calls); every public method acquires the GIL for the
/// duration of its golden calls. No numeric DSP is reimplemented — the golden is the
/// single source of truth. Beyond the durable seam this class exposes reference /
/// diagnostic methods used only by the fidelity proof.
/// </summary>
public sealed class PythonNetXdetEngine : IXdetEngine
{
    private static readonly object InitGate = new();
    private static bool _initialized;

    public PythonNetXdetEngine() => EnsureInitialized();

    // -- interpreter bootstrap (verbatim probe config) ------------------------

    private static void EnsureInitialized()
    {
        if (_initialized) return;
        lock (InitGate)
        {
            if (_initialized) return;

            string repoRoot = FindRepoRoot();
            string venvCfg = File.ReadAllText(Path.Combine(repoRoot, ".venv", "pyvenv.cfg"));
            // pyvenv.cfg 'home = <base python dir>' owns python312.dll.
            string baseHome = "";
            foreach (var line in venvCfg.Split('\n'))
            {
                var t = line.Trim();
                if (t.StartsWith("home", StringComparison.OrdinalIgnoreCase) && t.Contains('='))
                    baseHome = t[(t.IndexOf('=') + 1)..].Trim();
            }
            string pythonDll = Path.Combine(baseHome, "python312.dll");
            string sitePackages = Path.Combine(repoRoot, ".venv", "Lib", "site-packages");

            Runtime.PythonDLL = pythonDll;
            PythonEngine.PythonHome = baseHome;
            PythonEngine.Initialize();
            using (Py.GIL())
            {
                dynamic sys = Py.Import("sys");
                sys.path.insert(0, sitePackages);
                sys.path.insert(0, repoRoot);
            }
            // Release the GIL held by the init thread so every later Py.GIL() call
            // (possibly on another thread) can acquire it cleanly.
            PythonEngine.BeginAllowThreads();
            _initialized = true;
        }
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (File.Exists(Path.Combine(dir.FullName, "pyproject.toml")) &&
                Directory.Exists(Path.Combine(dir.FullName, ".venv")))
            {
                return dir.FullName;
            }
            dir = dir.Parent;
        }
        throw new DirectoryNotFoundException(
            "repo root (pyproject.toml + .venv) not found above " + AppContext.BaseDirectory);
    }

    // -- durable seam (IXdetEngine) ------------------------------------------

    public FrameData RunOffset(FrameData input, OffsetCalibData calib, OffsetParams parameters)
    {
        EnsureInitialized();
        using (Py.GIL())
        {
            dynamic np = Py.Import("numpy");
            dynamic xframe = Py.Import("common.xframe");
            dynamic offset = Py.Import("modules.offset");

            PyObject pix = FloatArrayToNumpy(input.Pixels, input.Rows, input.Cols, np);
            dynamic frame = xframe.new_frame(pix);
            dynamic calibObj = BuildOffsetCalib(calib, np);
            dynamic paramsObj = BuildOffsetParams(parameters);

            dynamic outFrame = offset.process(frame, calibObj, paramsObj);
            return FrameFromXFrame(outFrame, np);
        }
    }

    public MtfResult ComputeMtf(FrameData input, MtfParams parameters)
    {
        EnsureInitialized();
        using (Py.GIL())
        {
            dynamic np = Py.Import("numpy");
            dynamic xframe = Py.Import("common.xframe");
            dynamic mtf = Py.Import("metrics.mtf");

            PyObject pix = FloatArrayToNumpy(input.Pixels, input.Rows, input.Cols, np);
            dynamic frame = xframe.new_frame(pix);
            PyObject paramsObj = BuildMtfParams(parameters);
            PyObject res = InvokeComputeMtf(mtf, (PyObject)frame, paramsObj, parameters.Direction);
            return MtfResultFromPy(res, np);
        }
    }

    public PipelineResult RunPipeline(
        FrameData input,
        OffsetCalibData offsetCalib, OffsetParams offsetParams,
        GainCalibData gainCalib, GainParams gainParams)
    {
        EnsureInitialized();
        using (Py.GIL())
        {
            dynamic np = Py.Import("numpy");
            dynamic xframe = Py.Import("common.xframe");
            dynamic orchestrator = Py.Import("pipeline.orchestrator");

            // C# input -> numpy -> golden XFrame. Composition + canonical order +
            // the CalibSet entry gate are all decided inside run_pipeline.
            PyObject pix = FloatArrayToNumpy(input.Pixels, input.Rows, input.Cols, np);
            dynamic frame = xframe.new_frame(pix);

            dynamic outFrame = RunGoldenPipeline(
                orchestrator, np, (PyObject)frame,
                offsetCalib, offsetParams, gainCalib, gainParams);

            FrameData output = FrameFromXFrame(outFrame, np);
            string[] stages = StagesFromHistory(outFrame);

            // Engine-side (numpy over the golden output) statistics — the UI does
            // no DSP (SPEC-VIEWER-001). max|output - input| is the golden's own
            // proof the pipeline actually transformed the frame.
            PyObject outPix = (PyObject)outFrame.pixel;
            double outMin = ItemAsDouble(np.min(outPix));
            double outMax = ItemAsDouble(np.max(outPix));
            double outMean = ItemAsDouble(np.mean(outPix));
            dynamic diffAbs = np.abs(np.subtract(np.asarray(outPix, np.float64), np.asarray(pix, np.float64)));
            double maxAbsChange = ItemAsDouble(np.max(diffAbs));

            return new PipelineResult(input, output, stages, outMin, outMax, outMean, maxAbsChange);
        }
    }

    // -- fidelity / reference surface (P1.5 proof only) ----------------------

    /// <summary>
    /// Marshal a CLR float[] into numpy and read it straight back out, proving the
    /// C#-to-numpy transport preserves every float32 bit (SPEC FIDELITY input path).
    /// </summary>
    public float[] RoundTripPixels(float[] pixels, int rows, int cols)
    {
        EnsureInitialized();
        using (Py.GIL())
        {
            dynamic np = Py.Import("numpy");
            PyObject arr = FloatArrayToNumpy(pixels, rows, cols, np);
            return NumpyToFloatArray(arr, np);
        }
    }

    /// <summary>
    /// Render the golden slanted-edge phantom and return its float32 pixels to C#.
    /// The pixels then re-enter Python via <see cref="ComputeMtf"/> (seam path) while
    /// the reference path rebuilds them Python-side — proving transport fidelity.
    /// </summary>
    public FrameData MakeSlantedEdge(EdgePhantomSpec spec)
    {
        EnsureInitialized();
        using (Py.GIL())
        {
            dynamic np = Py.Import("numpy");
            dynamic gen = Py.Import("tests.metrics.phantoms.generators");
            dynamic ep = MakeSlantedEdgePy(gen, spec);
            float[] pixels = NumpyToFloatArray(ep.frame.pixel, np);
            return FrameData.FromPixels(pixels, spec.Rows, spec.Cols);
        }
    }

    /// <summary>
    /// Pure-Python reference: build the edge phantom with the golden generator and
    /// run <c>metrics.mtf.compute_mtf</c> directly (no C# frame crossing the seam).
    /// </summary>
    public MtfResult ComputeMtfReference(EdgePhantomSpec spec, MtfParams parameters)
    {
        EnsureInitialized();
        using (Py.GIL())
        {
            dynamic np = Py.Import("numpy");
            dynamic gen = Py.Import("tests.metrics.phantoms.generators");
            dynamic mtf = Py.Import("metrics.mtf");

            dynamic ep = MakeSlantedEdgePy(gen, spec);
            PyObject paramsObj = BuildMtfParams(parameters);
            PyObject res = InvokeComputeMtf(mtf, (PyObject)ep.frame, paramsObj, parameters.Direction);
            return MtfResultFromPy(res, np);
        }
    }

    /// <summary>
    /// The offset-path fidelity comparator. Reconstructs <paramref name="csOutput"/>
    /// (the frame produced by the C# seam, <see cref="RunOffset"/>) as a golden
    /// XFrame (output_A), independently runs the golden offset on
    /// <paramref name="referenceInput"/> Python-side (output_B), and compares the two
    /// with the frozen <c>common.equivalence.diff_frames</c>.
    /// </summary>
    public EquivalenceResult VerifyOffsetAgainstPython(
        FrameData csOutput, FrameData referenceInput, OffsetCalibData calib, OffsetParams parameters)
    {
        EnsureInitialized();
        using (Py.GIL())
        {
            dynamic np = Py.Import("numpy");
            dynamic xframe = Py.Import("common.xframe");
            dynamic offset = Py.Import("modules.offset");
            dynamic equivalence = Py.Import("common.equivalence");

            // output_A: the seam's result, reconstructed as a golden XFrame.
            PyObject pixA = FloatArrayToNumpy(csOutput.Pixels, csOutput.Rows, csOutput.Cols, np);
            PyObject masksA = ByteArrayToNumpyU8(csOutput.Masks, csOutput.Rows, csOutput.Cols, np);
            dynamic noiseA = xframe.NoiseModel(csOutput.NoiseAlpha, csOutput.NoiseSigma);
            dynamic frameA = xframe.XFrame(pixA, masksA, noiseA);

            // output_B: the golden offset run directly on the reference input.
            PyObject pixB = FloatArrayToNumpy(referenceInput.Pixels, referenceInput.Rows, referenceInput.Cols, np);
            dynamic frameBIn = xframe.new_frame(pixB);
            dynamic calibObj = BuildOffsetCalib(calib, np);
            dynamic paramsObj = BuildOffsetParams(parameters);
            dynamic frameB = offset.process(frameBIn, calibObj, paramsObj);

            dynamic diff = equivalence.diff_frames(frameA, frameB);
            bool pixelEqual = ((PyObject)diff.pixel_equal).As<bool>();
            bool masksEqual = ((PyObject)diff.masks_equal).As<bool>();
            bool noiseEqual = ((PyObject)diff.noise_equal).As<bool>();
            double maxAbs = ((PyObject)diff.max_pixel_abs_diff).As<double>();
            return new EquivalenceResult(pixelEqual, masksEqual, noiseEqual, maxAbs);
        }
    }

    /// <summary>
    /// The pipeline-path fidelity comparator (mirrors <see cref="VerifyOffsetAgainstPython"/>).
    /// Reconstructs <paramref name="csOutput"/> (the frame produced by the C# seam,
    /// <see cref="RunPipeline"/>) as a golden XFrame (output_A), independently runs the
    /// SAME golden <c>offset -&gt; gain</c> pipeline on <paramref name="referenceInput"/>
    /// Python-side (output_B), and compares the two with the frozen
    /// <c>common.equivalence.diff_frames</c>.
    /// </summary>
    public EquivalenceResult VerifyPipelineAgainstPython(
        FrameData csOutput, FrameData referenceInput,
        OffsetCalibData offsetCalib, OffsetParams offsetParams,
        GainCalibData gainCalib, GainParams gainParams)
    {
        EnsureInitialized();
        using (Py.GIL())
        {
            dynamic np = Py.Import("numpy");
            dynamic xframe = Py.Import("common.xframe");
            dynamic orchestrator = Py.Import("pipeline.orchestrator");
            dynamic equivalence = Py.Import("common.equivalence");

            // output_A: the seam's result, reconstructed as a golden XFrame.
            PyObject pixA = FloatArrayToNumpy(csOutput.Pixels, csOutput.Rows, csOutput.Cols, np);
            PyObject masksA = ByteArrayToNumpyU8(csOutput.Masks, csOutput.Rows, csOutput.Cols, np);
            dynamic noiseA = xframe.NoiseModel(csOutput.NoiseAlpha, csOutput.NoiseSigma);
            dynamic frameA = xframe.XFrame(pixA, masksA, noiseA);

            // output_B: the golden pipeline run directly on the reference input.
            PyObject pixB = FloatArrayToNumpy(referenceInput.Pixels, referenceInput.Rows, referenceInput.Cols, np);
            dynamic frameBIn = xframe.new_frame(pixB);
            dynamic frameB = RunGoldenPipeline(
                orchestrator, np, (PyObject)frameBIn,
                offsetCalib, offsetParams, gainCalib, gainParams);

            dynamic diff = equivalence.diff_frames(frameA, frameB);
            bool pixelEqual = ((PyObject)diff.pixel_equal).As<bool>();
            bool masksEqual = ((PyObject)diff.masks_equal).As<bool>();
            bool noiseEqual = ((PyObject)diff.noise_equal).As<bool>();
            double maxAbs = ((PyObject)diff.max_pixel_abs_diff).As<double>();
            return new EquivalenceResult(pixelEqual, masksEqual, noiseEqual, maxAbs);
        }
    }

    // -- golden-object builders ----------------------------------------------

    private static dynamic BuildOffsetCalib(OffsetCalibData calib, dynamic np)
    {
        // Reuse the golden test helper so the OFFSET CalibSet is built exactly as
        // the Python suite builds it (O_map float32).
        dynamic corrections = Py.Import("tests.modules.phantoms.corrections");
        PyObject omap = FloatArrayToNumpy(calib.OffsetMap, calib.Rows, calib.Cols, np);
        return corrections.offset_calib(omap);
    }

    private static dynamic BuildGainCalib(GainCalibData calib, dynamic np)
    {
        // Reuse the golden test helper so the GAIN CalibSet is built exactly as the
        // Python suite builds it (single-point G_map float32, panel_id PANEL-A —
        // matching offset_calib so the entry gate's mutual panel_id check passes).
        dynamic corrections = Py.Import("tests.modules.phantoms.corrections");
        PyObject gmap = FloatArrayToNumpy(calib.GainMap, calib.Rows, calib.Cols, np);
        return corrections.gain_calib(gmap);
    }

    private static PyObject BuildGainParams(GainParams p)
    {
        dynamic contract = Py.Import("common.contract");
        using var d = new PyDict();
        using (var v = new PyFloat(p.GainMin)) d["gain_min"] = v;
        using (var v = new PyFloat(p.GainMax)) d["gain_max"] = v;
        dynamic paramsObj = contract.Params(d);
        return (PyObject)paramsObj;
    }

    /// <summary>
    /// Build the golden orchestrator objects for the minimal <c>offset -&gt; gain</c>
    /// pipeline and run <c>pipeline.orchestrator.run_pipeline</c>. The stage subset is
    /// a subsequence of CANONICAL_ORDER; the registry maps each stage to its module
    /// <c>process</c> callable (matching <c>tests/pipeline/test_post_stages.py</c>); the
    /// calib/params maps are built from the golden test helpers. run_pipeline owns the
    /// canonical order and the CalibSet entry gate.
    /// </summary>
    private static dynamic RunGoldenPipeline(
        dynamic orchestrator, dynamic np, PyObject frame,
        OffsetCalibData offsetCalib, OffsetParams offsetParams,
        GainCalibData gainCalib, GainParams gainParams)
    {
        using var stages = new PyTuple(new PyObject[] { new PyString("offset"), new PyString("gain") });
        dynamic definition = orchestrator.PipelineDefinition(stages);

        dynamic offsetMod = Py.Import("modules.offset");
        dynamic gainMod = Py.Import("modules.gain");

        using var registry = new PyDict();
        registry["offset"] = (PyObject)offsetMod.process;   // process CALLABLE, not the module object
        registry["gain"] = (PyObject)gainMod.process;

        using var calibMap = new PyDict();
        calibMap["offset"] = (PyObject)BuildOffsetCalib(offsetCalib, np);
        calibMap["gain"] = (PyObject)BuildGainCalib(gainCalib, np);

        using var paramsMap = new PyDict();
        paramsMap["offset"] = BuildOffsetParams(offsetParams);
        paramsMap["gain"] = BuildGainParams(gainParams);

        return orchestrator.run_pipeline(frame, definition, registry, calibMap, paramsMap);
    }

    private static string[] StagesFromHistory(dynamic frame)
    {
        // Stages actually run, read from the golden append-only history chain
        // (module_name per stage) — not inferred in C#.
        PyObject history = (PyObject)frame.history;
        long n = history.Length();
        var stages = new string[n];
        for (int i = 0; i < n; i++)
        {
            using PyObject entry = history[i];
            using PyObject name = entry.GetAttr("module_name");
            stages[i] = name.As<string>();
        }
        return stages;
    }

    private static double ItemAsDouble(dynamic numpyScalar)
    {
        // numpy scalars need .item() to narrow to a native Python float first.
        PyObject s = (PyObject)numpyScalar;
        using PyObject native = s.InvokeMethod("item");
        return native.As<double>();
    }

    private static PyObject BuildOffsetParams(OffsetParams parameters)
    {
        dynamic contract = Py.Import("common.contract");
        using var d = new PyDict();
        using (var v = new PyFloat(parameters.RawSaturationThreshold))
            d["raw_saturation_threshold"] = v;
        dynamic paramsObj = contract.Params(d);
        return (PyObject)paramsObj;
    }

    private static PyObject BuildMtfParams(MtfParams p)
    {
        dynamic contract = Py.Import("common.contract");
        using var d = new PyDict();
        using (var v = new PyFloat(p.PixelPitchMm)) d["pixel_pitch_mm"] = v;
        using (var v = new PyInt(p.Oversample)) d["mtf_oversample"] = v;
        using (var v = new PyFloat(p.AngleMinDeg)) d["mtf_angle_min_deg"] = v;
        using (var v = new PyFloat(p.AngleMaxDeg)) d["mtf_angle_max_deg"] = v;
        using (var v = new PyFloat(p.AngleMarginDeg)) d["mtf_angle_margin_deg"] = v;
        dynamic paramsObj = contract.Params(d);
        return (PyObject)paramsObj;
    }

    private static dynamic MakeSlantedEdgePy(dynamic gen, EdgePhantomSpec spec)
    {
        // Positional call -> seed defaults to None (noise-free, deterministic) and
        // edge_pos_frac defaults to 0.5.
        using var shape = new PyTuple(new PyObject[] { new PyInt(spec.Rows), new PyInt(spec.Cols) });
        return gen.make_slanted_edge(
            shape, spec.AngleDeg, spec.SigmaPx, spec.PitchMm, spec.Low, spec.High);
    }

    private static PyObject InvokeComputeMtf(dynamic mtf, PyObject frame, PyObject paramsObj, string direction)
    {
        // direction is a keyword-only parameter of compute_mtf; pass it via kwargs.
        using var kwargs = new PyDict();
        using (var dir = new PyString(direction))
            kwargs["direction"] = dir;
        PyObject func = mtf.compute_mtf;
        return func.Invoke(new[] { frame, paramsObj }, kwargs);
    }

    private static FrameData FrameFromXFrame(dynamic frame, dynamic np)
    {
        float[] pixels = NumpyToFloatArray(frame.pixel, np);
        byte[] masks = NumpyToByteArray(frame.masks, np);
        PyObject noise = frame.noise;
        double alpha = noise.GetAttr("alpha").As<double>();
        double sigma = noise.GetAttr("sigma").As<double>();
        PyObject shape = frame.pixel.shape;
        int rows = shape[0].As<int>();
        int cols = shape[1].As<int>();
        return new FrameData(pixels, rows, cols, masks, alpha, sigma);
    }

    private static MtfResult MtfResultFromPy(PyObject res, dynamic np)
    {
        dynamic r = res;
        double[] freqs = NumpyToDoubleArray(r.get("frequencies_lpmm"), np);
        double[] mtf = NumpyToDoubleArray(r.get("mtf"), np);
        double edgeAngle = ((PyObject)r.get("edge_angle_deg")).As<double>();
        double nyquist = ((PyObject)r.get("nyquist_lpmm")).As<double>();
        double mtfAtNyquist = ((PyObject)r.get("mtf_at_nyquist")).As<double>();
        return new MtfResult(freqs, mtf, edgeAngle, nyquist, mtfAtNyquist);
    }

    // -- bit-exact marshaling helpers ----------------------------------------

    private static PyObject FloatArrayToNumpy(float[] data, int rows, int cols, dynamic np)
    {
        using var lst = new PyList();
        foreach (var v in data)
        {
            // float32 -> Python float (double) is lossless; np cast back to float32
            // returns the original bits exactly.
            using var f = new PyFloat((double)v);
            lst.Append(f);
        }
        dynamic arr = np.array(lst, np.float32);
        if (rows > 0 && cols > 0)
            arr = arr.reshape(rows, cols);
        return (PyObject)arr;
    }

    private static PyObject ByteArrayToNumpyU8(byte[] data, int rows, int cols, dynamic np)
    {
        using var lst = new PyList();
        foreach (var b in data)
        {
            using var pi = new PyInt((int)b);
            lst.Append(pi);
        }
        dynamic arr = np.array(lst, np.uint8);
        if (rows > 0 && cols > 0)
            arr = arr.reshape(rows, cols);
        return (PyObject)arr;
    }

    private static float[] NumpyToFloatArray(dynamic arr, dynamic np)
    {
        // Strongly type the flattened array as PyObject so the int indexer binds at
        // compile time (a dynamic `flat[i]` mis-binds to PyObject.this[string]).
        PyObject flat = np.ascontiguousarray(arr, np.float32).reshape(-1);
        long n = flat.Length();
        var outv = new float[n];
        for (int i = 0; i < n; i++)
        {
            // .item() converts the numpy scalar to a native Python float; the
            // float32 value promotes to double losslessly and narrows back exactly.
            using PyObject scalar = flat[i];
            using PyObject native = scalar.InvokeMethod("item");
            outv[i] = (float)native.As<double>();
        }
        return outv;
    }

    private static double[] NumpyToDoubleArray(dynamic arr, dynamic np)
    {
        PyObject flat = np.ascontiguousarray(arr, np.float64).reshape(-1);
        long n = flat.Length();
        var outv = new double[n];
        for (int i = 0; i < n; i++)
        {
            using PyObject scalar = flat[i];
            using PyObject native = scalar.InvokeMethod("item");
            outv[i] = native.As<double>();
        }
        return outv;
    }

    private static byte[] NumpyToByteArray(dynamic arr, dynamic np)
    {
        PyObject flat = np.ascontiguousarray(arr, np.uint8).reshape(-1);
        long n = flat.Length();
        var outv = new byte[n];
        for (int i = 0; i < n; i++)
        {
            using PyObject scalar = flat[i];
            using PyObject native = scalar.InvokeMethod("item");
            outv[i] = (byte)native.As<long>();
        }
        return outv;
    }
}
