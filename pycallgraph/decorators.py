import functools

from .pycallgraph import PyCallGraph


def trace(output=None, config=None):
    """Decorator to trace a function execution with PyCallGraph.

    Args:
        output: An Output instance or list of Output instances (e.g. GraphvizOutput()).
        config: A Config instance to configure tracing behavior.

    Example:
        @trace(GraphvizOutput(output_file='trace.png'))
        def my_function():
            ...
    """
    def inner(func):
        @functools.wraps(func)
        def exec_func(*args, **kw_args):
            with PyCallGraph(output, config):
                return func(*args, **kw_args)

        return exec_func

    return inner