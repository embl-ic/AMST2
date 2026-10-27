"""Regression coverage for the unified squirrel ElastixStack loading API."""
import tempfile
import unittest
from pathlib import Path


class TestElastixStackReadCompatibility(unittest.TestCase):

    def test_read_stack_and_image_shape_property(self):
        print('Testing ElastixStack: read directory and access image_shape property')
        try:
            from SimpleITK import ParameterMap
            from squirrel.library.elastix import ElastixStack
        except ImportError as exc:
            self.skipTest(f'Squirrel/SimpleITK unavailable: {exc}')

        transform = ParameterMap()
        transform['Transform'] = ['BSplineTransform']
        transform['Size'] = ['31', '23']
        transform['TransformParameters'] = ['0']

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'transforms'
            ElastixStack([transform]).write(str(path))
            loaded = ElastixStack.read(str(path))
            self.assertEqual(len(loaded), 1)
            self.assertEqual(list(loaded.image_shape), [23, 31])
