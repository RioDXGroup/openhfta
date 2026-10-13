import hashlib
import unittest
from pathlib import Path
import numpy as np

from openhfta_core.analysis import analyze
from openhfta_core.aoa import parse_frequency
from openhfta_core.exceptions import ProfileError, ValidationError
from openhfta_core.library import load_ytw_core
from openhfta_core.metrics import beamwidth_3db, compare_patterns, summarize_pattern
from openhfta_core.models import AnalysisConfig
from openhfta_core.profiles import parse_profile

ROOT = Path(__file__).parent

class TestCoreRegression(unittest.TestCase):
    def test_pattern_metrics(self):
        angles = np.arange(0.25, 10.25, 0.25)
        pattern = 10.0 - ((angles - 5.0) ** 2)
        summary = summarize_pattern(angles, pattern)
        self.assertAlmostEqual(summary["peak"]["angle_deg"], 5.0)
        self.assertTrue(summary["peaks"])
        self.assertIsNotNone(beamwidth_3db(angles, pattern)["width_deg"])

    def test_pattern_comparison(self):
        angles = np.array([1., 2., 3.])
        comparison = compare_patterns(angles, np.array([1., 2., 3.]), angles, np.array([2., 2., 4.]))
        self.assertAlmostEqual(comparison["rmse_db"], np.sqrt(2 / 3))
        self.assertAlmostEqual(comparison["max_absolute_delta_db"], 1.)

    def test_reference_analysis(self):
        result = analyze(AnalysisConfig(str(ROOT/'test/pro/PR1T-torre1-332.00.PRO'), parse_frequency('20m'), (10*3.28084,), (1,), lib_path=str(ROOT/'libopenytwcore.so')))
        np.testing.assert_array_equal(result.angles_deg, np.arange(.25, 35.25, .25))
        self.assertAlmostEqual(float(result.pattern_db.max()), 9.999393463134766, places=5)
        self.assertEqual(float(result.angles_deg[result.pattern_db.argmax()]), 27.25)
        self.assertEqual(hashlib.sha256(result.pattern_db.tobytes()).hexdigest(), '4657d80a8d6a8997631f479f6ca7b7c52592cc368b6f8066adf407e9510f9819')

    def test_profile_validation(self):
        import tempfile
        with tempfile.NamedTemporaryFile('w', delete=False) as file:
            file.write('feet\n0 1\n0 2\n')
            name = file.name
        with self.assertRaises(ProfileError): parse_profile(name)

    def test_library_symbol_error(self):
        with self.assertRaises(RuntimeError): load_ytw_core('/usr/lib/libm.so.6')

    def test_core_element_limit(self):
        config = AnalysisConfig(str(ROOT/'test/pro/PR1T-torre1-332.00.PRO'), 14.2, (1,2,3,4,5), (1,1,1,1,1))
        with self.assertRaises(ValidationError): analyze(config)

    def test_profile_point_limit_matches_fortran_abi(self):
        import tempfile
        with tempfile.NamedTemporaryFile('w', suffix='.PRO', delete=False) as file:
            file.write('feet\n')
            for point in range(150):
                file.write(f'{point * 100} {100 + point * 0.01}\n')
            name = file.name
        result = analyze(AnalysisConfig(name, 14.2, (10,), (1,), lib_path=str(ROOT/'libopenytwcore.so')))
        self.assertEqual(result.metadata['max_profile_points'], 149)
        self.assertEqual(result.metadata['profile_points'], 149)
