import unittest
import warnings

from amst2.workflows.pre_align import _alignment_stages


class TestPreAlign(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', category=Warning)

    def test_alignment_stages_all_combinations(self):
        print('Testing alignment_stages: seven valid combinations')
        for initial in (None, 'transforms.json'):
            for sbs in (False, True):
                for nsbs in (False, True):
                    config = {'workflow': {'pre_existing_transforms': initial,
                                           'run_sbs': sbs, 'run_nsbs': nsbs}}
                    if not (initial or sbs or nsbs):
                        with self.assertRaises(ValueError):
                            _alignment_stages(config)
                        continue
                    expected = []
                    if initial:
                        expected.append(('initial', initial))
                    if sbs:
                        expected.append(('sbs', None))
                    if nsbs:
                        expected.append(('nsbs', None))
                    self.assertEqual(_alignment_stages(config), expected)

    def test_alignment_stages_legacy_defaults(self):
        print('Testing alignment_stages: legacy defaults')
        self.assertEqual(_alignment_stages({}), [('sbs', None), ('nsbs', None)])
