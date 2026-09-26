

import inspect
import os
import sys
import sysconfig
import time
import warnings
from collections import defaultdict
from queue import Queue, Empty
from threading import Thread

from .util import Util
from .grouper import Grouper
from .exceptions import PyCallGraphException


#: Sentinel placed on the trace queue to tell the processor thread that
#: everything queued before it has been processed and it should exit.
_SHUTDOWN = object()


def _empty_int_dict():
    '''Module-level factory so the call graph default can be pickled.'''
    return defaultdict(int)


class ProcessedTraceConfig(object):
    '''The subset of configuration a *restored* trace still needs.

    Outputs read a handful of settings off ``processor.config`` while
    rendering (grouping, memory labels, verbosity). A live processor gets a
    full ``Config``, but that object holds an ``argparse`` parser and cannot
    be pickled. A dump therefore stores this small, picklable stand-in so a
    trace loaded later can still be rendered without the original process.
    '''

    def __init__(self, config=None):
        if config is not None:
            self.groups = getattr(config, 'groups', True)
            self.trace_grouper = getattr(config, 'trace_grouper', Grouper())
            self.memory = getattr(config, 'memory', False)
        else:
            self.groups = True
            self.trace_grouper = Grouper()
            self.memory = False
        self.verbose = False
        self.debug = False

    def log_verbose(self, text):
        if self.verbose:
            print(text)

    def log_debug(self, text):
        if self.debug:
            print(text)


class SyncronousTracer(object):

    def __init__(self, outputs, config):
        self.processor = TraceProcessor(outputs, config)
        self.config = config
        # Set once this tracer has reported that the memory backend cannot
        # measure, so the warning is not repeated for every traced event.
        self._memory_backend_warned = False

    def tracer(self, frame, event, arg):
        self.processor.process(frame, event, arg, self.memory())
        return self.tracer

    def memory(self):
        '''Return the current memory usage in bytes, or None if disabled.

        A negative reading from ``memory_usage`` means "could not measure"
        (for example ``ps v`` on macOS has no RSS column). That is reported as
        ``None`` so it is not published as a real, negative figure, and the
        reason is logged once rather than on every traced event.
        '''
        if not self.config.memory:
            return None

        from .memory_profiler import memory_usage

        sample = memory_usage(-1, 0)[0]
        if sample < 0:
            if not self._memory_backend_warned:
                self._memory_backend_warned = True
                warnings.warn(
                    'Memory usage could not be measured on this platform: the '
                    'memory backend returned -1, which usually means the '
                    'psutil module is missing and no usable ps backend is '
                    'available. Memory statistics will be omitted. Installing '
                    'psutil may help.'
                )
            return None

        return int(sample * 1000000)

    def start(self):
        sys.settrace(self.tracer)

    def stop(self):
        sys.settrace(None)

    def done(self):
        pass


class AsyncronousTracer(SyncronousTracer):

    #: How long to wait for the trace processor to drain and exit. A stuck
    #: processor used to block the traced program forever with no diagnostics.
    shutdown_timeout = 10.0

    def start(self):
        self.processor.start()
        SyncronousTracer.start(self)

    def tracer(self, frame, event, arg):
        self.processor.queue(frame, event, arg, self.memory())
        return self.tracer

    def done(self):
        self.processor.done()
        self.processor.join(self.shutdown_timeout)

        if self.processor.is_alive():
            raise PyCallGraphException(
                'The threaded trace processor did not finish within '
                '{0} seconds. The trace is incomplete; try running without '
                'threaded tracing.'.format(self.shutdown_timeout)
            )


class TraceProcessor(Thread):
    '''
    Contains a callback used by sys.settrace, which collects information about
    function call count, time taken, etc.
    '''

    # The subset of state that is meaningful once a trace has finished and
    # that can safely be pickled. Runtime-only threading state, the open
    # outputs and the config are deliberately excluded. Keep this in sync
    # with the counters set up in init_trace_data (see test_pickle.py).
    _picklable_state = (
        'call_stack',
        'func_count',
        'func_count_max',
        'func_time',
        'func_time_max',
        'func_memory_in',
        'func_memory_in_max',
        'func_memory_out',
        'func_memory_out_max',
    )

    def __init__(self, outputs, config):
        # Daemon so a trace that is never cleanly finished cannot keep the
        # interpreter alive at exit. A normal run still joins the processor in
        # AsyncronousTracer.done() before outputs are generated.
        Thread.__init__(self, daemon=True)
        self.trace_queue = Queue()
        self.keep_going = True
        self.outputs = outputs
        self.config = config
        self.updatables = [a for a in self.outputs if a.should_update()]

        self.init_trace_data()
        self.init_libpath()

    def init_trace_data(self):
        self.previous_event_return = False

        # A mapping of which function called which other function
        self.call_dict = defaultdict(lambda: defaultdict(int))

        # Current call stack
        self.call_stack = ['__main__']

        # Counters for each function
        self.func_count = defaultdict(int)
        self.func_count_max = 0
        self.func_count['__main__'] = 1

        # Accumulative time per function
        self.func_time = defaultdict(float)
        self.func_time_max = 0

        # Accumulative memory addition per function
        self.func_memory_in = defaultdict(int)
        self.func_memory_in_max = 0

        # Accumulative memory addition per function once exited
        self.func_memory_out = defaultdict(int)
        self.func_memory_out_max = 0

        # Keeps track of the start time of each call on the stack
        self.call_stack_timer = []
        self.call_stack_memory_in = []
        self.call_stack_memory_out = []

    def init_libpath(self):
        '''Work out the directories which contain library (non-user) code.

        ``sysconfig`` reports the *logical* install location, which is often a
        symlink (Homebrew, asdf and conda all do this). Modules report their
        *real* path via ``__file__``, so both the logical and the resolved
        paths are recorded to keep detection working on symlinked installs.
        '''
        paths = []
        for key in ('stdlib', 'platstdlib', 'purelib', 'platlib'):
            try:
                path = sysconfig.get_path(key)
            except KeyError:
                path = None
            if path:
                paths.append(path)

        libdest = sysconfig.get_config_var('LIBDEST')
        if libdest:
            paths.append(libdest)

        # Normalise to absolute, resolved (symlink-free) paths. A separator
        # suffix makes the lookup a proper path-boundary test rather than a
        # bare string prefix test, so '/usr/lib/python3.13-extra/x.py' is not
        # mistaken for a module inside '/usr/lib/python3.13'.
        self.lib_paths = []
        for path in paths:
            for candidate in (path, os.path.realpath(path)):
                candidate = os.path.join(
                    os.path.abspath(candidate), ''
                ).lower()
                if candidate not in self.lib_paths:
                    self.lib_paths.append(candidate)

        # Cache of file name -> bool. is_module_stdlib runs for every 'call'
        # event, and each miss costs syscalls (lstat/readlink in realpath), so
        # results are memoized exactly as inspect.getmodule is above.
        self.is_stdlib_cache = {}

    def queue(self, frame, event, arg, memory):
        data = {
            'frame': frame,
            'event': event,
            'arg': arg,
            'memory': memory,
        }
        self.trace_queue.put(data)

    def run(self):
        while True:
            try:
                data = self.trace_queue.get(timeout=0.1)
            except Empty:
                # Nothing to process yet. If shutdown has been requested and
                # the queue is genuinely empty, the backlog is drained.
                if not self.keep_going:
                    break
                continue

            if data is _SHUTDOWN:
                # Sentinel: everything queued before this has been processed.
                break

            self.process(**data)

    def done(self):
        '''Ask the processor to finish and exit.

        Everything already queued is still processed, then the worker exits
        on the sentinel. This replaces a busy-wait on ``queue.empty()`` that
        spun forever if the worker had already stopped.
        '''
        self.keep_going = False
        self.trace_queue.put(_SHUTDOWN)

    def process(self, frame, event, arg, memory=None):
        '''This function processes a trace result. Keeps track of
        relationships between calls.
        '''

        if event == 'call':
            keep = True
            code = frame.f_code

            # Stores all the parts of a human readable name of the current call
            full_name_list = []

            # Work out the module name
            module = inspect.getmodule(code)
            if module:
                module_name = module.__name__
                try:
                    module_path = module.__file__

                    if not self.config.include_stdlib \
                            and self.is_module_stdlib(module_path):
                        keep = False
                except AttributeError:
                    keep = False

                if module_name == '__main__':
                    module_name = ''
            else:
                module_name = ''

            if module_name:
                full_name_list.append(module_name)

            # Work out the class name
            try:
                class_name = frame.f_locals['self'].__class__.__name__
                full_name_list.append(class_name)
            except (KeyError, AttributeError):
                class_name = ''

            # Work out the current function or method
            func_name = code.co_name
            if func_name == '?':
                func_name = '__main__'
            full_name_list.append(func_name)

            # Create a readable representation of the current call
            full_name = '.'.join(full_name_list)

            if len(self.call_stack) > self.config.max_depth:
                keep = False

            # Load the trace filter, if any. 'keep' determines if we should
            # ignore this call
            if keep and self.config.trace_filter:
                keep = self.config.trace_filter(full_name)

            # Store the call information
            if keep:

                if self.call_stack:
                    src_func = self.call_stack[-1]
                else:
                    src_func = None

                self.call_dict[src_func][full_name] += 1

                self.func_count[full_name] += 1
                self.func_count_max = max(
                    self.func_count_max, self.func_count[full_name]
                )

                self.call_stack.append(full_name)
                self.call_stack_timer.append(time.perf_counter())

                if memory is not None:
                    self.call_stack_memory_in.append(memory)
                    self.call_stack_memory_out.append([full_name, memory])

            else:
                # Keep all four stacks in step so a return can pop them
                # positionally. Filtered frames push sentinels onto every
                # stack; previously the memory stacks were skipped, which
                # attributed memory to the wrong function whenever --memory
                # was combined with a filter or --max-depth.
                self.call_stack.append('')
                self.call_stack_timer.append(None)

                if memory is not None:
                    self.call_stack_memory_in.append(None)
                    self.call_stack_memory_out.append(None)

        if event == 'return':

            self.previous_event_return = True

            if self.call_stack:
                full_name = self.call_stack.pop(-1)

                if self.call_stack_timer:
                    start_time = self.call_stack_timer.pop(-1)
                else:
                    start_time = None

                if start_time:
                    call_time = time.perf_counter() - start_time

                    self.func_time[full_name] += call_time
                    self.func_time_max = max(
                        self.func_time_max, self.func_time[full_name]
                    )

                if memory is not None:
                    # Pop unconditionally so the stacks cannot drift. An entry
                    # is None for a filtered frame; a measured value of 0 is a
                    # real reading and must not be treated as "no data".
                    if self.call_stack_memory_in:
                        start_mem = self.call_stack_memory_in.pop(-1)
                    else:
                        start_mem = None

                    if start_mem is not None:
                        call_memory = memory - start_mem
                        self.func_memory_in[full_name] += call_memory

                        self.func_memory_in_max = max(
                            self.func_memory_in_max,
                            self.func_memory_in[full_name],
                        )

                    if self.call_stack_memory_out:
                        entry = self.call_stack_memory_out.pop(-1)
                    else:
                        entry = None

                    # Compute memory-out here, at return time, rather than
                    # relying on a global flag tied to the previous event,
                    # which desynchronised the stack when a reading was 0.
                    if entry is not None:
                        out_name, out_mem = entry
                        if out_mem is not None:
                            out_memory = memory - out_mem
                            self.func_memory_out[out_name] += out_memory
                            self.func_memory_out_max = max(
                                self.func_memory_out_max,
                                self.func_memory_out[out_name],
                            )

    def is_module_stdlib(self, file_name):
        '''
        Returns True if ``file_name`` lives under a known library directory.

        "Library" here means the standard library *and* installed packages:
        ``sysconfig``'s stdlib/platstdlib plus the purelib/platlib
        (site-packages) directories. That mirrors the ``--stdlib`` option,
        which controls whether both are included in the trace.

        The check is a path-boundary prefix match on the symlink-resolved,
        lower-cased path, so it is tolerant of symlinked interpreters
        (Homebrew, asdf, conda) and of case differences between the recorded
        paths and a module's ``__file__``.
        '''
        try:
            return self.is_stdlib_cache[file_name]
        except KeyError:
            pass

        resolved = os.path.realpath(file_name).lower()
        result = any([
            resolved.startswith(lib_path)
            for lib_path in self.lib_paths
        ])
        self.is_stdlib_cache[file_name] = result
        return result

    def __getstate__(self):
        '''Return only the collected trace data.

        TraceProcessor subclasses Thread, so the default state includes thread
        handles, locks, the trace queue and an excepthook closure, none of
        which can be pickled (and none of which are wanted). The configured
        outputs and config are dropped for the same reason, so a dump can be
        loaded without them.
        '''
        state = {
            key: getattr(self, key)
            for key in self._picklable_state
            if hasattr(self, key)
        }
        # The call graph is normally a defaultdict(lambda: defaultdict(int)),
        # and a lambda cannot be pickled. Rebuild it with a module-level
        # factory so the data survives a round trip.
        state['call_dict'] = defaultdict(
            _empty_int_dict,
            {src: defaultdict(int, dests)
             for src, dests in self.call_dict.items()},
        )
        # A restored trace still needs a few settings to render, and the live
        # config (argparse parser et al) cannot be pickled, so store a small
        # picklable stand-in instead.
        state['config'] = ProcessedTraceConfig(getattr(self, 'config', None))
        return state

    def groups(self):
        grp = defaultdict(list)
        for node in self.nodes():
            grp[node.group].append(node)
        for g in list(grp.items()):
            yield g

    def _grouper(self):
        '''The grouping function used to build nodes/edges.

        A live processor takes it from the config. An unpickled processor has
        no config, so the grouper is restored from the pickled state instead
        (see __getstate__); the default groups everything by top-level module.
        '''
        config = getattr(self, 'config', None)
        if config is not None:
            return config.trace_grouper
        return getattr(self, 'trace_grouper', Grouper())

    def stat_group_from_func(self, func, calls):
        stat_group = StatGroup()
        stat_group.name = func
        stat_group.group = self._grouper()(func)
        stat_group.calls = Stat(calls, self.func_count_max)
        stat_group.time = Stat(self.func_time.get(func, 0), self.func_time_max)
        stat_group.memory_in = Stat(
            self.func_memory_in.get(func, 0), self.func_memory_in_max
        )
        stat_group.memory_out = Stat(
            self.func_memory_out.get(func, 0), self.func_memory_out_max
        )
        return stat_group

    def nodes(self):
        for func, calls in list(self.func_count.items()):
            yield self.stat_group_from_func(func, calls)

    def edges(self):
        for src_func, dests in list(self.call_dict.items()):
            if not src_func:
                continue
            for dst_func, calls in list(dests.items()):
                edge = self.stat_group_from_func(dst_func, calls)
                edge.src_func = src_func
                edge.dst_func = dst_func
                yield edge


class Stat(object):
    '''Stores a "statistic" value, e.g. "time taken" along with the maximum
    possible value of the value, which is used to calculate the fraction of 1.
    The fraction is used for choosing colors.
    '''

    def __init__(self, value, total):
        self.value = value
        self.total = total
        try:
            self.fraction = value / total
        except ZeroDivisionError:
            self.fraction = 0

    @property
    def value_human_bibyte(self):
        '''Mebibyte of the value in human readable a form.'''
        return Util.human_readable_bibyte(self.value)


class StatGroup(object):
    pass


def simple_memoize(callable_object):
    '''Simple memoization for functions without keyword arguments.

    This is useful for mapping code objects to module in this context.
    inspect.getmodule() requires a number of system calls, which may slow down
    the tracing considerably. Caching the mapping from code objects (there is
    *one* code object for each function, regardless of how many simultaneous
    activations records there are).

    In this context we can ignore keyword arguments, but a generic memoizer
    ought to take care of that as well.
    '''

    cache = dict()

    def wrapper(*rest):
        if rest not in cache:
            cache[rest] = callable_object(*rest)
        return cache[rest]

    return wrapper


inspect.getmodule = simple_memoize(inspect.getmodule)
