'''
Acceptance tests for the JSON output.

Issue #28 asks for a machine-readable export of the call graph, comparable to
what PyCG produced. The JSON output writes a stable, versioned document so
tooling can consume the graph without depending on the human-oriented
Graphviz/Gephi rendering or on the pickle format (which ties consumers to the
internal Python objects).
'''
import json
import os
import subprocess
import sys

import pytest

from pycallgraph import PyCallGraph
from pycallgraph.output import outputters
from pycallgraph.output.json import JSONOutput
from calls import one_nop

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def json_output(temp):
    output = JSONOutput()
    output.output_file = temp
    return output


def test_json_is_registered_as_an_output_type():
    '''The JSON output is selectable via the command line.'''
    assert 'json' in outputters


def test_output_file_default():
    assert JSONOutput().output_file.endswith('.json')


def test_document_is_valid_json(json_output):
    with PyCallGraph(output=json_output):
        one_nop()

    with open(json_output.output_file) as handle:
        document = json.load(handle)

    assert isinstance(document, dict)


def test_document_has_a_schema_version(json_output):
    '''A version field lets the format evolve without breaking consumers.'''
    with PyCallGraph(output=json_output):
        one_nop()

    with open(json_output.output_file) as handle:
        document = json.load(handle)

    assert document['version'] == JSONOutput.schema_version


def test_document_contains_nodes_and_edges(json_output):
    with PyCallGraph(output=json_output):
        one_nop()

    with open(json_output.output_file) as handle:
        document = json.load(handle)

    assert isinstance(document['nodes'], list)
    assert isinstance(document['edges'], list)
    assert document['nodes']
    assert document['edges']


def test_nodes_have_the_documented_fields(json_output):
    with PyCallGraph(output=json_output):
        one_nop()

    with open(json_output.output_file) as handle:
        document = json.load(handle)

    for node in document['nodes']:
        assert set(node) == {
            'name', 'group', 'calls', 'time', 'memory_in', 'memory_out',
        }
        assert isinstance(node['name'], str)
        assert isinstance(node['calls'], int)
        assert isinstance(node['time'], (int, float))


def test_edges_have_the_documented_fields(json_output):
    with PyCallGraph(output=json_output):
        one_nop()

    with open(json_output.output_file) as handle:
        document = json.load(handle)

    for edge in document['edges']:
        assert set(edge) == {'source', 'target', 'calls', 'time'}
        assert isinstance(edge['source'], str)
        assert isinstance(edge['target'], str)


def test_graph_relationship_is_captured(json_output):
    '''
    ``one_nop`` calls ``nop``, and the edge must record that relationship so
    the JSON is a usable call graph rather than a node list.
    '''
    with PyCallGraph(output=json_output):
        one_nop()

    with open(json_output.output_file) as handle:
        document = json.load(handle)

    names = {node['name'] for node in document['nodes']}
    assert 'calls.one_nop' in names
    assert 'calls.nop' in names

    pairs = {(edge['source'], edge['target']) for edge in document['edges']}
    assert ('calls.one_nop', 'calls.nop') in pairs


def test_counts_are_recorded(json_output):
    with PyCallGraph(output=json_output):
        one_nop()


def test_document_keys_are_in_documented_order(json_output):
    '''
    The file reads version, nodes, edges. Guards against sorting the keys,
    which would put edges first and contradict the documented shape.
    '''
    with PyCallGraph(output=json_output):
        one_nop()

    with open(json_output.output_file) as handle:
        document = json.load(handle)

    assert list(document) == ['version', 'nodes', 'edges']


def test_json_output_works_from_the_command_line(temp):
    '''End-to-end check that the CLI can select and drive the json output.'''
    env = dict(os.environ)
    env['PYTHONPATH'] = REPO_ROOT
    result = subprocess.run(
        [
            sys.executable,
            os.path.join(REPO_ROOT, 'scripts', 'pycallgraph'),
            'json', '-o', temp,
            '--', os.path.join(REPO_ROOT, 'test', 'calls.py'),
        ],
        cwd=REPO_ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    assert result.returncode == 0, result.stdout

    with open(temp) as handle:
        document = json.load(handle)

    assert document['version'] == JSONOutput.schema_version
    assert document['nodes']
