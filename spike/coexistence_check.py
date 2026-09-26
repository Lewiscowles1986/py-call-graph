'''
Reproduces the coexistence test from ``FINDINGS.md`` (finding 3).

Shows that a ``sys.monitoring`` tracer and a ``sys.settrace`` tracer can be
active at the same time and both observe the same calls. This is the result
that matters for issue #40: a monitoring-based pycallgraph would not displace
a settrace-based coverage tool or debugger.

Run with ``PYTHONPATH=$(pwd) python spike/coexistence_check.py`` on 3.12+.
'''
import sys

# A spare tool id, as a third-party tool would pick.
SPARE_TOOL_ID = 4


def main():
    monitoring = getattr(sys, 'monitoring', None)
    if monitoring is None:
        raise SystemExit('sys.monitoring is not available on this interpreter')

    try:
        monitoring.use_tool_id(SPARE_TOOL_ID, 'coexistence-spike')
    except ValueError as error:
        raise SystemExit('could not acquire tool id: %s' % error)

    monitoring_calls = []

    def on_start(code, instruction_offset):
        monitoring_calls.append(code.co_name)
        return None

    monitoring.register_callback(
        SPARE_TOOL_ID, monitoring.events.PY_START, on_start
    )

    settrace_calls = []

    def tracer(frame, event, arg):
        if event == 'call':
            settrace_calls.append(frame.f_code.co_name)
        return tracer

    def work():
        return helper()

    def helper():
        return 42

    sys.settrace(tracer)
    monitoring.set_events(
        SPARE_TOOL_ID, monitoring.events.PY_START
    )
    work()
    monitoring.set_events(SPARE_TOOL_ID, 0)
    sys.settrace(None)

    monitoring.register_callback(
        SPARE_TOOL_ID, monitoring.events.PY_START, None
    )
    monitoring.free_tool_id(SPARE_TOOL_ID)

    print('settrace saw:  ', settrace_calls)
    print('monitoring saw:', monitoring_calls)
    stackable = bool(settrace_calls) and bool(monitoring_calls)
    print('BOTH ACTIVE - stackable:', stackable)
    return 0 if stackable else 1


if __name__ == '__main__':
    raise SystemExit(main())
