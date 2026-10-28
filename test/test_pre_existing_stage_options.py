import os
import tempfile
import unittest
from unittest.mock import patch

import yaml

from amst2.workflows.pre_align import _run_pre_align
from amst2.workflows.lib import run_apply_transformation


class TestPreExistingStageOptions(unittest.TestCase):

    def test_imported_stage_inherits_resources_and_keeps_fixed_output(self):
        print('Testing imported transforms: resource overrides and fixed output')
        with tempfile.TemporaryDirectory() as directory:
            params = {
                'general': {
                    'input_dirpath': 'input', 'output_dirpath': directory,
                    'cores': 16, 'batch_size': 8, 'cluster': 'local',
                },
                'stack_to_ome_zarr': {'active': False},
                'pre_existing_transforms': {
                    'active': True, 'transform_filepath': 'affines.json',
                    'auto_pad': True, 'cores': 4, 'cluster': 'slurm',
                },
                'sbs_alignment': {'active': True},
                'nsbs_alignment': {'active': False},
                'pre_align_to_tif_stack': {'active': False},
                'apply_pre_align': {},
            }
            filepath = os.path.join(directory, 'params.yaml')
            with open(filepath, 'w') as handle:
                yaml.safe_dump(params, handle)

            with patch('amst2.workflows.lib.run_apply_transformation') as apply, \
                    patch('amst2.workflows.lib.run_nsbs_alignment') as align:
                _run_pre_align(filepath, dryrun=True)

            initial = apply.call_args_list[0]
            stage_params = initial.args[0]['apply_initial_transforms']
            self.assertEqual(stage_params['cores'], 4)
            self.assertEqual(stage_params['cluster'], 'slurm')
            self.assertTrue(stage_params['auto_pad'])
            self.assertNotIn('output_filename', stage_params)
            self.assertEqual(initial.kwargs['output_filename'], 'initial.ome.zarr')
            self.assertEqual(
                align.call_args.kwargs['input_dirpath'],
                os.path.join(directory, 'apply_initial_transforms', 'initial.ome.zarr'))

    def test_apply_transformation_auto_pad_switch(self):
        print('Testing apply transformation: existing auto_pad switch')
        with tempfile.TemporaryDirectory() as directory:
            params = {
                'general': {
                    'output_dirpath': directory, 'input_dirpath': 'input',
                    'cores': 2, 'batch_size': 2,
                },
                'apply_initial_transforms': {'auto_pad': True},
            }
            with patch('amst2.workflows.lib.run_snakemake_workflow') as runner:
                run_apply_transformation(
                    params, 'apply_initial_transforms', 'affines.json',
                    output_filename='initial.ome.zarr')
                self.assertNotIn('--no_autopad', runner.call_args.args[0])
                params['apply_initial_transforms']['auto_pad'] = False
                run_apply_transformation(
                    params, 'apply_initial_transforms', 'affines.json',
                    output_filename='initial.ome.zarr')
                self.assertIn('--no_autopad', runner.call_args.args[0])
                params['apply_pre_align'] = {'auto_pad': True}
                run_apply_transformation(
                    params, 'apply_pre_align', 'affines.json',
                    output_filename='pre-align.ome.zarr')
                self.assertIn('--no_autopad', runner.call_args.args[0])

    def test_imported_padding_inherits_general_and_can_be_overridden(self):
        print('Testing imported transforms: padding precedence')
        with tempfile.TemporaryDirectory() as directory:
            params = {
                'general': {'input_dirpath': 'input', 'output_dirpath': directory,
                            'auto_pad': False},
                'stack_to_ome_zarr': {'active': False},
                'pre_existing_transforms': {'active': True,
                                            'transform_filepath': 'affines.json'},
                'sbs_alignment': {'active': True},
                'nsbs_alignment': {'active': False},
                'pre_align_to_tif_stack': {'active': False},
                'apply_pre_align': {},
            }
            filepath = os.path.join(directory, 'params.yaml')
            with patch('amst2.workflows.lib.run_apply_transformation') as apply, \
                    patch('amst2.workflows.lib.run_nsbs_alignment'):
                for general, override, padded in (
                        (False, None, False), (False, True, True),
                        (True, False, False), (None, None, True)):
                    if general is None:
                        params['general'].pop('auto_pad', None)
                    else:
                        params['general']['auto_pad'] = general
                    if override is None:
                        params['pre_existing_transforms'].pop('auto_pad', None)
                    else:
                        params['pre_existing_transforms']['auto_pad'] = override
                    with open(filepath, 'w') as handle:
                        yaml.safe_dump(params, handle)
                    _run_pre_align(filepath, dryrun=True)
                    initial = apply.call_args_list[-2]
                    self.assertEqual(initial.kwargs['transforms_filepath'], 'affines.json')
                    self.assertEqual(initial.args[0]['apply_initial_transforms']['auto_pad'], padded)

    def test_padding_is_delegated_to_snakemake_and_used_for_composition(self):
        print('Testing imported transforms: padding is not computed by the driver')
        with tempfile.TemporaryDirectory() as directory:
            original = os.path.join(directory, 'affines.json')
            with open(original, 'w') as handle:
                handle.write('[]')
            params = {
                'general': {'input_dirpath': 'input', 'output_dirpath': directory,
                            'auto_pad': False},
                'stack_to_ome_zarr': {'active': False},
                'pre_existing_transforms': {'active': True,
                                            'transform_filepath': original, 'auto_pad': True},
                'sbs_alignment': {'active': True},
                'nsbs_alignment': {'active': False},
                'pre_align_to_tif_stack': {'active': False},
                'apply_pre_align': {},
            }
            filepath = os.path.join(directory, 'params.yaml')
            with open(filepath, 'w') as handle:
                yaml.safe_dump(params, handle)

            def fake_apply(*args, **kwargs):
                key = kwargs['parameter_key']
                stage_dir = os.path.join(directory, key)
                os.makedirs(stage_dir, exist_ok=True)
                if key == 'apply_initial_transforms':
                    with open(os.path.join(stage_dir, 'initial-padded.json'), 'w'):
                        pass
                with open(os.path.join(stage_dir, f'{key}.done'), 'w'):
                    pass

            def fake_align(*args, **kwargs):
                stage_dir = os.path.join(directory, 'sbs_alignment')
                os.makedirs(stage_dir, exist_ok=True)
                with open(os.path.join(stage_dir, 'sbs_alignment.done'), 'w'):
                    pass

            with patch('amst2.workflows.pre_align._validate_imported_affine_stack'), \
                    patch('amst2.workflows.pre_align._check_run_identity'), \
                    patch('amst2.workflows.lib.run_apply_transformation',
                          side_effect=fake_apply) as apply, \
                    patch('amst2.workflows.lib.run_nsbs_alignment',
                          side_effect=fake_align), \
                    patch('amst2.workflows.pre_align._compose_stage_transforms') as compose:
                _run_pre_align(filepath)
                padded = os.path.join(directory, 'apply_initial_transforms',
                                      'initial-padded.json')
                self.assertEqual(apply.call_args_list[0].kwargs['transforms_filepath'], original)
                self.assertTrue(apply.call_args_list[0].args[0]['apply_initial_transforms']['auto_pad'])
                self.assertEqual(compose.call_args.args[0][0], padded)
                self.assertTrue(os.path.isfile(original))
