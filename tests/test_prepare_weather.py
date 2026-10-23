from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import WEATHER_FEATURES
from scripts.prepare_weather import prepare_table, run


def example():
    return pd.DataFrame({'time': ['2023-01-01T00:00:00','2023-01-01T01:00:00','2023-01-01T02:00:00'],
        'temperature_2m': [20,21,22], 'relative_humidity_2m': [70,80,90],
        'pressure_msl': [1000,1001,1002], 'cloud_cover': [30,40,50], 'rain': [4,0,0.1]})


class PrepareWeatherTests(unittest.TestCase):
    def test_exact_target_and_no_future_feature(self):
        source=example(); before=source.copy(deep=True)
        table,rejected,summary=prepare_table(source.iloc[::-1])
        self.assertEqual(table.rain_next_hour.tolist(),[0,1])
        self.assertEqual(table.temperature_2m.tolist(),[20,21])
        self.assertEqual(list(table.columns),['time',*WEATHER_FEATURES,'target_time','rain_next_hour'])
        self.assertTrue((table.target_time-table.time==pd.Timedelta(hours=1)).all())
        self.assertEqual(rejected.reason.tolist(),['missing_future_timestamp'])
        pd.testing.assert_frame_equal(source,before)

    def test_gap_does_not_use_next_row(self):
        table,rejected,summary=prepare_table(example().drop(index=1))
        self.assertTrue(table.empty)
        self.assertEqual(summary['missing_hours'],1)

    def test_missing_or_negative_future_is_not_dry(self):
        for value in [np.nan,np.inf,-1,'bad']:
            source=example(); source['rain']=source.rain.astype(object); source.loc[1,'rain']=value
            table,rejected,_=prepare_table(source)
            self.assertEqual(len(table),1)
            self.assertIn('invalid_or_missing_future_rain',rejected.reason.tolist())

    def test_missing_future_features_do_not_erase_known_rain(self):
        source=example(); source.loc[1,'temperature_2m']=np.nan
        table,_,_=prepare_table(source)
        self.assertEqual(table.rain_next_hour.tolist(),[0])

    def test_invalid_domain_excluded_without_imputation(self):
        source=example(); source.loc[0,'relative_humidity_2m']=101
        table,rejected,_=prepare_table(source)
        self.assertEqual(len(table),1)
        self.assertIn('features_outside_domain',rejected.reason.tolist())

    def test_ambiguous_or_incomplete_schema_fails(self):
        with self.assertRaises(ValueError): prepare_table(pd.concat([example(),example().iloc[:1]]))
        with self.assertRaises(ValueError): prepare_table(example().drop(columns='rain'))
        source=example(); source.loc[0,'time']='2023-01-01T00:30:00'
        with self.assertRaises(ValueError): prepare_table(source)

    def test_utc_is_converted_to_local(self):
        source=example(); source['time']=['2023-01-01T03:00:00Z','2023-01-01T04:00:00Z','2023-01-01T05:00:00Z']
        table,_,_=prepare_table(source)
        self.assertEqual(table.time.iloc[0].hour,0)

    def test_cannot_write_over_source(self):
        with self.assertRaises(ValueError): run('original.csv','original.csv')
