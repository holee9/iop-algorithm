# data/

Golden datasets and calibration payloads (Git LFS tracked). **No real data at
T0** — only the directory structure and LFS tracking rules are established
(REQ-INFRA-DATA-3 Exclusions).

Layout (populated by later work packages):

- `raw/`     — 16-bit raw frames (`.raw`) + per-frame metadata (`.json`).
- `calib/`   — CalibSet payloads (`.npz` arrays + `.json` sidecar metadata).
- `golden/`  — expected golden-model outputs for TC comparison.

Binary payloads are tracked via Git LFS; see `.gitattributes` at the repo root.
