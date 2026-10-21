import sys
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/data'))
from horizon_feasibility import complete_windows


class HorizonTests(unittest.TestCase):
    def test_gap_is_not_row_shift(self):
        index=pd.DatetimeIndex(['2023-01-01T00:00Z','2023-01-01T02:00Z','2023-01-01T03:00Z'])
        np.testing.assert_array_equal(complete_windows(index,[True]*3,1),[False,True,False])
        self.assertFalse(complete_windows(index,[True]*3,3).any())

    def test_missing_amount_and_boundaries(self):
        index=pd.date_range('2023-01-01',periods=5,freq='h',tz='UTC')
        np.testing.assert_array_equal(complete_windows(index,[True,True,False,True,True],2),[False,False,True,False,False])
        self.assertEqual(int(complete_windows(index,[True]*5,3).sum()),2)

    def test_ambiguous_index_rejected(self):
        index=pd.DatetimeIndex(['2023-01-01T00:00Z']*2)
        with self.assertRaises(ValueError): complete_windows(index,[True]*2,1)
        with self.assertRaises(ValueError): complete_windows(index.tz_localize(None),[True]*2,1)
