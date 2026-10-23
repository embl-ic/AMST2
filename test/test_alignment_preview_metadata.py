import unittest
import warnings

import numpy as np


class TestAlignmentPreviewMetadata(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', category=Warning)

    def test_affine_stack_shape_metadata_roundtrip(self):
        print('Testing alignment_preview: squirrel stack-shape metadata API')
        from squirrel.library.affine_matrices import AffineStack

        transforms = AffineStack.from_array(
            np.stack([np.eye(3), np.eye(3)]), sequenced=True
        )
        stack_shape = (2, 64, 64)

        self.assertFalse(transforms.has_metadata('stack_shape'))
        transforms.set_metadata('stack_shape', stack_shape)
        self.assertTrue(transforms.has_metadata('stack_shape'))
        self.assertEqual(
            tuple(transforms.get_metadata('stack_shape')), stack_shape
        )
