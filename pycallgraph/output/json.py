'''
JSON output.

Writes the collected call graph as a single JSON document so it can be
consumed by other tooling. The format is intentionally small and versioned:

    {
        "version": 1,
        "nodes": [
            {"name": ..., "group": ..., "calls": ..., "time": ...,
             "memory_in": ..., "memory_out": ...}
        ],
        "edges": [
            {"source": ..., "target": ..., "calls": ..., "time": ...}
        ]
    }
'''
import json

from .output import Output


class JSONOutput(Output):

    #: Bumped whenever the document shape changes incompatibly.
    schema_version = 1

    def __init__(self, **kwargs):
        self.fp = None
        self.output_file = 'pycallgraph.json'
        Output.__init__(self, **kwargs)

    @classmethod
    def add_arguments(cls, subparsers, parent_parser, usage):
        defaults = cls()

        subparser = subparsers.add_parser(
            'json', help='JSON call graph export',
            parents=[parent_parser], usage=usage,
        )

        cls.add_output_file(
            subparser, defaults, 'The generated JSON file'
        )

    def generate_nodes(self):
        return [
            {
                'name': node.name,
                'group': node.group,
                'calls': node.calls.value,
                'time': node.time.value,
                'memory_in': node.memory_in.value,
                'memory_out': node.memory_out.value,
            }
            for node in self.processor.nodes()
        ]

    def generate_edges(self):
        return [
            {
                'source': edge.src_func,
                'target': edge.dst_func,
                'calls': edge.calls.value,
                'time': edge.time.value,
            }
            for edge in self.processor.edges()
        ]

    def generate(self):
        '''Return the JSON document as a pretty-printed string.'''
        document = {
            'version': self.schema_version,
            'nodes': self.generate_nodes(),
            'edges': self.generate_edges(),
        }
        return json.dumps(document, indent=2, sort_keys=True)

    def done(self):
        with open(self.output_file, 'w') as handle:
            handle.write(self.generate())
        self.fp = None
