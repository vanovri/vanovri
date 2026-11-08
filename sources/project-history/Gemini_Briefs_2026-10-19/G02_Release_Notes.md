Educational Python runtime optimization with a before/after implementation, mutation-safe public contracts, and paired measurements. The candidate preserves nested input snapshots, fresh outputs, aliases/container types, editable history, and mutable tools. A preserved supplied candidate demonstrates the original mutation bug.

Fourteen contract tests pass locally on Windows/Linux and from a clean checkout. Nine-pair local measurements meet the requested 40% preparation and 20% cold-import reduction targets on both operating systems. Raw samples, memory measurements, source hashes, and first-validator-use costs are included. CI records performance separately from correctness because shared runners are not controlled benchmark environments.

No artificial sleeps, model calls, API keys, external Python dependencies, or upstream Google ADK benchmark claims. The bounded prompt is a template, not an unattended-run record.
