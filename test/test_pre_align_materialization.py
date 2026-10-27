import os
import tempfile
import unittest
import warnings
from unittest.mock import patch

from amst2.workflows.pre_align import _run_pre_align


class TestPreAlignMaterialization(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', category=Warning)

    def test_all_stage_combinations_materialize_only_intermediates(self):
        print('Testing pre_align: materialization across seven stage combinations')
        combinations = (
            (True, False, False),
            (False, True, False),
            (False, False, True),
            (True, True, False),
            (True, False, True),
            (False, True, True),
            (True, True, True),
        )
        with tempfile.TemporaryDirectory() as directory:
            initial_path = os.path.join(directory, 'initial.json')
            with open(initial_path, 'w', encoding='utf-8') as handle:
                handle.write('{}')

            for initial, sbs, nsbs in combinations:
                with self.subTest(initial=initial, sbs=sbs, nsbs=nsbs):
                    stages = (['initial'] if initial else [])
                    stages += (['sbs'] if sbs else [])
                    stages += (['nsbs'] if nsbs else [])
                    config = {
                        'general': {
                            'input_dirpath': '/original',
                            'output_dirpath': os.path.join(directory, 'output'),
                            'stack_key': 's0',
                            'auto_pad': False,
                        },
                        'workflow': {
                            'pre_existing_transforms': initial_path if initial else None,
                            'run_sbs': sbs,
                            'run_nsbs': nsbs,
                        },
                    }
                    calls = []

                    def record_alignment(parameters, **kwargs):
                        key = kwargs['parameter_key']
                        calls.append((key, kwargs['input_dirpath'],
                                      parameters[key]['materialize_output']))

                    def record_apply(parameters, **kwargs):
                        calls.append((kwargs['parameter_key'],
                                      kwargs['input_dirpath'], None))

                    with patch('amst2.workflows.lib.load_parameter_yaml', return_value=config), \
                            patch('amst2.workflows.lib.run_nsbs_alignment', side_effect=record_alignment), \
                            patch('amst2.workflows.lib.run_apply_transformation', side_effect=record_apply):
                        _run_pre_align('unused.yaml', dryrun=True)

                    expected = []
                    previous_input = '/original'
                    for index, stage in enumerate(stages):
                        materialize = index < len(stages) - 1
                        if stage == 'initial':
                            if materialize:
                                expected.append(('apply_initial_transforms', previous_input, None))
                                previous_input = os.path.join(config['general']['output_dirpath'],
                                                              'apply_initial_transforms/initial.ome.zarr')
                        else:
                            expected.append((f'{stage}_alignment', previous_input, materialize))
                            if materialize:
                                previous_input = os.path.join(config['general']['output_dirpath'],
                                                              f'{stage}_alignment/{stage}.ome.zarr')
                    expected.append(('apply_pre_align', '/original', None))
                    self.assertEqual(calls, expected)
