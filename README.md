# Ardhya Novri Ramadhan

Electrical Engineering graduate from Diponegoro University (GPA 3.43/4.00), based in Bekasi, Indonesia. I develop embedded-system experiments, AI security guardrails, and systems/Python/browser tools with AI coding assistance. My project notes distinguish simulations from field measurements and link implementation details to source.

[Portfolio](https://ardhyanovri.my.id) | [LinkedIn](https://www.linkedin.com/in/dhya/)

## Current internship

I started my Electrical Staff internship at PT Denki Engineering on 16 November 2026 through Kemnaker’s MagangHub program (Batch 3, Angkatan 2, 2026). [Portfolio entry](https://ardhyanovri.my.id/experience#denki-maganghub).

## Recognition

Team NusaSentinel earned Honorable Mention, Finalist Rank 8 at the Aerospace Innovation Challenge 2026 (ISAST 2026) in Yogyakarta, Indonesia (6–8 October 2026). The entry was [Nusantara SolarWing](https://github.com/vanovri/nusantara-solarwing). [Certificate](https://ardhyanovri.my.id/credentials#nusasentinel-isast-2026).

## Selected projects

| Project | Implementation | Portfolio notes |
| --- | --- | --- |
| [prompt-shield-eval](https://github.com/vanovri/prompt-shield-eval) ([`v1.1.0`](https://github.com/vanovri/prompt-shield-eval/releases/tag/v1.1.0)) | Hybrid TypeScript LLM prompt injection engine: 0-dep sub-ms Core (`0.046 ms` p50), optional `104.2 KB` ONNX INT8 Layer 3.5 Cascade (`60/60` exact match, `0.762 ms` p99), and MCP Middleware Guardrail (`20/20` hijack blocked, `0.752 ms` p99; `30/30` Vitest, 3-job CI). | [Hybrid LLM security](https://ardhyanovri.my.id/projects/prompt-shield-eval) |
| **HYPERION OMEGA** *(local monorepo)* | 20-channel (`CH01`–`CH20`) institutional exchange & formally verified distributed systems monorepo (Rust, Go, Python/Z3, TS/Next, Solidity, Wasmtime 50, eBPF/XDP, Arrow/DataFusion): `20/20` Overclock green (`98.52%` mutation kill, `0 B/cycle` 500k soak, `21/21` Wave 6 Rust 1.99 verification PASS). | [20-channel architecture](https://ardhyanovri.my.id/projects/hyperion-omega) |
| [uart-fixture-kit](https://github.com/vanovri/uart-fixture-kit) | Python byte-stream fixtures, fault injection, and virtual-time replay for serial parser tests. | [UART test fixtures](https://ardhyanovri.my.id/projects/uart-fixture-kit.html) |
| [DataRescue](https://github.com/vanovri/datarescue) | CSV/JSON validation, row quarantine, and traceable exports, with a FastAPI workbench. | [Data validation workbench](https://ardhyanovri.my.id/projects/datarescue.html) |
| [RepairGate](https://github.com/vanovri/repairgate) | Protected tests, independent holdouts, and reviewable local code-repair decisions. | [Code-repair verifier](https://ardhyanovri.my.id/projects/repairgate.html) |
| [Run Ledger](https://github.com/vanovri/run-ledger) | Decimal cost aggregation, SQLite records, and metadata redaction. | [Agent-run evidence ledger](https://ardhyanovri.my.id/projects/run-ledger.html) |
| [SignalProof](https://github.com/vanovri/signalproof) | JavaScript signal-quality metrics and finding-ID checks on explanations. | [Signal quality workbench](https://ardhyanovri.my.id/projects/signalproof.html) |
| [FIR Parity](https://github.com/vanovri/fir-parity) | Fortran and Rust filters checked against a Python reference. | [Cross-language signal processing](https://ardhyanovri.my.id/projects/fir-parity.html) |

## Technical focus

Embedded firmware & DSP (STM32/ESP32, Biquad IIR, UART/Modbus), AI/LLM security (OWASP LLM01/06/07, ONNX Runtime INT8, Model Context Protocol / MCP), systems & formal verification (Rust, Go, Python, TypeScript, Z3 SMT, Raft VOPR, Wasmtime, eBPF/XDP), and reproducible software checks. The projects above show where each skill appears in code.

My electrical background includes a team STM32 EMG thesis project (UNDIP, 2026) and internship exposure to UPS/converter systems and protection relays at PT Angkasa Pura Indonesia (Soekarno-Hatta Int'l Airport). The [EMG project page](https://ardhyanovri.my.id/projects/emg-thesis.html) separates my firmware and GUI contribution from the wider team system.

Source and profile copy reviewed on 20 November 2026. Tests check defined inputs and invariants. They do not establish production reliability, clinical validity, or performance on untested hardware.
