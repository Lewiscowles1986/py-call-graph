import collections

from .output import Output
from .graphviz import GraphvizOutput
from .gephi import GephiOutput
from .json import JSONOutput
from .ubigraph import UbigraphOutput
from .pickle import PickleOutput


outputters = collections.OrderedDict([
    ('graphviz', GraphvizOutput),
    ('gephi', GephiOutput),
    ('json', JSONOutput),
    ('pickle', PickleOutput),
    # ('ubigraph', UbigraphOutput),
])
