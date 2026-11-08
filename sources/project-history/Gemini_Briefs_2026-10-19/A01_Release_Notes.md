Separate FIR migration extension with real Fortran and Rust compilers.

Both causal FIR implementations match an independent Python reference on synthetic fixtures, including seeded random signed inputs. Strict finite/count/work bounds reject malformed inputs, overflow and existing-output overwrites. The harness rejects equally truncated outputs and rebuilds changed sources.

Validation: 26 tests on local native compilers, actual compiler versions recorded, 32-sample fixture parity with zero observed difference, independent GitHub Linux compilation and tests. No speedup or hardware performance claim.
