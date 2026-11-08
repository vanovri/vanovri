# Cislunar OEM Replay v0.1.0

A strict CCSDS OEM 2.0 subset reader for a **synthetic** cislunar teaching profile, with CSV replay, cubic Hermite reconstruction, a same-frame J2000 lunar ephemeris, clearance gates and a standalone 3D replay.

**Synthetic data.** Not an authenticated NASA product, not a propagated free-return solution, not a navigation tool.

## What is verified

- 43 referee tests: OEM and CSV routes, metadata/centre/frame/time-system rejection, duplicate and non-monotonic epochs, malformed rows, non-finite values, interpolation node reproduction and cubic exactness, ephemeris continuity, telemetry formulas, Earth and lunar impact gates, and CLI output protection.
- OEM and CSV replay produce identical samples.
- The embedded viewer payload is byte-identical to the parser output; the viewer loads no external asset and performs no network fetch.
- The analytic lunar ephemeris matches three JPL Horizons geocentric ICRF vectors within **12, 35 and 13 km** (max 34.5 km). Part of that residual is a UTC-versus-TDB comparison artefact.
- Clearance gates pass: minimum Earth altitude 199.9 km, minimum lunar altitude 7,263 km (7,276 km along the 600-point replay track).
- The two-body energy spread is reported as **63.4 km²/s²**, not hidden; it is a diagnostic, not a conserved quantity.
- Browser QA in Chromium (SwiftShader WebGL): **zero console errors**, all three camera locks exercised, scrubber midpoint verified. Evidence in `docs/browser-qa.json` plus four screenshots.
- Release ZIP is deterministic, checked entry-by-entry, and its remote SHA-256 matches.

## Limits

- No propagation, manoeuvres, covariance, light-time, aberration or third-body dynamics.
- UTC only; no TAI/TT/TDB/UT1 conversion.
- Truncated ELP2000 ephemeris: tens of kilometres of residual, not metre-level.
- The reference geometry is designed, not integrated; node velocities are spline derivatives.
- Clearance is a kinematic screen, not a collision probability.

## Assets

- `cislunar-oem-replay-v0.1.0.zip` — parser, fixtures, viewer, template, tests, tools and evidence.
- `SHA256SUMS-v0.1.0.txt` — checksums for every archived file.
