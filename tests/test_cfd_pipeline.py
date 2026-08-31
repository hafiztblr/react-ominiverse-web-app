import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from cfd_pipeline import convert_dataset, read_vtu, validate_dataset, write_animated_usda, write_usda


ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "vtu-files" / "ENTIRE_DOMAIN_0010.vtu"


class CFDPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame = read_vtu(FIXTURE)

    def test_real_fixture_structure(self):
        self.assertEqual(self.frame.mesh.point_count, 781)
        self.assertEqual(self.frame.mesh.cell_count, 700)
        self.assertEqual(set(self.frame.mesh.cell_types), {7})
        self.assertEqual(self.frame.point_fields, {})
        self.assertEqual(len(self.frame.cell_fields), 21)

    def test_real_fixture_cell_fields(self):
        self.assertEqual(self.frame.cell_fields["Gas_temperature"].values.shape, (700,))
        self.assertEqual(self.frame.cell_fields["Gas_Velocity"].values.shape, (700, 3))
        self.assertEqual(self.frame.cell_fields["Gas_temperature"].association, "cell")

    def test_single_file_conversion(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            output = write_usda(self.frame, Path(directory) / "frame_0010.usda")
            text = output.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("#usda 1.0"))
        self.assertIn("float[] primvars:Gas_temperature", text)
        self.assertIn("vector3f[] primvars:Gas_Velocity", text)
        self.assertIn("color3f[] primvars:displayColor", text)
        self.assertEqual(text.count('interpolation = "uniform"'), len(self.frame.cell_fields) + 1)
        self.assertTrue(np.isclose(self.frame.cell_fields["Gas_temperature"].minimum, 1070.2099609375))

    def test_dataset_validation_and_shared_mesh_output(self):
        validation = validate_dataset(ROOT / "vtu-files", start=9, end=10)
        self.assertFalse(validation.errors)
        self.assertTrue(validation.topology_consistent)
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            metadata_path = convert_dataset(ROOT / "vtu-files", directory, start=9, end=10, validation=validation)
            output = Path(directory)
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            mesh_text = (output / "mesh.usda").read_text(encoding="utf-8")
            frame_text = (output / "frames" / "frame_0010.usda").read_text(encoding="utf-8")
        self.assertEqual(metadata["frameCount"], 2)
        self.assertIn("faceVertexIndices", mesh_text)
        self.assertNotIn("faceVertexIndices", frame_text)
        self.assertIn("references = @../mesh.usda@</World>", frame_text)

    def test_animated_output(self):
        validation = validate_dataset(ROOT / "vtu-files", start=9, end=10)
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            output = write_animated_usda(validation, Path(directory) / "animation.usda")
            text = output.read_text(encoding="utf-8")
        self.assertIn("startTimeCode = 9", text)
        self.assertIn("endTimeCode = 10", text)
        self.assertIn("primvars:Gas_temperature.timeSamples", text)
        self.assertIn("primvars:displayColor.timeSamples", text)
        self.assertIn('interpolation = "faceVarying"', text)
        # One CFD topology plus one single-face backdrop; neither is time-sampled.
        self.assertEqual(text.count("faceVertexIndices"), 2)
        self.assertIn('def Camera "Camera"', text)
        self.assertIn('def Mesh "Backdrop"', text)


if __name__ == "__main__":
    unittest.main()
