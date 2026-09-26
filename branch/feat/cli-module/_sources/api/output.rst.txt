.. _output:

:class:`output.Output` --- Base class for all output modules
============================================================

Every output module subclasses :class:`pycallgraph.output.Output` and
implements :meth:`~pycallgraph.output.Output.done` to write the collected
trace out in its own format.

.. autoclass:: pycallgraph.output.Output
        :members:

Concrete outputs
----------------

These are the outputs registered by default and selectable from the command
line. See :ref:`outputs` in the guide for what each one produces.

.. autoclass:: pycallgraph.output.GraphvizOutput
        :members:

.. autoclass:: pycallgraph.output.GephiOutput
        :members:

.. autoclass:: pycallgraph.output.JSONOutput
        :members:

.. autoclass:: pycallgraph.output.PickleOutput
        :members:

Writing your own output
-----------------------

Subclass :class:`pycallgraph.output.Output`, implement ``done()``, and pass an
instance to :class:`pycallgraph.PyCallGraph` (or to the ``trace`` decorator):

.. code-block:: python

    from pycallgraph import PyCallGraph
    from pycallgraph.output import Output


    class LengthOutput(Output):
        '''Print how many functions were traced.'''

        def __init__(self, **kwargs):
            self.output_file = None
            Output.__init__(self, **kwargs)

        def done(self):
            self.verbose('traced {0} functions'.format(
                len(self.processor.call_dict)))


    with PyCallGraph(output=LengthOutput()):
        my_main_function()

Useful attributes available in ``done()``:

* ``self.processor`` -- the :class:`~pycallgraph.tracer.TraceProcessor` that
  holds the collected statistics.
* ``self.output_file`` -- set it (usually from a ``--output-file`` argument)
  and call :meth:`~pycallgraph.output.Output.normalize_path` before opening it,
  so ``~`` and environment variables are expanded.

Register a class in ``pycallgraph.output.outputters`` if it should also be
selectable from the command line. Implement ``add_arguments`` to declare its
own options.
