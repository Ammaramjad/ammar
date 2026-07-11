# AGENTS.md

## Cursor Cloud specific instructions

This repository is the **ThinkDSP** library (Allen Downey), consisting of two modules:
`thinkdsp.py` (DSP: signals, waves, spectra, WAV I/O) and `thinkplot.py` (matplotlib
plotting helpers). There is no test suite, no linter config, and no build step — it is a
plain Python library imported by scripts/notebooks.

### Environment (already provisioned by the update script)
- The code is **only compatible with Python ≤ 3.8** and **numpy < 1.24**:
  - `thinkdsp.py` uses `from fractions import gcd` (removed in Python 3.9).
  - `thinkdsp.py` uses `np.float` (removed in numpy 1.24).
- The startup update script installs `uv`, a Python 3.8 toolchain, and creates a virtual
  environment at `.venv/` with pinned deps (numpy 1.23.5, scipy 1.10.1, matplotlib 3.7.5,
  pandas 2.0.3, ipython 8.12.3). Do **not** use the system Python 3.12 — imports will fail.
- Use the venv interpreter directly: `.venv/bin/python`.

### Running / testing
- Plotting is headless: set `MPLBACKEND=Agg` when generating figures without a display.
- `thinkdsp` imports `thinkplot`, so scripts run from **outside** `/workspace` must set
  `PYTHONPATH=/workspace`. Scripts inside `/workspace` (e.g. `.venv/bin/python thinkdsp.py`)
  work without it.
- Quick smoke test: `MPLBACKEND=Agg PYTHONPATH=/workspace .venv/bin/python -c "import thinkdsp, thinkplot; print('ok')"`.
- `thinkdsp.py` has a `main()` runnable via `.venv/bin/python thinkdsp.py`.
- Syntax/"lint" check (no linter configured): `.venv/bin/python -m py_compile thinkdsp.py thinkplot.py`.
