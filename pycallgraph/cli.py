'''
The command line interface to pycallgraph.

The logic lives here rather than in the ``scripts/pycallgraph`` wrapper and
``pycallgraph/__main__.py`` so that both entry points share one implementation
and can be imported and tested directly.
'''
import os
import sys
import runpy

from .config import Config
from .pycallgraph import PyCallGraph
from .exceptions import PyCallGraphException


#: Exit code used when the target script cannot be found or read.
EXIT_SCRIPT_ERROR = 2

USAGE_HINT = 'Try "pycallgraph --help" for usage.'


def _print_error(message):
    sys.stderr.write('pycallgraph: error: {0}\n'.format(message))
    sys.stderr.write(USAGE_HINT + '\n')


def main(argv=None):
    '''Run the pycallgraph command line interface.

    Returns the process exit code. A missing target script is reported as a
    readable error rather than an unhandled traceback.
    '''
    if argv is not None:
        sys.argv = [sys.argv[0]] + list(argv)

    config = Config()
    config.parse_args()

    if not getattr(config, 'command', None):
        _print_error('no script was given to trace.')
        return EXIT_SCRIPT_ERROR

    config.strip_argv()

    if not os.path.exists(config.command):
        _print_error(
            'could not find the script to trace: {0}'.format(config.command)
        )
        return EXIT_SCRIPT_ERROR

    try:
        with open(config.command):
            pass
    except OSError as exc:
        _print_error('could not read {0}: {1}'.format(config.command, exc))
        return EXIT_SCRIPT_ERROR

    try:
        with PyCallGraph(config=config):
            runpy.run_path(config.command, run_name='__main__')
    except PyCallGraphException as exc:
        _print_error(str(exc))
        return EXIT_SCRIPT_ERROR

    return 0


def run():
    '''Console-script entry point.'''
    sys.exit(main())
