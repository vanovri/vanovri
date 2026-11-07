# Ardhya Novri Ramadhan

**Electrical Engineering Graduate (B.Eng. / S.T., Diponegoro University) · CTO / Technical Lead at ENVIID**  
Embedded C (`STM32F411` / `ESP32`) · Signal Processing · Python Verification Tooling · Full-Stack Web

- **Portfolio:** [ardhyanovri.my.id](https://ardhyanovri.my.id)
- **Company Platform (Sole Developer):** [enviid.web.id](https://enviid.web.id)
- **LinkedIn:** [linkedin.com/in/dhya](https://www.linkedin.com/in/dhya/)

---

## Selected Open-Source Repositories

| Repository | Scope | Verification Snapshot (8 Nov 2026) |
|---|---|---|
| [**aether-synth-flow**](https://github.com/vanovri/aether-synth-flow) | Multi-platform Swift 6 & Metal spatial audio synthesizer (iOS 18, isionOS 2 CompositorServices/6-DoF ARKit, macOS 15 CoreAudio HAL, watchOS 11 Lomb-Scargle HRV, AUv3) with CoreML SIMD MLP closed-loop bio-entrainment. | Zero external deps · 62 Swift/Metal files · [Project notes](https://ardhyanovri.my.id/projects/aether-synth-flow) |
| [**signalproof**](https://github.com/vanovri/signalproof) | Low-voltage ADC capture inspector computing six deterministic metrics (`E1`–`E6`: DC offset, AC RMS, rail clipping, `48–52 Hz` mains hum, timing gaps, capture duration) before gating optional LLM explanations against fixed finding IDs. | Zero runtime deps · `60/60` Node tests · [Live workbench](https://vanovri.github.io/signalproof/) |
| [**uart-fixture-kit**](https://github.com/vanovri/uart-fixture-kit) | Deterministic byte-stream replay, 22-check correctness-gated parser profiler (`2.12x` bulk chunk speedup vs `0.78x` single-byte pathology), and 8-scenario synthetic receiver fault viewer without attached hardware. | Zero runtime deps · `248` Python + `5` Node tests (`v0.3.0`) |
| [**repairgate**](https://github.com/vanovri/repairgate) | Code-repair gate separating visible tests from independent holdout checks and file-hash policy audits so overfitting or test-modifying patches are rejected before application. | `108` Python/FastAPI tests · 3 replayable regression cases |
| [**kilnmcp**](https://github.com/vanovri/kilnmcp) | FastMCP server & 3-agent pipeline over synthetic biochar pyrolysis kiln telemetry (`$KILN,...*XOR` UART framing, EWMA/$k\sigma$ fault isolation, and non-certified draft dMRV stoichiometry). | `36/36` pytest checks · synthetic telemetry (`NOT CERTIFIED`) |
| [**datarescue**](https://github.com/vanovri/datarescue) | Local CSV/JSON normalization workbench and CLI that quarantines rejected rows instead of dropping them and exports SHA-256 lineage reports. | `104` Python/FastAPI tests · loopback UI + CLI |
| [**emg-signal-tools**](https://github.com/vanovri/emg-signal-tools) | Companion filter verification and CRC-32/SHA-256 telemetry parity utilities extracted from my undergraduate STM32F411 surface-EMG subsystem (`nominal 4 kHz` DMA, cascaded DF-II Transposed Butterworth HPF/LPF + `50 Hz` notch). | Source-only synthetic verification (no human subject recordings) |

---

## Engineering Principles

- **Configured vs. Measured:** Firmware constants, synthetic benchmarks, and physical bench measurements are stated as distinct claims.
- **Deterministic Gates Around AI:** AI coding and inference outputs are constrained by schema checks, holdout tests, and reproducible CLI suites, with AI assistance disclosed per repository.
