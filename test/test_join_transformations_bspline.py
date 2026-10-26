import runpy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


class TestJoinTransformationsBspline(unittest.TestCase):

    def test_join_bspline_uses_elastix_stack_api(self):
        print('Testing join_transformations: concatenate B-spline transform directories')
        try:
            from SimpleITK import ParameterMap
            from squirrel.library.elastix import ElastixStack
        except ImportError as exc:
            self.skipTest(f'Squirrel/SimpleITK unavailable: {exc}')

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            inputs = [root / 'batch_0', root / 'batch_1']
            for idx, path in enumerate(inputs):
                transform = ParameterMap()
                transform['Transform'] = ['BSplineTransform']
                transform['TransformParameters'] = [str(idx)]
                ElastixStack([transform]).write(str(path))

            output = root / 'joined'
            snakemake = SimpleNamespace(
                input=[str(path) for path in inputs],
                output=[str(output)],
                params={'run_info': {'transform': 'bspline'}},
            )
            script = (Path(__file__).resolve().parents[1] / 'amst2' /
                      'snakemake_call_scripts' / 'join_transformations.py')
            runpy.run_path(str(script), init_globals={'snakemake': snakemake},
                           run_name='__main__')

            joined = ElastixStack.read(str(output))
            self.assertEqual(len(joined), 2)
            self.assertEqual([float(value) for value in joined[0]['TransformParameters']],
                             [0.0])
            self.assertEqual([float(value) for value in joined[1]['TransformParameters']],
                             [1.0])
