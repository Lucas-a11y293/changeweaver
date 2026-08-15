# Benchmark Notes

The benchmark command is stored in `tools/benchmark.py` and measures the complete local snapshot pipeline over a supplied repository. It reports minimum, maximum, and mean wall-clock seconds, along with node and edge counts and the snapshot digest.

## Baseline measurement

The following result was measured on the sandbox environment on 2026-08-16 using ten iterations over `tests/fixtures/sample_app`.

| Input | Iterations | Nodes | Edges | Min (s) | Mean (s) | Max (s) |
|---|---:|---:|---:|---:|---:|---:|
| Three-file Dart fixture | 10 | 3 | 2 | 0.001108 | 0.001392 | 0.002339 |

This is a smoke measurement, not a production capacity claim. Real repositories vary with source bytes, package count, filesystem cache, and unresolved imports. Future performance changes should add a controlled corpus and report environment details before claiming improvement.
