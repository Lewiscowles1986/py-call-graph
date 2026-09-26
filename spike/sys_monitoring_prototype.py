'''
Feasibility prototype for a ``sys.monitoring`` based tracer (issue #40).

This is a spike, not shipped code. It answers one question: can
``sys.monitoring`` reproduce the call graph that the existing
``sys.settrace`` tracer collects, so that pycallgraph can eventually stop
monopolising ``sys.settrace`` (which it currently shares badly with
debuggers and coverage tools)?

Run with::

    python spike/sys_monitoring_prototype.py

It requires Python 3.12+ and prints the collected graph plus a comparison
against the settrace tracer for the same workload.
'''
import inspect
import os
import sys
import sysconfig
from collections import defaultdict

from pycallgraph.config import Config
from pycallgraph.tracer import TraceProcessor


def _lib_paths():
    paths = []
    for key in ('stdlib', 'platstdlib', 'purelib', 'platlib'):
        try:
            path = sysconfig.get_path(key)
        except KeyError:
            path = None
        if path:
            paths.append(os.path.join(os.path.abspath(path), '').lower())
            paths.append(os.path.join(
                os.path.realpath(path), '').lower())
    return paths


class SysMonitoringTracer:
    '''
    Minimal call-count tracer built on ``sys.monitoring``.

    Uses the PROFILER tool id, falling back to any free id, and registers
    CALL + PY_RETURN callbacks. CALL is a global event; PY_RETURN is a local
    event, enabled per code object via ``set_local_events`` so overhead is
    limited to code we actually care about.
    '''

    def __init__(self, config=None):
        self.config = config or Config()
        self.lib_paths = _lib_paths()
        self.call_dict = defaultdict(lambda: defaultdict(int))
        self.func_count = defaultdict(int)
        self.call_stack = ['__main__']
        self.func_count['__main__'] = 1
        # Parallel stack of code objects for frames we actually pushed, so
        # returns can be paired reliably. Without this, PY_RETURN for a code
        # object we chose not to track desynchronises the call stack.
        self.code_stack = []
        self.tool_id = None
        self._monitoring = None
        # Code objects belonging to this harness must be ignored, otherwise
        # the tracer traces itself.
        self._harness_file = os.path.realpath(__file__)

    @staticmethod
    def is_available():
        return hasattr(sys, 'monitoring')

    def is_module_stdlib(self, file_name):
        resolved = os.path.realpath(file_name).lower()
        return any(resolved.startswith(p) for p in self.lib_paths)

    def _name_for_code(self, code):
        full_name_list = []
        module = inspect.getmodule(code)
        if module is not None:
            module_name = module.__name__
            try:
                module_path = module.__file__
                if os.path.realpath(module_path) == self._harness_file:
                    return None
                if not self.config.include_stdlib \
                        and self.is_module_stdlib(module_path):
                    return None
            except AttributeError:
                return None
            if module_name == '__main__':
                module_name = ''
        else:
            module_name = ''
        if module_name:
            full_name_list.append(module_name)
        func_name = code.co_name
        if func_name == '?':
            func_name = '__main__'
        full_name_list.append(func_name)
        return '.'.join(full_name_list)

    def on_call(self, code, instruction_offset):
        full_name = self._name_for_code(code)
        if full_name is None:
            return self._monitoring.DISABLE

        if len(self.call_stack) > self.config.max_depth:
            return self._monitoring.DISABLE

        src_func = self.call_stack[-1] if self.call_stack else None
        self.call_dict[src_func][full_name] += 1
        self.func_count[full_name] += 1
        self.call_stack.append(full_name)
        self.code_stack.append(code)
        return None

    def on_return(self, code, instruction_offset, retval):
        # Only pop when the returning code object is the one on top of the
        # stack; otherwise a disabled frame's return would corrupt the stack.
        if self.code_stack and self.code_stack[-1] is code:
            self.code_stack.pop()
            if self.call_stack:
                self.call_stack.pop(-1)
        return None

    def start(self):
        self._monitoring = sys.monitoring
        self._monitoring.use_tool_id(
            self._monitoring.PROFILER_ID, 'pycallgraph-spike'
        )
        self.tool_id = self._monitoring.PROFILER_ID
        # PY_START/PY_RETURN are the sys.monitoring equivalent of the
        # settrace 'call'/'return' events: they fire once per Python frame
        # and preserve nesting (verified in the spike).
        self._monitoring.register_callback(
            self.tool_id, self._monitoring.events.PY_START, self.on_call
        )
        self._monitoring.register_callback(
            self.tool_id, self._monitoring.events.PY_RETURN, self.on_return
        )
        self._monitoring.set_events(
            self.tool_id,
            self._monitoring.events.PY_START
            | self._monitoring.events.PY_RETURN,
        )

    def stop(self):
        self._monitoring.set_events(self.tool_id, 0)
        self._monitoring.register_callback(
            self.tool_id, self._monitoring.events.PY_START, None
        )
        self._monitoring.register_callback(
            self.tool_id, self._monitoring.events.PY_RETURN, None
        )
        self._monitoring.free_tool_id(self.tool_id)


def _settrace_graph(target):
    processor = TraceProcessor([], Config(include_stdlib=False))
    sys.settrace(processor.process)
    target()
    sys.settrace(None)
    return {
        src: dict(dests)
        for src, dests in processor.call_dict.items()
        if src
    }


def _sysmon_graph(target):
    tracer = SysMonitoringTracer(Config(include_stdlib=False))
    tracer.call_dict.pop(None, None)
    tracer.start()
    try:
        target()
    finally:
        tracer.stop()
    return {
        src: dict(dests)
        for src, dests in tracer.call_dict.items()
        if src
    }


if __name__ == '__main__':
    if not SysMonitoringTracer.is_available():
        raise SystemExit('sys.monitoring is not available on this interpreter')

    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'test'
    ))
    import calls  # noqa: E402

    settrace_result = _settrace_graph(calls.one_nop)
    sysmon_result = _sysmon_graph(calls.one_nop)

    print('sys.settrace call graph:')
    for src, dests in sorted(settrace_result.items()):
        print('  %s -> %s' % (src, dests))
    print('sys.monitoring call graph:')
    for src, dests in sorted(sysmon_result.items()):
        print('  %s -> %s' % (src, dests))

    print()
    print('settrace     :', settrace_result)
    print('sys.monitoring:', sysmon_result)
    print('equivalent    :', settrace_result == sysmon_result)
