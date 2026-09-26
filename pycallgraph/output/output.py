import os
from shutil import which
from typing import Optional

from ..exceptions import PyCallGraphException
from ..color import Color


class Output(object):
    '''Base class for all outputters.'''

    def __init__(self, **kwargs):
        self.node_color_func = self.node_color
        self.edge_color_func = self.edge_color
        self.node_label_func = self.node_label
        self.edge_label_func = self.edge_label

        # Update the defaults with anything from kwargs
        [setattr(self, k, v) for k, v in list(kwargs.items())]

    def set_config(self, config):
        '''Move the output options from a Config onto this output.

        Only attributes the output already declares (typically its
        constructor defaults, set from the command line as output options) are
        copied. This used to copy *every* attribute of the config unless the
        output had a callable of the same name, which put the argparse parser,
        the selected output-type name and unrelated config state onto the
        output.
        '''
        for key, value in list(vars(config).items()):
            if key not in vars(self):
                continue
            if callable(getattr(self, key, None)):
                continue
            setattr(self, key, value)

    def node_color(self, node):
        value = float(node.time.fraction * 2 + node.calls.fraction) / 3
        return Color.hsv(value / 2 + .5, value, 0.9)

    def edge_color(self, edge):
        value = float(edge.time.fraction * 2 + edge.calls.fraction) / 3
        return Color.hsv(value / 2 + .5, value, 0.7)

    def node_label(self, node):
        parts = [
            '{0.name}',
            'calls: {0.calls.value:n}',
            'time: {0.time.value:f}s',
        ]

        if self.processor.config.memory:
            parts += [
                'memory in: {0.memory_in.value_human_bibyte}',
                'memory out: {0.memory_out.value_human_bibyte}',
            ]

        return r'\n'.join(parts).format(node)

    def edge_label(self, edge):
        return '{0}'.format(edge.calls.value)

    def sanity_check(self):
        '''Basic checks for certain libraries or external applications.  Raise
        or warn if there is a problem.
        '''
        pass

    @classmethod
    def add_arguments(cls, subparsers):
        pass

    def reset(self):
        pass

    def set_processor(self, processor):
        self.processor = processor

    def start(self):
        '''Initialise variables after initial configuration.'''
        pass

    def update(self):
        '''Called periodically during a trace, but only when should_update is
        set to True.
        '''
        raise NotImplementedError('update')

    def should_update(self):
        '''Return True if the update method should be called periodically.'''
        return False

    def done(self):
        '''Called when the trace is complete and ready to be saved.'''
        raise NotImplementedError('done')

    def ensure_binary(self, cmd: str, pkg: Optional[str] = None):
        if which(cmd):
            return

        pkg_str = f" from {pkg}" if pkg else ""
        raise PyCallGraphException(
            f'The command "{cmd}"{pkg_str} is required to be in your path.'
        )

    def normalize_path(self, path):
        '''Expand both ``~`` and environment variables in ``path``.

        A path may legitimately use both forms (``~/graphs/$RUN.json``), so
        each expansion is applied in turn rather than choosing between them.
        '''
        return os.path.expandvars(os.path.expanduser(path))

    def prepare_output_file(self):
        if self.fp is None:
            self.output_file = self.normalize_path(self.output_file)
            self.fp = open(self.output_file, 'wb')

    def verbose(self, text):
        self.processor.config.log_verbose(text)

    def debug(self, text):
        self.processor.config.log_debug(text)

    @classmethod
    def add_output_file(cls, subparser, defaults, help):
        subparser.add_argument(
            '-o', '--output-file', type=str, default=defaults.output_file,
            help=help,
        )
