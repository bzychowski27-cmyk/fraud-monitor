"""Exercise plan permissions, preserved calculations, filters, and reruns."""
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

class AppTests(unittest.TestCase):
    def app(self):
        return AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=30)

    def button(self, app, label):
        return next(item for item in app.button if item.label == label)

    def test_free_upgrade_downgrade_and_controls(self):
        app = self.app()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '250')
        self.assertEqual(len(app.get('plotly_chart')), 2)
        self.assertTrue(app.slider[0].disabled)
        self.assertFalse(app.slider[2].disabled)
        self.assertTrue(app.multiselect[0].disabled)
        self.assertTrue((app.dataframe[2].value.flagged).all())
        self.assertIn('explanation', app.dataframe[2].value.columns)
        self.button(app,'Upgrade to Premium — $20/month').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['plan'],'Premium')
        self.assertEqual(app.metric[0].value, '500')
        self.assertEqual(len(app.get('plotly_chart')),5)
        self.assertFalse(app.slider[0].disabled)
        self.assertFalse(app.multiselect[0].disabled)
        app.selectbox[0].set_value('All').run()
        self.assertEqual(len(app.dataframe[4].value),500)
        app.multiselect[0].set_value(['CU001']).run()
        self.assertTrue((app.dataframe[4].value.customer_id == 'CU001').all())
        app.slider[4].set_value(100).run()
        self.assertFalse(app.exception)
        app.selectbox[0].set_value('Flagged').run()
        self.assertTrue((app.dataframe[4].value.risk_score >= 100).all())
        self.button(app,'Switch to Free Plan').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value,'250')
        self.assertEqual(app.session_state['plan'],'Free')
        self.assertTrue(app.slider[4].disabled)
        # Free uses its standard cutoff rather than the previously selected Premium 100.
        self.assertTrue((app.dataframe[2].value.risk_score >= 35).all())
        self.button(app,'Upgrade to Premium — $20/month').click().run()
        self.assertFalse(app.exception)

    def test_free_financial_totals_and_export_gate(self):
        from monitoring import generate_transactions, score_transactions, summary_metrics
        app = self.app()
        expected = summary_metrics(score_transactions(generate_transactions().head(250)))
        self.assertEqual(app.metric[1].value, '${:,.0f}'.format(expected['total']))
        self.assertEqual(app.metric[2].value, '${:,.2f}'.format(expected['average']))
        self.assertTrue(app.get('download_button')[0].proto.disabled)
        self.button(app,'Upgrade to Premium — $20/month').click().run()
        self.assertFalse(app.get('download_button')[0].proto.disabled)
