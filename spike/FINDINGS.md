# Spike: `sys.monitoring` as an alternative to `sys.settrace`

Issue: [#40 Investigate sys.monitoring](https://github.com/Lewiscowles1986/py-call-graph/issues/40)

## Why this matters

`pycallgraph` collects its call graph with `sys.settrace`. That hook is a
single global slot shared with debuggers and coverage tools: whoever sets it
last wins, so running pycallgraph under a debugger or with coverage produces
garbled results or breaks the other tool.

`sys.monitoring` (added in Python 3.12) is a separate, event-based mechanism
with its own tool slots. The open question in #40 was whether it can produce
the same call graph *and* coexist with `settrace`-based tools.

## What was tested

Prototype: [`spike/sys_monitoring_prototype.py`](sys_monitoring_prototype.py).
Run it with Python 3.12+ and `PYTHONPATH=$(pwd)`.

It traces `test/calls.py::one_nop` (which calls `nop`) with both the existing
`sys.settrace` tracer and a `sys.monitoring` tracer, and compares the graphs.

## Findings

### 1. `PY_START` / `PY_RETURN` reproduce the settrace call graph exactly

```
sys.settrace call graph:      sys.monitoring call graph:
  __main__ -> {calls.one_nop: 1}    __main__ -> {calls.one_nop: 1}
  calls.one_nop -> {calls.nop: 1}   calls.one_nop -> {calls.nop: 1}
equivalent: True
```

`PY_START` is the per-frame analogue of settrace's `call` event and
`PY_RETURN` of `return`. They preserve nesting, so the call stack can be
rebuilt the same way the existing `TraceProcessor` does.

### 2. The `CALL` event is **not** the right building block

`events.CALL` looks like the obvious equivalent of settrace's `call`, but it
fires only for *some* calls, and nested calls are missed entirely:

```
calls seen with only events.CALL: ['<module>', 'outer', '<module>']
calls seen with PY_START/PY_RETURN: outer, inner (start/return, in order)
```

This is a significant trap. A caller-tracking implementation must use
`PY_START`/`PY_RETURN` (or a combination with `CALL` for C-level callees),
not `CALL` alone. This finding alone justifies the spike.

### 3. `sys.monitoring` and `sys.settrace` **can run at the same time**

Reproduced by [`spike/coexistence_check.py`](coexistence_check.py)
(exit code 0 when both tracers observe the call):

```
settrace saw:   ['work', 'helper']
monitoring saw: ['work', 'helper']
BOTH ACTIVE - stackable: True
```

This is the important result for #40. A monitoring-based tracer does **not**
displace a `settrace`-based coverage tool or debugger. Migrating pycallgraph to
`sys.monitoring` would remove the mutual breakage described in the issue.

### 4. Tool slots are the remaining contention point

`sys.monitoring` provides a small, fixed set of tool ids
(`DEBUGGER_ID=0`, `COVERAGE_ID=1`, `PROFILER_ID=2`, plus a few spare).
`use_tool_id` raises `ValueError` when a slot is already taken:

```
ValueError: tool 1 is already in use
```

So monitoring-based tools still contend with each other, but on a *different,
larger* resource than `sys.settrace`, and the failure is an explicit
exception rather than silent clobbering. The prototype currently hard-codes
`PROFILER_ID` (it does not yet fall back to a free id); the implementation
should:

- prefer `PROFILER_ID`, fall back to a free id, and
- raise a clear, actionable error when none is available.

### 5. Local events limit overhead (and self-tracing)

`set_local_events(tool, code, ...)` enables events for specific code objects.
This allows excluding pycallgraph's own frames and third-party/stdlib code
without the per-frame filtering cost of settrace. During the spike the
prototype had to explicitly exclude its own module to avoid tracing itself.

## Recommendation

Implement an **opt-in** `SysMonitoringTracer` for Python 3.12+, selected via
configuration (e.g. `Config(tracer='monitoring')` or a `--tracer` CLI flag),
while keeping `sys.settrace` as the default. Rationale:

- No backward-incompatible change: existing behaviour, output formats and
  defaults are untouched. Users opt in when they need coexistence.
- The equivalence is demonstrated but only for Python-call graphs; memory
  tracking and threaded/async tracing need separate work.
- Python 3.8-3.11 users keep the settrace tracer, which the CI matrix still
  covers.

Suggested follow-up ticket scope:

1. Add `SysMonitoringTracer` next to `SyncronousTracer`/`AsyncronousTracer`,
   sharing the `TraceProcessor` so all outputs keep working unchanged.
2. Select it automatically only when explicitly requested, and document the
   coexistence benefit.
3. Add integration coverage for pycallgraph-under-coverage and
   pycallgraph-with-a-debugger-tracer-active.
4. Benchmark overhead against settrace before considering any default change.

## Risks / open questions

- **Overhead unmeasured.** Monitoring is generally cheaper than settrace, but
  this spike did not benchmark it. Do not claim a performance win without
  numbers.
- **`CALL` semantics.** Any code that wants C-function callees needs the
  `CALL` event, whose nesting behaviour (finding 2) must be handled carefully.
- **Exceptions / generators.** `PY_UNWIND`, `PY_YIELD` and `PY_RESUME` were not
  exercised; they matter for correct stacks on exceptions and generators.
- **Memory tracking** relies on `frame.f_locals` in the current tracer; the
  monitoring callbacks do not receive frames, so that path needs a rewrite.
