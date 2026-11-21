# Ardhya Novri Ramadhan

Electrical Engineering graduate from Diponegoro University (GPA 3.43/4.00), based in Bekasi, Indonesia. I build resource-constrained AI/ML systems, Next.js technical SEO & security blueprints, embedded firmware (STM32/ESP32), and formally verified distributed systems with AI coding assistance. Every metric in my repositories links directly to reproducible tests and JSON benchmark proofs.

[Portfolio](https://ardhyanovri.my.id) | [LinkedIn](https://www.linkedin.com/in/dhya/) | [AI Systems 4 GB VRAM Case Study](https://ardhyanovri.my.id/blog/10-ai-systems-4gb-vram) | [MagangHub SEO Teardown](https://ardhyanovri.my.id/blog/teardown-maganghub-kemnaker-nextjs-seo)

## Current internship

Electrical Staff Intern at PT Denki Engineering (since 16 November 2026) through Kemnaker's MagangHub program (Batch 3, Angkatan 2, 2026). [Portfolio entry](https://ardhyanovri.my.id/experience#denki-maganghub).

## Recognition

Team NusaSentinel earned Honorable Mention, Finalist Rank 8 at the Aerospace Innovation Challenge 2026 (ISAST 2026) in Yogyakarta, Indonesia (6-8 October 2026) with [Nusantara SolarWing](https://github.com/vanovri/nusantara-solarwing). [Certificate](https://ardhyanovri.my.id/credentials#nusasentinel-isast-2026).

## Featured Flagship Engineering Projects

| Project | Verified Implementation & Metrics | Case Study / Notes |
| --- | --- | --- |
| [ai-systems-4gb-vram](https://github.com/vanovri/ai-systems-4gb-vram) ([`v1.0.0`](https://github.com/vanovri/ai-systems-4gb-vram/releases/tag/v1.0.0)) | 10 end-to-end AI/ML & Python systems verified on a 4 GB GTX 1650 Ti (`151/151` pytest PASS): Neural Pong World Model (`101.2 FPS`, `0` game engine imports, `100%` counterfactual ordering), Pure NumPy INT4 + GPTQ-lite (`-67.70%` Layer-10 L2 err), `Qwen3-0.6B` LoRA (`0.00% -> 84.59%` Banking77), Two-Tower RecSys (`4.23x` Recall@10, `-51.5%` viral bias), Hybrid RAG (`1.00` MRR/Refusal), Coding Agent (`3/3` bugs), & Multi-Agent. | [10 AI Systems on 4 GB VRAM](https://ardhyanovri.my.id/blog/10-ai-systems-4gb-vram) |
| [maganghub-nextjs-seo-blueprint](https://github.com/vanovri/maganghub-nextjs-seo-blueprint) ([`v1.0.0`](https://github.com/vanovri/maganghub-nextjs-seo-blueprint/releases/tag/v1.0.0)) | Canonical Next.js App Router Technical SEO, Google for Jobs JSON-LD, Expired Job 410 Guard, GEO `llms.txt`/AI feeds, and Zero-Dep 8-Gate CI Validator for `maganghub.kemnaker.go.id`: `83/83` tests PASS, `1,518` fuzz iterations (`6.00 ms` max 50 KB ReDoS), `15/15` STRIDE mitigated (`0` OPEN), `p99 15.99 ms` (10k), `k6 4.53 ms` middleware. | [MagangHub SEO & GEO Teardown](https://ardhyanovri.my.id/blog/teardown-maganghub-kemnaker-nextjs-seo) |
| [prompt-shield-eval](https://github.com/vanovri/prompt-shield-eval) ([`v1.1.0`](https://github.com/vanovri/prompt-shield-eval/releases/tag/v1.1.0)) | Hybrid TypeScript LLM prompt injection engine: 0-dep sub-ms Core (`0.046 ms` p50), optional `104.2 KB` ONNX INT8 Layer 3.5 Cascade (`60/60` exact match, `0.762 ms` p99), and MCP Middleware Guardrail (`20/20` hijack blocked, `0.752 ms` p99; `30/30` Vitest, 3-job CI). | [Hybrid LLM security](https://ardhyanovri.my.id/projects/prompt-shield-eval) |
| [hyperion-omega](https://github.com/vanovri/hyperion-omega) | 20-channel (`CH01`-`CH20`) institutional exchange & formally verified distributed systems monorepo (Rust, Go, Python/Z3, TS/Next, Solidity, Wasmtime 50, eBPF/XDP, Arrow/DataFusion): `20/20` Overclock green (`98.52%` mutation kill, `0 B/cycle` 500k soak, `21/21` Wave 6 PASS). | [20-channel architecture](https://ardhyanovri.my.id/projects/hyperion-omega) |
| [ferrum-kv](https://github.com/vanovri/ferrum-kv) | Zero-dependency safe Rust (`#![forbid(unsafe_code)]`) RESP3 KV server with 3-node TCP Raft, HNSW SQ8 vector search (`173,007 VSEARCH/s`), BM25, Gorilla XOR, and LSM-Tree (`564,993 MIXED ops/s`). | [FerrumKV](https://ardhyanovri.my.id/projects/ferrum-kv) |
| [uart-fixture-kit](https://github.com/vanovri/uart-fixture-kit) | Zero-dependency Python byte-stream fixtures, fault injection, and virtual-time replay for serial parser tests (`238` tests PASS). | [UART test fixtures](https://ardhyanovri.my.id/projects/uart-fixture-kit.html) |
| [DataRescue](https://github.com/vanovri/datarescue) | CSV/JSON validation, row quarantine, and traceable exports with FastAPI workbench (`33/33` pytest). | [Data validation workbench](https://ardhyanovri.my.id/projects/datarescue.html) |
| [RepairGate](https://github.com/vanovri/repairgate) | Protected tests, independent holdouts, and anti-tamper hashing for local code-repair verification (`28/28` pytest). | [Code-repair verifier](https://ardhyanovri.my.id/projects/repairgate.html) |
| [SignalProof](https://github.com/vanovri/signalproof) | Zero-dependency low-voltage signal quality workbench & CLI (`54/54` Node tests, `15/15` scenarios). | [Signal quality workbench](https://ardhyanovri.my.id/projects/signalproof.html) |

## Core Engineering Stack

- **AI/ML & LLM Systems:** PyTorch CUDA FP16, PEFT LoRA, Pure NumPy INT4/GPTQ-lite quantization, World Models (Action-Conditioned U-Net + DAgger), Two-Tower RecSys, FAISS + BM25 Hybrid RAG, ONNX Runtime INT8, MCP Guardrails.
- **Growth, Web & Security Engineering:** Next.js App Router, TypeScript strict, Node.js 24 LTS, Technical SEO / Google for Jobs JSON-LD / `llms.txt` GEO, STRIDE Threat Modeling, ReDoS/SSRF hardening, Static CSP HTML/CSS/JS.
- **Embedded, DSP & Systems:** STM32 / ESP32 C, Biquad IIR & FIR DSP, UART/Modbus RTU, Rust (`std`-only / Raft / LSM / Wasmtime / eBPF), Go, Python (`pytest`).

My electrical engineering background includes an STM32 EMG thesis subsystem (UNDIP, 2026) and internship exposure to UPS/converter systems and protection relays at PT Angkasa Pura Indonesia (Soekarno-Hatta Int'l Airport). The [EMG project page](https://ardhyanovri.my.id/projects/emg-thesis.html) separates my firmware and GUI contribution from the wider team system.

Source and profile copy verified on 21 November 2026. Automated tests verify defined invariants and benchmarks on measured inputs.
