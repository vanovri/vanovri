<div align="center">

<a href="https://ardhyanovri.my.id">
  <img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=600&size=22&pause=1200&color=0071E3&center=true&vCenter=true&width=760&lines=Ardhya+Novri+Ramadhan;From+Sensor+to+Screen%3A+Firmware%2C+Signals+%26+Systems+Software;Zero-Dependency+Engineering+%26+Deterministic+Verification" alt="Ardhya Novri Ramadhan — Typing Header" />
</a>

**B.Eng. in Electrical Engineering (Diponegoro University) · Embedded Systems, Real-Time DSP & Systems Software · Bekasi, Indonesia**

<p align="center">
  <a href="https://ardhyanovri.my.id"><img src="https://img.shields.io/badge/Portfolio-ardhyanovri.my.id-0071E3?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Portfolio" /></a>
  <a href="https://www.linkedin.com/in/dhya/"><img src="https://img.shields.io/badge/LinkedIn-Ardhya_Novri-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn" /></a>
  <a href="mailto:ardhyasan@gmail.com"><img src="https://img.shields.io/badge/Email-ardhyasan%40gmail.com-EA4335?style=for-the-badge&logo=gmail&logoColor=white" alt="Email" /></a>
  <a href="https://github.com/vanovri"><img src="https://img.shields.io/badge/GitHub-vanovri-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub" /></a>
</p>

</div>

---

### 🚀 Flagship Systems & Engineering Releases

#### 1. [AetherSynth & Flow](https://github.com/vanovri/aether-synth-flow) (`v1.0.0`) · [Project Notes](https://ardhyanovri.my.id/projects/aether-synth-flow)
> *Spatial audio synthesis meets closed-loop physiology in native Swift 6 and Metal across iOS 18, watchOS 11, visionOS 2, macOS 15, and AUv3 (63 files, 46,959 LOC, zero external dependencies).*
- **visionOS 2 Spatial Performance:** 90 Hz Reverse-Z `.greaterEqual` stereoscopic CompositorServices rendering with sub-12 ms spatial pinch gesture latency (**7.67 ms slew / 9.1 ms E2E**) and wait-free `os_unfair_lock_trylock`.
- **Physical Acoustics:** 128-tap KEMAR HRIR UPOLS FFT convolver and 2D/3D FDTD physical acoustic waveguide with cubic PML boundaries delivering **51.22 dB** reflection attenuation across 4,096 CFL steps.
- **Optics & Metal Ray Tracing:** 4,096-ray hardware acoustic ray tracing with **-91.6% global loads** and **< 6.5 ms** GPU frame governor headroom.
- **Quantum Tensor & Biometrics:** Pre-allocated **χ_max = 16** Quantum MPS tensor network (**0 heap allocations**, **2.99e-10 DMRG** convergence), **30.56 dB SPWVD** (**49.90 dB** midpoint, 0 real-time heap allocs), and **14.65% drop & 95 ms Pareto jitter (0 false spikes)**. Streams Apple Watch RR intervals over 64-bit FNV-1a binary bridge into Lomb-Scargle HRV and 4-ch BLE EEG RLS filter (**30.31 dB** ocular blink suppression).
- **Verification:** **12/12 SHA-256 verification stages** passed across 34 test suites.

#### 2. [FerrumKV](https://github.com/vanovri/ferrum-kv) (`v1.0.0`) · [Project Notes](https://ardhyanovri.my.id/projects/ferrum-kv)
> *Distributed storage, stripped to bare metal. Zero-dependency RESP3 store, 3-node Raft consensus engine, HNSW vector search, and disk LSM-tree in pure safe Rust (`#![forbid(unsafe_code)]`, 24 modules, 19,200 LOC, 0 external crates).*
- **High-Throughput Sharded Core:** **564,993 MIXED ops/s**, **505,716 GET/s** (p50 = 39.66 µs), **307,853 INCR/s**, and **-95.46% SET p99.9 latency tail reduction (7.16 ms)** across 50 pipelined clients.
- **Engine Architecture:** **64 CachePadded shards**, **16-stripe tx_exec_fence**, in-memory `RwLock<LsmState>` MemTable, and zero-copy **`RespParser::parse_flat_command` + `get_into`** zero-allocation frame execution.
- **Vector & Full-Text Search:** Multi-layer HNSW graph with 8-bit scalar quantization (SQ8, 4× memory compression) sustaining **173,007 VSEARCH/s at 93.3% Recall@5**, Okapi BM25 inverted index with LEB128 delta postings, and Facebook Gorilla XOR time-series compression.
- **Consensus & Durability:** 3-node TCP Raft consensus verified under automated Jepsen fault injection (**199 committed ops, 0 stale writes**), 4 KB CRC32-verified SSTables, and RFC 8439 ChaCha20-Poly1305 AEAD snapshot encryption.

#### 3. [Cyberpunk Floating Ramen Stall](https://github.com/vanovri/cyberpunk-floating-ramen-stall) (`v1.0.0`) · [Project Notes](https://ardhyanovri.my.id/projects/cyberpunk-floating-ramen-stall)
> *100% self-contained Blender 4.0–4.3 procedural 3D diorama generator, binary glTF 2.0 serializer, software Z-buffer rasterizer, and lossless BT.709 container muxer in pure Python (stdlib only).*
- **Procedural Worldbuilding:** **32 tracks**, **0 external textures**, 579 procedural objects across 10 collections, 2 rigged armatures, and **4 shared ShaderNodeGroups (-32.6% shader node reduction)** alongside the **`GN_Cyber_Rain_Field`** geometry node dynamics.
- **Spec-Compliant Serialization:** Binary glTF 2.0 serializer (90,766 vertices, 170,840 triangles, 4.59 MB GLB) and zero-dependency software Z-buffer rasterizer with Z=0 planar reflections, separable Neon Bloom, and AgX tone mapping across three 1280×720 camera cuts.
- **Lossless BT.709 Video Mux:** **240 frames (10.0s @ 24fps) BT.709 (colr nclx)** multiplexer into RIFF/AVI 1.0 (46.17 MB) and ISO-BMFF H.264 `I_PCM` IDR MP4 (24.16 MB).
- **Verification Integrity:** **100% SHA-256 manifest match across all 6 Phase 7 artifacts** and 32/32 automated CI tracks passed on Windows & Linux.

#### 4. [Career Test Arena](https://github.com/vanovri/career-test-arena) (`v1.0.0`)
> *Offline-ready cognitive and technical exam simulator and engineering calculator.*
- **Assessment Engine:** 45 verified questions across United Tractors (UT) Cognitive, UT Tech & Infra 14929, and Formulatrix System Integration Engineer.
- **Interview & Compliance:** 8 STAR behavioral response cards, automated claim-boundary scanner, and 7/7 pytest verification suite.

---

### 🛠️ Core Engineering Background

- 🔌 **Embedded Systems & Firmware:** Timer-triggered 12-bit ADC acquisition with DMA on **STM32F411** (4 kHz), cascaded Biquad IIR causal digital filtering (HPF, LPF, 50 Hz notch), RMS/MAV feature extraction, and 115200-baud UART telemetry.
- ⚡ **Industrial Electrical Infrastructure:** Internship Trainee at **PT Angkasa Pura Indonesia / InJourney Airports** (Soekarno-Hatta International Airport UPS/converter systems, 20 kV medium-voltage distribution, transformer protection relays).
- 🌐 **Web Architecture & Leadership:** CTO / Technical Lead at **ENVIID Carbon Solutions** — sole developer of `enviid.web.id` with interactive carbon calculator and digital MRV workflow.
- 🛡️ **Verification Discipline:** Author of 20+ open-source verification labs with cryptographic testbench locks (`SHA-256`), AST assertion floors, mutation testing gates, and strict reproducibility bounds.

---

### 🧰 Technology Matrix

| Domain | Technologies & Standards |
|---|---|
| **Languages** | C, Safe Rust (`#![forbid(unsafe_code)]`), Swift 6 (Strict Concurrency), Python 3.12–3.14, JavaScript / TypeScript |
| **Embedded & DSP** | STM32 HAL, FreeRTOS, ESP32 / ESP-IDF, Biquad IIR, FIR, FDTD Waveguides, FFT / UPOLS, KEMAR HRIR |
| **Graphics & Systems** | Metal, WebGL2, WebGPU, Blender 4.0–4.3 (`bpy`/`bmesh`), Binary glTF 2.0, BT.709 (`colr nclx`), RIFF/AVI, ISO-BMFF MP4 |
| **Distributed & Storage** | RESP3, Raft Consensus, HNSW SQ8, Okapi BM25, LSM-Tree, ChaCha20-Poly1305, Gorilla XOR, Jepsen Verifier |
| **Apple Ecosystem** | iOS 18, watchOS 11, visionOS 2 (CompositorServices), macOS 15, AUv3, CoreML, MPSGraph, HealthKit |

---

<p align="center">
  <b>Portfolio & Evidence:</b> <a href="https://ardhyanovri.my.id">ardhyanovri.my.id</a> · <b>Direct Contact:</b> <a href="mailto:ardhyasan@gmail.com">ardhyasan@gmail.com</a>
</p>
