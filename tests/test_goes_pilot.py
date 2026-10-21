"""Testes sintéticos sem acesso ao acervo GOES, sem geolocalização presumida."""
import io
from pathlib import Path
import sys
import unittest
import zipfile
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.features.goes import reconstruct, inspect_payload, read_member, stats

NAME="dataset_goes/samples/2023/01/01/OR_ABI-L2-MCMIPF-M6_G16_s20230010300216_e20230010309529_c20230010310031.npz"


def metadata(**changes):
    result=dict(scale_factor=2.,add_offset=270.,fill_value=99,units="K",satellite="GOES-16",
                timestamp_utc="2023-01-01T03:00:21+00:00",grid_signature="synthetic",
                source_filename=Path(NAME).stem+".nc",source_key="example/"+Path(NAME).stem+".nc")
    result.update(changes)
    return result


def payload(raw,**changes):
    buffer=io.BytesIO()
    np.savez(buffer,cmi_c13_raw=raw,**metadata(**changes))
    return buffer.getvalue()


class PhysicalTests(unittest.TestCase):
    def test_reconstruction_and_nonminusone_fill(self):
        result=reconstruct(np.array([[0,2],[4,99]],dtype=np.int16),metadata())
        self.assertEqual(result.status,"reconstructed")
        np.testing.assert_allclose(result.values,[[270,274],[278,np.nan]],equal_nan=True)
        self.assertEqual(result.diagnostics["valid_pixels"],3)
        self.assertEqual(result.diagnostics["invalid_pixels"],1)
        self.assertEqual(result.diagnostics["valid_fraction"],.75)

    def test_five_statistics_on_known_synthetic_region(self):
        result=reconstruct(np.array([[0,2],[4,99]],dtype=np.int16),metadata())
        # Esta matriz artificial inteira representa uma região conhecida SOMENTE neste teste.
        actual=stats(result.values[result.valid])
        self.assertEqual(actual["mean"],274)
        self.assertAlmostEqual(actual["std_ddof0"],np.sqrt(32/3))
        self.assertEqual(actual["min"],270)
        self.assertEqual(actual["max"],278)
        self.assertEqual(actual["median"],274)

    def test_nonfinite_union_not_double_counted(self):
        result=reconstruct(np.array([[0.,np.nan],[np.inf,-np.inf]]),metadata(fill_value=np.nan))
        self.assertEqual(result.diagnostics["fill_pixels"],1)
        self.assertEqual(result.diagnostics["nonfinite_pixels"],3)
        self.assertEqual(result.diagnostics["invalid_pixels"],3)
        self.assertEqual(result.diagnostics["fill_nonfinite_overlap"],1)
        self.assertEqual(result.values[result.valid].tolist(),[270])

    def test_mask_applied_before_multiplication(self):
        result=reconstruct(np.array([[0.,1e308]]),metadata(fill_value=1e308))
        self.assertEqual(result.status,"reconstructed")
        self.assertEqual(result.values[result.valid].tolist(),[270])

    def test_all_invalid_is_not_zero(self):
        result=reconstruct(np.full((2,3),99,dtype=np.int16),metadata())
        self.assertEqual(result.status,"all_invalid")
        self.assertIsNone(result.values)
        self.assertEqual(result.diagnostics["valid_pixels"],0)
        self.assertNotIn("physical_min_K",result.diagnostics)

    def test_missing_physical_metadata(self):
        for key in ["scale_factor","add_offset","units","fill_value"]:
            with self.subTest(key=key):
                meta=metadata(); del meta[key]
                result=reconstruct(np.ones((2,2)),meta)
                self.assertIsNone(result.values)
                self.assertTrue(result.diagnostics["issues"])

    def test_inconsistent_physical_metadata(self):
        for change in [dict(scale_factor=np.inf),dict(scale_factor=0),dict(scale_factor="2"),
                       dict(add_offset=np.nan),dict(add_offset=[1,2]),dict(units="C"),dict(units="")]:
            with self.subTest(change=change):
                result=reconstruct(np.ones((2,2)),metadata(**change))
                self.assertEqual(result.status,"invalid_physical_metadata")
                self.assertIsNone(result.values)

    def test_unsigned_fill_is_not_wrapped(self):
        result=reconstruct(np.array([[0,255]],dtype=np.uint8),metadata(fill_value=-1))
        self.assertEqual(result.status,"invalid_mask_metadata")
        self.assertIsNone(result.valid)

    def test_kelvin_bytes_and_different_shapes(self):
        for shape in [(1,3),(2,2),(3,5)]:
            with self.subTest(shape=shape):
                result=reconstruct(np.ones(shape),metadata(units=b"Kelvin"))
                self.assertEqual(result.values.shape,shape)
                self.assertTrue(np.all(result.values==272))

    def test_bad_matrix(self):
        for raw in [np.ones(3),np.empty((0,2)),np.array([["text"]]),np.ones((2,2),dtype=complex)]:
            self.assertEqual(reconstruct(raw,metadata()).status,"invalid_matrix")

    def test_physical_overflow_fails(self):
        result=reconstruct(np.array([[1e308]]),metadata())
        self.assertEqual(result.status,"invalid_reconstruction")
        self.assertIsNone(result.values)


class NPZTests(unittest.TestCase):
    def test_same_payload_same_arrays_and_diagnostics(self):
        raw=payload(np.array([[0,2],[99,4]],dtype=np.int16))
        first=inspect_payload(raw,NAME); second=inspect_payload(raw,NAME)
        self.assertEqual(first.diagnostics,second.diagnostics)
        np.testing.assert_array_equal(first.valid,second.valid)
        np.testing.assert_allclose(first.values,second.values,equal_nan=True,rtol=0,atol=0)
        self.assertIsNone(first.diagnostics["region_statistics"])
        self.assertEqual(first.diagnostics["spatial_status"],"not_validated")

    def test_nonscalar_metadata_is_recorded(self):
        result=inspect_payload(payload(np.ones((2,2)),scale_factor=np.array([1,2])),NAME)
        self.assertEqual(result.status,"invalid_physical_metadata")
        self.assertIn("scale_factor",result.diagnostics["missing_metadata"])
        self.assertTrue(result.diagnostics["metadata_issues"])

    def test_identity_mismatch_and_naive_time_are_not_corrected(self):
        result=inspect_payload(payload(np.ones((2,2)),satellite="GOES-19",timestamp_utc="2023-01-01T03:00:21"),NAME)
        self.assertTrue(any("satellite diverge" in x for x in result.diagnostics["metadata_issues"]))
        self.assertTrue(any("sem offset" in x for x in result.diagnostics["metadata_issues"]))
        self.assertEqual(result.diagnostics["metadata"]["timestamp_utc"],"2023-01-01T03:00:21")

    def test_missing_identity_metadata_is_explicit(self):
        stream=io.BytesIO(); meta=metadata(); del meta["satellite"]
        np.savez(stream,cmi_c13_raw=np.ones((2,2)),**meta)
        result=inspect_payload(stream.getvalue(),NAME)
        self.assertIn("satellite",result.diagnostics["missing_metadata"])
        self.assertIn("satellite: ausente",result.diagnostics["metadata_issues"])

    def test_individual_member_without_extraction(self):
        stream=io.BytesIO()
        expected=payload(np.ones((2,2)))
        with zipfile.ZipFile(stream,"w") as archive: archive.writestr(NAME,expected)
        with zipfile.ZipFile(io.BytesIO(stream.getvalue())) as archive:
            actual,result=read_member(archive,archive.getinfo(NAME))
        self.assertEqual(actual,expected)
        self.assertEqual(result.status,"reconstructed")


if __name__=="__main__": unittest.main()
