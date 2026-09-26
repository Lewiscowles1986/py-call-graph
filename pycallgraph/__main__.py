'''Support ``python -m pycallgraph``.

The logic lives in :mod:`pycallgraph.cli` so the module entry point and the
``pycallgraph`` console script share one implementation.
'''
import sys

from .cli import main


if __name__ == '__main__':
    sys.exit(main())
