"""Testes de fronteiras temporais que afetam as conclusões exploratórias."""
from pathlib import Path
import sys
import unittest
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"/"data"))
from eda import name_time,spells


class TemporalTests(unittest.TestCase):
    def test_noaa_fractional_second_and_year_boundary(self):
        actual=name_time("OR_G16_s20200010300216_e20200010309529_c20200010310031.npz")
        self.assertEqual(actual,pd.Timestamp("2020-01-01T03:00:21.6Z"))
        self.assertEqual(name_time("x_s20203662359599.npz"),pd.Timestamp("2020-12-31T23:59:59.9Z"))

    def test_unknown_name_is_not_invented(self):
        self.assertTrue(pd.isna(name_time("unknown.npz")))

    def test_spells_break_on_gap_and_dry_hour(self):
        time=pd.Series(pd.to_datetime(["2020-01-01T00:00","2020-01-01T01:00","2020-01-01T03:00","2020-01-01T04:00","2020-01-01T05:00"]))
        result=spells(time,[True,True,True,False,True],[1,2,3,0,4])
        self.assertEqual(result.hours.tolist(),[2,1,1])
        self.assertEqual(result.total_mm.tolist(),[3,3,4])
        self.assertTrue(result.iloc[0].touches_start)
        self.assertTrue(result.iloc[-1].touches_end)


if __name__=="__main__": unittest.main()
