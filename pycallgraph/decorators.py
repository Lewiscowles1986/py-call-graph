import functools

from .pycallgraph import PyCallGraph


def trace(output=None, config=None):
    '''Trace every call of the decorated function.

    Each invocation is traced independently: a fresh
    :class:`~pycallgraph.pycallgraph.PyCallGraph` is started and finished
    around the call, so calling the function twice produces two outputs and
    the return value is passed straight through.

    :param output: an :class:`~pycallgraph.output.Output` instance, or a
        **sequence** of them. A generator cannot be used here: the outputs are
        iterated several times, so an iterator would be silently exhausted.
        If omitted, ``PyCallGraph`` raises ``PyCallGraphException`` when the
        decorated function runs.
    :param config: an optional :class:`~pycallgraph.config.Config`.

    Example::

        from pycallgraph import Config
        from pycallgraph.decorators import trace
        from pycallgraph.output import GraphvizOutput

        @trace(output=GraphvizOutput(output_file='trace.png'))
        def my_function():
            ...

        @trace(
            output=[GraphvizOutput(output_file='trace.png')],
            config=Config(max_depth=5),
        )
        def another_function():
            ...
    '''
    def inner(func):
        @functools.wraps(func)
        def exec_func(*args, **kw_args):
            with PyCallGraph(output, config):
                return func(*args, **kw_args)

        return exec_func

    return inner
