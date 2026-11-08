Initial educational numerical migration lab: a corrected legacy-style Fortran RK4
solver with safe Rust and C++20 ports. The supplied implicit-integer stage defect
is preserved and reproduced as a required negative control.

Validation includes 10 referee tests, 27 differential scenarios, 101 trajectory
checkpoints, circular/free-drift analytic oracles, RK4 convergence, invariants,
and 14 invalid-input/singular-stage cases per language. Both optimized and checked
builds passed locally. All four GitHub Actions jobs passed on Ubuntu 22.04/24.04.

Source commit: 6a0ef64a7785217765868e209f1339dbc610a6b6
CI: https://github.com/vanovri/legacy-orbital-port/actions/runs/39174423811

The ZIP includes source, tests, reports, a measured figure, provenance notes,
and a bounded migration prompt. SHA256SUMS.txt covers the downloadable ZIP.
Requires Python 3.10+, GNU Fortran, GCC C++20, and Rust. No compiler binaries
are bundled. This synthetic point-mass exercise is not historical flight software
or mission-grade orbital validation. No Gemini benchmark claims are made.
