"""Pure presentation invariants: no planning or filesystem fixtures."""
import unittest
from dashboard.display_metadata import METRICS, label, help_text, format_value


class DisplayTests(unittest.TestCase):
    def test_rates_and_percentage_points_are_distinct(self):
        self.assertEqual(format_value(.41, 'Horizon_Service_Level'), '41.0%')
        self.assertEqual(format_value(-6.5, 'Delta', delta_unit='percentage points'), '-6.50 pp')

    def test_zero_is_not_missing(self):
        self.assertEqual(format_value(0, 'Lost_Sales'), '0.00')
        self.assertEqual(format_value(float('nan'), 'Lost_Sales'), 'N/A')

    def test_all_metric_metadata_has_both_languages_and_basis(self):
        for key in METRICS:
            self.assertTrue(label(key, 'en')); self.assertTrue(label(key, 'zh-TW'))
            self.assertTrue(help_text(key, 'en')); self.assertTrue(help_text(key, 'zh-TW'))

    def test_legacy_and_horizon_service_are_not_conflated(self):
        self.assertIn('Legacy', help_text('Service_Level'))
        self.assertIn('opening-origin', help_text('Horizon_Service_Level'))

    def test_unknown_identifier_remains_accessible(self):
        self.assertEqual(label('unrecognized_machine_id', 'zh-TW'), 'unrecognized_machine_id')
