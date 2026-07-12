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

    // Viewer P0-loop adapter state: the loaded raw frame and the processed output,
    // held as live golden XFrame handles ACROSS LoadRawFrame -> ProcessLoadedFrame ->
    // SaveProcessedFrame (the interface methods are stateless in signature). Only
    // touched under Py.GIL(); replaced (old handle disposed) on each new load/process.
    private PyObject? _loadedFrame;
    private PyObject? _processedFrame;

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

    // -- QUARANTINE real-image plumbing/sanity (SPEC-REALDATA-001) ------------

    /// <summary>
    /// [HARD] QUARANTINE plumbing/sanity ONLY. Mirrors the frozen realdata sample arm
    /// (<c>tests/test_tc_realdata_arms.py::test_tc_001_offset_arm_sanity</c>) EXACTLY:
    /// <c>require_edrogi</c> -&gt; first non-<c>_result</c> raw under <c>아크릴</c> via
    /// <c>_load_full</c> (signal) -&gt; <c>build_offset_calibset</c> from
    /// <c>16bit cal/MasterDark.raw</c> (via <c>_load_full</c>) -&gt;
    /// <c>modules.offset.process(signal, calib, corr_params())</c> -&gt; the
    /// <c>_assert_sane</c> checks. No new load/DSP path is invented and nothing is fitted,
    /// tuned, or treated as a numeric golden. The stats + downsampled before/after previews
    /// are all produced HERE (engine-side numpy), never in the UI (SPEC-VIEWER-001).
    /// </summary>
    public RealImageSanityResult RunRealImageOffsetSanity()
    {
        EnsureInitialized();
        using (Py.GIL())
        {
            dynamic np = Py.Import("numpy");
            dynamic builtins = Py.Import("builtins");
            dynamic pathlib = Py.Import("pathlib");
            dynamic ing = Py.Import("scripts.ingest_edrogi");
            dynamic offset = Py.Import("modules.offset");
            dynamic corrections = Py.Import("tests.modules.phantoms.corrections");

            // Resolve the sample tree by an ABSOLUTE path so the verdict does not depend
            // on the launched app's working directory. require_edrogi/edrogi_available
            // both accept an explicit root; passing the absolute repo path reuses the
            // frozen helpers unchanged while staying CWD-independent.
            string edrogiRoot = Path.Combine(FindRepoRoot(), "images", "에드로지16BIT");

            // Availability is a clean bool (no pytest.skip raise) — reuse edrogi_available.
            bool available = ((PyObject)ing.edrogi_available(edrogiRoot)).As<bool>();
            if (!available)
                return RealImageSanityResult.Absent(edrogiRoot);

            // Reuse require_edrogi verbatim (asserts presence; no skip when available).
            ing.require_edrogi(edrogiRoot);

            // signal := first non-"_result" raw under 아크릴 (mirror of the arm's _first_raw:
            // sorted(rglob("*.raw")), skip vendor "_result.raw" outputs).
            dynamic acrylicDir = pathlib.Path(Path.Combine(edrogiRoot, "아크릴"));
            PyObject sortedRaws = (PyObject)builtins.sorted(acrylicDir.rglob("*.raw"));
            string signalFull = "";
            string signalName = "";
            long nRaw = sortedRaws.Length();
            for (long i = 0; i < nRaw; i++)
            {
                using PyObject p = sortedRaws[(int)i];
                string name = ((PyObject)p.GetAttr("name")).As<string>();
                if (!name.EndsWith("_result.raw", StringComparison.Ordinal))
                {
                    signalFull = p.ToString() ?? "";
                    signalName = name;
                    break;
                }
            }
            if (signalFull.Length == 0)
                return new RealImageSanityResult(
                    true, false,
                    "QUARANTINE 배관/sanity (수치 golden 아님): no signal raw under 아크릴",
                    "", 0, 0, "", false, 0.0, 0.0, 0.0, 0.0, null, null);

            // Load exactly as the arm does: _load_full (signal + MasterDark), then
            // build_offset_calibset(MasterDark) and offset.process(signal, calib, corr_params()).
            dynamic signal = ing._load_full(pathlib.Path(signalFull));
            string masterdarkFull = Path.Combine(edrogiRoot, "16bit cal", "MasterDark.raw");
            dynamic masterdark = ing._load_full(pathlib.Path(masterdarkFull));
            dynamic calib = ing.build_offset_calibset(masterdark);
            dynamic corrParams = corrections.corr_params();
            dynamic outFrame = offset.process(signal, calib, corrParams);

            // Sanity verdict — the _assert_sane checks, computed engine-side over the golden
            // output: shape (3072,3072) / dtype float32 / all-finite / std > 0 (non-degenerate).
            PyObject outPix = (PyObject)outFrame.pixel;
            PyObject shape = (PyObject)outFrame.pixel.shape;
            int rows = ((PyObject)shape[0]).As<int>();
            int cols = ((PyObject)shape[1]).As<int>();
            string dtype = ((PyObject)outFrame.pixel.dtype.name).As<string>();
            bool finite = ItemAsBool(np.all(np.isfinite(outPix)));
            double std = ItemAsDouble(np.std(outPix));
            double min = ItemAsDouble(np.min(outPix));
            double max = ItemAsDouble(np.max(outPix));
            double mean = ItemAsDouble(np.mean(outPix));
            bool sane = rows == 3072 && cols == 3072 && dtype == "float32" && finite && std > 0.0;

            // Downsample the raw signal (before) and the offset output (after) to ~512x512
            // ENGINE-side (block-mean) so the UI renders heatmaps with zero DSP.
            FrameData before = DownsamplePreview((PyObject)signal.pixel, np, builtins, 512);
            FrameData after = DownsamplePreview(outPix, np, builtins, 512);

            string status = sane
                ? $"QUARANTINE 배관/sanity (수치 golden 아님): offset EXECUTED on real {rows}x{cols} frame; "
                  + $"finite={finite}, std={std:G4} (>0), dtype={dtype}"
                : $"QUARANTINE 배관/sanity (수치 golden 아님): SANITY FAILED "
                  + $"(shape={rows}x{cols}, dtype={dtype}, finite={finite}, std={std:G4})";

            return new RealImageSanityResult(
                true, sane, status, signalName, rows, cols, dtype, finite, std, min, max, mean,
                before, after);
        }
    }

    // -- Viewer P0 loop: open arbitrary image -> process -> save --------------

    public LoadedFrameInfo LoadRawFrame(string path, int rows = 0, int cols = 0)
    {
        EnsureInitialized();
        if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
            return LoadedFrameInfo.Failed("load error: file not found — " + (path ?? "(null)"));

        using (Py.GIL())
        {
            dynamic np = Py.Import("numpy");
            dynamic builtins = Py.Import("builtins");
            dynamic xframe = Py.Import("common.xframe");

            string name = Path.GetFileName(path);
            // common.io sidecar convention: <name>.raw + <name>.json.
            string sidecar = Path.ChangeExtension(path, ".json");

            dynamic frame;
            int r;
            int c;
            try
            {
                if (File.Exists(sidecar))
                {
                    // Golden loader: raw16 + JSON sidecar ('resolution' required).
                    dynamic io = Py.Import("common.io");
                    frame = io.load_raw_frame(path);
                    PyObject shape = (PyObject)frame.pixel.shape;
                    r = ((PyObject)shape[0]).As<int>();
                    c = ((PyObject)shape[1]).As<int>();
                }
                else
                {
                    // No sidecar: infer the shape from the payload size (uint16).
                    dynamic raw = np.fromfile(path, "<u2");
                    long n = ((PyObject)raw.size).As<long>();
                    if (!TryInferShape(n, rows, cols, out r, out c))
                        return LoadedFrameInfo.Failed(
                            $"load error: cannot resolve shape for {name} ({n} uint16 pixels); "
                            + "pass rows/cols or provide a <name>.json sidecar with 'resolution'");
                    dynamic pix = raw.reshape(r, c).astype(np.float32);
                    frame = xframe.new_frame(pix);
                }
            }
            catch (Exception ex)
            {
                return LoadedFrameInfo.Failed("load error: " + ex.Message);
            }

            // Adopt as adapter state (dispose the prior loaded/processed handles).
            _processedFrame?.Dispose();
            _processedFrame = null;
            _loadedFrame?.Dispose();
            _loadedFrame = (PyObject)frame;

            // Engine-side stats + ~512x512 preview (the UI does no DSP).
            PyObject pixObj = (PyObject)frame.pixel;
            string dtype = ((PyObject)frame.pixel.dtype.name).As<string>();
            bool finite = ItemAsBool(np.all(np.isfinite(pixObj)));
            double min = ItemAsDouble(np.min(pixObj));
            double max = ItemAsDouble(np.max(pixObj));
            double mean = ItemAsDouble(np.mean(pixObj));
            FrameData preview = DownsamplePreview(pixObj, np, builtins, 512);

            string status =
                $"QUARANTINE 배관/sanity (수치 golden 아님): loaded {name} "
                + $"[{r}x{c}, dtype {dtype}, finite={finite}]";
            return new LoadedFrameInfo(true, status, name, r, c, dtype, finite, min, max, mean, preview);
        }
    }

    public ProcessedFrameInfo ProcessLoadedFrame()
    {
        EnsureInitialized();
        using (Py.GIL())
        {
            if (_loadedFrame is null)
                return ProcessedFrameInfo.Failed("process error: load a frame first");

            dynamic np = Py.Import("numpy");
            dynamic builtins = Py.Import("builtins");
            dynamic dataclasses = Py.Import("dataclasses");
            dynamic synth = Py.Import("common.synth_calibset");
            dynamic orchestrator = Py.Import("pipeline.orchestrator");
            dynamic offset = Py.Import("modules.offset");

            try
            {
                dynamic loaded = _loadedFrame;
                PyObject shapeObj = (PyObject)loaded.pixel.shape;
                int r = ((PyObject)shapeObj[0]).As<int>();
                int c = ((PyObject)shapeObj[1]).As<int>();

                // Blueprint CalibSet: make_synthetic_calibset(shape, OFFSET-kind). The
                // factory yields an EMPTY payload; offset.process REQUIRES an O_map, so
                // replace the payload with a synthetic ZERO dark — no measured
                // calibration exists for an arbitrary loaded frame, and a zero dark runs
                // the golden offset's subtract/clamp/saturation contract without
                // inventing a fitted correction (SWR-000-5: no silent default).
                dynamic kind = orchestrator.calib_kind_for_stage("offset");
                using var shapeTuple = new PyTuple(new PyObject[] { new PyInt(r), new PyInt(c) });
                dynamic calib0 = synth.make_synthetic_calibset(shapeTuple, kind);
                PyObject zeros = (PyObject)np.zeros(shapeTuple, np.float32);
                using var dataDict = new PyDict();
                dataDict["O_map"] = zeros;
                PyObject replaceFunc = (PyObject)dataclasses.replace;
                using var replaceKwargs = new PyDict();
                replaceKwargs["data"] = dataDict;
                dynamic calib = replaceFunc.Invoke(new[] { (PyObject)calib0 }, replaceKwargs);
                calib.validate();

                PyObject paramsObj = BuildOffsetParams(new OffsetParams(0.98 * 65535.0));
                dynamic outFrame = offset.process(loaded, calib, paramsObj);

                _processedFrame?.Dispose();
                _processedFrame = (PyObject)outFrame;

                PyObject outPix = (PyObject)outFrame.pixel;
                PyObject inPix = (PyObject)loaded.pixel;
                double outMin = ItemAsDouble(np.min(outPix));
                double outMax = ItemAsDouble(np.max(outPix));
                double outMean = ItemAsDouble(np.mean(outPix));
                dynamic diffAbs = np.abs(np.subtract(np.asarray(outPix, np.float64), np.asarray(inPix, np.float64)));
                double maxAbsChange = ItemAsDouble(np.max(diffAbs));
                string[] stages = StagesFromHistory(outFrame);

                FrameData before = DownsamplePreview(inPix, np, builtins, 512);
                FrameData after = DownsamplePreview(outPix, np, builtins, 512);

                string status =
                    $"QUARANTINE 배관/sanity (수치 golden 아님): offset EXECUTED on {r}x{c} frame "
                    + $"(synthetic zero dark); stages={string.Join("->", stages)}, max|delta|={maxAbsChange:G4}";
                return new ProcessedFrameInfo(
                    true, status, stages, outMin, outMax, outMean, maxAbsChange, before, after);
            }
            catch (Exception ex)
            {
                return ProcessedFrameInfo.Failed("process error: " + ex.Message);
            }
        }
    }

    public SaveResult SaveProcessedFrame(string outputPath)
    {
        EnsureInitialized();
        if (string.IsNullOrWhiteSpace(outputPath))
            return new SaveResult(false, false, "", "save error: empty output path");

        using (Py.GIL())
        {
            if (_processedFrame is null)
                return new SaveResult(false, false, outputPath, "save error: process a frame first");

            try
            {
                dynamic np = Py.Import("numpy");
                dynamic json = Py.Import("json");
                dynamic pathlib = Py.Import("pathlib");
                dynamic builtins = Py.Import("builtins");

                string repoRoot = FindRepoRoot();

                // -- C-20 guard: replicate apps.gui.io_panel.guard_output_path Python-side
                //    (do NOT import apps.gui). Refuse any path resolving under <repo>/data,
                //    checked BEFORE any file is written.
                dynamic resolvedP = pathlib.Path(outputPath).resolve();
                dynamic protectedP = pathlib.Path(Path.Combine(repoRoot, "data")).resolve();
                string resolvedStr = resolvedP.ToString() ?? outputPath;
                bool underData = true;
                try { resolvedP.relative_to(protectedP); }
                catch (PythonException) { underData = false; }
                if (underData)
                    return new SaveResult(false, true, resolvedStr,
                        $"C-20 guard: refusing to write under the protected data root '{protectedP}': {resolvedStr}");

                // -- export.py schema: <base>.npz (pixel f32 + masks u8) + <base>.json
                //    (noise / validation_mode / history / array_keys). Base = the dialog
                //    path with a trailing '.npz' stripped so the written npz IS the named file.
                string basePath = outputPath;
                if (basePath.EndsWith(".npz", StringComparison.OrdinalIgnoreCase))
                    basePath = basePath[..^4];
                string npzPath = basePath + ".npz";
                string jsonPath = basePath + ".json";
                Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(npzPath)) ?? ".");

                dynamic frame = _processedFrame;
                PyObject pixelObj = (PyObject)np.asarray(frame.pixel, np.float32);
                PyObject masksObj = (PyObject)np.asarray(frame.masks, np.uint8);

                PyObject savez = (PyObject)np.savez;
                using var savezKwargs = new PyDict();
                savezKwargs["pixel"] = pixelObj;
                savezKwargs["masks"] = masksObj;
                using (var pyNpz = new PyString(npzPath))
                    savez.Invoke(new[] { (PyObject)pyNpz }, savezKwargs).Dispose();

                // JSON sidecar (export.py schema), built engine-side from the golden frame.
                using var meta = new PyDict();
                using (var noiseDict = new PyDict())
                {
                    noiseDict["alpha"] = (PyObject)frame.noise.alpha;
                    noiseDict["sigma"] = (PyObject)frame.noise.sigma;
                    meta["noise"] = noiseDict;
                }
                meta["validation_mode"] = (PyObject)frame.validation_mode;

                PyObject historyObj = (PyObject)frame.history;
                long hn = historyObj.Length();
                using var histList = new PyList();
                for (int i = 0; i < hn; i++)
                {
                    using PyObject entry = historyObj[i];
                    using var d = new PyDict();
                    d["module_name"] = entry.GetAttr("module_name");
                    d["module_version"] = entry.GetAttr("module_version");
                    d["params_hash"] = entry.GetAttr("params_hash");
                    d["calibset_id"] = entry.GetAttr("calibset_id");
                    // extra is a frozen mappingproxy on the golden HistoryEntry; convert
                    // to a plain dict (as export.py does: dict(entry.extra)) so json.dumps
                    // accepts it — a mappingproxy is not JSON-serializable.
                    using PyObject extraObj = entry.GetAttr("extra");
                    d["extra"] = extraObj.IsNone() ? extraObj : (PyObject)builtins.dict(extraObj);
                    histList.Append(d);
                }
                meta["history"] = histList;
                using (var keys = new PyList())
                {
                    keys.Append(new PyString("pixel"));
                    keys.Append(new PyString("masks"));
                    meta["array_keys"] = keys;
                }

                PyObject dumps = (PyObject)json.dumps;
                using var dumpsKwargs = new PyDict();
                using (var ind = new PyInt(2)) dumpsKwargs["indent"] = ind;
                using PyObject jsonStr = dumps.Invoke(new[] { (PyObject)meta }, dumpsKwargs);
                File.WriteAllText(jsonPath, jsonStr.As<string>());

                return new SaveResult(true, false, npzPath,
                    $"wrote {Path.GetFileName(npzPath)} (+ {Path.GetFileName(jsonPath)})");
            }
            catch (Exception ex)
            {
                return new SaveResult(false, false, outputPath, "save error: " + ex.Message);
            }
        }
    }

    /// <summary>
    /// Diagnostic (concrete-only, like <see cref="MakeSlantedEdge"/>): the FULL
    /// processed frame currently held as adapter state, marshaled to a CLR transport
    /// frame via the fast bulk path. Used by the round-trip proof to compare the saved
    /// file against the in-memory golden output. The UI never calls this (it uses the
    /// ~512x512 previews); a full-res marshal is a test-only convenience.
    /// </summary>
    public FrameData GetProcessedFrame()
    {
        EnsureInitialized();
        using (Py.GIL())
        {
            if (_processedFrame is null)
                throw new InvalidOperationException("no processed frame — call ProcessLoadedFrame first");
            dynamic np = Py.Import("numpy");
            return FrameFromXFrameFast((dynamic)_processedFrame, np);
        }
    }

    /// <summary>
    /// Diagnostic (concrete-only): reload a frame previously written by
    /// <see cref="SaveProcessedFrame"/> (npz pixel/masks + JSON noise sidecar) into a
    /// CLR transport frame, proving the export round-trips. Mirrors the base-name
    /// resolution SaveProcessedFrame uses (a trailing '.npz' is stripped, then
    /// '.npz'/'.json' re-appended).
    /// </summary>
    public FrameData LoadExportedFrame(string outputPath)
    {
        EnsureInitialized();
        using (Py.GIL())
        {
            dynamic np = Py.Import("numpy");
            dynamic json = Py.Import("json");

            string basePath = outputPath;
            if (basePath.EndsWith(".npz", StringComparison.OrdinalIgnoreCase))
                basePath = basePath[..^4];
            string npzPath = basePath + ".npz";
            string jsonPath = basePath + ".json";

            dynamic npz = np.load(npzPath);
            try
            {
                PyObject pixel = (PyObject)npz["pixel"];
                PyObject masks = (PyObject)npz["masks"];
                float[] pixels = NumpyToFloatArrayFast(pixel, np);
                byte[] maskBytes = NumpyToByteArrayFast(masks, np);
                PyObject shape = (PyObject)((dynamic)pixel).shape;
                int r = ((PyObject)shape[0]).As<int>();
                int c = ((PyObject)shape[1]).As<int>();

                dynamic meta = json.loads(File.ReadAllText(jsonPath));
                double alpha = ((PyObject)meta["noise"]["alpha"]).As<double>();
                double sigma = ((PyObject)meta["noise"]["sigma"]).As<double>();
                return new FrameData(pixels, r, c, maskBytes, alpha, sigma);
            }
            finally
            {
                try { ((dynamic)npz).close(); } catch { /* best-effort NpzFile close */ }
            }
        }
    }

    /// <summary>
    /// Resolve a raw payload's (rows, cols) from its uint16 element count: use an
    /// explicit (rows, cols) when it matches, else a perfect square (edrogi 3072x3072),
    /// else 3072x2560. Returns false when none matches (the caller emits a clean error).
    /// </summary>
    private static bool TryInferShape(long n, int rows, int cols, out int r, out int c)
    {
        if (rows > 0 && cols > 0 && (long)rows * cols == n)
        {
            r = rows; c = cols; return true;
        }
        long root = (long)Math.Round(Math.Sqrt(n));
        if (root > 0 && root * root == n)
        {
            r = (int)root; c = (int)root; return true;
        }
        if (n == 3072L * 2560L)
        {
            r = 3072; c = 2560; return true;
        }
        r = 0; c = 0; return false;
    }

    /// <summary>
    /// Engine-side block-mean downsample of a full-res frame to about
    /// <paramref name="target"/> x <paramref name="target"/> for a display-only heatmap
    /// preview. Pure Python-side numpy (crop -&gt; reshape -&gt; mean over the block axes):
    /// the UI never touches full-res pixels (SPEC-VIEWER-001, C-20 memory guard).
    /// </summary>
    private static FrameData DownsamplePreview(PyObject pix, dynamic np, dynamic builtins, int target)
    {
        dynamic arr = np.asarray(pix, np.float32);
        PyObject shape = (PyObject)arr.shape;
        int rows = ((PyObject)shape[0]).As<int>();
        int cols = ((PyObject)shape[1]).As<int>();

        int fr = Math.Max(1, rows / target);
        int fc = Math.Max(1, cols / target);
        int outR = rows / fr;
        int outC = cols / fc;
        int h = outR * fr;
        int w = outC * fc;

        // crop to a block-divisible (h, w), then average each (fr x fc) block.
        PyObject rowSlice = (PyObject)builtins.slice(0, h);
        PyObject colSlice = (PyObject)builtins.slice(0, w);
        using var idx = new PyTuple(new[] { rowSlice, colSlice });
        PyObject cropped = ((PyObject)arr)[idx];
        dynamic reshaped = ((dynamic)cropped).reshape(outR, fr, outC, fc);
        using var axes = new PyTuple(new PyObject[] { new PyInt(1), new PyInt(3) });
        dynamic block = np.mean(reshaped, axes);   // (outR, outC), block-mean

        float[] buf = NumpyToFloatArrayFast((PyObject)block, np);
        return FrameData.FromPixels(buf, outR, outC);
    }

    /// <summary>
    /// Bulk float32 marshal for the previews via a numpy <c>tofile</c> scratch buffer:
    /// numpy writes the C-order float32 bytes once (native little-endian on x86) and C#
    /// reads them back with a single <c>Buffer.BlockCopy</c>. Used instead of the
    /// per-element <see cref="NumpyToFloatArray"/> because a ~512x512 preview has ~262k
    /// elements — a per-element <c>.item()</c> loop would be prohibitively slow — and
    /// pythonnet 3.0.5 exposes no <c>PyBytes</c> for an in-memory bulk transfer. The scratch
    /// file is a small (~1MB) transient in the OS temp dir (never a full-res raw, never
    /// under <c>data/</c>), deleted immediately.
    /// </summary>
    private static float[] NumpyToFloatArrayFast(PyObject arr, dynamic np)
    {
        dynamic contiguous = np.ascontiguousarray(arr, np.float32);
        string tmp = Path.Combine(Path.GetTempPath(), "xdet_preview_" + Guid.NewGuid().ToString("N") + ".f32");
        try
        {
            contiguous.tofile(tmp);   // raw C-order little-endian float32, closed on return
            byte[] raw = File.ReadAllBytes(tmp);
            var floats = new float[raw.Length / sizeof(float)];
            Buffer.BlockCopy(raw, 0, floats, 0, raw.Length);
            return floats;
        }
        finally
        {
            try { File.Delete(tmp); } catch { /* best-effort scratch cleanup */ }
        }
    }

    /// <summary>
    /// Bulk uint8 marshal (masks) via a numpy <c>tofile</c> scratch buffer — the byte
    /// twin of <see cref="NumpyToFloatArrayFast"/>. A full-res masks array has ~9.4M
    /// elements, so the per-element <c>.item()</c> loop in <see cref="NumpyToByteArray"/>
    /// would be prohibitively slow; uint8 <c>tofile</c> writes the raw bytes 1:1 and C#
    /// reads them straight back (no conversion).
    /// </summary>
    private static byte[] NumpyToByteArrayFast(PyObject arr, dynamic np)
    {
        dynamic contiguous = np.ascontiguousarray(arr, np.uint8);
        string tmp = Path.Combine(Path.GetTempPath(), "xdet_masks_" + Guid.NewGuid().ToString("N") + ".u8");
        try
        {
            contiguous.tofile(tmp);
            return File.ReadAllBytes(tmp);
        }
        finally
        {
            try { File.Delete(tmp); } catch { /* best-effort scratch cleanup */ }
        }
    }

    /// <summary>
    /// Marshal a golden XFrame to a CLR <see cref="FrameData"/> via the fast bulk
    /// paths (float32 pixels + uint8 masks). Used for full-res frames where the
    /// per-element <see cref="FrameFromXFrame"/> would be too slow.
    /// </summary>
    private static FrameData FrameFromXFrameFast(dynamic frame, dynamic np)
    {
        float[] pixels = NumpyToFloatArrayFast((PyObject)frame.pixel, np);
        byte[] masks = NumpyToByteArrayFast((PyObject)frame.masks, np);
        PyObject noise = (PyObject)frame.noise;
        double alpha = noise.GetAttr("alpha").As<double>();
        double sigma = noise.GetAttr("sigma").As<double>();
        PyObject shape = (PyObject)frame.pixel.shape;
        int rows = ((PyObject)shape[0]).As<int>();
        int cols = ((PyObject)shape[1]).As<int>();
        return new FrameData(pixels, rows, cols, masks, alpha, sigma);
    }

    private static bool ItemAsBool(dynamic numpyScalar)
    {
        // numpy bool_ scalar -> native Python bool via .item(), then to CLR bool.
        PyObject s = (PyObject)numpyScalar;
        using PyObject native = s.InvokeMethod("item");
        return native.As<bool>();
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
