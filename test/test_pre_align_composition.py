import os
import tempfile
import unittest
import warnings

import numpy as np

from amst2.workflows.pre_align import _compose_stage_transforms


class TestPreAlignComposition(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', category=Warning)

    def test_compose_stage_transforms_empty(self):
        print('Testing compose_stage_transforms: reject empty inputs')
        with self.assertRaises(ValueError):
            _compose_stage_transforms([], 'out.json')

    def test_compose_stage_transforms_single(self):
        print('Testing compose_stage_transforms: single transform copy')
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, 'source.json')
            target = os.path.join(directory, 'target.json')
            with open(source, 'w') as handle:
                handle.write('sample')
            _compose_stage_transforms([source], target)
            with open(target) as handle:
                self.assertEqual(handle.read(), 'sample')

    def test_compose_stage_transforms_noncommuting(self):
        print('Testing compose_stage_transforms: ordered affine multiplication')
        from squirrel.library.affine_matrices import AffineStack

        shift = np.array([[1., 0., 5.], [0., 1., 2.], [0., 0., 1.]])
        rotate = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
        scale = np.array([[2., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        matrices = [shift, rotate, scale]
        with tempfile.TemporaryDirectory() as directory:
            sources = []
            for index, matrix in enumerate(matrices):
                path = os.path.join(directory, f'stage-{index}.json')
                AffineStack.from_array(np.stack([matrix, matrix])).write(path)
                sources.append(path)
            output = os.path.join(directory, 'pre-align-combined.json')
            _compose_stage_transforms(sources, output)
            actual = AffineStack.read(output).as_homogeneous()
            expected = scale @ rotate @ shift
            np.testing.assert_allclose(actual[0], expected)
            self.assertFalse(np.allclose(expected, shift @ rotate @ scale))

    def test_compose_stage_transforms_order_all_stage_subsets(self):
        print('Testing compose_stage_transforms: all seven stage subsets')
        from squirrel.library.affine_matrices import AffineStack

        matrices = [
            np.array([[1., 0., 5.], [0., 1., 2.], [0., 0., 1.]]),
            np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]]),
            np.array([[2., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        ]
        with tempfile.TemporaryDirectory() as directory:
            for mask in range(1, 8):
                selected = [matrix for index, matrix in enumerate(matrices)
                            if mask & (1 << index)]
                paths = []
                for index, matrix in enumerate(selected):
                    path = os.path.join(directory, f'{mask}-{index}.json')
                    AffineStack.from_array(np.stack([matrix, matrix])).write(path)
                    paths.append(path)
                output = os.path.join(directory, f'{mask}-out.json')
                _compose_stage_transforms(paths, output)
                expected = np.eye(3)
                for matrix in selected:
                    expected = matrix @ expected
                np.testing.assert_allclose(
                    AffineStack.read(output).as_homogeneous()[0], expected
                )
