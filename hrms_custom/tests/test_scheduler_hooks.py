import importlib
import frappe
from frappe.tests.classes.integration_test_case import IntegrationTestCase
import hrms_custom.hooks as hooks


class TestSchedulerHooks(IntegrationTestCase):
    """Integration tests for scheduler_events in hrms_custom/hooks.py."""

    PROCESS_CURRENT_PERIOD = (
        "hrms_custom.hrms_custom.utils.late_lop_processor.process_current_period"
    )
    SEND_DOCUMENT_ALERTS = (
        "hrms_custom.hrms_custom.utils.document_alerts.send_document_alerts"
    )
    PROCESS_LATE_DEDUCTIONS = (
        "hrms_custom.hrms_custom.utils.late_lop_processor.process_late_deductions"
    )

    def setUp(self):
        super().setUp()
        importlib.reload(hooks)

    def _get_all_scheduler_entries(self):
        """Walk scheduler_events recursively (lists and nested dicts) and return all dotted paths."""
        events = getattr(hooks, "scheduler_events", {})
        entries = []

        def _walk(val):
            if isinstance(val, str):
                entries.append(val)
            elif isinstance(val, list):
                for item in val:
                    _walk(item)
            elif isinstance(val, dict):
                for subval in val.values():
                    _walk(subval)

        _walk(events)
        return entries

    def test_a_process_current_period_not_in_scheduler_events(self):
        """Test a: process_current_period appears in no list anywhere in scheduler_events."""
        all_entries = self._get_all_scheduler_entries()
        self.assertNotIn(
            self.PROCESS_CURRENT_PERIOD,
            all_entries,
            f"'{self.PROCESS_CURRENT_PERIOD}' must not appear anywhere in scheduler_events!",
        )

    def test_b_send_document_alerts_in_daily(self):
        """Test b: send_document_alerts is still in scheduler_events['daily']."""
        events = getattr(hooks, "scheduler_events", {})
        daily = events.get("daily", [])
        self.assertIn(
            self.SEND_DOCUMENT_ALERTS,
            daily,
            f"'{self.SEND_DOCUMENT_ALERTS}' must be in scheduler_events['daily']",
        )

    def test_c_process_late_deductions_in_monthly(self):
        """Test c: process_late_deductions is still in scheduler_events['monthly']."""
        events = getattr(hooks, "scheduler_events", {})
        monthly = events.get("monthly", [])
        self.assertIn(
            self.PROCESS_LATE_DEDUCTIONS,
            monthly,
            f"'{self.PROCESS_LATE_DEDUCTIONS}' must be in scheduler_events['monthly']",
        )

    def test_d_every_scheduler_entry_resolves(self):
        """Test d: every dotted path found in scheduler_events resolves with frappe.get_attr."""
        all_entries = self._get_all_scheduler_entries()
        self.assertTrue(len(all_entries) > 0, "No entries found in scheduler_events")
        for dotted_path in all_entries:
            try:
                fn = frappe.get_attr(dotted_path)
                self.assertTrue(
                    callable(fn),
                    f"Resolved object for '{dotted_path}' is not callable: {fn}",
                )
            except Exception as e:
                self.fail(
                    f"Could not resolve scheduler entry '{dotted_path}' with frappe.get_attr: {e}"
                )
