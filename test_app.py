"""Meaningful integration checks. Run: python test_app.py."""
import json
from pathlib import Path
import unittest
import tempfile
import shutil
import numpy as np
import pandas as pd

from ev_core import (FEATURES, validate_data, estimated_bills, load_artifacts,
                     prepare_inputs, predict)
from assessment1_billing_reference import calculate_bill

ROOT = Path(__file__).resolve().parent


class PortalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = validate_data(pd.read_csv(ROOT / 'cleaned_ev_dataset.csv'))
        cls.raw = pd.read_csv(ROOT / 'ev_campus_dataset.csv')
        cls.model, cls.meta, cls.categories = load_artifacts(ROOT / 'ev_model.pkl', ROOT / 'model_metadata.json')

    def app(self):
        """Run the app as an already signed-in user."""
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=45)
        at.session_state['user'] = 'SESS-1000'
        at.run()
        self.assertFalse(at.exception, str(at.exception))
        return at

    def temp_app(self, folder):
        """Copy app.py and the raw dataset to a temp folder, so registration
        tests never modify the real ev_campus_dataset.csv."""
        from streamlit.testing.v1 import AppTest
        shutil.copyfile(ROOT / 'app.py', Path(folder) / 'app.py')
        if not (Path(folder) / 'ev_campus_dataset.csv').exists():   # keep earlier registrations
            shutil.copyfile(ROOT / 'ev_campus_dataset.csv', Path(folder) / 'ev_campus_dataset.csv')
        return AppTest.from_file(str(Path(folder) / 'app.py'), default_timeout=45)

    @staticmethod
    def click(at, label):
        next(b for b in at.button if b.label == label).click().run()

    def test_login_gate_blocks_unknown_users(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=45).run()
        self.assertFalse(at.exception, str(at.exception))
        self.assertEqual(len(at.metric), 0)               # no data before login
        at.text_input(key='login_id').set_value('NOBODY-1')
        self.click(at, 'Log in')
        self.assertTrue(any('not registered' in x.value for x in at.error))
        self.assertNotIn('user', at.session_state)
        at.text_input(key='login_id').set_value(' sess-1000 ')  # case/space tolerant
        self.click(at, 'Log in')
        self.assertFalse(at.exception, str(at.exception))
        self.assertEqual(at.session_state['user'], 'SESS-1000')
        self.assertNotIn('show_guide', at.session_state)   # dataset users skip the guide
        self.assertEqual(len(at.metric), 4)
        self.click(at, 'Log out')
        self.assertNotIn('user', at.session_state)
        self.assertEqual(len(at.metric), 0)

    def test_registration_appends_to_dataset_then_allows_login(self):
        with tempfile.TemporaryDirectory() as folder:
            csv_path = Path(folder) / 'ev_campus_dataset.csv'
            at = self.temp_app(folder).run()
            at.text_input(key='login_id').set_value('NEW-USER-1')
            self.click(at, 'Log in')
            self.click(at, 'Register this ID')
            self.assertEqual(at.text_input(key='register_id').value, 'NEW-USER-1')
            at.selectbox(key='register_type').set_value('Student')
            self.click(at, 'Register')
            self.assertFalse(at.exception, str(at.exception))
            self.assertTrue(any('NEW-USER-1 is registered' in x.value for x in at.success))
            table = pd.read_csv(csv_path)
            self.assertEqual(len(table), len(self.raw) + 1)
            self.assertEqual(table.iloc[-1].Session_ID, 'NEW-USER-1')
            self.assertEqual(table.iloc[-1].User_Type, 'Student')
            # Back on the login form with the new ID filled in.
            self.assertEqual(at.text_input(key='login_id').value, 'NEW-USER-1')
            self.click(at, 'Log in')
            self.assertEqual(at.session_state['user'], 'NEW-USER-1')
            # A newly registered user gets the onboarding guide once.
            self.assertTrue(at.session_state['show_guide'])
            self.assertTrue(any('Welcome to Campus EV, NEW-USER-1' in m.value for m in at.markdown))
            self.click(at, 'Next')
            self.assertEqual(at.session_state['guide_step'], 1)
            self.click(at, 'Skip tour')
            self.assertFalse(at.session_state['show_guide'])
            done = json.loads((Path(folder) / 'onboarded_users.json').read_text())
            self.assertEqual(done, ['NEW-USER-1'])
            self.click(at, 'Log out')
            at.text_input(key='login_id').set_value('NEW-USER-1')
            self.click(at, 'Log in')
            self.assertNotIn('show_guide', at.session_state)   # guide not shown again

            # Existing IDs and invalid IDs are refused; the file is unchanged.
            for bad in ['SESS-1000', 'new-user-1', 'a,b', 'x']:
                at2 = self.temp_app(folder)
                at2.session_state['auth_mode'] = 'Register'
                at2.run()
                at2.text_input(key='register_id').set_value(bad)
                self.click(at2, 'Register')
                self.assertTrue(at2.error, bad)
            self.assertEqual(len(pd.read_csv(csv_path)), len(self.raw) + 1)

    def test_registered_rows_do_not_change_task1_output(self):
        from auth import register
        from data_pipeline import clean, load_data
        with tempfile.TemporaryDirectory() as folder:
            csv_path = Path(folder) / 'ev_campus_dataset.csv'
            shutil.copyfile(ROOT / 'ev_campus_dataset.csv', csv_path)
            register(csv_path, 'reg-test', 'Visitor')
            cleaned = clean(load_data(csv_path), {})
            # Only labelled sessions survive (users registered earlier are dropped too).
            self.assertEqual(len(cleaned), int(self.raw.Grid_Status_Label.notna().sum()))
            self.assertEqual(len(cleaned), 1200)
            self.assertNotIn('REG-TEST', set(cleaned.Session_ID))

    def test_original_holdout_predictions_unchanged(self):
        expected = pd.read_csv(ROOT / 'test_predictions.csv')
        rows = self.raw.set_index('Session_ID').loc[expected.Session_ID].reset_index()
        actual = self.model.predict(prepare_inputs(rows))
        np.testing.assert_array_equal(actual, expected.predicted_DecisionTree)

    def test_saved_preprocessing_and_unknown_category(self):
        row = {c: np.nan for c in FEATURES}
        row.update(Charger_Type='Unknown', User_Type=' Staff ')
        label, probs, x = predict(self.model, row)
        self.assertIn(label, {'Normal', 'Overheated', 'Grid_Surge'})
        self.assertAlmostEqual(sum(probs.values()), 1)
        self.assertEqual(x.User_Type.iloc[0], 'Staff')
        self.assertTrue(x.Duration_Mins.isna().all())
        # The fitted encoder ignores unseen categories without changing its width.
        self.assertEqual(self.model.named_steps['preprocess'].transform(x).shape[1], 11)

    def test_task1_output_is_sanitised(self):
        self.assertEqual(int(self.df.drop(columns='Period').isna().sum().sum()), 0)
        self.assertFalse(self.df.Session_ID.duplicated().any())
        expected = self.df.Start_Hour.between(12, 17).astype(int)
        np.testing.assert_array_equal(self.df.Peak_Hour_Flag, expected)
        power = self.df.Energy_kWh / (self.df.Duration_Mins / 60)
        np.testing.assert_allclose(self.df.Power_kW, power, atol=1e-3)

    def test_peak_flag_derived_at_inference(self):
        row = dict(Charger_Type='AC', User_Type='Staff', Start_Hour=17, Duration_Mins=90,
                   Energy_kWh=10, Overstay_Mins=0, Battery_Temp_C=30)
        label, _, x = predict(self.model, row)
        self.assertEqual(x.Peak_Hour_Flag.iloc[0], 1)
        self.assertEqual(label, 'Grid_Surge')
        row['Battery_Temp_C'] = 48
        self.assertEqual(predict(self.model, row)[0], 'Overheated')

    def test_validation_rejects_bad_data(self):
        for bad in [self.df.drop(columns='Energy_kWh'), self.df.iloc[:0],
                    pd.concat([self.df, self.df.iloc[:1]]),
                    self.df.assign(Duration_Mins=-1), self.df.assign(Peak_Hour_Flag=2)]:
            with self.assertRaises(ValueError):
                validate_data(bad)

    def test_billing_matches_recovered_prototype(self):
        cases = []
        for charger in ['AC', 'DC']:
            for user in ['Staff', 'Student', 'Visitor']:
                for duration in [15, 120, 121, 240, 241, 360, 361, 2000]:
                    for peak in [0, 1]:
                        for idle in [0, 1]:
                            cases.append(dict(Charger_Type=charger, User_Type=user,
                                              Duration_Mins=duration, Peak_Hour_Flag=peak,
                                              Overstay_Mins=idle * 5))
        result = estimated_bills(pd.DataFrame(cases))
        for _, row in result.iterrows():
            ref = calculate_bill(row.User_Type.lower(), row.Charger_Type,
                                 row.Duration_Mins / 60, peak=bool(row.Peak_Hour_Flag),
                                 idle=row.Overstay_Mins > 0)
            self.assertAlmostEqual(row.Estimated_Revenue_RM, ref['net'])

    def test_dashboard_filters_metrics_and_empty_state(self):
        at = self.app()
        self.assertEqual(len(at.metric), 4)
        self.assertEqual(at.metric[0].value, f'{self.df.Energy_kWh.sum():,.2f} kWh')
        at.multiselect(key='filter_charger').set_value(['DC']).run()
        self.assertFalse(at.exception)
        dc = self.df[self.df.Charger_Type.eq('DC')]
        self.assertEqual(at.metric[0].value, f'{dc.Energy_kWh.sum():,.2f} kWh')
        at.selectbox(key='filter_period').set_value('Peak').run()
        peak = estimated_bills(dc.loc[dc.Peak_Hour_Flag.eq(1)])
        self.assertEqual(at.metric[2].value, f'RM {peak.Estimated_Revenue_RM.sum():,.2f}')
        at.multiselect(key='filter_charger').set_value([]).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.metric[1].value, '—')
        self.assertTrue(any('No sessions' in x.value for x in at.info))
        next(b for b in at.button if b.label == 'Reset filters').click().run()
        self.assertEqual(at.metric[3].value, '1,200')

    def test_analytics_three_figures_and_controls(self):
        at = self.app()
        at.radio(key='page').set_value('Visual Analytics Studio').run()
        self.assertFalse(at.exception, str(at.exception))
        self.assertEqual(len(at.get('imgs')), 3)
        next(s for s in at.selectbox if s.label == 'Peak vs Non-peak comparison').set_value('Session count').run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.get('imgs')), 3)
        at.multiselect(key='filter_charger').set_value([]).run()
        self.assertFalse(at.exception)
        self.assertTrue(any('No sessions' in x.value for x in at.info))

    def test_missing_artifacts_display_actionable_errors(self):
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as temporary:
            entry = Path(temporary) / 'app.py'
            shutil.copyfile(ROOT / 'app.py', entry)
            at = AppTest.from_file(str(entry), default_timeout=45).run()
            self.assertFalse(at.exception)
            self.assertTrue(any('Cannot load the user list' in x.value for x in at.error))
            at.session_state['user'] = 'SESS-1000'
            at.run()
            self.assertFalse(at.exception)
            self.assertTrue(any('Cannot load cleaned_ev_dataset.csv' in x.value for x in at.error))
            at.radio(key='page').set_value('Live Machine Learning Inference').run()
            self.assertFalse(at.exception)
            self.assertTrue(any('Cannot load the saved model' in x.value for x in at.error))

    def test_inference_three_status_banners(self):
        at = self.app()
        at.radio(key='page').set_value('Live Machine Learning Inference').run()
        self.assertFalse(at.exception, str(at.exception))
        rows = self.raw.dropna(subset=[c for c in FEATURES if c != 'Peak_Hour_Flag']).copy()
        predictions = self.model.predict(prepare_inputs(rows))
        for label, banner in [('Normal', 'success'), ('Overheated', 'warning'), ('Grid_Surge', 'error')]:
            sample = rows.loc[np.asarray(predictions) == label].iloc[0]
            at.selectbox(key='input_charger').set_value(sample.Charger_Type)
            at.selectbox(key='input_user').set_value(sample.User_Type)
            at.slider(key='input_hour').set_value(int(sample.Start_Hour))
            for key, col in [('input_duration', 'Duration_Mins'), ('input_energy', 'Energy_kWh'),
                             ('input_overstay', 'Overstay_Mins'), ('input_temperature', 'Battery_Temp_C')]:
                at.number_input(key=key).set_value(float(sample[col]))
            at.run()
            self.assertFalse(at.exception, str(at.exception))
            self.assertTrue(any(label in x.value for x in at.get(banner)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
