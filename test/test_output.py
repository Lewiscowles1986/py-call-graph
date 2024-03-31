from pycallgraph.config import Config
from pycallgraph.output import Output


def test_set_config():
    '''Should not raise!'''
    Output().set_config(Config())
