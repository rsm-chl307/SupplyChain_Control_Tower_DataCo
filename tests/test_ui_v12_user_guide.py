"""Focused V1.2 guide/content/UI checks; planning functions are guarded."""
from datetime import date
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from dashboard.user_guide.guide_content import GuideContentError, load_sections
from dashboard.user_guide.guide_navigation import SECTION_IDS, navigation


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "dashboard" / "scenario_planning_app.py"
DEMO = ROOT / "examples" / "planning" / "synthetic_demo"


class UserGuideContentTests(unittest.TestCase):
    def test_all_stable_sections_and_subsections_exist_in_both_locales(self):
        for locale in ("en", "zh-TW"):
            sections = load_sections(locale)
            self.assertEqual(tuple(section.section_id for section in sections), SECTION_IDS)
            self.assertEqual(len({section.section_id for section in sections}), len(SECTION_IDS))
            self.assertEqual(tuple(section_id for section_id, _ in navigation(locale)), SECTION_IDS)
            for section in sections:
                self.assertTrue(section.title.strip())
                self.assertTrue(section.introduction.strip())
                self.assertTrue(section.subsections)
                self.assertTrue(all(subsection.title.strip() and subsection.markdown.strip()
                                    for subsection in section.subsections))

    def test_missing_locale_fails_explicitly(self):
        with self.assertRaises(GuideContentError):
            load_sections("fr")


class UserGuideAppTests(unittest.TestCase):
    def setUp(self):
        self.guards = []
        for name in ("run_csv_planning", "run_sequential_planning", "run_planning"):
            guard = patch(f"src.run_planning.{name}", side_effect=AssertionError("Guide UI must not plan"))
            self.guards.append(guard.start())
            self.addCleanup(guard.stop)
        from streamlit.testing.v1 import AppTest
        self.app = AppTest.from_file(str(APP), default_timeout=60).run()
        self.assertFalse(self.app.exception)

    def tearDown(self):
        self.assertTrue(all(guard.call_count == 0 for guard in self.guards))

    def test_guide_toc_locale_and_close_keep_active_section(self):
        self.app.button(key="ui_user_guide_toggle").click().run()
        self.assertTrue(self.app.session_state["ui_user_guide_open"])
        for section_id in SECTION_IDS:
            self.app.button(key=f"ui_guide_nav_{section_id}").click().run()
            self.assertEqual(self.app.session_state["ui_guide_section"], section_id)
            self.assertTrue(any("ui-v12-guide-top" in str(item.value) for item in self.app.markdown))
        self.app.selectbox(key="ui_language_request").set_value("zh-TW").run()
        self.assertEqual(self.app.session_state["ui_guide_section"], SECTION_IDS[-1])
        self.assertTrue(self.app.session_state["ui_user_guide_open"])
        self.assertTrue(any(expander.label for expander in self.app.expander))
        self.app.button(key="ui_user_guide_close").click().run()
        self.assertFalse(self.app.session_state["ui_user_guide_open"])

    def test_guide_actions_keep_csv_uploads_and_pending_form_values(self):
        uploads = {}
        for dataset, filename in {
            "products": "products.csv",
            "plants": "plants.csv",
            "product_plant_mapping": "product_plant_mapping.csv",
            "demand": "demand.csv",
        }.items():
            uploads[dataset] = (filename, (DEMO / filename).read_bytes())
        self.app.session_state["_user_csv_upload_data"] = uploads
        self.app.run()
        self.app.number_input(key="upload_surge_pct").set_value(18.0)
        self.app.date_input(key=next(w.key for w in self.app.date_input if w.key.startswith("upload_start_week_"))).set_value(date(2026, 12, 6))
        self.app.button(key="ui_user_guide_toggle").click().run()
        self.app.button(key="ui_guide_nav_planning").click().run()
        self.app.selectbox(key="ui_language_request").set_value("zh-TW").run()
        self.assertEqual(self.app.number_input(key="upload_surge_pct").value, 18.0)
        self.assertEqual(self.app.date_input(key=next(w.key for w in self.app.date_input if w.key.startswith("upload_start_week_"))).value, date(2026, 12, 6))
        for dataset, (_, content) in uploads.items():
            self.assertEqual(self.app.session_state["_user_csv_upload_data"][dataset][1], content)
        self.app.button(key="ui_guide_nav_wp1").click().run()
        self.app.button(key="ui_user_guide_close").click().run()
        self.assertEqual(self.app.number_input(key="upload_surge_pct").value, 18.0)

    def test_order_line_completeness_control_is_visible_with_status_values(self):
        self.app.session_state["_user_csv_upload_data"] = {
            dataset: (filename, (DEMO / filename).read_bytes())
            for dataset, filename in {
                "products": "products.csv",
                "plants": "plants.csv",
                "product_plant_mapping": "product_plant_mapping.csv",
                "demand": "demand.csv",
            }.items()
        }
        self.app.run()
        self.app.radio(key="upload_demand_format").set_value("ORDER_LINES").run()
        self.assertIsNotNone(self.app.checkbox(key="upload_ui_user_csv_upload_workflow_checkbox_45"))
        self.assertTrue(any(widget.key.startswith("eligibility_") for widget in self.app.selectbox))

    def test_legacy_run_is_disabled_for_existing_output_folder(self):
        self.app.selectbox(key="ui_planning_model").set_value("Legacy independent weeks").run()
        run_button = self.app.button(key="ui_run_controls_button_7")
        self.assertTrue(run_button.disabled)
        self.assertTrue(any("output folder" in str(item.value).lower()
                            for item in self.app.warning))


class PlanningCopyTests(unittest.TestCase):
    def test_ui_capacity_calibration_uses_adapter_configuration_key(self):
        from dashboard.scenario_planning_app import _build_upload_config

        present = object()
        uploads = {
            "products": present, "plants": present, "product_plant_mapping": present,
            "demand": present, "priorities": None, "weekly_capacity": None,
            "workload_factors": present, "initial_inventory": present,
            "opening_backlog": present, "external_receipts": present,
        }
        mappings = {
            "products": {"Product_ID": "Product_ID", "Product_Name": "Product_Name",
                         "Quantity_Unit": "Quantity_Unit", "Planning_Priority": "Planning_Priority"},
            "plants": {"Plant_ID": "Plant_ID"},
            "product_plant_mapping": {"Product_ID": "Product_ID", "Plant_ID": "Plant_ID"},
            "demand": {"Product_ID": "Product_ID", "Demand_Qty": "Demand_Qty", "Week": "Week"},
            "workload_factors": {"Product_ID": "Product_ID", "Workload_Factor": "Workload_Factor", "Workload_Unit": "Workload_Unit"},
            "initial_inventory": {"Plant_ID": "Plant_ID", "Product_ID": "Product_ID", "Beginning_Inventory": "Beginning_Inventory"},
            "opening_backlog": {"Plant_ID": "Plant_ID", "Product_ID": "Product_ID", "Beginning_Backlog": "Beginning_Backlog"},
            "external_receipts": {"Receipt_ID": "Receipt_ID", "Plant_ID": "Plant_ID", "Product_ID": "Product_ID", "Week": "Week", "External_Receipts_Qty": "External_Receipts_Qty"},
        }
        assumptions = {
            "quantity_unit": "", "use_priority": False, "planning_priority": 2,
            "use_factor": False, "uniform_factor": 1.0, "workload_unit": "EqWU",
            "zero_inventory": False, "zero_backlog": False, "no_receipts": False,
            "capacity_calibration": True, "target_utilization": 0.75,
        }
        config, errors = _build_upload_config(
            uploads=uploads, mappings=mappings, demand_format="WEEKLY", status_eligibility={},
            already_qualified=True, source_is_complete=False, quantity_step=0,
            assumption_version="test", start_week=date(2026, 12, 6), end_week=date(2026, 12, 6),
            interpretation="USER_PROVIDED_PLAN", surge_pct=10, disruption_pct=20,
            disrupted_plants=[], backlog_policy="CARRY_FORWARD", assumptions=assumptions,
        )
        self.assertEqual(errors, [])
        self.assertEqual(config["capacity_calibration"]["target_utilization"], 0.75)
        self.assertNotIn("capacity_calibration", config["assumptions"])

    def test_ui_calibration_config_passes_existing_synthetic_adapter(self):
        from src.csv_planning_inputs import load_csv_planning_inputs

        config = json.loads((DEMO / "config.json").read_text(encoding="utf-8"))
        config["files"].pop("weekly_capacity")
        config["capacity_calibration"] = {
            "start_week": config["planning_start_week"],
            "end_week": config["planning_end_week"],
            "target_utilization": 0.75,
            "capacity_version": "ui-synthetic-calibration-v1",
        }
        result = load_csv_planning_inputs(config, DEMO)
        self.assertEqual(result.report["Status"], "READY")
        self.assertEqual(set(result.capacity_calendar["Provenance_Type"]), {"SYNTHETIC_DEMAND_CALIBRATED"})
        self.assertTrue(any(item.get("Name") == "capacity_calibration" for item in result.report["Assumptions"]))


if __name__ == "__main__":
    unittest.main()
