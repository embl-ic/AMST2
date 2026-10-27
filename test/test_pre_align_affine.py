import unittest
import warnings

import numpy as np


class TestPreAlignAffine(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', category=Warning)

    def test_composition_order_noncommuting(self):
        print('Testing composition: noncommuting translation and rotation')
        from squirrel.library.affine_matrices import AffineStack

        translation = np.array([[1., 0., 4.], [0., 1., -2.], [0., 0., 1.]])
        rotation = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
        first = AffineStack.from_array(np.stack([translation, translation]))
        second = AffineStack.from_array(np.stack([rotation, rotation]))

        result = first @ second
        np.testing.assert_allclose(result.as_homogeneous()[0], translation @ rotation)
        self.assertFalse(np.allclose(translation @ rotation, rotation @ translation))

    def test_sequencing_relative_translations(self):
        print('Testing sequencing: cumulative translations')
        from squirrel.library.affine_matrices import AffineStack

        identity = np.eye(3)
        shift = np.array([[1., 0., 3.], [0., 1., -1.], [0., 0., 1.]])
        relative = AffineStack.from_array(np.stack([identity, shift, shift]))
        sequenced = relative.to_sequenced()

        self.assertTrue(sequenced.sequenced)
        np.testing.assert_allclose(sequenced.as_homogeneous()[0], identity)
        np.testing.assert_allclose(sequenced.as_homogeneous()[1], shift)
        np.testing.assert_allclose(sequenced.as_homogeneous()[2], shift @ shift)
