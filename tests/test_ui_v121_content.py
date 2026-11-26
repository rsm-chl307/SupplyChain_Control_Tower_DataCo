"""Content safeguards for the bilingual business user manual."""
import re
import unittest
from pathlib import Path
from markdown_it import MarkdownIt
from dashboard.user_guide.guide_content import load_sections
from dashboard.user_guide.guide_navigation import SECTION_IDS

class ContentUsabilityTests(unittest.TestCase):
    def test_bilingual_sections_and_rendered_markdown(self):
        parser = MarkdownIt('commonmark').enable('table')
        for locale in ('en', 'zh-TW'):
            sections = load_sections(locale)
            self.assertEqual(tuple(s.section_id for s in sections), SECTION_IDS)
            html = ''
            for section in sections:
                html += parser.render(section.introduction)
                for sub in section.subsections:
                    rendered = parser.render(sub.markdown)
                    self.assertNotIn('**', rendered)
                    self.assertNotRegex(rendered, r'<p>#{2,3} ')
                    self.assertNotIn('&lt;strong', rendered)
                    html += rendered
            for tag in ('<strong>', '<table>', '<ol>', '<ul>', '<code>'):
                self.assertIn(tag, html)

    def test_no_internal_terminology_in_visible_content(self):
        for locale in ('en', 'zh-TW'):
            for section in load_sections(locale):
                text = section.title + section.introduction + ''.join(s.title+s.markdown for s in section.subsections)
                text = text.replace('run_manifest.json', '')
                self.assertNotRegex(text, r'(?i)\b(WP1|WP2|ui_locale|canonical|artifacts?|repository|manifest|frontend|backend|schema|payload|implementation|developer|legacy)\b')

    def test_model_display_labels_keep_internal_values(self):
        from dashboard.scenario_planning_app import _planning_model_label
        self.assertEqual(_planning_model_label('Legacy independent weeks','zh-TW'),'單週獨立分析')
        self.assertEqual(_planning_model_label('Legacy independent weeks','en'),'Independent-week analysis')
        self.assertEqual(_planning_model_label('Sequential workload','zh-TW'),'連續週次規劃')
