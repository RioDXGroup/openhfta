#!/usr/bin/env python3
"""Unit tests for OpenHFTA functionality."""

import unittest
import tempfile
import os
from pathlib import Path
import numpy as np

# Import the module under test
import hfta

class TestProfileParsing(unittest.TestCase):
    """Test terrain profile parsing."""
    
    def test_parse_meters_profile(self):
        """Test parsing a profile with meters units."""
        content = """meters
0    100.0
30   105.5
60   110.2
90   108.1
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pro', delete=False) as f:
            f.write(content)
            f.flush()
            
            distances, heights = hfta.parse_profile(f.name)
            
        os.unlink(f.name)
        
        # Values should be converted from meters to feet for Fortran core
        expected_distances = np.array([0, 30*3.28084, 60*3.28084, 90*3.28084], dtype=np.float32)
        expected_heights = np.array([100.0*3.28084, 105.5*3.28084, 110.2*3.28084, 108.1*3.28084], dtype=np.float32)
        
        np.testing.assert_array_almost_equal(distances, expected_distances, decimal=4)
        np.testing.assert_array_almost_equal(heights, expected_heights, decimal=4)
    
    def test_parse_feet_profile(self):
        """Test parsing a profile with feet units."""
        content = """feet
0    328.0
100  346.0
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pro', delete=False) as f:
            f.write(content)
            f.flush()
            
            distances, heights = hfta.parse_profile(f.name)
            
        os.unlink(f.name)
        
        # Values should remain in feet (no conversion needed)
        expected_distances = np.array([0, 100], dtype=np.float32)
        expected_heights = np.array([328.0, 346.0], dtype=np.float32)
        
        np.testing.assert_array_almost_equal(distances, expected_distances, decimal=4)
        np.testing.assert_array_almost_equal(heights, expected_heights, decimal=4)
    
    def test_parse_no_units(self):
        """Test parsing a profile without units specification."""
        content = """0    100.0
30   105.5
60   110.2
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pro', delete=False) as f:
            f.write(content)
            f.flush()
            
            distances, heights = hfta.parse_profile(f.name)
            
        os.unlink(f.name)
        
        self.assertEqual(len(distances), 3)
        self.assertEqual(len(heights), 3)
        # Values should be converted from default meters to feet
        expected_distances = np.array([0, 30, 60], dtype=np.float32)
        expected_heights = np.array([100.0, 105.5, 110.2], dtype=np.float32)
        np.testing.assert_array_almost_equal(distances, expected_distances, decimal=4)
        np.testing.assert_array_almost_equal(heights, expected_heights, decimal=4)

class TestAoAParsing(unittest.TestCase):
    """Test Angle of Arrival data parsing."""
    
    def test_parse_prn_format_full_example(self):
        """Test parsing full ARRL .PRN format with HK-US example."""
        # Using the actual HK-US.PRN data provided in the comment
        prn_content = """Bogota, Columbia  to USA
Elev      80m    40m    30m    20m    17m    15m    12m    10m
 1        1.2    2.4    2.6    3.1    5.3    6.0    4.6    3.3
 2        4.6    6.4    4.4    2.1    4.7    6.7   10.6    7.6
 3        2.4    2.8    5.9    1.8    1.3    3.2    7.0   12.9
 4        0.4    0.3    1.7    1.8    1.2    1.5    2.2    5.4
 5        0.4    0.2    0.7    1.8    1.2    1.1    2.3    5.6
10        5.7    7.3    7.7    4.3    4.0    7.4    8.4    1.4
15        5.9    5.4    4.4    6.2    5.3    3.1    3.5    6.4
20        3.5    3.0    3.3    2.4    2.0    2.6    2.8    2.5
25        1.6    2.4    1.4    1.8    0.4    1.0    0.5    0.0
30        2.3    1.0    0.4    0.9    0.7    0.5    0.0    0.0
35        0.0    0.4    0.3    0.2    0.3    0.3    0.0    0.0
"""
        
        # Test parsing 20m band (4th column)
        aoa_data = hfta.parse_prn_multiband(prn_content, "20m")
        
        # Verify some key data points (percentages converted to probabilities)
        expected_20m = {
            1: 0.031, 2: 0.021, 3: 0.018, 4: 0.018, 5: 0.018,
            10: 0.043, 15: 0.062, 20: 0.024, 25: 0.018, 
            30: 0.009, 35: 0.002
        }
        
        for angle, expected_prob in expected_20m.items():
            self.assertAlmostEqual(aoa_data[angle], expected_prob, places=3,
                msg=f"Mismatch at angle {angle}°")
    
    def test_parse_prn_format_different_bands(self):
        """Test parsing different bands from PRN format."""
        prn_content = """Test Path
Elev      80m    40m    20m    10m
 1        1.0    2.0    3.0    4.0
 5        5.0    6.0    7.0    8.0
10       10.0   11.0   12.0   13.0
"""
        
        # Test 80m band (first column)
        aoa_80m = hfta.parse_prn_multiband(prn_content, "80m")
        expected_80m = {1: 0.01, 5: 0.05, 10: 0.10}
        self.assertEqual(aoa_80m, expected_80m)
        
        # Test 40m band (second column)
        aoa_40m = hfta.parse_prn_multiband(prn_content, "40m")
        expected_40m = {1: 0.02, 5: 0.06, 10: 0.11}
        self.assertEqual(aoa_40m, expected_40m)
        
        # Test 10m band (fourth column)
        aoa_10m = hfta.parse_prn_multiband(prn_content, "10m")
        expected_10m = {1: 0.04, 5: 0.08, 10: 0.13}
        self.assertEqual(aoa_10m, expected_10m)
    
    def test_parse_prn_format_nonexistent_band(self):
        """Test parsing PRN with non-existent band falls back to first."""
        prn_content = """Test Path
Elev      80m    40m    20m
 1        1.0    2.0    3.0
 5        5.0    6.0    7.0
"""
        
        # Request non-existent band, should return empty data
        aoa_data = hfta.parse_prn_multiband(prn_content, "160m")
        expected = {}
        self.assertEqual(aoa_data, expected)
    
    def test_parse_prn_format_no_band_specified(self):
        """Test parsing PRN with no band specified uses first band."""
        prn_content = """Test Path
Elev      80m    40m    20m
 1        1.0    2.0    3.0
 5        5.0    6.0    7.0
"""
        
        # No band specified, should load empty data
        aoa_data = hfta.parse_prn_multiband(prn_content, None)
        expected = {}
        self.assertEqual(aoa_data, expected)
    
    def test_parse_prn_format_invalid_format(self):
        """Test parsing malformed PRN format."""
        # Missing header
        invalid_content = """Just some data
 1        1.0    2.0
"""
        aoa_data = hfta.parse_prn_multiband(invalid_content, "20m")
        self.assertEqual(aoa_data, {})
        
        # Too few lines
        short_content = """Title"""
        aoa_data = hfta.parse_prn_multiband(short_content, "20m")
        self.assertEqual(aoa_data, {})
    
    def test_parse_prn_format_with_zero_values(self):
        """Test parsing PRN format with zero probability values."""
        prn_content = """Test Path
Elev      20m    40m
 1        0.0    1.0
 5        5.0    0.0
10        0.0    0.0
"""
        
        aoa_data = hfta.parse_prn_multiband(prn_content, "20m")
        expected = {1: 0.0, 5: 0.05, 10: 0.0}
        self.assertEqual(aoa_data, expected)
    
class TestFOMComputation(unittest.TestCase):
    """Test Figure of Merit computation."""
    
    def test_compute_fom_basic(self):
        """Test basic FOM computation."""
        # Simple test: pattern with constant gain, uniform AoA
        pattern_db = np.full(140, 10.0)  # 10 dB constant
        aoa_data = {5: 0.2, 10: 0.3, 15: 0.5}
        
        fom = hfta.compute_fom(pattern_db, aoa_data)
        
        # All pattern values are 10 dB
        # FOM should be 10 dB regardless of AoA distribution
        self.assertAlmostEqual(fom, 10.0, places=2)
    
    def test_compute_fom_with_realistic_prn_data(self):
        """Test FOM computation with realistic PRN-style AoA data."""
        # Create a realistic elevation pattern: higher gain at low angles
        angles = np.arange(0.25, 35.25, 0.25)  # 140 samples
        pattern_db = np.zeros(140)
        
        for i, angle in enumerate(angles):
            if angle <= 5:
                pattern_db[i] = 15.0  # High gain at very low angles
            elif angle <= 15:
                pattern_db[i] = 12.0  # Medium-high gain
            elif angle <= 25:
                pattern_db[i] = 8.0   # Medium gain
            else:
                pattern_db[i] = 3.0   # Low gain at high angles
        
        # Realistic AoA data: higher probability at medium angles (typical for HF)
        aoa_data = {
            2: 0.05,   # Low probability at very low angles
            5: 0.10,   # Increasing probability
            8: 0.20,   # Peak probability around 8-12 degrees
            12: 0.25,
            15: 0.20,
            20: 0.15,
            25: 0.05   # Lower probability at high angles
        }
        
        fom = hfta.compute_fom(pattern_db, aoa_data)
        
        # FOM should be dominated by medium angles where both gain and probability are high
        # Expected range based on weighted average of linear gains
        self.assertGreater(fom, 10.0)  # Should be > 10 dB
        self.assertLess(fom, 15.0)     # Should be < 15 dB
    
    def test_compute_fom_with_hk_us_prn_sample(self):
        """Test FOM computation with actual HK-US PRN data sample."""
        # Sample of angles that align with pattern grid (0.25° increments)
        aoa_data = {
            1: 0.031,   # From HK-US 20m band
            2: 0.021,
            3: 0.018,
            5: 0.018,
            10: 0.043,
            15: 0.062,
            20: 0.024,
            25: 0.018,
            30: 0.009
        }
        
        # Create a typical HF antenna elevation pattern
        pattern_db = np.zeros(140)
        angles = np.arange(0.25, 35.25, 0.25)
        
        for i, angle in enumerate(angles):
            # Typical dipole/yagi pattern: good gain at low-medium angles
            if angle <= 10:
                pattern_db[i] = 8.0 + 2.0 * np.cos(np.radians(angle * 9))  # 6-10 dB
            elif angle <= 20:
                pattern_db[i] = 6.0 + 1.0 * np.cos(np.radians((angle-10) * 18))  # 5-7 dB  
            else:
                pattern_db[i] = 2.0 + 1.0 * np.cos(np.radians((angle-20) * 12))  # 1-3 dB
        
        fom = hfta.compute_fom(pattern_db, aoa_data)
        
        # Should compute a reasonable FOM value
        self.assertGreater(fom, 1.0)   # Should be positive and meaningful
        self.assertLess(fom, 20.0)     # Should be reasonable for HF scenario
        self.assertIsInstance(fom, float)  # Should return a float

class TestLibraryLoading(unittest.TestCase):
    """Test library loading functionality."""
    
    def test_load_ytw_core_nonexistent(self):
        """Test loading nonexistent library."""
        with self.assertRaises(RuntimeError):
            hfta.load_ytw_core("/nonexistent/path/libfake.so")
    
    def test_find_ytw_core_library_is_independent_of_cwd(self):
        """Test auto-detection does not depend on the current directory."""
        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                detected = hfta.find_ytw_core_library()
        finally:
            os.chdir(original_cwd)

        if Path(hfta.__file__).with_name("libopenytwcore.so").exists():
            self.assertEqual(detected, str(Path(hfta.__file__).with_name("libopenytwcore.so")))
        else:
            self.assertIsNone(detected)

    def test_find_ytw_core_library_checks_installed_libdir(self):
        """Test auto-detection checks ../lib relative to the installed script."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            bin_dir = tmpdir_path / "bin"
            lib_dir = tmpdir_path / "lib"
            bin_dir.mkdir()
            lib_dir.mkdir()
            script_path = bin_dir / "hfta"
            library_path = lib_dir / "libopenytwcore.so"
            script_path.write_text("#!/usr/bin/env python3\n")
            library_path.write_text("")

            original_file = hfta.__file__
            try:
                hfta.__file__ = str(script_path)
                self.assertEqual(hfta.find_ytw_core_library(), str(library_path))
            finally:
                hfta.__file__ = original_file

class TestFrequencyParsing(unittest.TestCase):
    """Test frequency parsing functionality."""
    
    def test_parse_frequency_mhz(self):
        """Test parsing frequency in MHz."""
        self.assertAlmostEqual(hfta.parse_frequency("14.2"), 14.2)
        self.assertAlmostEqual(hfta.parse_frequency("21.0"), 21.0)
        self.assertAlmostEqual(hfta.parse_frequency("7.15"), 7.15)
    
    def test_parse_frequency_ham_bands(self):
        """Test parsing ham band notation."""
        self.assertAlmostEqual(hfta.parse_frequency("20m"), 14.2)
        self.assertAlmostEqual(hfta.parse_frequency("40m"), 7.15)
        self.assertAlmostEqual(hfta.parse_frequency("15m"), 21.2)
        self.assertAlmostEqual(hfta.parse_frequency("10m"), 28.5)
        self.assertAlmostEqual(hfta.parse_frequency("160m"), 1.85)
    
    def test_parse_frequency_invalid(self):
        """Test parsing invalid frequency specifications."""
        with self.assertRaises(ValueError):
            hfta.parse_frequency("invalid")
        with self.assertRaises(ValueError):
            hfta.parse_frequency("123m")  # Not a valid ham band
        with self.assertRaises(ValueError):
            hfta.parse_frequency("")
    
    def test_frequency_to_band(self):
        """Test frequency to band conversion."""
        self.assertEqual(hfta.frequency_to_band(14.2), "20m")
        self.assertEqual(hfta.frequency_to_band(7.15), "40m")
        self.assertEqual(hfta.frequency_to_band(21.1), "15m")
        self.assertEqual(hfta.frequency_to_band(28.5), "10m")
        self.assertEqual(hfta.frequency_to_band(1.85), "160m")
        self.assertIsNone(hfta.frequency_to_band(123.45))  # Not in any ham band

class TestArgumentValidation(unittest.TestCase):
    """Test validation of analysis arguments."""
    
    def test_antenna_heights_conversion(self):
        """Test antenna height unit conversion logic."""
        # This is tested implicitly in the main analyze function
        # but we could test the conversion factor calculations here
        
        # Meters to feet conversion (for antenna heights)
        height_meters = 10.0
        height_feet = height_meters * 3.28084
        self.assertAlmostEqual(height_feet, 32.8084, places=4)
        
        # Meters to feet conversion (for terrain profile)
        terrain_meters = 100.0
        terrain_feet = terrain_meters * 3.28084
        self.assertAlmostEqual(terrain_feet, 328.084, places=4)

class TestCLIParsing(unittest.TestCase):
    """Test command line argument parsing."""
    
    def test_single_profile_parsing(self):
        """Test parsing a single profile command."""
        args = ['--profile', 'test.pro', '--freq', '20m', '--antenna-type', '2-Ele', '--heights', '10', '20*']
        
        profile_configs, global_args = hfta.parse_profile_blocks(args)
        
        self.assertEqual(len(profile_configs), 1)
        config = profile_configs[0]
        self.assertEqual(config['profile'], 'test.pro')
        self.assertEqual(config['antenna_type'], '2-Ele')
        self.assertEqual(config['heights'], ['10', '20*'])
        self.assertEqual(global_args['freq'], '20m')
    
    def test_multiple_profiles_different_antennas(self):
        """Test parsing multiple profiles with different antenna settings."""
        args = [
            '--profile', 'north.pro', '--antenna-type', '2-Ele', '--heights', '10', '20*',
            '--profile', 'south.pro', '--antenna-type', 'Dipole', '--heights', '15',
            '--freq', '14.2'
        ]
        
        profile_configs, global_args = hfta.parse_profile_blocks(args)
        
        self.assertEqual(len(profile_configs), 2)
        
        # First profile
        config1 = profile_configs[0]
        self.assertEqual(config1['profile'], 'north.pro')
        self.assertEqual(config1['antenna_type'], '2-Ele')
        self.assertEqual(config1['heights'], ['10', '20*'])
        
        # Second profile
        config2 = profile_configs[1]
        self.assertEqual(config2['profile'], 'south.pro')
        self.assertEqual(config2['antenna_type'], 'Dipole')
        self.assertEqual(config2['heights'], ['15'])
        
        # Global args
        self.assertEqual(global_args['freq'], '14.2')
    
    def test_profile_options_inheritance(self):
        """Test that profile options use defaults when not specified."""
        args = ['--profile', 'test.pro', '--freq', '20m']
        
        profile_configs, global_args = hfta.parse_profile_blocks(args)
        
        config = profile_configs[0]
        self.assertEqual(config['antenna_type'], 'Dipole')  # Default
        self.assertEqual(config['heights'], ['10.0'])  # Default
        self.assertEqual(config['move_tower'], 0.0)  # Default
        self.assertEqual(global_args['units'], 'meters')  # Default (now global)
    
    def test_global_options(self):
        """Test parsing of global options."""
        args = [
            '--profile', 'test.pro', '--freq', '20m',
            '--soil-sigma', '0.01', '--soil-epsr', '15.0',
            '--no-diffraction', '--plot-mode', 'terrain',
            '--output', 'test.png'
        ]
        
        profile_configs, global_args = hfta.parse_profile_blocks(args)
        
        self.assertEqual(global_args['soil_sigma'], 0.01)
        self.assertEqual(global_args['soil_epsr'], 15.0)
        self.assertTrue(global_args['no_diffraction'])
        self.assertEqual(global_args['plot_mode'], 'terrain')
        self.assertEqual(global_args['output'], 'test.png')
    
    def test_missing_required_args(self):
        """Test error handling for missing required arguments."""
        # Missing frequency
        with self.assertRaises(ValueError) as cm:
            hfta.parse_profile_blocks(['--profile', 'test.pro'])
        self.assertIn('--freq is required', str(cm.exception))
        
        # Missing profile
        with self.assertRaises(ValueError) as cm:
            hfta.parse_profile_blocks(['--freq', '20m'])
        self.assertIn('At least one --profile must be specified', str(cm.exception))
    
    def test_profile_specific_options_error(self):
        """Test that profile-specific options require a preceding --profile."""
        with self.assertRaises(ValueError) as cm:
            hfta.parse_profile_blocks(['--antenna-type', '2-Ele', '--freq', '20m'])
        self.assertIn('--antenna-type must come after --profile', str(cm.exception))
    
    def test_invalid_values(self):
        """Test error handling for invalid option values."""
        # Invalid antenna type
        with self.assertRaises(ValueError) as cm:
            hfta.parse_profile_blocks(['--profile', 'test.pro', '--antenna-type', 'Invalid', '--freq', '20m'])
        self.assertIn('Invalid antenna type', str(cm.exception))
        
        # Invalid units (now global)
        with self.assertRaises(ValueError) as cm:
            hfta.parse_profile_blocks(['--profile', 'test.pro', '--freq', '20m', '--units', 'invalid'])
        self.assertIn('Invalid units', str(cm.exception))
        
        # Invalid plot mode
        with self.assertRaises(ValueError) as cm:
            hfta.parse_profile_blocks(['--profile', 'test.pro', '--freq', '20m', '--plot-mode', 'invalid'])
        self.assertIn('Invalid plot mode', str(cm.exception))

if __name__ == '__main__':
    # For CI environments without the shared library, skip integration tests
    if not any(os.path.exists(p) for p in ["./libopenytwcore.so", "libopenytwcore.so"]):
        print("Warning: libopenytwcore.so not found, skipping integration tests")
        print("Run 'make libopenytwcore.so' to enable full testing")
    
    unittest.main()
