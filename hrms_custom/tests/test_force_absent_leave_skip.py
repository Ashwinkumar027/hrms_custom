from datetime import datetime, timedelta
import frappe
from frappe.tests.classes.integration_test_case import IntegrationTestCase
from frappe.utils import nowdate, add_to_date, get_datetime

from hrms_custom.hrms_custom.utils.attendance_request_guard import FULL_DAY_REASONS
import hrms_custom.hrms_custom.utils.force_absent_missing_checkout as force_absent_missing_checkout

TEST_COMPANY = "_Test Limit Company"
EMP_LEAVE_USER = "test_g3_leave_emp@example.com"


class TestForceAbsentLeaveSkip(IntegrationTestCase):
    """
    Unit/Integration tests for Issue 6: force_absent_missing_checkout skipping rows
    covered by an approved Leave Application.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")

        if not frappe.db.exists("Company", TEST_COMPANY):
            frappe.get_doc({
                "doctype": "Company",
                "company_name": TEST_COMPANY,
                "abbr": "_TLC2",
                "default_currency": "INR",
                "country": "India",
            }).insert(ignore_permissions=True)

        if not frappe.db.exists("User", EMP_LEAVE_USER):
            u = frappe.get_doc({
                "doctype": "User",
                "email": EMP_LEAVE_USER,
                "first_name": "LeaveEmp",
                "enabled": 1,
                "user_type": "System User",
            })
            u.insert(ignore_permissions=True)
            u.add_roles("Employee", "Employee Self Service")

        cls.emp_leave = cls._create_employee("EMP-G3-LEAVE-001", "Leave", "Employee", EMP_LEAVE_USER)

    @classmethod
    def _create_employee(cls, emp_id, first_name, last_name, user_id):
        existing = frappe.db.get_value("Employee", {"user_id": user_id}, "name")
        if existing:
            return existing
        emp = frappe.get_doc({
            "doctype": "Employee",
            "employee": emp_id,
            "first_name": first_name,
            "last_name": last_name,
            "company": TEST_COMPANY,
            "status": "Active",
            "date_of_joining": "2026-01-01",
            "date_of_birth": "1990-01-01",
            "gender": "Female",
            "employee_number": emp_id,
            "custom_roles_responsibilities": "Test Roles",
            "ctc": 500000,
            "user_id": user_id,
        }).insert(ignore_permissions=True, ignore_mandatory=True)
        return emp.name

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        cls._cleanup_all()
        if cls.emp_leave and frappe.db.exists("Employee", cls.emp_leave):
            frappe.db.delete("Employee", cls.emp_leave)
        if frappe.db.exists("User", EMP_LEAVE_USER):
            frappe.db.delete("User", EMP_LEAVE_USER)
        frappe.db.commit()

    @classmethod
    def _cleanup_all(cls):
        if not hasattr(cls, "emp_leave") or not cls.emp_leave:
            return
        # Cancel and delete attendance
        for att in frappe.get_all("Attendance", filters={"employee": cls.emp_leave}, pluck="name"):
            try:
                doc = frappe.get_doc("Attendance", att)
                if doc.docstatus == 1:
                    doc.cancel()
                doc.delete(force=True)
            except Exception:
                pass
        frappe.db.delete("Attendance", {"employee": cls.emp_leave})
        frappe.db.delete("Employee Checkin", {"employee": cls.emp_leave})
        frappe.db.delete("Leave Application", {"employee": cls.emp_leave})
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        self._cleanup_all()

    def tearDown(self):
        frappe.set_user("Administrator")
        self._cleanup_all()

    def _create_leave_application(self, from_date, to_date, status="Approved", docstatus=1):
        la = frappe.new_doc("Leave Application")
        la.employee = self.emp_leave
        la.leave_type = "Casual Leave"
        la.from_date = from_date
        la.to_date = to_date
        la.company = TEST_COMPANY
        la.flags.ignore_permissions = True
        la.flags.ignore_validate = True
        la.flags.ignore_mandatory = True
        la.insert()
        frappe.db.set_value(
            "Leave Application",
            la.name,
            {"docstatus": docstatus, "status": status},
            update_modified=False,
        )
        la.reload()
        return la

    def _create_attendance_with_autoclosed_out(self, attendance_date, leave_application=None):
        att = frappe.new_doc("Attendance")
        att.employee = self.emp_leave
        att.attendance_date = attendance_date
        att.status = "Present"
        att.company = TEST_COMPANY
        if leave_application:
            att.leave_application = leave_application
        att.flags.ignore_permissions = True
        att.flags.ignore_validate = True
        att.insert()
        att.submit()

        # create auto-closed OUT checkin linked to this attendance
        ck = frappe.new_doc("Employee Checkin")
        ck.employee = self.emp_leave
        ck.time = get_datetime(f"{attendance_date} 19:00:00")
        ck.log_type = "OUT"
        ck.attendance = att.name
        ck.custom_auto_closed = 1
        ck.flags.ignore_permissions = True
        ck.flags.ignore_validate = True
        ck.insert()

        return att

    def test_row_with_leave_application_and_dates_covered_by_approved_leave_is_skipped(self):
        att_date = add_to_date(nowdate(), days=-2)
        la = self._create_leave_application(from_date=att_date, to_date=att_date, status="Approved", docstatus=1)
        att = self._create_attendance_with_autoclosed_out(att_date, leave_application=la.name)

        force_absent_missing_checkout.execute()
        att.reload()

        self.assertEqual(att.status, "Present")
        self.assertNotEqual(att.custom_absent_due_to_missing_checkout, 1)

    def test_row_with_leave_application_but_leave_not_approved_is_not_skipped(self):
        att_date_1 = add_to_date(nowdate(), days=-2)
        la_rej = self._create_leave_application(from_date=att_date_1, to_date=att_date_1, status="Rejected", docstatus=1)
        att1 = self._create_attendance_with_autoclosed_out(att_date_1, leave_application=la_rej.name)

        att_date_2 = add_to_date(nowdate(), days=-3)
        la_open = self._create_leave_application(from_date=att_date_2, to_date=att_date_2, status="Open", docstatus=0)
        att2 = self._create_attendance_with_autoclosed_out(att_date_2, leave_application=la_open.name)

        force_absent_missing_checkout.execute()
        att1.reload()
        att2.reload()

        self.assertEqual(att1.status, "Absent")
        self.assertEqual(att1.custom_absent_due_to_missing_checkout, 1)
        self.assertEqual(att2.status, "Absent")
        self.assertEqual(att2.custom_absent_due_to_missing_checkout, 1)

    def test_row_with_leave_application_but_dates_not_covered_is_not_skipped(self):
        att_date = add_to_date(nowdate(), days=-2)
        # Approved Leave Application for a different date range
        la = self._create_leave_application(
            from_date=add_to_date(nowdate(), days=-10),
            to_date=add_to_date(nowdate(), days=-5),
            status="Approved",
            docstatus=1,
        )
        att = self._create_attendance_with_autoclosed_out(att_date, leave_application=la.name)

        force_absent_missing_checkout.execute()
        att.reload()

        self.assertEqual(att.status, "Absent")
        self.assertEqual(att.custom_absent_due_to_missing_checkout, 1)

    def test_row_without_leave_application_is_processed_as_before(self):
        att_date = add_to_date(nowdate(), days=-2)
        att = self._create_attendance_with_autoclosed_out(att_date, leave_application=None)

        force_absent_missing_checkout.execute()
        att.reload()

        self.assertEqual(att.status, "Absent")
        self.assertEqual(att.custom_absent_due_to_missing_checkout, 1)

    def test_full_day_reasons_unchanged(self):
        expected = {"Regularization", "On Duty", "Work From Home"}
        self.assertEqual(set(FULL_DAY_REASONS), expected)
        self.assertNotIn("Permission", FULL_DAY_REASONS)
        self.assertNotIn("Late In", FULL_DAY_REASONS)
        self.assertNotIn("Early Out", FULL_DAY_REASONS)
        self.assertNotIn("Week Off Credit", FULL_DAY_REASONS)
