import tempfile
import unittest
import warnings
from pathlib import Path

import numpy as np


class TestSquirrelCompatibility(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', category=Warning)

    def test_affine_stack_batch_sequencing(self):
        print('Testing AffineStack.read_many: batch offsets are composed')
        from squirrel.library.affine_matrices import AffineStack
        from amst2.snakemake_call_scripts.finalize_alignment_transforms import (
            finalize_alignment_transforms)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            batch_paths = []
            for index, shifts in enumerate(([1, 2], [3, 4])):
                matrices = np.repeat(np.eye(3)[None, :, :], 2, axis=0)
                matrices[:, 0, 2] = shifts
                stack = AffineStack.from_array(matrices, sequenced=False)
                path = root / f'batch_{index}.json'
                stack.write(path)
                batch_paths.append(str(path))

            output = root / 'final.json'
            run_info = {'input_ome_zarr_filepath': str(root),
                        'stack_key': 's0', 'stack_pattern': '*.tif',
                        'stack_shape': [4, 8, 9]}
            # Avoid image loading: provide shape as metadata on the first batch.
            first = AffineStack.read(batch_paths[0])
            first.set_metadata('stack_shape', [4, 8, 9])
            first.write(batch_paths[0])
            finalize_alignment_transforms(batch_paths, str(output), run_info)
            result = AffineStack.read(output)
            self.assertTrue(result.sequenced)
            self.assertEqual(len(result), 4)
            np.testing.assert_allclose(
                result.as_array()[:, 0, 2], [1, 3, 6, 10])
            self.assertEqual(result.get_metadata('stack_shape'), [4, 8, 9])

    def test_affine_stack_z_step(self):
        print('Testing AffineStack.apply_z_step: expansion and metadata')
        from squirrel.library.affine_matrices import AffineStack
        matrices = np.repeat(np.eye(3)[None, :, :], 3, axis=0)
        matrices[:, 0, 2] = [0, 2, 4]
        stack = AffineStack.from_array(
            matrices, sequenced=True,
            metadata={'z_step': 2, 'stack_shape': [3, 8, 9]})
        result = stack.apply_z_step(max_length=5)
        self.assertEqual(len(result), 5)
        self.assertEqual(result.get_metadata('z_step'), 1)
        self.assertEqual(result.get_metadata('stack_shape'), [5, 8, 9])
        np.testing.assert_allclose(result.as_array()[:, 0, 2], [0, 1, 2, 3, 4])

    def test_affine_stack_auto_pad(self):
        print('Testing AffineStack.auto_pad: nonnegative canvas bounds')
        from squirrel.library.affine_matrices import AffineStack
        matrices = np.repeat(np.eye(3)[None, :, :], 2, axis=0)
        matrices[1, 0, 2] = -3
        bounds = [[0, 0, 8, 9], [0, 0, 8, 9]]
        stack = AffineStack.from_array(
            matrices, sequenced=True, metadata={'bounds': bounds})
        result, shape = stack.auto_pad(extra_padding=2)
        self.assertEqual(len(result), 2)
        self.assertEqual(shape[0], 2)
        self.assertGreaterEqual(shape[1], 8)
        self.assertGreaterEqual(shape[2], 9)
        self.assertTrue(np.isfinite(result.as_array()).all())

    def test_affine_application_identity(self):
        print('Testing apply_affine_workflow: identity preserves pixels')
        from squirrel.library.affine_matrices import AffineMatrix
        from squirrel.workflows.transformation import apply_affine_workflow
        image = np.arange(64, dtype=np.uint8).reshape(8, 8)
        result = apply_affine_workflow(
            image, AffineMatrix.identity(ndim=2), no_offset_to_center=True)
        np.testing.assert_array_equal(result, image)


if __name__ == '__main__':
    unittest.main()
