# Copyright (c) 2026, ASHWIN and Contributors
# See license.txt

import datetime
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from hrms_custom.hrms_custom.utils.attendance_lock import (
    _get_lock_threshold,
    check_attendance_lock,
)
from hrms_custom.hrms_custom.utils.late_lop_processor import process_late_deductions

TEST_COMPANY = "_Test Lock Company"
HOLIDAY_LIST = "_Test Lock Holiday List"
SHIFT_TYPE = "_Test Lock Shift"

EMP_USER = "test_emp_lock_pkg@example.com"
APPR_USER = "test_appr_lock_pkg@example.com"
HR_MGR_USER = "test_hr_mgr_lock_pkg@example.com"
HR_ONLY_USER = "test_hr_only_lock_pkg@example.com"
HR_USER = "test_hr_user_lock_pkg@example.com"
SYS_MGR_USER = "test_sys_mgr_lock_pkg@example.com"

TEST_USERS = [EMP_USER, APPR_USER, HR_MGR_USER, HR_ONLY_USER, HR_USER, SYS_MGR_USER]
LEAVE_TYPE_NAME = "_Test Lock Casual Leave"

FROZEN_TIME = datetime.datetime(2026, 11, 7, 10, 0, 0)
LOCKED_DATE = "2026-10-20"  # Tuesday (Working day)
OPEN_DATE = "2026-10-28"    # Wednesday (Working day)


class TestPayrollLock(IntegrationTestCase):
    _suite_start_time = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._suite_start_time = frappe.utils.now_datetime()
        frappe.set_user("Administrator")
        cls._create_test_fixtures()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        cls._cleanup_test_fixtures()
        super().tearDownClass()

    @classmethod
    def _create_test_fixtures(cls):
        # 1. Test Company
        if not frappe.db.exists("Company", TEST_COMPANY):
            frappe.get_doc({
                "doctype": "Company",
                "company_name": TEST_COMPANY,
                "abbr": "_TLC",
                "default_currency": "INR",
                "country": "India",
            }).insert(ignore_permissions=True)

        # 2. Test Holiday List
        if not frappe.db.exists("Holiday List", HOLIDAY_LIST):
            frappe.get_doc({
                "doctype": "Holiday List",
                "holiday_list_name": HOLIDAY_LIST,
                "from_date": "2026-01-01",
                "to_date": "2026-12-31",
                "country": "India",
            }).insert(ignore_permissions=True)

        # 3. Company Holiday List Assignment
        if not frappe.db.exists("Holiday List Assignment", {"applicable_for": "Company", "assigned_to": TEST_COMPANY, "docstatus": 1}):
            frappe.get_doc({
                "doctype": "Holiday List Assignment",
                "applicable_for": "Company",
                "assigned_to": TEST_COMPANY,
                "holiday_list": HOLIDAY_LIST,
                "from_date": "2026-04-01",
                "docstatus": 1,
            }).insert(ignore_permissions=True)

        # 4. Test Shift Type
        if not frappe.db.exists("Shift Type", SHIFT_TYPE):
            frappe.get_doc({
                "doctype": "Shift Type",
                "name": SHIFT_TYPE,
                "start_time": "09:00:00",
                "end_time": "18:00:00",
                "holiday_list": HOLIDAY_LIST,
            }).insert(ignore_permissions=True)

        # 5. Clean up any leftover test data
        frappe.db.delete("User Permission", {"user": ["in", TEST_USERS]})
        frappe.db.delete("Attendance Reason Allocation", {"company": TEST_COMPANY})
        for u in TEST_USERS:
            frappe.clear_cache(user=u)

        # 6. Test Users
        cls._create_user(EMP_USER, ["Employee", "Employee Self Service"])
        cls._create_user(APPR_USER, ["Employee", "Leave Approver", "Employee Self Service"])
        cls._create_user(HR_MGR_USER, ["Employee", "HR Manager", "Leave Approver", "Employee Self Service"])
        cls._create_user(HR_ONLY_USER, ["Employee", "HR Manager", "Employee Self Service"])
        cls._create_user(HR_USER, ["Employee", "HR User", "Employee Self Service"])
        cls._create_user(SYS_MGR_USER, ["Employee", "System Manager", "Employee Self Service"])

        # 7. Test Employees (hierarchy: HR Manager is top; Approver reports to HR; Employee reports to Approver)
        cls.hr_emp = cls._create_employee("EMP-PL-HR", HR_MGR_USER, "Test HR Manager", reports_to=None, leave_approver=APPR_USER)
        cls.appr_emp = cls._create_employee("EMP-PL-APPR", APPR_USER, "Test Approver", reports_to=cls.hr_emp)
        cls.test_emp = cls._create_employee("EMP-PL-EMP", EMP_USER, "Test Employee", reports_to=cls.appr_emp, leave_approver=APPR_USER)
        cls.hr_only_emp = cls._create_employee("EMP-PL-HR-ONLY", HR_ONLY_USER, "Test HR Only", reports_to=cls.hr_emp, leave_approver=APPR_USER)

        from frappe.utils.nestedset import rebuild_tree
        rebuild_tree("Employee")

        # 8. Shift Assignments
        cls._create_shift_assignment(cls.test_emp)
        cls._create_shift_assignment(cls.hr_emp)
        cls._create_shift_assignment(cls.hr_only_emp)

        # 9. Leave Type
        if not frappe.db.exists("Leave Type", LEAVE_TYPE_NAME):
            frappe.get_doc({
                "doctype": "Leave Type",
                "leave_type_name": LEAVE_TYPE_NAME,
                "is_optional_leave": 0,
            }).insert(ignore_permissions=True)

        # 10. Leave Allocations
        cls._create_allocation(cls.test_emp, LEAVE_TYPE_NAME, 50)
        cls._create_allocation(cls.hr_emp, LEAVE_TYPE_NAME, 50)

        # 11. Attendance Reason Types and Allocations for TEST_COMPANY
        for rt in ["Work From Home Allowance", "Missed Attendance", "On Duty", "Permission"]:
            if not frappe.db.exists("Attendance Reason Type", rt):
                frappe.get_doc({
                    "doctype": "Attendance Reason Type",
                    "name": rt,
                }).insert(ignore_permissions=True)
            if not frappe.db.exists("Attendance Reason Allocation", {"applies_to": "Company", "company": TEST_COMPANY, "attendance_reason_type": rt, "docstatus": 1}):
                frappe.get_doc({
                    "doctype": "Attendance Reason Allocation",
                    "applies_to": "Company",
                    "company": TEST_COMPANY,
                    "attendance_reason_type": rt,
                    "effective_from": "2026-04-01",
                    "monthly_limit": 10,
                    "period_start_day": 26,
                    "docstatus": 1,
                }).insert(ignore_permissions=True)

        for u in TEST_USERS:
            frappe.clear_cache(user=u)

    @classmethod
    def _create_user(cls, email, roles):
        if not frappe.db.exists("User", email):
            user = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": email.split("@")[0],
                "send_welcome_email": 0,
                "roles": [{"role": r} for r in roles],
            }).insert(ignore_permissions=True)
        else:
            user = frappe.get_doc("User", email)
            existing_roles = {r.role for r in user.roles}
            for r in roles:
                if r not in existing_roles:
                    user.append("roles", {"role": r})
            user.save(ignore_permissions=True)

    @classmethod
    def _create_employee(cls, emp_id, email, first_name, reports_to=None, leave_approver=None):
        existing = frappe.db.get_value("Employee", {"user_id": email}, "name")
        if existing:
            frappe.db.set_value("Employee", existing, {
                "reports_to": reports_to,
                "leave_approver": leave_approver,
            })
            return existing

        emp = frappe.get_doc({
            "doctype": "Employee",
            "employee": emp_id,
            "first_name": first_name,
            "user_id": email,
            "company": TEST_COMPANY,
            "status": "Active",
            "date_of_joining": "2026-04-01",
            "date_of_birth": "1990-01-01",
            "gender": "Female",
            "employee_number": emp_id,
            "custom_roles_responsibilities": "Test Roles",
            "ctc": 500000,
            "reports_to": reports_to,
            "leave_approver": leave_approver,
        }).insert(ignore_permissions=True, ignore_mandatory=True)
        return emp.name

    @classmethod
    def _create_shift_assignment(cls, employee):
        if not frappe.db.exists("Shift Assignment", {"employee": employee, "docstatus": 1}):
            frappe.get_doc({
                "doctype": "Shift Assignment",
                "employee": employee,
                "shift_type": SHIFT_TYPE,
                "start_date": "2026-04-01",
                "status": "Active",
                "docstatus": 1,
            }).insert(ignore_permissions=True)

    @classmethod
    def _create_allocation(cls, employee, leave_type, days):
        if not frappe.db.exists("Leave Allocation", {"employee": employee, "leave_type": leave_type, "docstatus": 1}):
            frappe.get_doc({
                "doctype": "Leave Allocation",
                "employee": employee,
                "leave_type": leave_type,
                "from_date": "2026-04-01",
                "to_date": "2027-03-31",
                "new_leaves_allocated": days,
                "company": TEST_COMPANY,
                "docstatus": 1,
            }).insert(ignore_permissions=True)

    @classmethod
    def _cleanup_test_fixtures(cls):
        frappe.set_user("Administrator")
        # Explicit cancel and delete_doc in reverse dependency order
        # 1. Transient attendance & requests & leaves for TEST_COMPANY
        for dt in ["Leave Application", "Attendance Request", "Attendance"]:
            for name in frappe.get_all(dt, filters={"company": TEST_COMPANY}, pluck="name"):
                try:
                    doc = frappe.get_doc(dt, name)
                    if doc.docstatus == 1:
                        doc.cancel()
                    frappe.delete_doc(dt, name, force=True)
                except Exception:
                    pass

        # 2. Shift assignments
        for name in frappe.get_all("Shift Assignment", filters={"company": TEST_COMPANY}, pluck="name"):
            try:
                doc = frappe.get_doc("Shift Assignment", name)
                if doc.docstatus == 1:
                    doc.cancel()
                frappe.delete_doc("Shift Assignment", name, force=True)
            except Exception:
                pass

        # 3. Leave Allocations
        for name in frappe.get_all("Leave Allocation", filters={"company": TEST_COMPANY}, pluck="name"):
            try:
                doc = frappe.get_doc("Leave Allocation", name)
                if doc.docstatus == 1:
                    doc.cancel()
                frappe.delete_doc("Leave Allocation", name, force=True)
            except Exception:
                pass

        # 4. Leave Ledger Entry for test employees
        for emp in ["EMP-PL-HR", "EMP-PL-APPR", "EMP-PL-EMP", "EMP-PL-HR-ONLY"]:
            for name in frappe.get_all("Leave Ledger Entry", filters={"employee": emp}, pluck="name"):
                try:
                    frappe.delete_doc("Leave Ledger Entry", name, force=True)
                except Exception:
                    pass

        # 5. Employees
        for emp in ["EMP-PL-EMP", "EMP-PL-HR-ONLY", "EMP-PL-APPR", "EMP-PL-HR"]:
            if frappe.db.exists("Employee", emp):
                try:
                    frappe.delete_doc("Employee", emp, force=True)
                except Exception:
                    pass
        from frappe.utils.nestedset import rebuild_tree
        rebuild_tree("Employee")

        # 6. User Permissions
        frappe.db.delete("User Permission", {"user": ["in", TEST_USERS]})

        # 7. Users
        for u in TEST_USERS:
            if frappe.db.exists("User", u):
                try:
                    frappe.delete_doc("User", u, force=True)
                except Exception:
                    pass
            frappe.clear_cache(user=u)

        # 8. Holiday List Assignment
        for name in frappe.get_all("Holiday List Assignment", filters={"applicable_for": "Company", "assigned_to": TEST_COMPANY}, pluck="name"):
            try:
                doc = frappe.get_doc("Holiday List Assignment", name)
                if doc.docstatus == 1:
                    doc.cancel()
                frappe.delete_doc("Holiday List Assignment", name, force=True)
            except Exception:
                pass

        # 9. Attendance Reason Allocation
        for name in frappe.get_all("Attendance Reason Allocation", filters={"company": TEST_COMPANY}, pluck="name"):
            try:
                doc = frappe.get_doc("Attendance Reason Allocation", name)
                if doc.docstatus == 1:
                    doc.cancel()
                frappe.delete_doc("Attendance Reason Allocation", name, force=True)
            except Exception:
                pass

        # 10. Leave Type
        if frappe.db.exists("Leave Type", LEAVE_TYPE_NAME):
            try:
                frappe.delete_doc("Leave Type", LEAVE_TYPE_NAME, force=True)
            except Exception:
                pass

        # 11. Shift Type
        if frappe.db.exists("Shift Type", SHIFT_TYPE):
            try:
                frappe.delete_doc("Shift Type", SHIFT_TYPE, force=True)
            except Exception:
                pass

        # 12. Holiday List
        if frappe.db.exists("Holiday List", HOLIDAY_LIST):
            try:
                frappe.delete_doc("Holiday List", HOLIDAY_LIST, force=True)
            except Exception:
                pass

        # 13. Company
        if frappe.db.exists("Company", TEST_COMPANY):
            try:
                frappe.delete_doc("Company", TEST_COMPANY, force=True)
            except Exception:
                pass

        # 14. Delete Version & Comment audit records created during test run
        if getattr(cls, "_suite_start_time", None):
            frappe.db.delete("Comment", {"creation": [">=", cls._suite_start_time]})
            frappe.db.delete("Version", {"creation": [">=", cls._suite_start_time]})

        # Commit deletes so database returns to pristine state
        frappe.db.commit()

    def setUp(self):
        super().setUp()
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")
        # Clean up any transient documents created inside tests
        for dt in ["Leave Application", "Attendance Request", "Attendance"]:
            for name in frappe.get_all(dt, filters={"company": TEST_COMPANY}, pluck="name"):
                try:
                    doc = frappe.get_doc(dt, name)
                    if doc.docstatus == 1:
                        doc.cancel()
                    frappe.delete_doc(dt, name, force=True)
                except Exception:
                    pass
        super().tearDown()

    # -------------------------------------------------------------------------
    # Pure unit tests for boundary times
    # -------------------------------------------------------------------------
    def test_lock_threshold_boundary_times(self):
        """Boundary test: 26th before 11:00 AM locks previous month, at 11:00 AM locks current month."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime",
                   return_value=datetime.datetime(2026, 10, 26, 10, 59, 59)):
            self.assertEqual(_get_lock_threshold(), datetime.date(2026, 9, 25))

        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime",
                   return_value=datetime.datetime(2026, 10, 26, 11, 0, 0)):
            self.assertEqual(_get_lock_threshold(), datetime.date(2026, 10, 25))

        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime",
                   return_value=datetime.datetime(2026, 1, 26, 10, 59, 59)):
            self.assertEqual(_get_lock_threshold(), datetime.date(2025, 12, 25))

        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime",
                   return_value=datetime.datetime(2026, 1, 26, 11, 0, 0)):
            self.assertEqual(_get_lock_threshold(), datetime.date(2026, 1, 25))

    # -------------------------------------------------------------------------
    # Leave Application Real Entry-Point Tests
    # -------------------------------------------------------------------------
    def test_leave_application_employee_insert_in_locked_period_is_blocked(self):
        """Employee insert in locked period is blocked via doc.insert()."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user(EMP_USER)

            doc = frappe.get_doc({
                "doctype": "Leave Application",
                "employee": self.test_emp,
                "leave_type": LEAVE_TYPE_NAME,
                "from_date": LOCKED_DATE,
                "to_date": LOCKED_DATE,
                "leave_approver": APPR_USER,
                "company": TEST_COMPANY,
                "status": "Open",
                "follow_via_email": 0
            })
            with patch("frappe.sendmail"):
                with self.assertRaises(frappe.ValidationError) as cm:
                    doc.insert()
                self.assertIn("That payroll period is locked", str(cm.exception))
                self.assertIn("20-Oct-2026", str(cm.exception))
                self.assertIn("25-Oct-2026", str(cm.exception))

    def test_leave_application_employee_insert_in_open_period_is_allowed(self):
        """Employee insert in open period succeeds."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user(EMP_USER)

            doc = frappe.get_doc({
                "doctype": "Leave Application",
                "employee": self.test_emp,
                "leave_type": LEAVE_TYPE_NAME,
                "from_date": OPEN_DATE,
                "to_date": OPEN_DATE,
                "leave_approver": APPR_USER,
                "company": TEST_COMPANY,
                "status": "Open",
                "follow_via_email": 0
            })
            with patch("frappe.sendmail"):
                doc.insert()
                self.assertTrue(bool(doc.name))
                self.assertEqual(doc.docstatus, 0)

    def test_leave_application_partial_overlap_blocked(self):
        """Leave application spanning across lock threshold (locked start, open end) is blocked."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user(EMP_USER)

            doc = frappe.get_doc({
                "doctype": "Leave Application",
                "employee": self.test_emp,
                "leave_type": LEAVE_TYPE_NAME,
                "from_date": "2026-10-24",
                "to_date": "2026-10-28",
                "leave_approver": APPR_USER,
                "company": TEST_COMPANY,
                "status": "Open",
                "follow_via_email": 0
            })
            with patch("frappe.sendmail"):
                with self.assertRaises(frappe.ValidationError) as cm:
                    doc.insert()
                self.assertIn("That payroll period is locked", str(cm.exception))
                self.assertIn("25-Oct-2026", str(cm.exception))

    def test_leave_application_hr_manager_insert_in_locked_period_is_allowed(self):
        """HR Manager insert in locked period succeeds via HR Manager bypass."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user(HR_MGR_USER)

            doc = frappe.get_doc({
                "doctype": "Leave Application",
                "employee": self.test_emp,
                "leave_type": LEAVE_TYPE_NAME,
                "from_date": LOCKED_DATE,
                "to_date": LOCKED_DATE,
                "leave_approver": APPR_USER,
                "company": TEST_COMPANY,
                "status": "Open",
                "follow_via_email": 0
            })
            with patch("frappe.sendmail"):
                doc.insert()
                self.assertTrue(bool(doc.name))

    def test_leave_approval_non_hr_approver_setting_approved_is_blocked(self):
        """For a locked-period leave, non-HR approver setting status='Approved' and saving is blocked at before_submit."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user("Administrator")
            doc = frappe.get_doc({
                "doctype": "Leave Application",
                "employee": self.test_emp,
                "leave_type": LEAVE_TYPE_NAME,
                "from_date": "2026-10-14",
                "to_date": "2026-10-14",
                "leave_approver": APPR_USER,
                "company": TEST_COMPANY,
                "status": "Open",
                "follow_via_email": 0
            })
            with patch("frappe.sendmail"):
                doc.insert(ignore_permissions=True)

            frappe.set_user(APPR_USER)
            doc_to_approve = frappe.get_doc("Leave Application", doc.name)
            doc_to_approve.status = "Approved"

            with patch("frappe.sendmail"):
                with self.assertRaises(frappe.ValidationError) as cm:
                    doc_to_approve.save()
                self.assertIn("That payroll period is locked", str(cm.exception))

    def test_leave_approval_hr_manager_setting_approved_succeeds_and_ends_docstatus_1(self):
        """HR Manager setting status='Approved' and saving succeeds and auto-submits to docstatus 1."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user("Administrator")
            doc = frappe.get_doc({
                "doctype": "Leave Application",
                "employee": self.test_emp,
                "leave_type": LEAVE_TYPE_NAME,
                "from_date": "2026-10-14",
                "to_date": "2026-10-14",
                "leave_approver": APPR_USER,
                "company": TEST_COMPANY,
                "status": "Open",
                "follow_via_email": 0
            })
            with patch("frappe.sendmail"):
                doc.insert(ignore_permissions=True)

            frappe.set_user(HR_MGR_USER)
            doc_to_approve = frappe.get_doc("Leave Application", doc.name)
            doc_to_approve.status = "Approved"

            with patch("frappe.sendmail"):
                doc_to_approve.save()
                doc_to_approve.reload()
                self.assertEqual(doc_to_approve.status, "Approved")
                self.assertEqual(doc_to_approve.docstatus, 1)

    def test_leave_approval_hr_only_without_leave_approver_role_raises_permission_error(self):
        """HR Manager WITHOUT 'Leave Approver' role who is not named approver throws PermissionError on save."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user("Administrator")
            doc = frappe.get_doc({
                "doctype": "Leave Application",
                "employee": self.test_emp,
                "leave_type": LEAVE_TYPE_NAME,
                "from_date": "2026-10-14",
                "to_date": "2026-10-14",
                "leave_approver": APPR_USER,
                "company": TEST_COMPANY,
                "status": "Open",
                "follow_via_email": 0
            })
            with patch("frappe.sendmail"):
                doc.insert(ignore_permissions=True)

            frappe.set_user(HR_ONLY_USER)
            doc_to_approve = frappe.get_doc("Leave Application", doc.name)
            doc_to_approve.status = "Approved"

            with patch("frappe.sendmail"):
                with self.assertRaises(frappe.PermissionError):
                    doc_to_approve.save()

    def test_leave_approval_non_hr_approver_rejecting_is_blocked_at_before_submit(self):
        """Non-HR approver rejecting attempts auto-submit and is blocked by before_submit hook."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user("Administrator")
            doc = frappe.get_doc({
                "doctype": "Leave Application",
                "employee": self.test_emp,
                "leave_type": LEAVE_TYPE_NAME,
                "from_date": "2026-10-15",
                "to_date": "2026-10-15",
                "leave_approver": APPR_USER,
                "company": TEST_COMPANY,
                "status": "Open",
                "follow_via_email": 0
            })
            with patch("frappe.sendmail"):
                doc.insert(ignore_permissions=True)

            frappe.set_user(APPR_USER)
            doc_to_reject = frappe.get_doc("Leave Application", doc.name)
            doc_to_reject.status = "Rejected"

            with patch("frappe.sendmail"):
                with self.assertRaises(frappe.ValidationError) as cm:
                    doc_to_reject.save()
                self.assertIn("That payroll period is locked", str(cm.exception))

    def test_leave_approval_hr_manager_rejecting_succeeds(self):
        """HR Manager rejecting succeeds and auto-submits with status='Rejected'."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user("Administrator")
            doc = frappe.get_doc({
                "doctype": "Leave Application",
                "employee": self.test_emp,
                "leave_type": LEAVE_TYPE_NAME,
                "from_date": "2026-10-15",
                "to_date": "2026-10-15",
                "leave_approver": APPR_USER,
                "company": TEST_COMPANY,
                "status": "Open",
                "follow_via_email": 0
            })
            with patch("frappe.sendmail"):
                doc.insert(ignore_permissions=True)

            frappe.set_user(HR_MGR_USER)
            doc_to_reject = frappe.get_doc("Leave Application", doc.name)
            doc_to_reject.status = "Rejected"

            with patch("frappe.sendmail"):
                doc_to_reject.save()
                doc_to_reject.reload()
                self.assertEqual(doc_to_reject.status, "Rejected")
                self.assertEqual(doc_to_reject.docstatus, 1)

    # -------------------------------------------------------------------------
    # Attendance Request Real Entry-Point Tests
    # -------------------------------------------------------------------------
    def test_attendance_request_employee_insert_in_locked_period_is_blocked(self):
        """Employee insert for Attendance Request in locked period is blocked via doc.insert()."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user(EMP_USER)

            doc = frappe.get_doc({
                "doctype": "Attendance Request",
                "employee": self.test_emp,
                "from_date": LOCKED_DATE,
                "to_date": LOCKED_DATE,
                "reason": "Work From Home",
                "company": TEST_COMPANY,
            })
            with self.assertRaises(frappe.ValidationError) as cm:
                doc.insert()
            self.assertIn("That payroll period is locked", str(cm.exception))
            self.assertIn("20-Oct-2026", str(cm.exception))
            self.assertIn("25-Oct-2026", str(cm.exception))

    def test_attendance_request_employee_insert_in_open_period_is_allowed(self):
        """Employee insert for Attendance Request in open period succeeds."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user(EMP_USER)

            doc = frappe.get_doc({
                "doctype": "Attendance Request",
                "employee": self.test_emp,
                "from_date": OPEN_DATE,
                "to_date": OPEN_DATE,
                "reason": "Work From Home",
                "company": TEST_COMPANY,
            })
            doc.insert()
            self.assertTrue(bool(doc.name))
            self.assertEqual(doc.docstatus, 0)

    def test_attendance_request_hr_manager_insert_in_locked_period_is_allowed(self):
        """HR Manager insert for Attendance Request in locked period succeeds via HR Manager bypass."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user(HR_MGR_USER)

            doc = frappe.get_doc({
                "doctype": "Attendance Request",
                "employee": self.test_emp,
                "from_date": LOCKED_DATE,
                "to_date": LOCKED_DATE,
                "reason": "Work From Home",
                "company": TEST_COMPANY,
            })
            doc.insert()
            self.assertTrue(bool(doc.name))

    def test_attendance_request_non_hr_approver_apply_workflow_approve_is_blocked(self):
        """Non-HR approver executing apply_workflow('Approve') on locked-period request is blocked."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user("Administrator")
            doc = frappe.get_doc({
                "doctype": "Attendance Request",
                "employee": self.test_emp,
                "from_date": "2026-10-13",
                "to_date": "2026-10-13",
                "reason": "Work From Home",
                "company": TEST_COMPANY,
            })
            doc.insert(ignore_permissions=True)

            frappe.set_user(APPR_USER)
            with self.assertRaises(frappe.ValidationError) as cm:
                frappe.model.workflow.apply_workflow(doc, "Approve")
            self.assertIn("That payroll period is locked", str(cm.exception))

    def test_attendance_request_non_hr_approver_rejecting_in_locked_period_is_allowed(self):
        """Non-HR approver executing apply_workflow('Reject') on locked-period request is ALLOWED."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user("Administrator")
            doc = frappe.get_doc({
                "doctype": "Attendance Request",
                "employee": self.test_emp,
                "from_date": "2026-10-13",
                "to_date": "2026-10-13",
                "reason": "Work From Home",
                "company": TEST_COMPANY,
            })
            doc.insert(ignore_permissions=True)

            frappe.set_user(APPR_USER)
            frappe.model.workflow.apply_workflow(doc, "Reject")
            doc.reload()
            self.assertEqual(doc.workflow_state, "Rejected")

    def test_attendance_request_hr_manager_apply_workflow_approve_succeeds(self):
        """HR Manager executing apply_workflow('Approve') on locked-period request succeeds."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user("Administrator")
            doc = frappe.get_doc({
                "doctype": "Attendance Request",
                "employee": self.test_emp,
                "from_date": "2026-10-13",
                "to_date": "2026-10-13",
                "reason": "Work From Home",
                "company": TEST_COMPANY,
            })
            doc.insert(ignore_permissions=True)

            frappe.set_user(HR_MGR_USER)
            frappe.model.workflow.apply_workflow(doc, "Approve")
            doc.reload()
            self.assertEqual(doc.workflow_state, "Approved")
            self.assertEqual(doc.docstatus, 1)

    def test_attendance_request_hr_only_without_leave_approver_role_fails_workflow(self):
        """Documents a workflow-role limitation (transition requires role 'Leave Approver'), not a lock behaviour."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user("Administrator")
            doc = frappe.get_doc({
                "doctype": "Attendance Request",
                "employee": self.test_emp,
                "from_date": "2026-10-12",
                "to_date": "2026-10-12",
                "reason": "Work From Home",
                "company": TEST_COMPANY,
            })
            doc.insert(ignore_permissions=True)

            frappe.set_user(HR_ONLY_USER)
            with self.assertRaises(frappe.model.workflow.WorkflowTransitionError):
                frappe.model.workflow.apply_workflow(doc, "Approve")

    # -------------------------------------------------------------------------
    # HR Self-Application & Self-Approval Rules
    # -------------------------------------------------------------------------
    def test_hr_manager_can_apply_own_leave_and_attendance_request_in_locked_period(self):
        """HR Manager can insert their OWN leave and attendance request in locked period."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user(HR_MGR_USER)

            doc_la = frappe.get_doc({
                "doctype": "Leave Application",
                "employee": self.hr_emp,
                "leave_type": LEAVE_TYPE_NAME,
                "from_date": LOCKED_DATE,
                "to_date": LOCKED_DATE,
                "leave_approver": APPR_USER,
                "company": TEST_COMPANY,
                "status": "Open",
                "follow_via_email": 0
            })
            with patch("frappe.sendmail"):
                doc_la.insert()
                self.assertTrue(bool(doc_la.name))

            doc_ar = frappe.get_doc({
                "doctype": "Attendance Request",
                "employee": self.hr_emp,
                "from_date": LOCKED_DATE,
                "to_date": LOCKED_DATE,
                "reason": "Work From Home",
                "company": TEST_COMPANY,
            })
            doc_ar.insert()
            self.assertTrue(bool(doc_ar.name))

    def test_hr_manager_cannot_self_approve_own_leave_or_attendance_request(self):
        """Self-approval hardening blocks HR Manager from approving their OWN leave or request."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user(HR_MGR_USER)

            doc_la = frappe.get_doc({
                "doctype": "Leave Application",
                "employee": self.hr_emp,
                "leave_type": LEAVE_TYPE_NAME,
                "from_date": "2026-10-14",
                "to_date": "2026-10-14",
                "leave_approver": APPR_USER,
                "company": TEST_COMPANY,
                "status": "Approved",
                "follow_via_email": 0
            })
            with patch("frappe.sendmail"):
                with self.assertRaises(frappe.ValidationError) as cm:
                    doc_la.insert()
                self.assertIn("Self-approval for leaves is not allowed", str(cm.exception))

            doc_ar = frappe.get_doc({
                "doctype": "Attendance Request",
                "employee": self.hr_emp,
                "from_date": "2026-10-14",
                "to_date": "2026-10-14",
                "reason": "Work From Home",
                "company": TEST_COMPANY,
            })
            doc_ar.insert()
            with self.assertRaises(frappe.ValidationError) as cm_ar:
                doc_ar.submit()
            self.assertIn("Self-approval for Attendance Requests is not allowed", str(cm_ar.exception))

    # -------------------------------------------------------------------------
    # End-to-End Attendance Table Impact
    # -------------------------------------------------------------------------
    def test_end_to_end_regularization_approval_updates_attendance_table(self):
        """HR Manager approving locked Regularization updates pre-existing Absent record to Present."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user("Administrator")
            att = frappe.get_doc({
                "doctype": "Attendance",
                "employee": self.test_emp,
                "attendance_date": "2026-10-08",
                "status": "Absent",
                "company": TEST_COMPANY,
            })
            att.insert(ignore_permissions=True)
            att.submit()

            ar = frappe.get_doc({
                "doctype": "Attendance Request",
                "employee": self.test_emp,
                "from_date": "2026-10-08",
                "to_date": "2026-10-08",
                "reason": "Regularization",
                "company": TEST_COMPANY,
            })
            ar.insert(ignore_permissions=True)

            frappe.set_user(HR_MGR_USER)
            frappe.model.workflow.apply_workflow(ar, "Approve")
            ar.reload()
            self.assertEqual(ar.workflow_state, "Approved")
            self.assertEqual(ar.docstatus, 1)

            att.reload()
            self.assertEqual(att.status, "Present")
            self.assertEqual(att.custom_attendance_request, ar.name)

    def test_end_to_end_leave_approval_attendance_table_impact(self):
        """HR Manager approving locked Leave Application updates pre-existing Absent Attendance to 'On Leave'."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user("Administrator")
            att = frappe.get_doc({
                "doctype": "Attendance",
                "employee": self.test_emp,
                "attendance_date": "2026-10-07",
                "status": "Absent",
                "company": TEST_COMPANY,
            })
            att.insert(ignore_permissions=True)
            att.submit()

            la = frappe.get_doc({
                "doctype": "Leave Application",
                "employee": self.test_emp,
                "leave_type": LEAVE_TYPE_NAME,
                "from_date": "2026-10-07",
                "to_date": "2026-10-07",
                "leave_approver": APPR_USER,
                "company": TEST_COMPANY,
                "status": "Open",
                "follow_via_email": 0
            })
            with patch("frappe.sendmail"):
                la.insert(ignore_permissions=True)

            frappe.set_user(HR_MGR_USER)
            la = frappe.get_doc("Leave Application", la.name)
            la.status = "Approved"
            with patch("frappe.sendmail"):
                la.save()

            att.reload()
            self.assertEqual(att.status, "On Leave")
            self.assertEqual(att.leave_application, la.name)
            self.assertEqual(att.leave_type, LEAVE_TYPE_NAME)

    # -------------------------------------------------------------------------
    # Administrator and Other System Roles
    # -------------------------------------------------------------------------
    def test_administrator_context_passes_insert_and_submit_both_doctypes(self):
        """Administrator user passes both insert and submit for Leave Application and Attendance Request."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user("Administrator")

            doc_la = frappe.get_doc({
                "doctype": "Leave Application",
                "employee": self.test_emp,
                "leave_type": LEAVE_TYPE_NAME,
                "from_date": "2026-10-05",
                "to_date": "2026-10-05",
                "leave_approver": APPR_USER,
                "company": TEST_COMPANY,
                "status": "Approved",
                "follow_via_email": 0
            })
            with patch("frappe.sendmail"):
                doc_la.insert()
                self.assertEqual(doc_la.docstatus, 1)

            doc_ar = frappe.get_doc({
                "doctype": "Attendance Request",
                "employee": self.test_emp,
                "from_date": "2026-10-06",
                "to_date": "2026-10-06",
                "reason": "Work From Home",
                "company": TEST_COMPANY,
            })
            doc_ar.insert()
            doc_ar.submit()
            self.assertEqual(doc_ar.docstatus, 1)

    def test_check_attendance_lock_on_attendance_unchanged(self):
        """Attendance doctype hook remains unchanged: HR roles pass, others fail."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            att = frappe.new_doc("Attendance")
            att.employee = self.test_emp
            att.attendance_date = LOCKED_DATE
            att.status = "Present"

            frappe.set_user(EMP_USER)
            with self.assertRaises(frappe.ValidationError) as cm:
                check_attendance_lock(att)
            self.assertIn("cannot be modified directly", str(cm.exception))

            frappe.set_user(APPR_USER)
            with self.assertRaises(frappe.ValidationError):
                check_attendance_lock(att)

            frappe.set_user(HR_MGR_USER)
            check_attendance_lock(att)

            frappe.set_user(HR_USER)
            check_attendance_lock(att)

            frappe.set_user(SYS_MGR_USER)
            check_attendance_lock(att)

    def test_late_lop_processor_smoke_test_does_not_raise(self):
        """late_lop_processor.process_late_deductions smoke test: executes without raising. Non-test company data is untouched."""
        with patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME):
            frappe.set_user("Administrator")
            att = frappe.get_doc({
                "doctype": "Attendance",
                "employee": self.test_emp,
                "attendance_date": "2026-10-06",
                "status": "Present",
                "late_entry": 1,
                "in_time": datetime.datetime(2026, 10, 6, 11, 0, 0),
                "company": TEST_COMPANY,
            })
            att.insert(ignore_permissions=True)
            att.submit()

            non_test_count_before = frappe.db.count("Attendance", {"company": ["!=", TEST_COMPANY]})
            res_before = frappe.db.sql("SELECT MAX(modified) FROM `tabAttendance` WHERE company != %s", (TEST_COMPANY,))
            non_test_max_mod_before = res_before[0][0] if res_before else None

            process_late_deductions(datetime.date(2026, 9, 26), datetime.date(2026, 10, 25))

            non_test_count_after = frappe.db.count("Attendance", {"company": ["!=", TEST_COMPANY]})
            res_after = frappe.db.sql("SELECT MAX(modified) FROM `tabAttendance` WHERE company != %s", (TEST_COMPANY,))
            non_test_max_mod_after = res_after[0][0] if res_after else None

            self.assertEqual(non_test_count_before, non_test_count_after)
            self.assertEqual(non_test_max_mod_before, non_test_max_mod_after)

            att.reload()
            self.assertIn(att.status, ("Present", "Half Day"))
