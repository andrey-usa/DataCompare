# Daily DataCompare refactor brief

The goal of this automated agent is to make small, focused improvements to the
Python/Polars codebase behind the DataCompare project. Each run should consider
performance, readability and maintainability, but must avoid making wide‑ranging
API changes. Please adhere to the following guidelines:

1. **Use lazy evaluation and pipeline chaining**: When loading and processing
   data, prefer `scan_*` functions and `LazyFrame` pipelines so Polars can plan
   the execution for optimal memory and speed【577295089812310†L512-L557】.
2. **Filter early and minimize conversions**: Apply filters as soon as possible
   in a pipeline and avoid converting columns between types unnecessarily.
   Avoid Python loops; instead, use built‑in Polars expressions for
   transformations【577295089812310†L564-L579】.
3. **Optimise memory usage**: Select only the columns needed for comparison,
   drop unused columns and choose the smallest reasonable integer types to
   reduce memory footprint【577295089812310†L586-L594】.
4. **Be mindful of parallelism**: Polars automatically uses available CPU cores,
   but parallelism has overhead; do not force extra parallelism unless profiles
   demonstrate clear benefits【577295089812310†L595-L618】.
5. **Keep changes minimal**: Limit each refactor to fewer than 200 lines of
   change. Preserve all public APIs, CLI and GUI behaviour unless explicitly
   instructed otherwise.
6. **Run tests and benchmarks**: After your changes, execute the test suite
   (`pytest`) and the benchmark suite (`pytest --benchmark-only`). If any test
   fails or the benchmark shows a significant regression, revert your changes.

At the end of each run, commit the successful changes and let the workflow
open a pull request with a clear summary of what was improved.
