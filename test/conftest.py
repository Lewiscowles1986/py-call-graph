import pytest

from pycallgraph.config import Config
from pycallgraph.pycallgraph import PyCallGraph


@pytest.fixture
def pycg():
    return PyCallGraph()


@pytest.fixture
def config():
    return Config()
