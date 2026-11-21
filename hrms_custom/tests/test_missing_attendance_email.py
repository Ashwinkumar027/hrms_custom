# Copyright (c) 2026, ASHWIN and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta, date, time
from unittest.mock import patch, MagicMock
import frappe
from frappe.tests.classes.integration_test_case import IntegrationTestCase
from frappe.utils import getdate, nowdate, add_days, formatdate

import hrms_custom.hrms_custom.utils.missing_attendance_email as mae

TEST_EMPLOYEE = "HR-EMP-00002"
TEST_SHIFT = "Corona shift"


class TestMissingAttendanceEmail(IntegrationTestCase):
    """
    Integration tests for Group 4: missing attendance reminder emails.
    Covers R1 (deferral for unprocessed shifts), R2 (lookback), R3 (dedupe per employee+date),
    R4 (Absent wording), and R5 (forensic log).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")

        # Record original shift settings to restore in tearDownClass
        cls.orig_corona = frappe.db.get_value(
            "Shift Type",
            TEST_SHIFT,
            ["enable_auto_attendance", "last_sync_of_checkin", "allow_check_out_after_shift_end_time", "start_time", "end_time"],
            as_dict=True,
        )

        cls.orig_hr_enable = frappe.db.get_single_value("HR Settings", "custom_enable_missing_attendance_email")
        frappe.db.set_single_value("HR Settings", "custom_enable_missing_attendance_email", 1)

        # Ensure employee has assignment to TEST_SHIFT
        cls.sa_name = frappe.db.get_value(
            "Shift Assignment",
            {"employee": TEST_EMPLOYEE, "docstatus": 1, "status": "Active"},
            "name",
        )
        if cls.sa_name:
            cls.orig_sa_shift = frappe.db.get_value("Shift Assignment", cls.sa_name, "shift_type")
            frappe.db.set_value("Shift Assignment", cls.sa_name, "shift_type", TEST_SHIFT, update_modified=False)
        else:
            cls.orig_sa_shift = None

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        if cls.orig_corona:
            frappe.db.set_value(
                "Shift Type",
                TEST_SHIFT,
                {
                    "enable_auto_attendance": cls.orig_corona.enable_auto_attendance,
                    "last_sync_of_checkin": cls.orig_corona.last_sync_of_checkin,
                    "allow_check_out_after_shift_end_time": cls.orig_corona.allow_check_out_after_shift_end_time,
                },
                update_modified=False,
            )
        if cls.sa_name and cls.orig_sa_shift:
            frappe.db.set_value("Shift Assignment", cls.sa_name, "shift_type", cls.orig_sa_shift, update_modified=False)
        frappe.db.set_single_value("HR Settings", "custom_enable_missing_attendance_email", cls.orig_hr_enable)

    def setUp(self):
        super().setUp()
        frappe.set_user("Administrator")
        self._cleanup()

    def tearDown(self):
        self._cleanup()
        super().tearDown()

    def _cleanup(self):
        # Remove any attendance, checkins, or email queues created for TEST_EMPLOYEE
        frappe.db.delete("Attendance", {"employee": TEST_EMPLOYEE})
        frappe.db.delete("Employee Checkin", {"employee": TEST_EMPLOYEE})
        frappe.db.delete("Email Queue", {"reference_doctype": "Employee", "reference_name": TEST_EMPLOYEE})

    # T1: Shift not yet processed (enable_auto_attendance=1, last_sync before actual_end): no email queued for yesterday, "deferred" counted.
    def test_01_shift_not_yet_processed_is_deferred(self):
        att_date = "2026-10-12"
        # Corona shift ends at 23:59:00 + 360m = 05:59:00 next day
        # Set last_sync_of_checkin to 02:00:00 (before 05:59:00)
        frappe.db.set_value(
            "Shift Type",
            TEST_SHIFT,
            {
                "enable_auto_attendance": 1,
                "last_sync_of_checkin": "2026-10-13 02:00:00",
            },
            update_modified=False,
        )

        with patch("hrms_custom.hrms_custom.utils.missing_attendance_email.today", return_value="2026-10-13"):
            res = mae.send_missing_attendance_emails(attendance_date=att_date, dry_run=True, employee=TEST_EMPLOYEE)

        self.assertIn("deferred", res)
        self.assertEqual(res["deferred"], 1)
        self.assertEqual(res["queued"], 0)
        self.assertEqual(len(res["employees"]), 0)

    # T2: Shift processed (last_sync after actual_end): email queued when no Attendance row exists.
    def test_02_shift_processed_queues_email_when_no_attendance(self):
        att_date = "2026-10-12"
        # Set last_sync_of_checkin to 06:30:00 (after 05:59:00 actual_end)
        frappe.db.set_value(
            "Shift Type",
            TEST_SHIFT,
            {
                "enable_auto_attendance": 1,
                "last_sync_of_checkin": "2026-10-13 06:30:00",
            },
            update_modified=False,
        )

        with patch("hrms_custom.hrms_custom.utils.missing_attendance_email.today", return_value="2026-10-13"):
            res = mae.send_missing_attendance_emails(attendance_date=att_date, dry_run=True, employee=TEST_EMPLOYEE)

        self.assertEqual(res.get("deferred", 0), 0)
        self.assertEqual(res["queued"], 1)
        self.assertEqual(len(res["employees"]), 1)
        self.assertEqual(res["employees"][0]["employee"], TEST_EMPLOYEE)

    # T3: enable_auto_attendance=0: never deferred.
    def test_03_enable_auto_attendance_zero_never_deferred(self):
        att_date = "2026-10-12"
        frappe.db.set_value(
            "Shift Type",
            TEST_SHIFT,
            {
                "enable_auto_attendance": 0,
                "last_sync_of_checkin": None,
            },
            update_modified=False,
        )

        with patch("hrms_custom.hrms_custom.utils.missing_attendance_email.today", return_value="2026-10-13"):
            res = mae.send_missing_attendance_emails(attendance_date=att_date, dry_run=True, employee=TEST_EMPLOYEE)

        self.assertEqual(res.get("deferred", 0), 0)
        self.assertEqual(res["queued"], 1)

    # T4: Shift end after midnight (end_time <= start_time) computes actual_end on the next day.
    def test_04_cross_midnight_shift_actual_end_computation(self):
        helper = getattr(mae, "compute_actual_shift_end", None)
        self.assertIsNotNone(helper, "compute_actual_shift_end helper must exist in missing_attendance_email")

        # Night shift: 20:00 to 04:00 (+60 min checkout window)
        actual_end = helper("2026-10-12", "20:00:00", "04:00:00", 60)
        self.assertEqual(actual_end, datetime(2026, 10, 13, 5, 0))

        # Day shift: 09:00 to 18:00 (+30 min checkout window)
        actual_end_day = helper("2026-10-12", "09:00:00", "18:00:00", 30)
        self.assertEqual(actual_end_day, datetime(2026, 10, 12, 18, 30))

        # 23:59 shift with 360 min window (Corona shift):
        actual_end_corona = helper("2026-10-12", "09:00:00", "23:59:00", 360)
        self.assertEqual(actual_end_corona, datetime(2026, 10, 13, 5, 59))

    # T5: Lookback: deferred employee gets the email on the next day's run for older date; dedupe prevents duplicate email.
    def test_05_lookback_processing_and_dedup(self):
        # On 2026-10-13 at 02:30, 2026-10-12 shift is not yet synced (last_sync=None)
        frappe.db.set_value(
            "Shift Type",
            TEST_SHIFT,
            {
                "enable_auto_attendance": 1,
                "last_sync_of_checkin": None,
            },
            update_modified=False,
        )

        with patch("hrms_custom.hrms_custom.utils.missing_attendance_email.today", return_value="2026-10-13"):
            res_day1 = mae.send_missing_attendance_emails_for_yesterday()

        self.assertIsInstance(res_day1, dict)
        self.assertIn("yesterday", res_day1)
        self.assertIn("day_before", res_day1)
        # Yesterday was 2026-10-12 and was deferred
        emp_yesterday = [e["employee"] for e in res_day1["yesterday"].get("employees", [])]
        self.assertNotIn(TEST_EMPLOYEE, emp_yesterday)
        self.assertGreaterEqual(res_day1["yesterday"].get("deferred", 0), 1)

        # On 2026-10-14, last_sync_of_checkin has progressed past 2026-10-12
        frappe.db.set_value(
            "Shift Type",
            TEST_SHIFT,
            {"last_sync_of_checkin": "2026-10-13 08:00:00"},
            update_modified=False,
        )

        with patch("hrms_custom.hrms_custom.utils.missing_attendance_email.today", return_value="2026-10-14"), \
             patch("frappe.sendmail") as mock_send:
            res_day2 = mae.send_missing_attendance_emails_for_yesterday()

            # In res_day2, day_before is 2026-10-12. Because it was deferred on Day 1, it is processed now!
            emp_day_before = [e["employee"] for e in res_day2["day_before"].get("employees", [])]
            self.assertIn(TEST_EMPLOYEE, emp_day_before)

            # Insert an Email Queue record representing this sent email
            emp_doc = frappe.get_doc("Employee", TEST_EMPLOYEE)
            subj = mae._get_subject(emp_doc, "2026-10-12")
            eq = frappe.get_doc({
                "doctype": "Email Queue",
                "reference_doctype": "Employee",
                "reference_name": TEST_EMPLOYEE,
                "message": f"Subject: {subj}\n\nBody test",
                "status": "Not Sent",
            })
            eq.insert(ignore_permissions=True)

            # Run again on 2026-10-14: must be deduped for 2026-10-12!
            res_day2_repeat = mae.send_missing_attendance_emails_for_yesterday()
            emp_repeat = [e["employee"] for e in res_day2_repeat["day_before"].get("employees", [])]
            self.assertNotIn(TEST_EMPLOYEE, emp_repeat)

    # T6: Dedupe ignores an unrelated Email Queue row that references the same Employee today.
    def test_06_dedupe_ignores_unrelated_email_queue_row_today(self):
        att_date = "2026-10-12"
        frappe.db.set_value(
            "Shift Type",
            TEST_SHIFT,
            {
                "enable_auto_attendance": 1,
                "last_sync_of_checkin": "2026-10-13 08:00:00",
            },
            update_modified=False,
        )

        # Insert unrelated Email Queue row referencing TEST_EMPLOYEE created today
        eq = frappe.get_doc({
            "doctype": "Email Queue",
            "reference_doctype": "Employee",
            "reference_name": TEST_EMPLOYEE,
            "message": "Subject: Password Reset Request\n\nYour OTP is 123456",
            "status": "Not Sent",
        })
        eq.insert(ignore_permissions=True)

        with patch("hrms_custom.hrms_custom.utils.missing_attendance_email.today", return_value="2026-10-13"):
            res = mae.send_missing_attendance_emails(attendance_date=att_date, dry_run=True, employee=TEST_EMPLOYEE)

        # Unrelated email queue row must NOT cause this reminder to be skipped
        self.assertEqual(res["queued"], 1)
        self.assertEqual(len(res["employees"]), 1)

    # T7: Dedupe sees an existing reminder email for the same date even when it was queued on an earlier day.
    def test_07_dedupe_sees_existing_reminder_queued_on_earlier_day(self):
        att_date = "2026-10-12"
        frappe.db.set_value(
            "Shift Type",
            TEST_SHIFT,
            {
                "enable_auto_attendance": 1,
                "last_sync_of_checkin": "2026-10-13 08:00:00",
            },
            update_modified=False,
        )

        emp_doc = frappe.get_doc("Employee", TEST_EMPLOYEE)
        subj = mae._get_subject(emp_doc, att_date)

        # Insert Email Queue record created earlier with reminder subject in message
        eq = frappe.get_doc({
            "doctype": "Email Queue",
            "reference_doctype": "Employee",
            "reference_name": TEST_EMPLOYEE,
            "message": f"Subject: {subj}\n\nDear Local Test,\nNo attendance record was found",
            "status": "Sent",
        })
        eq.insert(ignore_permissions=True)

        # Set creation to 3 days ago in database
        frappe.db.set_value("Email Queue", eq.name, "creation", "2026-10-10 02:30:00", update_modified=False)

        with patch("hrms_custom.hrms_custom.utils.missing_attendance_email.today", return_value="2026-10-13"):
            res = mae.send_missing_attendance_emails(attendance_date=att_date, dry_run=True, employee=TEST_EMPLOYEE)

        # Because reminder for 2026-10-12 already exists, it must be skipped!
        self.assertEqual(res["queued"], 0)
        self.assertEqual(res["skipped"], 1)

    # T8: Employee with Absent row gets "marked Absent"; employee with IN and no real OUT keeps "no checkout"; employee with nothing keeps "No attendance record".
    def test_08_wording_variations(self):
        att_date = "2026-10-12"
        formatted_date = formatdate(att_date)
        emp_doc = frappe.get_doc("Employee", TEST_EMPLOYEE)
        recipient = mae._get_employee_email(emp_doc)
        subj = mae._get_subject(emp_doc, att_date)

        # Case A: Marked Absent row exists in tabAttendance
        att = frappe.get_doc({
            "doctype": "Attendance",
            "employee": TEST_EMPLOYEE,
            "attendance_date": att_date,
            "status": "Absent",
            "docstatus": 1,
        })
        att.insert(ignore_permissions=True, ignore_mandatory=True)

        with patch("frappe.sendmail") as mock_send:
            mae._send_missing_attendance_email(emp_doc, recipient, att_date, subj)
            self.assertTrue(mock_send.called)
            msg = mock_send.call_args[1].get("message", "")
            self.assertIn("marked Absent", msg)
            self.assertIn(f"Your attendance for <b>{formatted_date}</b> is marked Absent.", msg)

        frappe.db.delete("Attendance", {"name": att.name})

        # Case B: IN checkin without real OUT
        ck = frappe.get_doc({
            "doctype": "Employee Checkin",
            "employee": TEST_EMPLOYEE,
            "time": f"{att_date} 09:15:00",
            "log_type": "IN",
            "custom_auto_closed": 0,
        })
        ck.insert(ignore_permissions=True, ignore_mandatory=True)

        with patch("frappe.sendmail") as mock_send:
            mae._send_missing_attendance_email(emp_doc, recipient, att_date, subj)
            self.assertTrue(mock_send.called)
            msg = mock_send.call_args[1].get("message", "")
            self.assertIn("no checkout was recorded", msg)

        frappe.db.delete("Employee Checkin", {"name": ck.name})

        # Case C: No checkins and no attendance
        with patch("frappe.sendmail") as mock_send:
            mae._send_missing_attendance_email(emp_doc, recipient, att_date, subj)
            self.assertTrue(mock_send.called)
            msg = mock_send.call_args[1].get("message", "")
            self.assertIn(f"No attendance record was found for <b>{formatted_date}</b>.", msg)

    # T9: Employee with a submitted Present row is skipped (guards against regression).
    def test_09_submitted_present_row_is_skipped(self):
        att_date = "2026-10-12"
        frappe.db.set_value(
            "Shift Type",
            TEST_SHIFT,
            {
                "enable_auto_attendance": 1,
                "last_sync_of_checkin": "2026-10-13 08:00:00",
            },
            update_modified=False,
        )

        att = frappe.get_doc({
            "doctype": "Attendance",
            "employee": TEST_EMPLOYEE,
            "attendance_date": att_date,
            "status": "Present",
            "docstatus": 1,
        })
        att.insert(ignore_permissions=True, ignore_mandatory=True)

        with patch("hrms_custom.hrms_custom.utils.missing_attendance_email.today", return_value="2026-10-13"):
            res = mae.send_missing_attendance_emails(attendance_date=att_date, dry_run=True, employee=TEST_EMPLOYEE)

        self.assertEqual(res["queued"], 0)
        self.assertEqual(res["skipped"], 1)

    # T10: The log line from R5 is produced (patch frappe.logger and assert on the call).
    def test_10_forensic_log_produced(self):
        att_date = "2026-10-12"
        frappe.db.set_value(
            "Shift Type",
            TEST_SHIFT,
            {
                "enable_auto_attendance": 1,
                "last_sync_of_checkin": "2026-10-13 08:00:00",
            },
            update_modified=False,
        )

        mock_logger = MagicMock()
        with patch("frappe.logger", return_value=mock_logger), \
             patch("frappe.sendmail"), \
             patch("hrms_custom.hrms_custom.utils.missing_attendance_email.today", return_value="2026-10-13"):
            res = mae.send_missing_attendance_emails(attendance_date=att_date, dry_run=False, employee=TEST_EMPLOYEE)

        self.assertEqual(res["queued"], 1)
        # Check that mock_logger.info was called with forensic details
        info_calls = [c[0][0] for c in mock_logger.info.call_args_list if c[0]]
        forensic_calls = [msg for msg in info_calls if TEST_EMPLOYEE in msg and att_date in msg and "attendance_rows" in msg]
        self.assertGreaterEqual(len(forensic_calls), 1, "R5 forensic log must be called with employee, date, and attendance_rows")
