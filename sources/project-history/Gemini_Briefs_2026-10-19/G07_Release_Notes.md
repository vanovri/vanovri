# Body Data Viewer v0.1.0

A seven-region DEXA-style teaching twin: a strict parser for a documented synthetic report template, plus a standalone schematic 3D viewer with three heatmap layers and a raycast inspector.

**Synthetic data only.** No patient, scan, vendor report or clinical claim is included. The parser checks table consistency; it does not diagnose, classify or estimate missing values.

## What is verified

- 36 referee tests covering the text, PDF and JSON routes, unit conversion, missing values, the fat-percent basis, the 0.5 % mass gate, structural rejection cases, CLI output protection and clean error exits.
- The three fixture routes produce identical JSON.
- The embedded viewer payload is byte-identical to the parser output; the viewer references no external asset and performs no network fetch.
- Browser QA in Chromium (SwiftShader WebGL) completed with **zero console errors**, a successful trunk raycast and all three layers switched. Evidence: `docs/browser-qa.json` and four screenshots.
- Computed mass 80.000 kg against a reported 80.000 kg (0.000 % deviation); fat 17.45 kg, lean soft tissue 59.65 kg, BMC 2.90 kg.
- The release ZIP is rebuilt deterministically and checked entry-by-entry against the working tree; `SHA256SUMS-v0.1.0.txt` is included.

## Limits

- BODY_DATA_V1 template only; no OCR, no vendor adapter, no general DEXA reader.
- PDF needs a text layer, 1–3 pages, ≤5 MB, unencrypted.
- JSON duplicate keys cannot be detected.
- Mannequin geometry is schematic, not an anatomical model or a scanner ROI projection.
- Frame timing under headless software WebGL is not a performance measurement.

## Assets

- `body-data-viewer-v0.1.0.zip` — parser, generated viewer, template, fixtures, tests, tools and evidence.
- `SHA256SUMS-v0.1.0.txt` — checksums for every file in the archive.
