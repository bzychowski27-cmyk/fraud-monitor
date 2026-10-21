import unittest
import pandas as pd
from monitoring import Thresholds, financial_analyses, generate_transactions, score_transactions


class MonitoringTests(unittest.TestCase):
    def sample(self, amounts, minutes):
        return pd.DataFrame([dict(transaction_id=str(i), account_id='A', amount=amount,
            timestamp=pd.Timestamp('2025-01-01') + pd.Timedelta(minutes=minute),
            direction='Debit', channel='Transfer', category='Other')
            for i, (amount, minute) in enumerate(zip(amounts, minutes))])

    def test_generator_reproducible_and_minimum(self):
        pd.testing.assert_frame_equal(generate_transactions(250), generate_transactions(250))
        self.assertEqual(len(generate_transactions()), 500)
        with self.assertRaises(ValueError):
            generate_transactions(249)

    def test_exact_boundaries_and_combination(self):
        result = score_transactions(self.sample([10, 5000, 10], [0, 60, 121]), Thresholds(5000, 2, 60, 40))
        self.assertEqual(result['window_count'].tolist(), [1, 2, 1])
        self.assertEqual(result['risk_score'].tolist(), [0, 100, 0])
        self.assertIn('Both rules', result.iloc[1]['explanation'])

    def test_account_isolation_no_future_leakage(self):
        frame = self.sample([1, 1, 1], [0, 1, 2])
        frame.loc[1, 'account_id'] = 'B'
        result = score_transactions(frame, Thresholds(5000, 2, 60, 40))
        self.assertEqual(result['window_count'].tolist(), [1, 1, 2])
        self.assertEqual(result['risk_score'].tolist(), [0, 0, 40])

    def test_ties_and_input_order(self):
        frame = self.sample([1, 1], [0, 0])
        a = score_transactions(frame, Thresholds(frequency_count=2))
        b = score_transactions(frame.iloc[::-1], Thresholds(frequency_count=2))
        pd.testing.assert_frame_equal(a, b)
        self.assertEqual(a['window_count'].tolist(), [2, 2])

    def test_cutoff_changes_flags_only(self):
        frame = self.sample([5000], [0])
        a = score_transactions(frame)
        b = score_transactions(frame, Thresholds(flag_score=41))
        self.assertTrue(a.iloc[0]['flagged'])
        self.assertFalse(b.iloc[0]['flagged'])
        self.assertEqual(a.iloc[0]['risk_score'], b.iloc[0]['risk_score'])

    def test_invalid_data_and_configuration(self):
        for amount in [-1, 0, float('inf'), float('nan')]:
            with self.assertRaises(ValueError):
                score_transactions(self.sample([amount], [0]))
        for config in [Thresholds(large_amount=0), Thresholds(window_minutes=0), Thresholds(flag_score=101)]:
            with self.assertRaises(ValueError):
                score_transactions(self.sample([1], [0]), config)
        frame = self.sample([1, 2], [0, 1])
        frame.loc[1, 'transaction_id'] = '0'
        with self.assertRaises(ValueError):
            score_transactions(frame)
        for frame in [pd.DataFrame(), self.sample([1], [0]).assign(timestamp='invalid'), self.sample([1], [0]).assign(direction='Unknown')]:
            with self.assertRaises(ValueError):
                score_transactions(frame)

    def test_analyses_reconcile_to_source(self):
        data = score_transactions(generate_transactions())
        daily, accounts, channels = financial_analyses(data)
        expected = data.loc[data.direction == 'Credit', 'amount'].sum() - data.loc[data.direction == 'Debit', 'amount'].sum()
        self.assertAlmostEqual(daily['Net flow'].sum(), expected)
        self.assertAlmostEqual(accounts['value_share_pct'].sum(), 100)
        self.assertAlmostEqual(channels['flagged_value'].sum(), data.loc[data.flagged, 'amount'].sum())
        self.assertGreater(data['large_amount'].sum(), 0)
        self.assertGreater(data['high_frequency'].sum(), 0)


if __name__ == '__main__':
    unittest.main()
