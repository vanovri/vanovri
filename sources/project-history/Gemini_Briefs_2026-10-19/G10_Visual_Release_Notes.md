Fix court perimeter lines by emitting complete independent segment pairs, removing unintended diagonals. Pause match physics and scoring until both controller slots are paired; show the waiting state in the UI.

Validation: 28 Node tests, actual local browser host plus two paired controllers, touch fallback, waiting/playing state transitions, corrected court screenshot and zero browser console errors. Retains explicit TTS opt-in, request bounds and token pairing from v0.2.0. No physical phone or live provider test.
