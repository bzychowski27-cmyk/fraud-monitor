import unittest
import pandas as pd
from monitoring import Thresholds, generate_transactions, score_transactions, summary_metrics, financial_analyses
import test_monitoring

class ExtendedTests(unittest.TestCase):
    def sample(self, amounts, minutes):
        return test_monitoring.MonitoringTests().sample(amounts, minutes)

    def test_relative_rule_uses_only_history(self):
        frame = self.sample([100]*5 + [400, 10000], list(range(7)))
        data = score_transactions(frame, Thresholds(relative_multiplier=4))
        self.assertFalse(data.iloc[4].relative_amount)
        self.assertEqual(data.iloc[5].prior_mean, 100)
        self.assertTrue(data.iloc[5].relative_amount)
        self.assertEqual(data.iloc[5].relative_points, 25)
        changed = frame.copy()
        changed.loc[6,'amount'] = 1
        pd.testing.assert_frame_equal(data.iloc[:6], score_transactions(changed).iloc[:6])
        self.assertFalse(score_transactions(frame, Thresholds(relative_multiplier=5)).iloc[5].relative_amount)

    def test_simultaneous_and_direction_baselines(self):
        frame = self.sample([100]*5 + [10000,400,100], [0,1,2,3,4,5,5,6])
        frame.loc[7,'direction'] = 'Credit'
        data = score_transactions(frame)
        self.assertEqual(data.iloc[5].prior_mean,100)
        self.assertEqual(data.iloc[6].prior_mean,100)
        self.assertEqual(data.iloc[7].history_count,0)

    def test_financial_hand_calculation(self):
        frame = self.sample([100,200,6000],[0,120,240])
        frame.loc[0,'direction']='Credit'
        data = score_transactions(frame, Thresholds(flag_score=35))
        result = summary_metrics(data)
        self.assertEqual(result['total'],6300)
        self.assertEqual(result['average'],2100)
        self.assertEqual(result['flagged_count'],1)
        self.assertAlmostEqual(result['flagged_pct'],100/3)
        self.assertEqual(result['flagged_value'],6000)
        self.assertEqual(financial_analyses(data)[0]['Net flow'].sum(),-6100)

    def test_balances_reconcile(self):
        data = generate_transactions()
        for _, group in data.groupby('account_id'):
            expected = 50000 + group.amount.where(group.direction == 'Credit',-group.amount).cumsum()
            self.assertTrue(((expected - group.account_balance).abs() < .001).all())
        self.assertEqual(data.customer_id.nunique(),30)

    def test_empty_and_missing(self):
        empty = pd.DataFrame()
        self.assertEqual(summary_metrics(empty)['average'],0)
        self.assertTrue(financial_analyses(empty)[0].empty)
        for frame in [self.sample([100],[0]).assign(account_id=None),self.sample([100],[0]).assign(customer_id=None)]:
            with self.assertRaises(ValueError):
                score_transactions(frame)
        for config in [Thresholds(relative_multiplier=1),Thresholds(min_history=0)]:
            with self.assertRaises(ValueError):
                score_transactions(self.sample([100],[0]), config)
