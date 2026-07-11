using System;
using System.IO;
using Python.Runtime;

// Diagnostic probe (SPEC-XSEAM-001 P1.5, risk-first). Proves the pythonnet
// in-process adapter can embed the uv .venv CPython and import numpy/scipy plus
// the frozen Python golden packages (common/modules/metrics). If this prints
// PROBE_SUCCESS the load-bearing interop of the seam is de-risked.

static string FindRepoRoot()
{
    // Walk up from the running assembly until a dir containing pyproject.toml + .venv.
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
    throw new DirectoryNotFoundException("repo root (pyproject.toml + .venv) not found above " + AppContext.BaseDirectory);
}

string repoRoot = FindRepoRoot();
string venvCfg = File.ReadAllText(Path.Combine(repoRoot, ".venv", "pyvenv.cfg"));
// pyvenv.cfg 'home = <base python dir>' gives the CPython that owns python3XX.dll.
string baseHome = "";
foreach (var line in venvCfg.Split('\n'))
{
    var t = line.Trim();
    if (t.StartsWith("home", StringComparison.OrdinalIgnoreCase) && t.Contains('='))
        baseHome = t[(t.IndexOf('=') + 1)..].Trim();
}
string pythonDll = Path.Combine(baseHome, "python312.dll");
string sitePackages = Path.Combine(repoRoot, ".venv", "Lib", "site-packages");

Console.WriteLine($"repoRoot     = {repoRoot}");
Console.WriteLine($"baseHome     = {baseHome}");
Console.WriteLine($"pythonDll    = {pythonDll} (exists={File.Exists(pythonDll)})");
Console.WriteLine($"sitePackages = {sitePackages} (exists={Directory.Exists(sitePackages)})");

Runtime.PythonDLL = pythonDll;
PythonEngine.PythonHome = baseHome;
PythonEngine.Initialize();
using (Py.GIL())
{
    dynamic sys = Py.Import("sys");
    sys.path.insert(0, sitePackages);
    sys.path.insert(0, repoRoot);

    dynamic np = Py.Import("numpy");
    Console.WriteLine($"[OK] numpy {np.__version__}");
    dynamic sp = Py.Import("scipy");
    Console.WriteLine($"[OK] scipy {sp.__version__}");
    Py.Import("common.xframe");
    Console.WriteLine("[OK] common.xframe imported");
    Py.Import("modules.offset");
    Console.WriteLine("[OK] modules.offset imported");
    Py.Import("metrics.mtf");
    Console.WriteLine("[OK] metrics.mtf imported");
}
Console.WriteLine("PROBE_SUCCESS");
