import json
import tempfile
import unittest
import warnings
from pathlib import Path

import numpy as np

from amst2.workflows.pre_align import _validate_imported_affine_stack


class TestImportedAffineValidation(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', category=Warning)

    def _fixture(self, directory, matrices, metadata=None):
        from squirrel.library.affine_matrices import AffineStack
        from squirrel.library.ome_zarr import OMEZarrStore

        input_path = directory / 'input.ome.zarr'
        source = np.zeros((5, 16, 16), dtype=np.uint16)
        store = OMEZarrStore.create(
            str(input_path), shape=source.shape, dtype=source.dtype,
            chunks=(1, 8, 8), shards=None, downsample_factors=((1, 2, 2),),
            resolution=(1., 1., 1.), unit='micrometer',
            ome_version='0.4', zarr_format=2)
        store.write(0, (0, 0, 0), source, update_pyramid=True)
        transforms_path = directory / 'transforms.json'
        AffineStack.from_array(matrices, metadata=metadata).write(str(transforms_path))
        return transforms_path, input_path

    def test_valid_stack(self):
        print('Testing imported affine validation: valid stack')
        with tempfile.TemporaryDirectory() as temp:
            transforms, source = self._fixture(Path(temp), np.repeat(np.eye(3)[None], 5, axis=0),
                                               metadata={'stack_shape': [5, 16, 16]})
            self.assertEqual(len(_validate_imported_affine_stack(str(transforms), str(source))), 5)

    def test_reject_wrong_slice_count(self):
        print('Testing imported affine validation: slice count')
        with tempfile.TemporaryDirectory() as temp:
            transforms, source = self._fixture(Path(temp), np.repeat(np.eye(3)[None], 4, axis=0))
            with self.assertRaisesRegex(ValueError, '4 transforms'):
                _validate_imported_affine_stack(str(transforms), str(source))

    def test_reject_nonfinite_coefficients(self):
        print('Testing imported affine validation: nonfinite coefficients')
        with tempfile.TemporaryDirectory() as temp:
            transforms, source = self._fixture(
                Path(temp), np.repeat(np.eye(3)[None], 5, axis=0))
            with transforms.open('r', encoding='utf-8') as handle:
                serialized = json.load(handle)
            serialized['transforms'][2][2] = float('nan')
            with transforms.open('w', encoding='utf-8') as handle:
                json.dump(serialized, handle)
            with self.assertRaisesRegex(ValueError, 'finite'):
                _validate_imported_affine_stack(str(transforms), str(source))

    def test_reject_mismatched_shape_metadata(self):
        print('Testing imported affine validation: shape metadata')
        with tempfile.TemporaryDirectory() as temp:
            transforms, source = self._fixture(Path(temp), np.repeat(np.eye(3)[None], 5, axis=0),
                                               metadata={'stack_shape': [5, 20, 16]})
            with self.assertRaisesRegex(ValueError, 'does not match'):
                _validate_imported_affine_stack(str(transforms), str(source))
