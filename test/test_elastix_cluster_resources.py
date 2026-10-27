"""Regression tests for Elastix alignment Slurm resource defaults."""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
import warnings

from amst2.cluster.general import set_resources


class TestElastixClusterResources(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', category=Warning)

    @staticmethod
    def _resource_arguments():
        source = Path(__file__).resolve().parents[1] / 'amst2' / 'stack_alignment.py'
        tree = ast.parse(source.read_text())
        workflow = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name == 'snk_elastix_stack_alignment')
        call = next(node for node in ast.walk(workflow) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name) and node.func.id == 'set_resources')
        return [ast.literal_eval(argument) for argument in call.args[1:4]]

    def test_elastix_alignment_resource_defaults(self):
        print('Testing elastix alignment: cluster resource defaults match Snakemake rules')

        rule_names, mem_defaults, runtime_defaults = self._resource_arguments()
        self.assertEqual(rule_names, [
            'elastix_stack_alignment', 'create_ome_zarr', 'apply_final_transformations'
        ])
        self.assertEqual(mem_defaults, [16000, 1024, 8000])
        self.assertEqual(runtime_defaults, [30, 5, 30])

        sn_args = SimpleNamespace()
        set_resources(sn_args, rule_names, mem_defaults, runtime_defaults)
        self.assertEqual(sn_args.set_resources['create_ome_zarr'],
                         {'mem_mb': 1024, 'runtime': 5})
        self.assertEqual(sn_args.set_resources['apply_final_transformations'],
                         {'mem_mb': 8000, 'runtime': 30})

    def test_elastix_alignment_resource_overrides(self):
        print('Testing elastix alignment: explicit memory and runtime overrides')

        rule_names, mem_defaults, runtime_defaults = self._resource_arguments()
        sn_args = SimpleNamespace()
        set_resources(sn_args, rule_names, mem_defaults, runtime_defaults,
                      mem_args=['elastix_stack_alignment:32000'],
                      runtime_args=['elastix_stack_alignment:90'])
        self.assertEqual(sn_args.set_resources['elastix_stack_alignment'],
                         {'mem_mb': 32000, 'runtime': 90})
        self.assertEqual(sn_args.set_resources['create_ome_zarr'],
                         {'mem_mb': 1024, 'runtime': 5})


if __name__ == '__main__':
    unittest.main()
