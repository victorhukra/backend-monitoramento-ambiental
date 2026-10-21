import io
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.make_sample import make_sample,read_one
from scripts.check_staged import allowed
from test_goes_pilot import payload
import numpy as np


class OnboardingTests(unittest.TestCase):
    def test_repository_policy(self):
        for name in ('data/sample/a.py','x.NPZ','.env','.env.local','report.csv','node_modules/x.md','x.zip'):
            self.assertFalse(allowed(name),name)
        for name in ('src/data/audit.py','reports/eda/eda_report.md','.env.example'):
            self.assertTrue(allowed(name),name)

    def test_sample_preserves_payload_and_source(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root=Path(directory); source=root/'input.zip'; output=root/'sample.npz'
            raw=payload(np.array([[100,101]],dtype=np.int16))
            with np.load(io.BytesIO(raw),allow_pickle=False) as item:
                name=str(item['source_filename'].item()).replace('.nc','.npz')
            with zipfile.ZipFile(source,'w') as archive: archive.writestr(name,raw)
            before=source.read_bytes()
            selected,size=make_sample(source,output)
            self.assertEqual(output.read_bytes(),raw)
            self.assertEqual(source.read_bytes(),before)
            self.assertLess(size,50_000_000)
            with self.assertRaises(ValueError): make_sample(source,output)

    def test_missing_member_fails(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            source=Path(directory)/'a.zip'
            with zipfile.ZipFile(source,'w') as archive: archive.writestr('a.npz',b'x')
            with self.assertRaises(ValueError): read_one(source,'missing.npz')
