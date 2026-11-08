# G06 / A06 implementation contract

Original brief is archived verbatim in Project_06_Original_Brief.txt. Preserve both new fur mode and earlier cable-learning mode in one numerical lab.

Use 16,384 strands with eight segments and nine particles per strand. One compute invocation owns an entire strand. Read one state buffer, solve only local particle arrays and write the other buffer. This avoids races between neighboring particles. Keep pinned roots fixed. Use fixed simulation steps, bounded catch-up, velocity damping and repeated length projection. Keep this an educational solver rather than a physically validated material model.

The render pass reads the same GPU output buffer. Use one instanced line strip per strand, rather than a single strip joining the tip of one strand to the next root. Do not map GPU buffers in the animation loop. Readback is reserved for explicit verification and evidence export. Pack uniform integer fields through Uint32Array/DataView, not Float32Array bit patterns. Storage output access must use read_write. Derive perspective depth within WebGPU's clip range.

Provide a JavaScript CPU reference and an explicit lower-count Canvas fallback. An in-app Verify action runs held-out small inputs on CPU and GPU with identical parameters, compares finite positions and velocities, root drift and segment-length error, and exports an actual report. Distinguish wall time including readback from GPU execution time. Never display a hardcoded FPS or unmeasured speedup. Device loss must stop GPU work and expose the fallback.

Verify normal and zero wind, damping, root immobility, long runs, invalid inputs, buffer-size limits, pause/restart, per-strand rendering, narrow layout and actual device compilation. A GPU feature is only marked tested if the visible browser app successfully runs it. Static shader text is insufficient.

Primary references checked on2026-10-19:
- https://www.w3.org/TR/WGSL/
- https://gpuweb.github.io/types/interfaces/GPURenderPassEncoder.html
- https://gpuweb.github.io/gpuweb/

The supplied example has no actual spring projection, uses invalid storage-write syntax, writes an integer uniform as a float, joins strands into one strip and places depth outside the visible clip range. Implement and test the intended simulation rather than preserving these defects.
