# Motion Rally v0.1.0

Two phones become rackets over a local WebSocket bridge. The server owns pairing, validated input, stale/disconnect handling and a deterministic 120 Hz match; the desktop page renders the court at 20 Hz snapshots.

**Teaching project.** No real phone motion was exercised in CI, no network latency guarantee is made, and no TTS audio was generated (no API key is included).

## What is verified

- 21 Node tests: protocol decode and range checks, room/slot rules, deterministic replay, bounce/out/hit/miss physics, stale-input decay, serve alternation, comment gating, pairing, duplicate-slot rejection, disconnect and host-close behaviour, invalid-frame handling, static serving and traversal guard.
- Two controllers pair with a host; the duplicate slot is rejected with `slot_taken`.
- Input is timestamped and sequence-checked; stale input decays to neutral and slots are marked stale after 1.5 s.
- Host disconnect closes the room and notifies controllers.
- TTS: without `GEMINI_API_KEY` the adapter reports disabled and performs **zero** fetches; with a stub key it calls the provider once and returns audio.
- Browser QA with real pages (host + two phone-sized controllers): 0 console errors, both slots connected, touch input moved paddles to x = 0.80 / −0.60, score advanced to 0–5 and five commentary entries were produced.
- Local load probe, two simulated controllers at 30 Hz for 6 s: 107 snapshots, gap p50 **62.6 ms** / p95 70.1 ms, server tick average 21.2 ms, zero rejected frames.
- Release ZIP is built by a deterministic writer and verified entry-by-entry (CRC and content).

## Limits

- Raw `DeviceOrientation` only; no sensor fusion, drift correction or racket calibration beyond neutral-pose offset.
- Physics is a teaching model without spin, deformation or aerodynamic detail.
- Room code is the only access control; use on a trusted LAN.
- No HTTPS setup, so iOS motion permission requires the operator to provide a secure context.
- Snapshot interpolation in the host is visual only; the authoritative state is the server tick.
- Load numbers are from one machine on loopback, not from Wi-Fi or real devices.
- No reconnection token, match history or persistent score.

## Assets

- `motion-rally-v0.1.0.zip` — server, clients, tests, tools, evidence and screenshots.
- `SHA256SUMS-v0.1.0.txt` — checksums for every archived file.
