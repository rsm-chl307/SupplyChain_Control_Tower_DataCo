"""Streamlit acceptance checks for uploaded CSV readiness and planning runs."""

from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
USER_EXAMPLE = ROOT / "examples" / "planning" / "user_data"
APP = ROOT / "dashboard" / "scenario_planning_app.py"


class DashboardUploadWorkflowTests(unittest.TestCase):
    def app_with_user_example(self):
        app = AppTest.from_file(str(APP), default_timeout=60).run()
        filenames = {
            "products": "products.csv",
            "plants": "plants.csv",
            "product_plant_mapping": "mapping.csv",
            "demand": "demand.csv",
            "weekly_capacity": "capacity.csv",
            "workload_factors": "factors.csv",
            "initial_inventory": "initial_inventory.csv",
            "opening_backlog": "opening_backlog.csv",
            "external_receipts": "receipts.csv",
        }
        uploaders = app.get("file_uploader")
        for dataset, filename in filenames.items():
            uploader = next(item for item in uploaders if item.key == f"upload_widget_{dataset}")
            uploader.set_value((filename, (USER_EXAMPLE / filename).read_bytes(), "text/csv"))
        app.run()
        app.selectbox(key="eligibility_0_RELEASED").set_value("Qualified")
        return app

    def test_uploads_mappings_and_scenario_settings_survive_model_switch(self):
        app = self.app_with_user_example()
        app.number_input(key="upload_surge_pct").set_value(17.0).run()

        app.sidebar.selectbox[0].set_value("Legacy independent weeks").run()
        app.sidebar.selectbox[0].set_value("Sequential workload").run()

        self.assertFalse(app.exception)
        self.assertTrue(any("Retained upload: products.csv" in item.value for item in app.caption))
        self.assertEqual(app.number_input(key="upload_surge_pct").value, 17.0)
        self.assertEqual(app.selectbox(key="map_products_Product_ID_products.csv").value, "sku")
        self.assertEqual(app.selectbox(key="eligibility_0_RELEASED").value, "Qualified")

        app.button(key="FormSubmitter:user_csv_planning_form-Validate inputs").click().run()
        self.assertTrue(any("Data readiness: READY" in item.value for item in app.success))

    def test_uploaded_user_data_validates_runs_and_loads_published_outputs(self):
        app = self.app_with_user_example()
        app.button(key="FormSubmitter:user_csv_planning_form-Validate and run planning").click().run()

        self.assertFalse(app.exception)
        self.assertTrue(any("Data readiness: READY" in item.value for item in app.success))
        self.assertTrue(any("completed and published" in item.value for item in app.success))
        self.assertTrue(any("Active results:" in item.value for item in app.caption))
        self.assertIn("Download KPI results", [item.label for item in app.get("download_button")])
        self.assertIn("Download allocation detail", [item.label for item in app.get("download_button")])
        self.assertIn("Planning Risk Summary", [item.label for item in app.get("tab")])
        self.assertTrue(any("Product Risk" in item.label for item in app.get("tab")))

    def test_duplicate_column_mapping_is_reported_and_blocks_execution(self):
        app = self.app_with_user_example()
        app.selectbox(key="map_products_Product_ID_products.csv").set_value("title")
        app.button(key="FormSubmitter:user_csv_planning_form-Validate inputs").click().run()

        self.assertFalse(app.exception)
        self.assertTrue(any("BLOCKED" in item.value for item in app.error))
        self.assertTrue(any("mapped more than once" in item.value for item in app.markdown))
        self.assertFalse(any("Planning run completed" in item.value for item in app.success))


if __name__ == "__main__":
    unittest.main()
