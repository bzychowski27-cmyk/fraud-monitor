"""Exercise the rendered dashboard and reactive controls without a browser."""
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest


class AppTests(unittest.TestCase):
    def test_dashboard_and_controls(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '500')
        self.assertEqual(len(app.dataframe), 3)
        app.slider[2].set_value(100).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[2].value, '0 (0.0%)')
        app.checkbox[0].uncheck().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe[2].value), 500)
