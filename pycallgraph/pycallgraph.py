import locale

from .output import Output
from .config import Config
from .tracer import AsyncronousTracer, SyncronousTracer
from .exceptions import PyCallGraphException


class PyCallGraph(object):
    def __init__(self, output=None, config=None):
        '''output can be a single Output instance or a sequence of them.
        Any other iterable (for example a generator) is materialised here so
        it can be iterated safely more than once.  Example usage:

            PyCallGraph(output=GraphvizOutput(), config=Config())
        '''
        locale.setlocale(locale.LC_ALL, '')

        if output is None:
            self.output = []
        elif isinstance(output, Output):
            self.output = [output]
        else:
            self.output = list(output)

        self.config = config or Config()

        # True between __enter__ and its matching __exit__, so a context that
        # is exited more than once does not render the outputs again.
        self._in_context = False

        configured_ouput = self.config.get_output()
        if configured_ouput:
            self.output.append(configured_ouput)

        self.reset()

    def __enter__(self):
        '''Start tracing and return this instance.

        Returning self allows ``with PyCallGraph(...) as graph:``; it used to
        return None, so ``graph`` was silently bound to None.
        '''
        self.start()
        self._in_context = True
        return self

    def __exit__(self, type, value, traceback):
        '''Finish the trace and generate the outputs.

        Idempotent, and returns a falsy value so an exception raised in the
        body still propagates.
        '''
        if self._in_context:
            self._in_context = False
            self.done()

    def get_tracer_class(self):
        if self.config.threaded:
            return AsyncronousTracer
        else:
            return SyncronousTracer

    def reset(self):
        '''Resets all collected statistics.  This is run automatically by
        start(reset=True) and when the class is initialized.
        '''
        self.tracer = self.get_tracer_class()(self.output, config=self.config)

        for output in self.output:
            self.prepare_output(output)

    def start(self, reset=True):
        '''Begins a trace.  Setting reset to True will reset all previously
        recorded trace data.
        '''
        if not self.output:
            raise PyCallGraphException(
                'No outputs declared. Please see the '
                'examples in the online documentation.'
            )

        if reset:
            self.reset()

        for output in self.output:
            output.start()

        self.tracer.start()

    def stop(self):
        '''Stops the currently running trace, if any.'''
        self.tracer.stop()

    def done(self):
        '''Stops the trace and tells the outputters to generate their
        output.
        '''
        self.stop()

        self.generate()

    def generate(self):
        # If in threaded mode, wait for the processor thread to complete
        self.tracer.done()

        for output in self.output:
            output.done()

    def add_output(self, output):
        self.output.append(output)
        self.prepare_output(output)

    def prepare_output(self, output):
        output.sanity_check()
        output.set_processor(self.tracer.processor)
        output.reset()
