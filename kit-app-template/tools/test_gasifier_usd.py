import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("generate_gasifier_usd.py")
SPEC = importlib.util.spec_from_file_location("gasifier_generator", SCRIPT)
GEN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GEN)


class GasifierUsdTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.tmp.name) / "gasifier_cfd.usd"
        cls.counts = GEN.generate(cls.path)
        cls.text = cls.path.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_stage_is_self_contained_and_structurally_balanced(self):
        self.assertTrue(self.text.startswith("#usda 1.0"))
        self.assertNotIn("@", self.text)
        self.assertEqual(self.text.count("{"), self.text.count("}"))

    def test_required_hierarchy_and_metadata(self):
        for name in ("Geometry", "Reactor", "TemperatureField", "SyngasFlow", "GasOutlet",
                     "DryingZone", "PyrolysisZone", "CombustionZone", "ReductionZone", "AshZone"):
            self.assertIn(f'"{name}"', self.text)
        for value in ("326.3", "565.1", "875", "707.2", "390.6", "316.1", "25.8", "18.84", "5.77", "3.32", "0.27"):
            self.assertIn(value, self.text)

    def test_interpolated_field_and_animation(self):
        self.assertGreater(self.counts["field_points"], 2500)
        self.assertEqual(self.counts["particles"], 110)
        self.assertIn('def Mesh "Field"', self.text)
        self.assertNotIn('def Points "Field"', self.text)
        self.assertIn("faceVertexIndices", self.text)
        self.assertNotIn("float[] widths = [0.205", self.text)
        self.assertIn('def Material "TemperatureMaterial"', self.text)
        self.assertIn('rel material:binding = </Gasifier/Looks/TemperatureMaterial>', self.text)
        self.assertIn('token inputs:varname = "displayColor"', self.text)
        self.assertIn("points.timeSamples", self.text)
        self.assertIn("48:", self.text)
        self.assertGreater(GEN.field_temperature(0, 0, 5), GEN.field_temperature(1.5, 0, 5))
        self.assertAlmostEqual(GEN.axial_temperature(6), 875.0)
        self.assertAlmostEqual(GEN.field_temperature(0, 0, 6), 875.0)
        self.assertLessEqual(max(GEN.field_temperature(0, 0, z / 10) for z in range(100)), 875.0)
        self.assertGreaterEqual(min(GEN.field_temperature(1.5, 0, z / 10) for z in range(100)), 316.1)
        cold, hot = GEN.color(316.1), GEN.color(875.0)
        self.assertGreater(cold[2], cold[0])
        self.assertGreater(hot[0], hot[2])

    def test_sample_data_parser_drives_output(self):
        sample = SCRIPT.resolve().parents[2] / "samle-data.txt"
        temperatures, composition = GEN.parse_sample_data(sample)
        self.assertEqual(temperatures["CombustionZone"], 875.0)
        self.assertEqual(composition["H2"], 25.80)
        driven_path = Path(self.tmp.name) / "driven.usd"
        GEN.generate(driven_path, sample)
        driven = driven_path.read_text(encoding="utf-8")
        self.assertIn('custom string data:source = "samle-data.txt"', driven)
        self.assertIn("custom double composition:CO = 18.84", driven)

    def test_particle_path_stays_in_reactor_then_outlet(self):
        # Vertical-zone samples remain inside the reactor radius and move up.
        reactor = [GEN.particle_path(p, 0.7, 0.44) for p in (0.0, 0.18, 0.38, 0.58, 0.72)]
        self.assertTrue(all((x * x + y * y) ** 0.5 < 1.7 for x, y, _ in reactor))
        self.assertEqual([round(z, 2) for _, _, z in reactor], [11.25, 8.4, 6.0, 3.7, 1.45])
        # Once in the horizontal outlet, YZ offsets fit inside its 0.24 radius.
        outlet = [GEN.particle_path(p, 1.2, 0.44) for p in (0.78, 0.86, 0.94, 1.0)]
        self.assertTrue(all(abs(y) <= 0.111 for _, y, _ in outlet))
        self.assertGreater(outlet[-1][0], outlet[0][0])


if __name__ == "__main__":
    unittest.main()
