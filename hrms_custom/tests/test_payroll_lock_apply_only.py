import frappe
from frappe.utils import getdate, add_days
from datetime import date, datetime
from unittest.mock import patch
from frappe.tests.classes.integration_test_case import IntegrationTestCase

TEST_COMPANY = "_Test Apply Only Company"
HOLIDAY_LIST = "_Test Apply Only Holiday List"
SHIFT_TYPE = "_Test Apply Only Shift"
LEAVE_TYPE_NAME = "_Test Apply Only Leave"

EMP_USER = "_test_apply_emp@example.com"
APPR_USER = "_test_apply_appr@example.com"
HR_MGR_USER = "_test_apply_hr@example.com"

LOCKED_DATE_1 = "2026-10-10"
LOCKED_DATE_2 = "2026-10-12"
LOCKED_DATE_3 = "2026-10-13"
LOCKED_DATE_LEAVE = "2026-10-14"
OPEN_DATE = "2026-11-10"
FROZEN_TIME = datetime(2026, 11, 15, 12, 0, 0)


class TestPayrollLockApplyOnly(IntegrationTestCase):
    _created_companies = []
    _created_holiday_lists = []
    _created_shifts = []
    _created_users = []
    _created_employees = []
    _created_leave_types = []
    _created_leave_allocations = []
    _created_reason_types = []
    _created_reasons = []
    _created_reason_allocations = []

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._created_companies = []
        cls._created_holiday_lists = []
        cls._created_shifts = []
        cls._created_users = []
        cls._created_employees = []
        cls._created_leave_types = []
        cls._created_leave_allocations = []
        cls._created_reason_types = []
        cls._created_reasons = []
        cls._created_reason_allocations = []

        cls._cleanup_all()

        # 1. Company
        if not frappe.db.exists("Company", TEST_COMPANY):
            frappe.get_doc({
                "doctype": "Company",
                "company_name": TEST_COMPANY,
                "default_currency": "INR",
                "country": "India",
            }).insert(ignore_permissions=True)
            cls._created_companies.append(TEST_COMPANY)

        # 2. Holiday List with a fixed holiday
        if not frappe.db.exists("Holiday List", HOLIDAY_LIST):
            frappe.get_doc({
                "doctype": "Holiday List",
                "holiday_list_name": HOLIDAY_LIST,
                "from_date": "2026-01-01",
                "to_date": "2026-12-31",
                "holidays": [
                    {"holiday_date": "2026-10-15", "description": "Festival Holiday"}
                ]
            }).insert(ignore_permissions=True)
            cls._created_holiday_lists.append(HOLIDAY_LIST)

        # 3. Shift Type
        if not frappe.db.exists("Shift Type", SHIFT_TYPE):
            frappe.get_doc({
                "doctype": "Shift Type",
                "name": SHIFT_TYPE,
                "start_time": "09:00:00",
                "end_time": "18:00:00",
                "holiday_list": HOLIDAY_LIST,
            }).insert(ignore_permissions=True)
            cls._created_shifts.append(SHIFT_TYPE)

        # 4. Roles & Users
        cls._ensure_user(EMP_USER, ["Employee", "Employee Self Service"])
        cls._ensure_user(APPR_USER, ["Employee", "Leave Approver", "Employee Self Service"])
        cls._ensure_user(HR_MGR_USER, ["Employee", "HR Manager", "Leave Approver", "Employee Self Service"])

        for u in [EMP_USER, APPR_USER, HR_MGR_USER]:
            for up in frappe.get_all("User Permission", filters={"user": u}, pluck="name"):
                frappe.delete_doc("User Permission", up, force=1)

        # 5. Employees (Hierarchy: Approver -> Employee reports to Approver)
        cls.appr_emp = cls._create_employee("EMP-APPLY-002", "Appr", "Employee", APPR_USER)
        cls.test_emp = cls._create_employee("EMP-APPLY-001", "Test", "Employee", EMP_USER, reports_to=cls.appr_emp, leave_approver=APPR_USER)
        cls.hr_emp = cls._create_employee("EMP-APPLY-003", "HR", "Manager", HR_MGR_USER, leave_approver=APPR_USER)

        from frappe.utils.nestedset import rebuild_tree
        rebuild_tree("Employee")

        frappe.db.set_value("Employee", cls.test_emp, "leave_approver", APPR_USER)
        frappe.db.set_value("Employee", cls.hr_emp, "leave_approver", APPR_USER)

        # 6. Assert local workflow "Attendance Request Approval" exists and matches fixture
        assert frappe.db.exists("Workflow", "Attendance Request Approval"), (
            "Workflow 'Attendance Request Approval' does not exist in local site"
        )
        wf_ar = frappe.get_doc("Workflow", "Attendance Request Approval")
        assert wf_ar.is_active == 1, "Workflow 'Attendance Request Approval' is not active"
        states_ar = {s.state: s.doc_status for s in wf_ar.states}
        assert states_ar.get("Pending Approval") == "0", f"Pending Approval missing or docstatus != 0: {states_ar}"
        assert states_ar.get("Approved") == "1", f"Approved missing or docstatus != 1: {states_ar}"
        assert states_ar.get("Rejected") == "0", f"Rejected missing or docstatus != 0: {states_ar}"

        transitions_ar = {(t.state, t.action): t.next_state for t in wf_ar.transitions}
        assert transitions_ar.get(("Pending Approval", "Approve")) == "Approved", (
            f"Approve transition missing: {transitions_ar}"
        )
        assert transitions_ar.get(("Pending Approval", "Reject")) == "Rejected", (
            f"Reject transition missing: {transitions_ar}"
        )

        # 7. Leave Type
        if not frappe.db.exists("Leave Type", LEAVE_TYPE_NAME):
            frappe.get_doc({
                "doctype": "Leave Type",
                "leave_type_name": LEAVE_TYPE_NAME,
                "is_optional_leave": 0,
                "include_holiday": 0,
            }).insert(ignore_permissions=True)
            cls._created_leave_types.append(LEAVE_TYPE_NAME)

        # 8. Leave Allocation
        cls._create_allocation(cls.test_emp, LEAVE_TYPE_NAME, 50)
        cls._create_allocation(cls.appr_emp, LEAVE_TYPE_NAME, 50)
        cls._create_allocation(cls.hr_emp, LEAVE_TYPE_NAME, 50)

        # 9. Reason Types, Reasons, and Reason Allocations (matching test_attendance_request_limit.py)
        for rt, behavior in [
            ("Work From Home Allowance", "Creates Attendance"),
            ("Permission", "Tags Existing Attendance"),
            ("Missed Attendance", "Creates Attendance"),
            ("On Duty", "Creates Attendance"),
        ]:
            if not frappe.db.exists("Attendance Reason Type", rt):
                frappe.get_doc({
                    "doctype": "Attendance Reason Type",
                    "name": rt,
                    "type_name": rt,
                    "attendance_behavior": behavior,
                    "is_active": 1,
                }).insert(ignore_permissions=True)
                cls._created_reason_types.append(rt)

        for r_name, rt in [
            ("Work From Home", "Work From Home Allowance"),
            ("Late In", "Permission"),
            ("Early Out", "Permission"),
            ("Regularization", "Missed Attendance"),
            ("On Duty", "On Duty"),
        ]:
            if not frappe.db.exists("Attendance Reason", r_name):
                frappe.get_doc({
                    "doctype": "Attendance Reason",
                    "name": r_name,
                    "reason_name": r_name,
                    "attendance_reason_type": rt,
                    "is_active": 1,
                }).insert(ignore_permissions=True)
                cls._created_reasons.append(r_name)

        # Assert Attendance Reason -> Reason Type mapping
        wfh_rt = frappe.db.get_value("Attendance Reason", "Work From Home", "attendance_reason_type")
        assert wfh_rt == "Work From Home Allowance", (
            f"Attendance Reason 'Work From Home' mapped to '{wfh_rt}', expected 'Work From Home Allowance'"
        )
        late_rt = frappe.db.get_value("Attendance Reason", "Late In", "attendance_reason_type")
        assert late_rt == "Permission", (
            f"Attendance Reason 'Late In' mapped to '{late_rt}', expected 'Permission'"
        )

        # Reason Allocations for TEST_COMPANY (monthly_limit=2, period_start_day=26)
        frappe.db.delete("Attendance Reason Allocation", {"company": TEST_COMPANY})
        for rt, limit in [("Work From Home Allowance", 2), ("Permission", 2)]:
            ra_doc = frappe.get_doc({
                "doctype": "Attendance Reason Allocation",
                "applies_to": "Company",
                "company": TEST_COMPANY,
                "attendance_reason_type": rt,
                "effective_from": "2026-04-01",
                "monthly_limit": limit,
                "period_start_day": 26,
                "docstatus": 1,
            }).insert(ignore_permissions=True)
            cls._created_reason_allocations.append(ra_doc.name)

        frappe.clear_cache()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        errors = []

        cls._cleanup_transactional_data()

        # Delete tracked reason allocations
        for ra in getattr(cls, "_created_reason_allocations", []):
            try:
                frappe.db.set_value("Attendance Reason Allocation", ra, "docstatus", 2)
                frappe.delete_doc("Attendance Reason Allocation", ra, force=1)
            except Exception as e:
                errors.append(f"Attendance Reason Allocation {ra}: {e}")

        # Delete tracked reasons
        for r in getattr(cls, "_created_reasons", []):
            try:
                frappe.delete_doc("Attendance Reason", r, force=1)
            except Exception as e:
                errors.append(f"Attendance Reason {r}: {e}")

        # Delete tracked reason types
        for rt in getattr(cls, "_created_reason_types", []):
            try:
                frappe.delete_doc("Attendance Reason Type", rt, force=1)
            except Exception as e:
                errors.append(f"Attendance Reason Type {rt}: {e}")

        # Delete tracked leave allocations
        for la in getattr(cls, "_created_leave_allocations", []):
            try:
                frappe.db.set_value("Leave Allocation", la, "docstatus", 2)
                frappe.delete_doc("Leave Allocation", la, force=1)
            except Exception as e:
                errors.append(f"Leave Allocation {la}: {e}")

        # Delete tracked leave types
        for lt in getattr(cls, "_created_leave_types", []):
            try:
                frappe.delete_doc("Leave Type", lt, force=1)
            except Exception as e:
                errors.append(f"Leave Type {lt}: {e}")

        # Delete shift assignments
        for sa in frappe.get_all("Shift Assignment", filters={"company": TEST_COMPANY}, pluck="name"):
            try:
                frappe.delete_doc("Shift Assignment", sa, force=1)
            except Exception as e:
                errors.append(f"Shift Assignment {sa}: {e}")

        # Delete employees
        for emp in getattr(cls, "_created_employees", []):
            try:
                frappe.delete_doc("Employee", emp, force=1)
            except Exception as e:
                errors.append(f"Employee {emp}: {e}")

        # Delete users
        for u in getattr(cls, "_created_users", []):
            for up in frappe.get_all("User Permission", filters={"user": u}, pluck="name"):
                try:
                    frappe.delete_doc("User Permission", up, force=1)
                except Exception as e:
                    errors.append(f"User Permission {up}: {e}")
            try:
                frappe.delete_doc("User", u, force=1)
            except Exception as e:
                errors.append(f"User {u}: {e}")

        # Delete Shift Type
        for st in getattr(cls, "_created_shifts", []):
            try:
                frappe.delete_doc("Shift Type", st, force=1)
            except Exception as e:
                errors.append(f"Shift Type {st}: {e}")

        # Delete Holiday List Assignment
        for hla in frappe.get_all("Holiday List Assignment", filters={"assigned_to": TEST_COMPANY}, pluck="name"):
            try:
                frappe.db.set_value("Holiday List Assignment", hla, "docstatus", 2)
                frappe.delete_doc("Holiday List Assignment", hla, force=1)
            except Exception as e:
                errors.append(f"Holiday List Assignment {hla}: {e}")

        # Delete Holiday List
        for hl in getattr(cls, "_created_holiday_lists", []):
            try:
                frappe.delete_doc("Holiday List", hl, force=1)
            except Exception as e:
                errors.append(f"Holiday List {hl}: {e}")

        # Delete Company
        for c in getattr(cls, "_created_companies", []):
            try:
                frappe.delete_doc("Company", c, force=1)
            except Exception as e:
                errors.append(f"Company {c}: {e}")

        if errors:
            print("\n[tearDownClass cleanup errors]:")
            for err in errors:
                print(f"  - {err}")

        super().tearDownClass()

    def setUp(self):
        self.patcher = patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_TIME)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        frappe.set_user("Administrator")

    def tearDown(self):
        self._cleanup_transactional_data()
        frappe.set_user("Administrator")

    @classmethod
    def _ensure_user(cls, email, roles):
        if not frappe.db.exists("User", email):
            u = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": email.split("@")[0],
                "send_welcome_email": 0,
            }).insert(ignore_permissions=True)
            cls._created_users.append(email)
        else:
            u = frappe.get_doc("User", email)
        current_roles = {r.role for r in u.roles}
        for role in roles:
            if role not in current_roles:
                u.append("roles", {"role": role})
        u.save(ignore_permissions=True)

    @classmethod
    def _create_employee(cls, emp_id, first_name, last_name, user_id, reports_to=None, leave_approver=None):
        existing = frappe.db.get_value("Employee", {"user_id": user_id}, "name")
        if existing:
            frappe.db.set_value("Employee", existing, {
                "reports_to": reports_to,
                "leave_approver": leave_approver,
            })
            for up in frappe.get_all("User Permission", filters={"user": user_id}, pluck="name"):
                frappe.delete_doc("User Permission", up, force=1)
            return existing
        doc = frappe.get_doc({
            "doctype": "Employee",
            "employee": emp_id,
            "employee_name": f"{first_name} {last_name}",
            "first_name": first_name,
            "last_name": last_name,
            "company": TEST_COMPANY,
            "user_id": user_id,
            "reports_to": reports_to,
            "leave_approver": leave_approver,
            "date_of_joining": "2026-01-01",
            "status": "Active",
            "default_shift": SHIFT_TYPE,
            "holiday_list": HOLIDAY_LIST,
            "employee_number": emp_id,
            "gender": "Female",
            "custom_roles_responsibilities": "Test Employee",
            "ctc": 100000,
            "create_user_permission": 0,
        })
        doc.insert(ignore_permissions=True, ignore_mandatory=True)
        cls._created_employees.append(doc.name)
        for up in frappe.get_all("User Permission", filters={"user": user_id}, pluck="name"):
            frappe.delete_doc("User Permission", up, force=1)
        return doc.name

    @classmethod
    def _create_allocation(cls, employee, leave_type, days):
        existing = frappe.db.get_value(
            "Leave Allocation",
            {"employee": employee, "leave_type": leave_type, "docstatus": 1},
            "name",
        )
        if not existing:
            doc = frappe.get_doc({
                "doctype": "Leave Allocation",
                "employee": employee,
                "leave_type": leave_type,
                "from_date": "2026-01-01",
                "to_date": "2026-12-31",
                "new_leaves_allocated": days,
                "total_leaves_allocated": days,
                "company": TEST_COMPANY,
                "docstatus": 1,
            })
            doc.insert(ignore_permissions=True, ignore_mandatory=True)
            cls._created_leave_allocations.append(doc.name)

    @classmethod
    def _cleanup_transactional_data(cls):
        frappe.db.delete("Attendance", {"company": TEST_COMPANY})
        frappe.db.delete("Attendance Request", {"company": TEST_COMPANY})
        frappe.db.delete("Leave Application", {"company": TEST_COMPANY})

    @classmethod
    def _cleanup_all(cls):
        cls._cleanup_transactional_data()
        for u in [EMP_USER, APPR_USER, HR_MGR_USER]:
            emp = frappe.db.get_value("Employee", {"user_id": u}, "name")
            if emp:
                try:
                    frappe.delete_doc("Employee", emp, force=1)
                except Exception:
                    pass
        frappe.db.delete("Email Queue", {"reference_doctype": ["in", ["Attendance Request", "Leave Application", "Attendance"]]})
        frappe.db.delete("Workflow Action", {"reference_doctype": ["in", ["Attendance Request", "Leave Application"]]})
        frappe.db.delete("Shift Assignment", {"company": TEST_COMPANY})

    def _seed_attendance_request(self, employee, reason, dt):
        doc = frappe.get_doc({
            "doctype": "Attendance Request",
            "employee": employee,
            "from_date": dt,
            "to_date": dt,
            "reason": reason,
            "company": TEST_COMPANY,
            "workflow_state": "Pending Approval",
            "docstatus": 0,
        })
        doc.flags.ignore_validate = True
        doc.insert(ignore_permissions=True)
        doc.flags.pop("ignore_validate", None)
        doc.reload()
        # Database round-trip assertion
        row = frappe.db.get_value("Attendance Request", doc.name, ["name", "workflow_state", "docstatus"], as_dict=True)
        self.assertIsNotNone(row)
        self.assertEqual(row.workflow_state, "Pending Approval")
        self.assertEqual(row.docstatus, 0)
        return doc

    def _seed_leave_application(self, employee, from_dt, to_dt):
        doc = frappe.get_doc({
            "doctype": "Leave Application",
            "employee": employee,
            "leave_type": LEAVE_TYPE_NAME,
            "from_date": from_dt,
            "to_date": to_dt,
            "leave_approver": APPR_USER,
            "company": TEST_COMPANY,
            "status": "Open",
            "docstatus": 0,
            "follow_via_email": 0,
        })
        doc.flags.ignore_validate = True
        with patch("frappe.sendmail"):
            doc.insert(ignore_permissions=True)
        doc.flags.pop("ignore_validate", None)
        doc.reload()
        # Database round-trip assertion
        row = frappe.db.get_value("Leave Application", doc.name, ["name", "status", "docstatus"], as_dict=True)
        self.assertIsNotNone(row)
        self.assertEqual(row.status, "Open")
        self.assertEqual(row.docstatus, 0)
        return doc

    # =========================================================================
    # Tests
    # =========================================================================

    def test_01_non_hr_approver_approves_attendance_request_in_locked_period(self):
        """1. Non-HR approver Approves an Attendance Request dated in a locked period:
        succeeds (docstatus 1, state Approved) AND Attendance row exists.
        """
        req = self._seed_attendance_request(self.test_emp, "Work From Home", LOCKED_DATE_1)
        self.assertEqual(frappe.db.count("Attendance", {"employee": self.test_emp, "attendance_date": LOCKED_DATE_1}), 0)

        frappe.set_user(APPR_USER)
        frappe.model.workflow.apply_workflow(req, "Approve")

        req.reload()
        self.assertEqual(req.docstatus, 1)
        self.assertEqual(req.workflow_state, "Approved")
        att = frappe.db.get_value("Attendance", {"employee": self.test_emp, "attendance_date": LOCKED_DATE_1}, ["name", "status"], as_dict=True)
        self.assertIsNotNone(att)
        self.assertEqual(att.status, "Work From Home")

    def test_02_non_hr_approver_approves_leave_application_in_locked_period(self):
        """2. Same for Leave Application: Approve succeeds AND Attendance row exists."""
        leave = self._seed_leave_application(self.test_emp, LOCKED_DATE_LEAVE, LOCKED_DATE_LEAVE)
        self.assertEqual(frappe.db.count("Attendance", {"employee": self.test_emp, "attendance_date": LOCKED_DATE_LEAVE}), 0)

        frappe.set_user(APPR_USER)
        doc = frappe.get_doc("Leave Application", leave.name)
        doc.status = "Approved"
        with patch("frappe.sendmail"):
            doc.save()

        doc.reload()
        self.assertEqual(doc.docstatus, 1)
        self.assertEqual(doc.status, "Approved")
        att = frappe.db.get_value("Attendance", {"employee": self.test_emp, "attendance_date": LOCKED_DATE_LEAVE}, ["name", "status"], as_dict=True)
        self.assertIsNotNone(att)
        self.assertEqual(att.status, "On Leave")

    def test_03_non_hr_approver_rejects_attendance_request_in_locked_period(self):
        """3. Non-HR approver Rejects an Attendance Request in a locked period: succeeds."""
        req = self._seed_attendance_request(self.test_emp, "Work From Home", LOCKED_DATE_1)
        frappe.set_user(APPR_USER)
        frappe.model.workflow.apply_workflow(req, "Reject")

        req.reload()
        self.assertEqual(req.workflow_state, "Rejected")
        self.assertEqual(req.docstatus, 0)

    def test_04_non_hr_approver_rejects_leave_application_in_locked_period(self):
        """4. Non-HR approver Rejects a Leave Application in a locked period: succeeds (covers auto-submit)."""
        leave = self._seed_leave_application(self.test_emp, LOCKED_DATE_LEAVE, LOCKED_DATE_LEAVE)
        frappe.set_user(APPR_USER)
        doc = frappe.get_doc("Leave Application", leave.name)
        doc.status = "Rejected"
        with patch("frappe.sendmail"):
            doc.save()

        doc.reload()
        self.assertEqual(doc.docstatus, 1)
        self.assertEqual(doc.status, "Rejected")

    def test_05_employee_inserts_in_locked_period_is_blocked(self):
        """5. Employee inserts an Attendance Request or Leave Application for a locked date: blocked (lock message)."""
        frappe.set_user(EMP_USER)

        # Attendance Request insert in locked period
        ar = frappe.get_doc({
            "doctype": "Attendance Request",
            "employee": self.test_emp,
            "from_date": LOCKED_DATE_1,
            "to_date": LOCKED_DATE_1,
            "reason": "Work From Home",
            "company": TEST_COMPANY,
        })
        with self.assertRaises(frappe.ValidationError) as cm_ar:
            ar.insert()
        self.assertIn("That payroll period is locked. Please contact HR.", str(cm_ar.exception))

        # Leave Application insert in locked period
        la = frappe.get_doc({
            "doctype": "Leave Application",
            "employee": self.test_emp,
            "leave_type": LEAVE_TYPE_NAME,
            "from_date": LOCKED_DATE_LEAVE,
            "to_date": LOCKED_DATE_LEAVE,
            "leave_approver": APPR_USER,
            "company": TEST_COMPANY,
            "follow_via_email": 0
        })
        with patch("frappe.sendmail"):
            with self.assertRaises(frappe.ValidationError) as cm_la:
                la.insert()
            self.assertIn("That payroll period is locked. Please contact HR.", str(cm_la.exception))

    def test_06_employee_edits_dates_of_pending_request_into_locked_date_blocked(self):
        """6. Employee edits dates of an existing pending request into a locked date: blocked."""
        # Seed pending request in OPEN period
        req = self._seed_attendance_request(self.test_emp, "Work From Home", OPEN_DATE)

        frappe.set_user(EMP_USER)
        doc = frappe.get_doc("Attendance Request", req.name)
        doc.from_date = LOCKED_DATE_1
        doc.to_date = LOCKED_DATE_1
        with self.assertRaises(frappe.ValidationError) as cm_ar:
            doc.save()
        self.assertIn("That payroll period is locked. Please contact HR.", str(cm_ar.exception))

        # Same for Leave Application
        leave = self._seed_leave_application(self.test_emp, OPEN_DATE, OPEN_DATE)
        doc_la = frappe.get_doc("Leave Application", leave.name)
        doc_la.from_date = LOCKED_DATE_LEAVE
        doc_la.to_date = LOCKED_DATE_LEAVE
        with patch("frappe.sendmail"):
            with self.assertRaises(frappe.ValidationError) as cm_la:
                doc_la.save()
            self.assertIn("That payroll period is locked. Please contact HR.", str(cm_la.exception))

    def test_07_hr_manager_inserting_in_locked_period_is_allowed(self):
        """7. HR Manager inserting in a locked period: allowed."""
        frappe.set_user(HR_MGR_USER)

        ar = frappe.get_doc({
            "doctype": "Attendance Request",
            "employee": self.test_emp,
            "from_date": LOCKED_DATE_1,
            "to_date": LOCKED_DATE_1,
            "reason": "Work From Home",
            "company": TEST_COMPANY,
        })
        ar.insert()
        self.assertTrue(bool(ar.name))

        la = frappe.get_doc({
            "doctype": "Leave Application",
            "employee": self.test_emp,
            "leave_type": LEAVE_TYPE_NAME,
            "from_date": LOCKED_DATE_LEAVE,
            "to_date": LOCKED_DATE_LEAVE,
            "leave_approver": APPR_USER,
            "company": TEST_COMPANY,
            "follow_via_email": 0
        })
        with patch("frappe.sendmail"):
            la.insert()
        self.assertTrue(bool(la.name))

    def test_08_self_approval_of_own_request_blocked(self):
        """8. Self-approval of own request: blocked with 'Self-approval...' message."""
        frappe.set_user(HR_MGR_USER)

        # Leave Application
        doc_la = frappe.get_doc({
            "doctype": "Leave Application",
            "employee": self.hr_emp,
            "leave_type": LEAVE_TYPE_NAME,
            "from_date": LOCKED_DATE_LEAVE,
            "to_date": LOCKED_DATE_LEAVE,
            "leave_approver": APPR_USER,
            "company": TEST_COMPANY,
            "status": "Approved",
            "follow_via_email": 0
        })
        with patch("frappe.sendmail"):
            with self.assertRaises(frappe.ValidationError) as cm:
                doc_la.insert()
            self.assertIn("Self-approval for leaves is not allowed", str(cm.exception))

        # Attendance Request
        doc_ar = frappe.get_doc({
            "doctype": "Attendance Request",
            "employee": self.hr_emp,
            "from_date": LOCKED_DATE_1,
            "to_date": LOCKED_DATE_1,
            "reason": "Work From Home",
            "company": TEST_COMPANY,
        })
        doc_ar.insert()
        with self.assertRaises(frappe.ValidationError) as cm_ar:
            doc_ar.submit()
        self.assertIn("Self-approval for Attendance Requests is not allowed", str(cm_ar.exception))

    def test_09_group2_approval_time_limit_still_enforced(self):
        """9. Group 2 approval-time limit still enforced: approver Approves 3 pending WFH
        requests of an employee (limit 2) in a locked period: 3rd blocked with 'Monthly limit exceeded'.
        No try/except: assert r1 and r2 succeed (docstatus 1), r3 raises monthly limit exceeded.
        (Before the Part 2 fix, fails at approving r1 because the payroll lock blocks approval).
        """
        r1 = self._seed_attendance_request(self.test_emp, "Work From Home", LOCKED_DATE_1)
        r2 = self._seed_attendance_request(self.test_emp, "Work From Home", LOCKED_DATE_2)
        r3 = self._seed_attendance_request(self.test_emp, "Work From Home", LOCKED_DATE_3)

        frappe.set_user(APPR_USER)

        # Approve 1 and 2
        frappe.model.workflow.apply_workflow(r1, "Approve")
        r1.reload()
        self.assertEqual(r1.docstatus, 1)

        frappe.model.workflow.apply_workflow(r2, "Approve")
        r2.reload()
        self.assertEqual(r2.docstatus, 1)

        # 3rd must raise monthly limit exceeded
        with self.assertRaises(frappe.ValidationError) as cm:
            frappe.model.workflow.apply_workflow(r3, "Approve")
        self.assertIn("Monthly limit exceeded", str(cm.exception))

    def test_10_no_leak_direct_attendance_save_after_approval_blocked(self):
        """10. NO LEAK: after an approver approves a locked-period request, the SAME session
        user saves a direct edit of an Attendance row in a locked period: blocked by the Attendance lock.
        First assert approval succeeded, then edit existing attendance row and assert lock message.
        Also assert frappe.flags.in_attendance_approval is falsy after approval.
        (Before the Part 2 fix, fails at the approval step because the payroll lock blocks approval).
        """
        req = self._seed_attendance_request(self.test_emp, "Work From Home", LOCKED_DATE_1)

        # Seed an existing Attendance row with a locked date using ignore_validate
        existing_att = frappe.get_doc({
            "doctype": "Attendance",
            "employee": self.test_emp,
            "attendance_date": LOCKED_DATE_2,
            "status": "Absent",
            "company": TEST_COMPANY,
            "docstatus": 0,
        })
        existing_att.flags.ignore_validate = True
        existing_att.insert(ignore_permissions=True)
        existing_att.flags.pop("ignore_validate", None)

        frappe.set_user(APPR_USER)

        # 1. Assert approval succeeded
        frappe.model.workflow.apply_workflow(req, "Approve")
        req.reload()
        self.assertEqual(req.docstatus, 1)
        self.assertEqual(req.workflow_state, "Approved")
        self.assertFalse(getattr(frappe.flags, "in_attendance_approval", False))

        # 2. As the SAME session user, edit existing Attendance row in locked period -> blocked
        att_doc = frappe.get_doc("Attendance", existing_att.name)
        att_doc.status = "Present"
        with self.assertRaises(frappe.ValidationError) as cm:
            att_doc.save(ignore_permissions=True)
        self.assertIn("cannot be modified directly", str(cm.exception))
        self.assertFalse(getattr(frappe.flags, "in_attendance_approval", False))

    def test_11_direct_manual_edit_of_attendance_in_locked_period_blocked(self):
        """11. Direct manual edit of an Attendance row in a locked period by a non-exempt user: blocked."""
        frappe.set_user(APPR_USER)
        att = frappe.get_doc({
            "doctype": "Attendance",
            "employee": self.test_emp,
            "attendance_date": LOCKED_DATE_1,
            "status": "Absent",
            "company": TEST_COMPANY,
        })
        with self.assertRaises(frappe.ValidationError) as cm:
            att.insert(ignore_permissions=True)
        self.assertIn("cannot be modified directly", str(cm.exception))

    def test_12a_administrator_ignore_validate_submit_observed(self):
        """12a. REPORT ONLY: Administrator with doc.flags.ignore_validate then submit()
        on a locked-period request. Seeded through shared helper _seed_attendance_request.
        """
        req = self._seed_attendance_request(self.test_emp, "Work From Home", LOCKED_DATE_1)
        frappe.set_user("Administrator")

        doc = frappe.get_doc("Attendance Request", req.name)
        doc.flags.ignore_validate = True
        try:
            doc.submit()
            print(f"\n[test_12a observed, not desired] submit(ignore_validate=True) succeeded, docstatus={doc.docstatus}")
        except Exception as e:
            print(f"\n[test_12a observed, not desired] submit(ignore_validate=True) raised: {e}")

    def test_12b_administrator_db_set_value_approval_observed(self):
        """12b. REPORT ONLY: Administrator frappe.db.set_value approval on a locked-period request.
        Seeded through shared helper _seed_attendance_request.
        """
        req2 = self._seed_attendance_request(self.test_emp, "Work From Home", LOCKED_DATE_2)
        frappe.set_user("Administrator")

        frappe.db.set_value("Attendance Request", req2.name, {"workflow_state": "Approved", "docstatus": 1})
        v = frappe.db.get_value("Attendance Request", req2.name, ["workflow_state", "docstatus"], as_dict=True)
        print(f"\n[test_12b observed, not desired] db.set_value directly set docstatus={v.docstatus}, workflow_state={v.workflow_state} (bypasses all hooks)")

    def test_13_non_hr_approver_inserts_leave_with_status_approved_is_blocked(self):
        """13. A non-HR Leave Approver INSERTS a new Leave Application for a locked date
        with status 'Approved': blocked (closes the status loophole).
        """
        frappe.set_user(APPR_USER)
        la = frappe.get_doc({
            "doctype": "Leave Application",
            "employee": self.test_emp,
            "leave_type": LEAVE_TYPE_NAME,
            "from_date": LOCKED_DATE_LEAVE,
            "to_date": LOCKED_DATE_LEAVE,
            "leave_approver": APPR_USER,
            "company": TEST_COMPANY,
            "status": "Approved",
            "follow_via_email": 0
        })
        with patch("frappe.sendmail"):
            with self.assertRaises(frappe.ValidationError) as cm:
                la.insert()
            self.assertIn("That payroll period is locked. Please contact HR.", str(cm.exception))

    def test_14_non_hr_approver_changing_dates_during_approval_is_blocked(self):
        """14. A non-HR approver changes the dates of a pending locked Leave Application
        into a different locked date while approving: blocked.
        # This must stay blocked after the fix because the dates CHANGED (D1 rule), not because of status.
        """
        leave = self._seed_leave_application(self.test_emp, LOCKED_DATE_LEAVE, LOCKED_DATE_LEAVE)
        frappe.set_user(APPR_USER)
        doc = frappe.get_doc("Leave Application", leave.name)
        doc.from_date = LOCKED_DATE_1
        doc.to_date = LOCKED_DATE_1
        with patch("frappe.sendmail"):
            with self.assertRaises(frappe.ValidationError) as cm:
                doc.save()
            self.assertIn("That payroll period is locked. Please contact HR.", str(cm.exception))

    def test_15_approver_approves_leave_with_existing_absent_attendance_becomes_on_leave(self):
        """15. A non-HR approver approves a Leave Application whose dates are unchanged and locked,
        where an Absent Attendance row already exists: succeeds and row becomes On Leave (asserted from DB).
        """
        # Seed Absent attendance
        att = frappe.get_doc({
            "doctype": "Attendance",
            "employee": self.test_emp,
            "attendance_date": LOCKED_DATE_LEAVE,
            "status": "Absent",
            "company": TEST_COMPANY,
            "docstatus": 1,
        })
        att.flags.ignore_validate = True
        att.insert(ignore_permissions=True)

        leave = self._seed_leave_application(self.test_emp, LOCKED_DATE_LEAVE, LOCKED_DATE_LEAVE)
        frappe.set_user(APPR_USER)
        doc = frappe.get_doc("Leave Application", leave.name)
        doc.status = "Approved"
        with patch("frappe.sendmail"):
            doc.save()

        doc.reload()
        self.assertEqual(doc.status, "Approved")
        self.assertEqual(doc.docstatus, 1)
        updated_att = frappe.db.get_value("Attendance", {"employee": self.test_emp, "attendance_date": LOCKED_DATE_LEAVE}, "status")
        self.assertEqual(updated_att, "On Leave")

    def test_16_approver_approves_leave_with_no_existing_attendance_creates_row(self):
        """16. Same approval where NO Attendance row exists: succeeds and row created (asserted from DB)."""
        self.assertEqual(frappe.db.count("Attendance", {"employee": self.test_emp, "attendance_date": LOCKED_DATE_LEAVE}), 0)
        leave = self._seed_leave_application(self.test_emp, LOCKED_DATE_LEAVE, LOCKED_DATE_LEAVE)

        frappe.set_user(APPR_USER)
        doc = frappe.get_doc("Leave Application", leave.name)
        doc.status = "Approved"
        with patch("frappe.sendmail"):
            doc.save()

        doc.reload()
        self.assertEqual(doc.status, "Approved")
        self.assertEqual(doc.docstatus, 1)
        new_att = frappe.db.get_value("Attendance", {"employee": self.test_emp, "attendance_date": LOCKED_DATE_LEAVE}, "status")
        self.assertEqual(new_att, "On Leave")

    def test_17_leave_covering_holiday_with_existing_attendance_observation(self):
        """17. Leave covering a holiday date with existing Attendance row (include_holiday off):
        asserts upstream holiday validation message.
        This message comes from upstream validation, not from before_cancel or payroll lock,
        proving that the leave-side P4 bypass flag is NOT justified by this test.
        """
        holiday_date = "2026-10-15"
        att = frappe.get_doc({
            "doctype": "Attendance",
            "employee": self.test_emp,
            "attendance_date": holiday_date,
            "status": "Absent",
            "company": TEST_COMPANY,
            "docstatus": 1,
        })
        att.flags.ignore_validate = True
        att.insert(ignore_permissions=True)

        leave = self._seed_leave_application(self.test_emp, holiday_date, holiday_date)
        frappe.set_user(APPR_USER)
        doc = frappe.get_doc("Leave Application", leave.name)
        doc.status = "Approved"
        with patch("frappe.sendmail"):
            with self.assertRaises(frappe.ValidationError) as cm:
                doc.save()
            self.assertIn(
                "The day(s) on which you are applying for leave are holidays. You need not apply for leave.",
                str(cm.exception),
            )
            print(
                f"\n[test_17 observed] Leave approval covering holiday BLOCKED by upstream holiday validation: {cm.exception}"
            )

    def test_18_p4_context_manager_nesting(self):
        """18. The P4 context manager nests correctly: after inner use, flag is still True;
        after outer one, flag is falsy; pre-existing True value is restored (test helper directly).
        """
        try:
            from hrms_custom.hrms_custom.utils.attendance_lock import bypass_attendance_lock_for_approval
        except ImportError:
            self.fail("bypass_attendance_lock_for_approval context manager not implemented in attendance_lock.py yet")

        initial = getattr(frappe.flags, "in_attendance_approval", False)
        self.assertFalse(initial)

        # 1. Nesting test
        with bypass_attendance_lock_for_approval():
            self.assertTrue(frappe.flags.in_attendance_approval)
            with bypass_attendance_lock_for_approval():
                self.assertTrue(frappe.flags.in_attendance_approval)
            self.assertTrue(frappe.flags.in_attendance_approval)

        self.assertFalse(frappe.flags.in_attendance_approval)

        # 2. Pre-existing True restoration test
        frappe.flags.in_attendance_approval = True
        try:
            with bypass_attendance_lock_for_approval():
                self.assertTrue(frappe.flags.in_attendance_approval)
            self.assertTrue(frappe.flags.in_attendance_approval)
        finally:
            frappe.flags.in_attendance_approval = False

    def test_19_non_hr_approver_changing_dates_during_attendance_request_approval_is_blocked(self):
        """19. Attendance Request counterpart of test 14:
        An approver who changes an Attendance Request's dates into a locked date on a pending request is blocked.
        # Must stay blocked after the fix because dates CHANGED (D1 rule), not because of status.
        """
        req = self._seed_attendance_request(self.test_emp, "Work From Home", OPEN_DATE)
        frappe.set_user(APPR_USER)
        doc = frappe.get_doc("Attendance Request", req.name)
        doc.from_date = LOCKED_DATE_1
        doc.to_date = LOCKED_DATE_1
        with self.assertRaises(frappe.ValidationError) as cm:
            doc.save()
        self.assertIn("That payroll period is locked. Please contact HR.", str(cm.exception))
