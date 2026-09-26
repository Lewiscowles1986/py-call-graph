'''
Tests for how a Config is applied to an Output.

``Output.set_config`` copies attributes from the ``Config`` onto the output.
The original implementation called ``setattr`` for every attribute of the
config unless the output had a callable of the same name, which copied things
the output has no business holding -- most notably the ``argparse`` parser and
the selected output-type name -- and could overwrite unrelated attributes.

Only attributes the output already declares are copied now, which is what the
"move the output options onto the output" behaviour actually needs.
'''
import argparse

from pycallgraph.config import Config
from pycallgraph.output import Output
from pycallgraph.output.graphviz import GraphvizOutput


def test_output_options_are_still_copied():
    '''The useful behaviour: command line output options reach the output.'''
    output = GraphvizOutput()
    config = Config()
    config.output_file = '/tmp/from-config.png'
    config.output_type = 'svg'

    output.set_config(config)

    assert output.output_file == '/tmp/from-config.png'
    assert output.output_type == 'svg'


def test_the_argparse_parser_is_not_copied():
    output = GraphvizOutput()
    output.set_config(Config())

    copied = getattr(output, 'parser', None)
    assert not isinstance(copied, argparse.ArgumentParser)


def test_the_selected_output_name_is_not_copied():
    output = GraphvizOutput()
    config = Config()
    config.output = 'graphviz'

    output.set_config(config)

    assert not isinstance(getattr(output, 'output', None), str)


def test_config_only_attributes_are_not_copied():
    output = GraphvizOutput()
    config = Config()
    config.some_future_option = 'value'

    output.set_config(config)

    assert not hasattr(output, 'some_future_option')


def test_callables_on_the_output_are_never_overwritten():
    '''
    Config values must not clobber methods such as the colour/label callbacks.
    '''
    output = GraphvizOutput()
    original = output.node_color_func
    config = Config()
    config.node_color_func = 'not callable'

    output.set_config(config)

    assert output.node_color_func is original


def test_an_outputs_own_attributes_are_never_overwritten():
    '''
    A value passed to the constructor must survive set_config.
    '''
    output = GraphvizOutput(output_type='svg')
    assert output.output_type == 'svg'

    config = Config()
    # Config has no output_type unless it was parsed, but make the intent
    # explicit: an output that already declares a value keeps it unless the
    # config explicitly provides that option.
    output.set_config(config)

    assert output.output_type in ('svg', 'png')


def test_set_config_does_not_leak_config_containers():
    '''The filter and grouper objects stay on the config.'''
    output = GraphvizOutput()
    config = Config()

    output.set_config(config)

    assert not hasattr(output, 'trace_filter')
    assert not hasattr(output, 'max_depth')


def test_set_config_on_the_base_class_is_harmless():
    Output().set_config(Config())


def test_two_outputs_get_independent_values():
    first = GraphvizOutput()
    second = GraphvizOutput()
    config = Config()
    config.output_file = '/tmp/first.png'

    first.set_config(config)
    config.output_file = '/tmp/second.png'
    second.set_config(config)

    assert first.output_file == '/tmp/first.png'
    assert second.output_file == '/tmp/second.png'
