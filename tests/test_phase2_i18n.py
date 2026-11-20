"""Pure translation contracts; no app execution or persisted planning."""
import unittest
from dashboard.i18n import dictionary, t, localize, placeholders, diagnostic


class TranslationTests(unittest.TestCase):
    def test_legacy_summary_translation_preserves_dynamic_ids_and_numbers(self):
        import ast
        from pathlib import Path
        from dashboard.i18n import t, localize
        tree = ast.parse(Path('dashboard/scenario_planning_app.py').read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == '_display_scenario_insight')
        namespace = {'t': t, 'localize': localize}
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<display-only>', 'exec'), namespace)
        render = namespace[node.name]
        message = 'Greatest capacity pressure: 001 (+0.23 percentage points utilization versus Baseline).'
        self.assertEqual(render(message, locale='en'), message)
        translated = render(message, locale='zh-TW')
        self.assertIn('最大產能壓力', translated)
        self.assertIn('001', translated)
        self.assertIn('+0.23 百分點', translated)
        self.assertEqual(render('Performance status: 001: Healthy.', locale='zh-TW'),
                         '績效狀態：001: Healthy。')

    def test_owned_dynamic_display_labels_preserve_canonical_identifiers(self):
        for source, expected in [('Required', '必填'), ('Uploaded', '已上傳'),
                                 ('Missing', '缺少'),
                                 ('None — SELECTED is empty / N/A', '未選取 — SELECTED 為空／N/A')]:
            self.assertEqual(localize(source, locale='zh-TW'), expected)
            self.assertEqual(localize(source, locale='en'), source)
        self.assertEqual(localize('Quantity_Unit', locale='zh-TW'), 'Quantity_Unit')

    def test_display_fields_follow_current_catalog_not_import_snapshot(self):
        from unittest.mock import patch
        from dashboard import display_metadata
        with patch.dict(display_metadata.FIELDS, {}, clear=True):
            self.assertEqual(display_metadata.label('Label', 'zh-TW'), '顯示名稱')
            self.assertEqual(display_metadata.label('Definition', 'zh-TW'), '定義')
            self.assertEqual(display_metadata.label('raw_user_column', 'zh-TW'), 'raw_user_column')

    def test_dictionary_and_placeholder_parity(self):
        en = dictionary('en'); zh = dictionary('zh-TW')
        self.assertEqual(set(en), set(zh))
        for key in en:
            self.assertTrue(en[key]); self.assertTrue(zh[key])
            self.assertEqual(placeholders(en[key]), placeholders(zh[key]), key)

    def test_explicit_default_and_fallback(self):
        self.assertEqual(t('side.reference', locale='xx'), 'Reference')
        self.assertEqual(t('nonexistent.key', locale='zh-TW'), '[missing:nonexistent.key]')

    def test_missing_parameters_do_not_crash_ui(self):
        self.assertIn('missing:parameters', t('priority.label', locale='zh-TW'))

    def test_dynamic_ids_and_unknown_raw_values_unchanged(self):
        self.assertEqual(localize('001', locale='zh-TW'), '001')
        self.assertEqual(localize('Baseline', locale='zh-TW'), 'Baseline')
        self.assertIn('001', t('workflow.global', locale='zh-TW', scenario='001'))

    def test_diagnostic_keeps_original(self):
        message = 'Zero denominator; rate is N/A'
        result = diagnostic(message, locale='zh-TW')
        self.assertIn(message, result); self.assertIn('分母', result)
