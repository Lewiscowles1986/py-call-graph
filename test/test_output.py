from pycallgraph.config import Config
from pycallgraph.output import Output


def test_set_config():
    '''Should not raise!'''
    Output().set_config(Config())


def test_normalize_path_expands_user(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    expanded = Output().normalize_path('~/graph.json')
    assert expanded == str(tmp_path / 'graph.json')
    assert '~' not in expanded


def test_normalize_path_expands_environment_variables(tmp_path, monkeypatch):
    monkeypatch.setenv('PYCG_OUT_DIR', str(tmp_path))
    expanded = Output().normalize_path('$PYCG_OUT_DIR/graph.json')
    assert expanded == str(tmp_path / 'graph.json')


def test_normalize_path_expands_both_user_and_variables(tmp_path, monkeypatch):
    '''
    A path may legitimately use both forms. ``normalize_path`` used to apply
    ``expanduser`` *or* ``expandvars`` depending on the first character, so
    ``~/graphs/$RUN.json`` left a literal ``$RUN.json`` under the home
    directory.
    '''
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('RUN', '42')
    expanded = Output().normalize_path('~/graphs/$RUN.json')
    assert expanded == str(tmp_path / 'graphs' / '42.json')
    assert '$RUN' not in expanded
    assert '~' not in expanded


def test_normalize_path_leaves_plain_paths_alone(tmp_path):
    plain = str(tmp_path / 'graph.png')
    assert Output().normalize_path(plain) == plain
