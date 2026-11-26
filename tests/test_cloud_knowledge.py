"""Only reviewed documentation excerpts enter the synthetic question context."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from src.ai_copilot.cloud_knowledge import ROOT, select_business_context


class CloudKnowledgeTests(unittest.TestCase):
    def test_topic_selection_and_full_document_hash(self):
        selected = select_business_context("Which capacity bottleneck matters?")
        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0]["source"], "docs/02_Risk_Dictionary.md")
        for item in selected:
            self.assertEqual(item["sha256"], hashlib.sha256((ROOT / item["source"]).read_bytes()).hexdigest())
            self.assertLessEqual(len(item["excerpt"]), 3000)

    def test_missing_document_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                select_business_context("Service level", root=Path(temp))

    def test_symlinked_reviewed_document_is_not_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            docs = root / "docs"
            docs.mkdir()
            (docs / "02_Risk_Dictionary.md").symlink_to(root / "unapproved.txt")
            (root / "unapproved.txt").write_text("secret-sentinel")
            with self.assertRaisesRegex(ValueError, "unavailable"):
                select_business_context("Demand risk", root=root)


if __name__ == "__main__":
    unittest.main()
