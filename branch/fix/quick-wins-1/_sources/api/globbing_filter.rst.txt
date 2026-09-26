.. _globbing_filter:

:class:`globbing_filter.GlobbingFilter`
=======================================

Selects which functions are traced, using ``fnmatch`` patterns. Exclusions are
checked first, then inclusions; anything matching neither is excluded.

.. autoclass:: pycallgraph.globbing_filter.GlobbingFilter
        :members:

:class:`grouper.Grouper`
========================

Assigns each traced function to a group, which controls how nodes are grouped
in the rendered graph. By default the top-level module name is used.

.. autoclass:: pycallgraph.grouper.Grouper
        :members:
