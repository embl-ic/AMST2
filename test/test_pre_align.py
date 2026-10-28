import unittest
import warnings

from amst2.workflows.pre_align import _alignment_stages


class TestPreAlign(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', category=Warning)

    def test_alignment_stages_all_combinations(self):
        print('Testing alignment_stages: seven valid combinations')
        for initial in (False, True):
            for sbs in (False, True):
                for nsbs in (False, True):
                    config = {
                        'stack_to_ome_zarr': {'active': False},
                        'pre_align_to_tif_stack': {'active': False},
                        'pre_existing_transforms': {
                            'active': initial, 'transform_filepath': 'transforms.json'
                        },
                        'sbs_alignment': {'active': sbs},
                        'nsbs_alignment': {'active': nsbs},
                    }
                    if not (initial or sbs or nsbs):
                        with self.assertRaisesRegex(ValueError, 'at least one'):
                            _alignment_stages(config)
                        continue
                    expected = []
                    if initial:
                        expected.append(('initial', 'transforms.json'))
                    if sbs:
                        expected.append(('sbs', None))
                    if nsbs:
                        expected.append(('nsbs', None))
                    self.assertEqual(_alignment_stages(config), expected)

    def test_alignment_stages_requires_explicit_activation(self):
        print('Testing alignment_stages: reject missing sections and activation')
        base = {
            'stack_to_ome_zarr': {'active': False},
                        'pre_align_to_tif_stack': {'active': False},
                        'pre_existing_transforms': {'active': False},
            'sbs_alignment': {'active': True},
            'nsbs_alignment': {'active': False},
        }
        for key in base:
            config = {name: dict(settings) for name, settings in base.items()}
            del config[key]
            with self.assertRaisesRegex(ValueError, key):
                _alignment_stages(config)
            config = {name: dict(settings) for name, settings in base.items()}
            del config[key]['active']
            with self.assertRaisesRegex(ValueError, key):
                _alignment_stages(config)

    def test_alignment_stages_rejects_non_boolean_active(self):
        print('Testing alignment_stages: strict YAML booleans')
        for value in (None, 0, 1, 'false', 'true', [], {}):
            config = {
                'stack_to_ome_zarr': {'active': False},
                        'pre_align_to_tif_stack': {'active': False},
                        'pre_existing_transforms': {'active': False},
                'sbs_alignment': {'active': value},
                'nsbs_alignment': {'active': True},
            }
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'boolean'):
                _alignment_stages(config)

    def test_alignment_stages_requires_transform_path_when_enabled(self):
        print('Testing alignment_stages: require enabled imported transform path')
        config = {
            'stack_to_ome_zarr': {'active': False},
                        'pre_align_to_tif_stack': {'active': False},
                        'pre_existing_transforms': {'active': True},
            'sbs_alignment': {'active': False},
            'nsbs_alignment': {'active': False},
        }
        with self.assertRaisesRegex(ValueError, 'transform_filepath'):
            _alignment_stages(config)

    def test_alignment_stages_rejects_legacy_workflow(self):
        print('Testing alignment_stages: reject legacy workflow section')
        config = {
            'workflow': {'run_sbs': True},
            'stack_to_ome_zarr': {'active': False},
                        'pre_align_to_tif_stack': {'active': False},
                        'pre_existing_transforms': {'active': False},
            'sbs_alignment': {'active': True},
            'nsbs_alignment': {'active': False},
        }
        with self.assertRaisesRegex(ValueError, 'no longer supported'):
            _alignment_stages(config)
