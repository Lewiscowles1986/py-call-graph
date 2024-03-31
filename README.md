# Python Call Graph

Welcome! Python Call Graph is a [Python](http://www.python.org) module that creates [call graph](http://en.wikipedia.org/wiki/Call_graph) visualizations for Python applications.

This repo used to be `pycallgraph` which is still hosted at pypi [link](https://pypi.org/project/pycallgraph/).

The uploader makes no representations of their contribution, and merely wanted this to work in python 3.5; with a goal to porting it to 3.11 and 3.12

[![CI Status](https://github.com/Lewiscowles1986/py-call-graph/actions/workflows/ci.yml/badge.svg)](https://github.com/Lewiscowles1986/py-call-graph/actions/workflows/ci.yml)

## Screenshots

Click on the images below to see a larger version and the source code that generated them.

[![Basic Output thumbnail](http://pycallgraph.readthedocs.io/en/develop/_images/basic_thumb.png)](http://pycallgraph.readthedocs.io/en/develop/examples/basic.html)

[![Regex grouped Output thumbnail](https://pycallgraph.readthedocs.io/en/develop/_images/regexp_grouped_thumb.png)](https://pycallgraph.readthedocs.io/en/develop/examples/regexp_grouped.html)

[![Regex ungrouped Output thumbnail](https://pycallgraph.readthedocs.io/en/develop/_images/regexp_ungrouped_thumb.png)](https://pycallgraph.readthedocs.io/en/develop/examples/regexp_ungrouped.html)

## Project Status

The latest version is **2.1.1** which was released on 2024-03-31.
The latest version has been tested running on Python versions 3.8 - 3.12

The [project lives on GitHub](https://github.com/lewiscowles1986/py-call-graph/#python-call-graph), where you can [report issues](https://github.com/lewiscowles1986/py-call-graph/issues), contribute to the project by [forking the project](https://help.github.com/articles/fork-a-repo) then creating a [pull request](https://help.github.com/articles/using-pull-requests), or just [browse the source code](https://github.com/lewiscowles1986/py-call-graph/).

The documentation needs some work stiil. Feel free to contribute :smile:

## Features

* Support for Python 3.8 - 3.12.
* Static visualizations of the call graph using various tools such as Graphviz and Gephi.
* Execute pycallgraph from the command line or import it in your code.
* Customisable colors. You can programatically set the colors based on number of calls, time taken, memory usage, etc.
* Modules can be visually grouped together.
* Easily extendable to create your own output formats.

## Quick Start

Installation is easy as

```shell
pip install python-call-graph

```

You can either use the [command-line interface](https://pycallgraph.readthedocs.io/en/develop/guide/command_line_usage.html) for a quick visualization of your Python script, or the [pycallgraph module](https://pycallgraph.readthedocs.io/en/develop/api/pycallgraph.html) for more fine-grained settings.

The following examples specify graphviz as the outputter, so it's required to be installed. They will generate a file called `pycallgraph.png`.

### The command-line method of running pycallgraph is

```shell
pycallgraph graphviz -- ./mypythonscript.py

```

### A simple use of the API is

```python
from pycallgraph import PyCallGraph
from pycallgraph.output import GraphvizOutput

with PyCallGraph(output=GraphvizOutput()):
    code_to_profile()

```

## Documentation

Feel free to browse the [documentation of pycallgraph](https://pycallgraph.readthedocs.io/en/develop/) for the [usage guide](https://pycallgraph.readthedocs.io/en/develop/guide/index.html) and [API reference](https://pycallgraph.readthedocs.io/en/develop/api/api.html).
