"""Casos científicos mínimos: máscara, unidades e referência temporal."""
import io
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "data"))
from audit import inspect_npz


def sample(**changes):
    fields = dict(cmi_c13_raw=np.array([[0., 2.], [-1., np.nan]]),
                  scale_factor=2., add_offset=270., fill_value=-1., units="K",
                  timestamp_utc="2020-01-01T03:00:21Z")
    fields.update(changes)
    stream = io.BytesIO()
    np.savez(stream, **fields)
    return stream.getvalue()


class ImageTests(unittest.TestCase):
    def test_mask_and_kelvin(self):
        result = inspect_npz(sample(), "2020-01-01T00:00:00")
        self.assertEqual(result["valid_pixels"], 2)
        self.assertEqual(result["invalid_pixels"], 2)
        self.assertEqual(result["physical"]["mean"], 272.)
        self.assertAlmostEqual(result["celsius"]["mean"], -1.15)
        self.assertEqual(result["capture_minus_csv_seconds"], 21.)

    def test_explicit_offset(self):
        result = inspect_npz(sample(timestamp_utc="2020-01-01T00:00:21-03:00"), "2020-01-01T00:00:00")
        self.assertEqual(result["capture_minus_csv_seconds"], 21.)
        self.assertTrue(result["warnings"])

    def test_other_unit_is_not_celsius_converted(self):
        result = inspect_npz(sample(units="W"), "2020-01-01T00:00:00")
        self.assertNotIn("celsius", result)

    def test_all_invalid_fails_clearly(self):
        with self.assertRaisesRegex(ValueError, "Nenhum pixel válido"):
            inspect_npz(sample(cmi_c13_raw=np.full((2, 2), -1.)), "2020-01-01T00:00:00")

    def test_missing_metadata_does_not_invent_reconstruction(self):
        stream = io.BytesIO()
        np.savez(stream, cmi_c13_raw=np.ones((2, 2)))
        result = inspect_npz(stream.getvalue(), "2020-01-01T00:00:00")
        self.assertNotIn("physical", result)
        self.assertIn("fill_value", result["missing_metadata"])
        self.assertTrue(result["warnings"])


if __name__ == "__main__":
    unittest.main()
