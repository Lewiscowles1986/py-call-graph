:class:`SyncronousTracer` / :class:`SynchronousTracer`
========================================================

The synchronous tracer installs ``sys.settrace`` and processes each event as
it arrives on the calling thread. It is the default.

.. autoclass:: pycallgraph.tracer.SyncronousTracer
        :members:

Both spellings resolve to the same class. The historical names misspell
"Synchronous" and "Asynchronous", but they are part of the public API, so the
correctly spelled names (:class:`SynchronousTracer` and
:class:`AsynchronousTracer`) are provided as aliases rather than a rename.

:class:`AsyncronousTracer` / :class:`AsynchronousTracer`
=========================================================

The asynchronous tracer hands every event to a
:class:`~pycallgraph.tracer.TraceProcessor` worker thread over a queue, so the
traced program is not slowed down by the work of recording. It is enabled with
``Config(threaded=True)`` or ``--threaded``.

Shutdown is bounded: :meth:`~pycallgraph.tracer.AsyncronousTracer.done` waits
for the queue to drain and then joins the worker with a timeout. If the worker
does not finish in time, a :class:`~pycallgraph.exceptions.PyCallGraphException`
is raised rather than blocking the traced program indefinitely.

.. autoclass:: pycallgraph.tracer.AsyncronousTracer
        :members:

:class:`TraceProcessor`
=======================

The processor accumulates the statistics the outputs render, and is also a
:class:`threading.Thread` for the asynchronous case.

.. autoclass:: pycallgraph.tracer.TraceProcessor
        :members:
