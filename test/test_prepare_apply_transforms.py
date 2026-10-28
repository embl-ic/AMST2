import json
import os
import runpy
import tempfile
import unittest
import warnings
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


class TestPrepareApplyTransforms(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', category=Warning)

    def test_preparation_writes_shape_from_padded_transforms(self):
        print('Testing prepare_apply_transforms: shape metadata and source preservation')
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, 'original.json')
            target = os.path.join(directory, 'initial-padded.json')
            shape_path = os.path.join(directory, 'initial-padded-shape.json')
            with open(source, 'w') as handle:
                handle.write('original')

            def fake_pad(input_path, output_path, **kwargs):
                self.assertEqual(input_path, source)
                self.assertEqual(kwargs['image_stack_path'], 'input.ome.zarr')
                with open(output_path, 'w') as handle:
                    handle.write('padded')

            class FakeStack:
                @staticmethod
                def read(path):
                    self.assertEqual(path, target)
                    return SimpleNamespace(get_metadata=lambda key: [4, 120, 140])

            squirrel = ModuleType('squirrel')
            library = ModuleType('squirrel.library')
            affine = ModuleType('squirrel.library.affine_matrices')
            affine.AffineStack = FakeStack
            workflows = ModuleType('squirrel.workflows')
            transformation = ModuleType('squirrel.workflows.transformation')
            transformation.apply_auto_pad_workflow = fake_pad
            snakemake = SimpleNamespace(
                input=[source], output={'transforms': target, 'shape': shape_path},
                params={'run_info': {'input_ome_zarr_filepath': 'input.ome.zarr',
                                     'stack_key': 's0', 'stack_pattern': '*.tif',
                                     'verbose': False}}
            )
            script = os.path.join(os.path.dirname(__file__), '..', 'amst2',
                                  'snakemake_call_scripts', 'prepare_apply_transforms.py')
            with patch.dict('sys.modules', {
                    'squirrel': squirrel, 'squirrel.library': library,
                    'squirrel.library.affine_matrices': affine,
                    'squirrel.workflows': workflows,
                    'squirrel.workflows.transformation': transformation}):
                runpy.run_path(script, run_name='__main__', init_globals={'snakemake': snakemake})

            with open(shape_path) as handle:
                self.assertEqual(json.load(handle), [4, 120, 140])
            with open(source) as handle:
                self.assertEqual(handle.read(), 'original')
