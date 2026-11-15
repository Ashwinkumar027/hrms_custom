import json
from datetime import date, datetime, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.classes.integration_test_case import IntegrationTestCase
from frappe.utils import getdate

TEST_COMPANY = "_Test Limit Company"
TEST_COMPANY_ABBR = "_TLC2"
HOLIDAY_LIST_NAME = "_Test Limit Holiday List"
SHIFT_TYPE_NAME = "_Test Limit Shift"

EMP_USER = "test_limit_emp@example.com"
APPROVER_USER = "test_limit_approver@example.com"
HR_MGR_USER = "test_limit_hr@example.com"

FROZEN_DATETIME = datetime(2026, 11, 15, 12, 0, 0)
FROZEN_DATE_STR = "2026-11-15"

CYCLE_START = "2026-10-26"
CYCLE_END = "2026-11-25"
PREV_CYCLE_DATE = "2026-10-24"
CYCLE_DATE_1 = "2026-11-10"
CYCLE_DATE_2 = "2026-11-11"
CYCLE_DATE_3 = "2026-11-12"
CYCLE_DATE_4 = "2026-11-13"


class TestAttendanceRequestLimit(IntegrationTestCase):
    """
    Comprehensive test suite for Attendance Request limits at apply time (Group 2, Issue 3).
    Ensures allocation limits are enforced at apply time (validate on docstatus 0)
    using the exact same allocation and counting logic as approval time.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._suite_start_time = frappe.utils.now_datetime()
        frappe.set_user("Administrator")

        cls._created_reason_types = []
        cls._created_reasons = []

        # 1. Company
        if not frappe.db.exists("Company", TEST_COMPANY):
            frappe.get_doc({
                "doctype": "Company",
                "company_name": TEST_COMPANY,
                "abbr": TEST_COMPANY_ABBR,
                "default_currency": "INR",
                "country": "India",
            }).insert(ignore_permissions=True)

        # 2. Holiday List
        if not frappe.db.exists("Holiday List", HOLIDAY_LIST_NAME):
            frappe.get_doc({
                "doctype": "Holiday List",
                "holiday_list_name": HOLIDAY_LIST_NAME,
                "from_date": "2026-01-01",
                "to_date": "2026-12-31",
                "country": "India",
            }).insert(ignore_permissions=True)

        # 2b. Holiday List Assignment for Company
        if not frappe.db.exists("Holiday List Assignment", {"applicable_for": "Company", "assigned_to": TEST_COMPANY, "docstatus": 1}):
            frappe.get_doc({
                "doctype": "Holiday List Assignment",
                "applicable_for": "Company",
                "assigned_to": TEST_COMPANY,
                "holiday_list": HOLIDAY_LIST_NAME,
                "from_date": "2026-01-01",
                "docstatus": 1,
            }).insert(ignore_permissions=True)

        # 3. Shift Type
        if not frappe.db.exists("Shift Type", SHIFT_TYPE_NAME):
            frappe.get_doc({
                "doctype": "Shift Type",
                "name": SHIFT_TYPE_NAME,
                "shift_type_name": SHIFT_TYPE_NAME,
                "start_time": "09:00:00",
                "end_time": "18:00:00",
                "holiday_list": HOLIDAY_LIST_NAME,
                "enable_auto_attendance": 0,
            }).insert(ignore_permissions=True)

        # 4. Users
        cls._create_user(EMP_USER, ["Employee", "Employee Self Service"])
        cls._create_user(APPROVER_USER, ["Employee", "Leave Approver", "Employee Self Service"])
        cls._create_user(HR_MGR_USER, ["Employee", "HR Manager", "Leave Approver", "Employee Self Service"])

        # 5. Employees (Hierarchy: Approver -> Employee reports to Approver)
        cls.approver_emp = cls._create_employee("EMP-LIMIT-002", "Limit", "Approver", APPROVER_USER)
        cls.test_emp = cls._create_employee("EMP-LIMIT-001", "Limit", "Employee", EMP_USER, reports_to=cls.approver_emp)
        cls.hr_emp = cls._create_employee("EMP-LIMIT-003", "Limit", "HRManager", HR_MGR_USER)

        from frappe.utils.nestedset import rebuild_tree
        rebuild_tree("Employee")

        # Set leave approver on test_emp
        frappe.db.set_value("Employee", cls.test_emp, "leave_approver", APPROVER_USER)
        frappe.db.set_value("Employee", cls.hr_emp, "leave_approver", APPROVER_USER)

        # 5b. Shift Assignments
        cls._create_shift_assignment(cls.test_emp)
        cls._create_shift_assignment(cls.approver_emp)
        cls._create_shift_assignment(cls.hr_emp)

        # 6. Ensure Attendance Reason Types exist (track created)
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

        # 7. Ensure Attendance Reasons exist (track created)
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
        assert wfh_rt == "Work From Home Allowance", f"Attendance Reason 'Work From Home' mapped to '{wfh_rt}', expected 'Work From Home Allowance'"
        late_rt = frappe.db.get_value("Attendance Reason", "Late In", "attendance_reason_type")
        assert late_rt == "Permission", f"Attendance Reason 'Late In' mapped to '{late_rt}', expected 'Permission'"
        early_rt = frappe.db.get_value("Attendance Reason", "Early Out", "attendance_reason_type")
        assert early_rt == "Permission", f"Attendance Reason 'Early Out' mapped to '{early_rt}', expected 'Permission'"

        # 8. Reason Allocations for TEST_COMPANY
        # WFH limit = 2, Permission limit = 2, cycle start = 26
        frappe.db.delete("Attendance Reason Allocation", {"company": TEST_COMPANY})
        for rt, limit in [("Work From Home Allowance", 2), ("Permission", 2)]:
            frappe.get_doc({
                "doctype": "Attendance Reason Allocation",
                "applies_to": "Company",
                "company": TEST_COMPANY,
                "attendance_reason_type": rt,
                "effective_from": "2026-04-01",
                "monthly_limit": limit,
                "period_start_day": 26,
                "docstatus": 1,
            }).insert(ignore_permissions=True)

        frappe.clear_cache()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        errors = []

        # 1. Cancel and delete all Attendance Requests for TEST_COMPANY
        for name in frappe.get_all("Attendance Request", filters={"company": TEST_COMPANY}, pluck="name"):
            try:
                doc = frappe.get_doc("Attendance Request", name)
                if doc.docstatus == 1:
                    doc.cancel()
                doc.delete(force=True)
            except Exception as e:
                errors.append(f"Failed deleting Attendance Request {name}: {e}")

        # Delete any Attendance records generated for test employees
        for att in frappe.get_all("Attendance", filters={"employee": ["in", [cls.test_emp, cls.approver_emp, cls.hr_emp]]}, pluck="name"):
            try:
                adoc = frappe.get_doc("Attendance", att)
                if adoc.docstatus == 1:
                    adoc.cancel()
                adoc.delete(force=True)
            except Exception as e:
                errors.append(f"Failed deleting Attendance {att}: {e}")

        # Check leftover attendance requests
        leftover_ar = frappe.db.count("Attendance Request", {"company": TEST_COMPANY})
        if leftover_ar != 0:
            errors.append(f"Leftover Attendance Requests for {TEST_COMPANY}: {leftover_ar}")

        # 2. Delete allocations & holiday list assignment & shift assignments
        frappe.db.delete("Attendance Reason Allocation", {"company": TEST_COMPANY})
        frappe.db.delete("Holiday List Assignment", {"assigned_to": TEST_COMPANY})
        frappe.db.delete("Shift Assignment", {"employee": ["in", [cls.test_emp, cls.approver_emp, cls.hr_emp]]})

        # 3. Delete tracked created reasons & reason types
        for r_name in cls._created_reasons:
            if frappe.db.exists("Attendance Reason", r_name):
                try:
                    frappe.delete_doc("Attendance Reason", r_name, force=True, ignore_permissions=True)
                except Exception as e:
                    errors.append(f"Failed deleting Attendance Reason {r_name}: {e}")

        for rt in cls._created_reason_types:
            if frappe.db.exists("Attendance Reason Type", rt):
                try:
                    frappe.delete_doc("Attendance Reason Type", rt, force=True, ignore_permissions=True)
                except Exception as e:
                    errors.append(f"Failed deleting Attendance Reason Type {rt}: {e}")

        # 4. Delete employees
        for emp in [cls.test_emp, cls.approver_emp, cls.hr_emp]:
            if frappe.db.exists("Employee", emp):
                try:
                    frappe.delete_doc("Employee", emp, force=True, ignore_permissions=True)
                except Exception as e:
                    errors.append(f"Failed deleting Employee {emp}: {e}")

        # 5. Delete users
        for u in [EMP_USER, APPROVER_USER, HR_MGR_USER]:
            if frappe.db.exists("User", u):
                try:
                    frappe.delete_doc("User", u, force=True, ignore_permissions=True)
                except Exception as e:
                    errors.append(f"Failed deleting User {u}: {e}")

        # 6. Delete Shift Type & Holiday List & Company
        if frappe.db.exists("Shift Type", SHIFT_TYPE_NAME):
            try:
                frappe.delete_doc("Shift Type", SHIFT_TYPE_NAME, force=True, ignore_permissions=True)
            except Exception as e:
                errors.append(f"Failed deleting Shift Type: {e}")
        if frappe.db.exists("Holiday List", HOLIDAY_LIST_NAME):
            try:
                frappe.delete_doc("Holiday List", HOLIDAY_LIST_NAME, force=True, ignore_permissions=True)
            except Exception as e:
                errors.append(f"Failed deleting Holiday List: {e}")
        if frappe.db.exists("Company", TEST_COMPANY):
            try:
                frappe.delete_doc("Company", TEST_COMPANY, force=True, ignore_permissions=True)
            except Exception as e:
                errors.append(f"Failed deleting Company: {e}")

        # 7. Purge audit comments/versions
        frappe.db.sql(
            "DELETE FROM `tabComment` WHERE creation >= %s AND reference_doctype IN ('Attendance Request', 'Employee', 'Company')",
            (cls._suite_start_time,)
        )
        frappe.db.sql(
            "DELETE FROM `tabVersion` WHERE creation >= %s AND ref_doctype IN ('Attendance Request', 'Employee', 'Company')",
            (cls._suite_start_time,)
        )
        frappe.db.sql(
            "DELETE FROM `tabWorkflow Action` WHERE reference_doctype = 'Attendance Request' AND creation >= %s",
            (cls._suite_start_time,)
        )
        frappe.db.sql(
            "DELETE FROM `tabEmail Queue` WHERE reference_doctype = 'Attendance Request' AND creation >= %s",
            (cls._suite_start_time,)
        )

        if errors:
            print("\n[Cleanup warnings in tearDownClass]:")
            for err in errors:
                print("  -", err)

        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._patches = [
            patch("hrms_custom.hrms_custom.utils.attendance_lock.now_datetime", return_value=FROZEN_DATETIME),
            patch("frappe.utils.today", return_value=FROZEN_DATE_STR),
            patch("frappe.utils.data.today", return_value=FROZEN_DATE_STR),
            patch("frappe.utils.nowdate", return_value=FROZEN_DATE_STR),
            patch("frappe.utils.data.nowdate", return_value=FROZEN_DATE_STR),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        frappe.set_user("Administrator")
        errors = []
        for name in frappe.get_all("Attendance Request", filters={"company": TEST_COMPANY}, pluck="name"):
            try:
                doc = frappe.get_doc("Attendance Request", name)
                if doc.docstatus == 1:
                    doc.cancel()
                doc.delete(force=True)
            except Exception as e:
                errors.append(f"Failed deleting Attendance Request {name} in tearDown: {e}")

        for att in frappe.get_all("Attendance", filters={"employee": ["in", [self.test_emp, self.approver_emp, self.hr_emp]]}, pluck="name"):
            try:
                adoc = frappe.get_doc("Attendance", att)
                if adoc.docstatus == 1:
                    adoc.cancel()
                adoc.delete(force=True)
            except Exception as e:
                errors.append(f"Failed deleting Attendance {att} in tearDown: {e}")

        if errors:
            print("\n[tearDown errors]:", errors)

        for p in reversed(self._patches):
            p.stop()
        super().tearDown()

    @classmethod
    def _create_user(cls, email, roles):
        if not frappe.db.exists("User", email):
            user = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": email.split("@")[0],
                "send_welcome_email": 0,
            }).insert(ignore_permissions=True)
            for r in roles:
                user.add_roles(r)

    @classmethod
    def _create_employee(cls, emp_id, first_name, last_name, user_id, reports_to=None):
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
            "reports_to": reports_to,
        }).insert(ignore_permissions=True, ignore_mandatory=True)
        return emp.name

    @classmethod
    def _create_shift_assignment(cls, employee):
        if not frappe.db.exists("Shift Assignment", {"employee": employee, "docstatus": 1}):
            frappe.get_doc({
                "doctype": "Shift Assignment",
                "employee": employee,
                "shift_type": SHIFT_TYPE_NAME,
                "start_date": "2026-01-01",
                "status": "Active",
                "docstatus": 1,
            }).insert(ignore_permissions=True)

    def _seed_attendance_request(
        self,
        employee,
        reason,
        from_date,
        to_date=None,
        docstatus=0,
        workflow_state="Pending Approval",
        half_day=0,
        explanation="Test explanation",
    ):
        """
        Seeding helper (T1-a): creates existing attendance request state bypassing validate/apply check.
        Uses doc.flags.ignore_validate = True, sets workflow_state and docstatus explicitly,
        and verifies that DB row exactly matches expected state.
        Clears flags.ignore_validate afterwards so subsequent test actions are not bypassed.
        """
        if to_date is None:
            to_date = from_date
        owner = frappe.db.get_value("Employee", employee, "user_id") or "Administrator"
        doc = frappe.get_doc({
            "doctype": "Attendance Request",
            "employee": employee,
            "reason": reason,
            "from_date": from_date,
            "to_date": to_date,
            "half_day": half_day,
            "half_day_date": from_date if half_day else None,
            "company": TEST_COMPANY,
            "explanation": explanation,
            "owner": owner,
        })
        doc.flags.ignore_validate = True
        doc.insert(ignore_permissions=True)
        if docstatus == 1:
            doc.db_set("workflow_state", "Approved")
            doc.db_set("docstatus", 1)
        elif workflow_state != "Pending Approval":
            doc.db_set("workflow_state", workflow_state)
        doc.db_set("owner", owner)

        # DB round-trip assertion (T1)
        row = frappe.db.get_value(
            "Attendance Request",
            doc.name,
            ["name", "docstatus", "workflow_state", "employee", "reason", "from_date", "to_date"],
            as_dict=True,
        )
        expected_state = "Approved" if docstatus == 1 else workflow_state
        self.assertEqual(row.docstatus, docstatus)
        self.assertEqual(row.workflow_state, expected_state)
        self.assertEqual(row.employee, employee)
        self.assertEqual(row.reason, reason)
        self.assertEqual(str(row.from_date), str(getdate(from_date)))
        self.assertEqual(str(row.to_date), str(getdate(to_date)))

        # Clear ignore_validate flag so subsequent test operations are validated
        doc.flags.pop("ignore_validate", None)
        doc.reload()
        return doc

    # =========================================================================
    # TESTS
    # =========================================================================

    def test_01_wfh_request_exceeding_allocation_is_blocked_on_insert(self):
        """1. New WFH request that would exceed allocation 2 (2 approved already in cycle) is blocked on insert.
        Runs as EMP_USER.
        """
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_1, docstatus=1)
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_2, docstatus=1)

        # T3 Precondition check
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "docstatus": 1}), 2)
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "workflow_state": "Pending Approval"}), 0)

        frappe.set_user(EMP_USER)
        doc = frappe.get_doc({
            "doctype": "Attendance Request",
            "employee": self.test_emp,
            "reason": "Work From Home",
            "from_date": CYCLE_DATE_3,
            "to_date": CYCLE_DATE_3,
            "company": TEST_COMPANY,
        })
        with self.assertRaises(frappe.ValidationError) as cm:
            doc.insert()
        self.assertIn("Limit exceeded", str(cm.exception))

    def test_02_pending_plus_approved_requests_exceeding_allocation_blocked_on_insert(self):
        """2. 1 approved + 1 other Pending Approval + new request exceeds 2: blocked (pending counts).
        Runs as EMP_USER.
        """
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_1, docstatus=1)
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_2, docstatus=0, workflow_state="Pending Approval")

        # T3 Precondition check
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "docstatus": 1}), 1)
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "workflow_state": "Pending Approval"}), 1)

        frappe.set_user(EMP_USER)
        doc = frappe.get_doc({
            "doctype": "Attendance Request",
            "employee": self.test_emp,
            "reason": "Work From Home",
            "from_date": CYCLE_DATE_3,
            "to_date": CYCLE_DATE_3,
            "company": TEST_COMPANY,
        })
        with self.assertRaises(frappe.ValidationError) as cm:
            doc.insert()
        self.assertIn("Limit exceeded", str(cm.exception))

    def test_03_draft_rejected_cancelled_requests_do_not_count(self):
        """3. Draft, Rejected and Cancelled requests of the same employee do not count:
        with 1 approved and 5 of those, a new request is allowed (1 + 1 <= 2).
        """
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_1, docstatus=1)
        self._seed_attendance_request(self.test_emp, "Work From Home", "2026-11-01", docstatus=0, workflow_state="Draft")
        self._seed_attendance_request(self.test_emp, "Work From Home", "2026-11-02", docstatus=0, workflow_state="Rejected")
        self._seed_attendance_request(self.test_emp, "Work From Home", "2026-11-03", docstatus=0, workflow_state="Rejected")
        self._seed_attendance_request(self.test_emp, "Work From Home", "2026-11-04", docstatus=0, workflow_state="Cancelled")
        self._seed_attendance_request(self.test_emp, "Work From Home", "2026-11-05", docstatus=0, workflow_state="Cancelled")

        # T3 Precondition check
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "docstatus": 1}), 1)
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "workflow_state": "Draft"}), 1)
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "workflow_state": "Rejected"}), 2)
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "workflow_state": "Cancelled"}), 2)

        frappe.set_user(EMP_USER)
        doc = frappe.get_doc({
            "doctype": "Attendance Request",
            "employee": self.test_emp,
            "reason": "Work From Home",
            "from_date": CYCLE_DATE_3,
            "to_date": CYCLE_DATE_3,
            "company": TEST_COMPANY,
        })
        doc.insert()
        self.assertEqual(doc.docstatus, 0)
        self.assertEqual(doc.workflow_state, "Pending Approval")

    def test_04_document_itself_is_excluded_on_resave(self):
        """4. The document itself is excluded: re-saving an existing Pending Approval request
        that is within limit does not count itself twice.
        """
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_1, docstatus=1)
        pending_doc = self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_2, docstatus=0, workflow_state="Pending Approval")

        # T3 Precondition check
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "docstatus": 1}), 1)
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "workflow_state": "Pending Approval"}), 1)

        frappe.set_user(EMP_USER)
        doc = frappe.get_doc("Attendance Request", pending_doc.name)
        doc.explanation = "Updating notes on pending request"
        doc.save()
        self.assertEqual(doc.workflow_state, "Pending Approval")

    def test_05_no_allocation_for_company_reason_allows_insert(self):
        """5. No allocation for the company/reason: insert is allowed, no exception."""
        # On Duty has no allocation in TEST_COMPANY
        self.assertEqual(frappe.db.count("Attendance Reason Allocation", {"company": TEST_COMPANY, "attendance_reason_type": "On Duty"}), 0)

        frappe.set_user(EMP_USER)
        doc = frappe.get_doc({
            "doctype": "Attendance Request",
            "employee": self.test_emp,
            "reason": "On Duty",
            "from_date": CYCLE_DATE_1,
            "to_date": CYCLE_DATE_1,
            "company": TEST_COMPANY,
        })
        doc.insert()
        self.assertEqual(doc.docstatus, 0)

    def test_06_approving_first_of_multiple_pending_requests_succeeds(self):
        """6. Approving the first of 5 pending requests of an over-limit employee works (R2).
        Seed 0 approved, 5 Pending Approval WFH. Approving 1st succeeds, 2nd succeeds, 3rd blocked (T4).
        Uses the real workflow path: frappe.model.workflow.apply_workflow(doc, 'Approve').
        """
        p1 = self._seed_attendance_request(self.test_emp, "Work From Home", "2026-11-01", docstatus=0, workflow_state="Pending Approval")
        p2 = self._seed_attendance_request(self.test_emp, "Work From Home", "2026-11-02", docstatus=0, workflow_state="Pending Approval")
        p3 = self._seed_attendance_request(self.test_emp, "Work From Home", "2026-11-03", docstatus=0, workflow_state="Pending Approval")
        p4 = self._seed_attendance_request(self.test_emp, "Work From Home", "2026-11-04", docstatus=0, workflow_state="Pending Approval")
        p5 = self._seed_attendance_request(self.test_emp, "Work From Home", "2026-11-05", docstatus=0, workflow_state="Pending Approval")

        # T3 Precondition check
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "docstatus": 1}), 0)
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "workflow_state": "Pending Approval"}), 5)

        frappe.set_user(APPROVER_USER)
        # Approving 1st: approved becomes 1 (1 <= 2) -> succeeds
        frappe.model.workflow.apply_workflow(p1, "Approve")
        self.assertEqual(p1.docstatus, 1)
        self.assertEqual(p1.workflow_state, "Approved")

        # Approving 2nd: approved becomes 2 (2 <= 2) -> succeeds
        frappe.model.workflow.apply_workflow(p2, "Approve")
        self.assertEqual(p2.docstatus, 1)
        self.assertEqual(p2.workflow_state, "Approved")

        # Approving 3rd: approved would become 3 (3 > 2) -> BLOCKED
        with self.assertRaises(frappe.ValidationError) as cm:
            frappe.model.workflow.apply_workflow(p3, "Approve")
        self.assertIn("Monthly limit exceeded", str(cm.exception))

    def test_07_resaving_request_without_changing_relevant_fields_skips_check(self):
        """7. Saving an existing request without changing employee, reason, from_date, to_date, half_day
        skips the check even if the employee is genuinely over limit (2 approved + pending p) (T5).
        """
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_1, docstatus=1)
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_2, docstatus=1)
        p = self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_3, docstatus=0, workflow_state="Pending Approval")

        # T3 Precondition check
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "docstatus": 1}), 2)
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "workflow_state": "Pending Approval"}), 1)

        # Saving p with only explanation updated must skip the limit check
        frappe.set_user(EMP_USER)
        doc = frappe.get_doc("Attendance Request", p.name)
        doc.explanation = "Changing non-relevant field"
        doc.save()
        self.assertEqual(doc.explanation, "Changing non-relevant field")
        self.assertEqual(doc.workflow_state, "Pending Approval")

    def test_08_changing_dates_on_existing_draft_reruns_check(self):
        """8. Changing from_date/to_date on an existing draft re-runs the check.
        Runs as EMP_USER.
        """
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_1, docstatus=1)
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_2, docstatus=1)
        draft = self._seed_attendance_request(self.test_emp, "Work From Home", "2026-11-05", docstatus=0, workflow_state="Pending Approval")

        # T3 Precondition check
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "docstatus": 1}), 2)
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "workflow_state": "Pending Approval"}), 1)

        frappe.set_user(EMP_USER)
        doc = frappe.get_doc("Attendance Request", draft.name)
        doc.from_date = "2026-11-06"
        doc.to_date = "2026-11-06"
        with self.assertRaises(frappe.ValidationError) as cm:
            doc.save()
        self.assertIn("Limit exceeded", str(cm.exception))

    def test_09_workflow_state_rejected_or_cancelled_skips_check(self):
        """9. workflow_state Rejected or Cancelled: check skipped."""
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_1, docstatus=1)
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_2, docstatus=1)
        rej = self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_3, docstatus=0, workflow_state="Rejected")

        # T3 Precondition check
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "docstatus": 1}), 2)
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "workflow_state": "Rejected"}), 1)

        doc = frappe.get_doc("Attendance Request", rej.name)
        doc.explanation = "Rejected record update"
        doc.save(ignore_permissions=True)
        self.assertEqual(doc.workflow_state, "Rejected")

    def test_10_whole_day_counting_half_day_counts_as_one(self):
        """10. Whole-day counting: a half-day request counts as 1 day."""
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_1, docstatus=1, half_day=1)

        # T3 Precondition check
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "docstatus": 1}), 1)

        frappe.set_user(EMP_USER)
        # Second half day request (1 + 1 = 2) should be allowed
        doc2 = frappe.get_doc({
            "doctype": "Attendance Request",
            "employee": self.test_emp,
            "reason": "Work From Home",
            "from_date": CYCLE_DATE_2,
            "to_date": CYCLE_DATE_2,
            "half_day": 1,
            "half_day_date": CYCLE_DATE_2,
            "company": TEST_COMPANY,
        })
        doc2.insert()
        self.assertEqual(doc2.docstatus, 0)

        # Third half day request (1 + 1 + 1 = 3 > 2) must be blocked
        doc3 = frappe.get_doc({
            "doctype": "Attendance Request",
            "employee": self.test_emp,
            "reason": "Work From Home",
            "from_date": CYCLE_DATE_3,
            "to_date": CYCLE_DATE_3,
            "half_day": 1,
            "half_day_date": CYCLE_DATE_3,
            "company": TEST_COMPANY,
        })
        with self.assertRaises(frappe.ValidationError) as cm:
            doc3.insert()
        self.assertIn("Limit exceeded", str(cm.exception))

    def test_11_cycle_boundaries_independent_allocation(self):
        """11. Cycle boundaries: requests dated 25th and 26th belong to different cycles;
        approved requests in previous cycle do not count against new cycle.
        """
        self._seed_attendance_request(self.test_emp, "Work From Home", PREV_CYCLE_DATE, docstatus=1)
        self._seed_attendance_request(self.test_emp, "Work From Home", "2026-10-25", docstatus=1)

        # T3 Precondition check
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "docstatus": 1}), 2)

        frappe.set_user(EMP_USER)
        doc = frappe.get_doc({
            "doctype": "Attendance Request",
            "employee": self.test_emp,
            "reason": "Work From Home",
            "from_date": CYCLE_START,
            "to_date": CYCLE_START,
            "company": TEST_COMPANY,
        })
        doc.insert()
        self.assertEqual(doc.docstatus, 0)

    def test_12_hr_manager_gets_no_bypass(self):
        """12. HR Manager user gets NO bypass: an HR Manager employee's over-limit request is blocked.
        Runs as HR_MGR_USER.
        """
        self._seed_attendance_request(self.hr_emp, "Work From Home", CYCLE_DATE_1, docstatus=1)
        self._seed_attendance_request(self.hr_emp, "Work From Home", CYCLE_DATE_2, docstatus=1)

        # T3 Precondition check
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.hr_emp, "docstatus": 1}), 2)

        frappe.set_user(HR_MGR_USER)
        doc = frappe.get_doc({
            "doctype": "Attendance Request",
            "employee": self.hr_emp,
            "reason": "Work From Home",
            "from_date": CYCLE_DATE_3,
            "to_date": CYCLE_DATE_3,
            "company": TEST_COMPANY,
        })
        with self.assertRaises(frappe.ValidationError) as cm:
            doc.insert()
        self.assertIn("Limit exceeded", str(cm.exception))

    def test_13_error_message_contains_reason_limit_used_and_cycle_dates(self):
        """13. The error message contains the reason type, used, allowed, and the cycle dates (T6).
        Asserts exact fragments: 'Allowed: 2', 'Already used/pending: 2', 'Requested: 1',
        'Total would be: 3', '26-Oct-2026', '25-Nov-2026', 'Work From Home Allowance'.
        """
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_1, docstatus=1)
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_2, docstatus=1)

        # T3 Precondition check
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "docstatus": 1}), 2)

        frappe.set_user(EMP_USER)
        doc = frappe.get_doc({
            "doctype": "Attendance Request",
            "employee": self.test_emp,
            "reason": "Work From Home",
            "from_date": CYCLE_DATE_3,
            "to_date": CYCLE_DATE_3,
            "company": TEST_COMPANY,
        })
        with self.assertRaises(frappe.ValidationError) as cm:
            doc.insert()
        err_str = frappe.utils.strip_html(str(cm.exception))
        print("\n[test_13 stripped exception]:", err_str)
        self.assertIn("Allowed: 2", err_str)
        self.assertIn("Already used/pending: 2", err_str)
        self.assertIn("Requested: 1", err_str)
        self.assertIn("Total would be: 3", err_str)
        self.assertIn("26-Oct-2026", err_str)
        self.assertIn("25-Nov-2026", err_str)
        self.assertIn("Work From Home Allowance", err_str)

    def test_14_administrator_behavior_matches_approval_check(self):
        """14. Administrator behaviour matches A5(e): Administrator is not exempt and is blocked when over limit (T12)."""
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_1, docstatus=1)
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_2, docstatus=1)

        # T3 Precondition check
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "docstatus": 1}), 2)

        frappe.set_user("Administrator")
        doc = frappe.get_doc({
            "doctype": "Attendance Request",
            "employee": self.test_emp,
            "reason": "Work From Home",
            "from_date": CYCLE_DATE_3,
            "to_date": CYCLE_DATE_3,
            "company": TEST_COMPANY,
        })
        with self.assertRaises(frappe.ValidationError) as cm:
            doc.insert()
        self.assertIn("Limit exceeded", str(cm.exception))

    def test_15_apply_and_approval_checks_use_same_counting_and_allocation(self):
        """15. Spies assert _count_period_usage and _get_allocation are called during apply-time insert and during apply_workflow('Approve') (T7)."""
        import hrms_custom.overrides.attendance_request as ar_module

        with patch.object(ar_module, "_count_period_usage", wraps=ar_module._count_period_usage) as spy_count, \
             patch.object(ar_module, "_get_allocation", wraps=ar_module._get_allocation) as spy_alloc:

            # (1) Apply-time insert attempt:
            frappe.set_user(EMP_USER)
            doc = frappe.get_doc({
                "doctype": "Attendance Request",
                "employee": self.test_emp,
                "reason": "Work From Home",
                "from_date": CYCLE_DATE_1,
                "to_date": CYCLE_DATE_1,
                "company": TEST_COMPANY,
            })
            try:
                doc.insert()
            except frappe.ValidationError:
                pass

            self.assertGreaterEqual(spy_alloc.call_count, 1, "_get_allocation must be called during apply-time insert")
            self.assertGreaterEqual(spy_count.call_count, 1, "_count_period_usage must be called during apply-time insert")

            # Reset call counts
            spy_alloc.reset_mock()
            spy_count.reset_mock()

            # (2) Approval-time attempt on an existing pending request:
            pending = self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_2, docstatus=0, workflow_state="Pending Approval")
            frappe.set_user(APPROVER_USER)
            frappe.model.workflow.apply_workflow(pending, "Approve")

            self.assertGreaterEqual(spy_alloc.call_count, 1, "_get_allocation must be called during apply_workflow('Approve')")
            self.assertGreaterEqual(spy_count.call_count, 1, "_count_period_usage must be called during apply_workflow('Approve')")

    def test_16_multi_day_request_not_applicable_at_apply_time(self):
        """16. Multi-day request: NOT applicable at apply time because _validate_single_date
        blocks multi-day creation at validate time (T12).
        """
        frappe.set_user(EMP_USER)
        doc = frappe.get_doc({
            "doctype": "Attendance Request",
            "employee": self.test_emp,
            "reason": "Work From Home",
            "from_date": CYCLE_DATE_1,
            "to_date": CYCLE_DATE_2,
            "company": TEST_COMPANY,
        })
        with self.assertRaises(frappe.ValidationError) as cm:
            doc.insert()
        self.assertIn("allowed only for a single date", str(cm.exception))

    def test_17_ui_style_save_string_dates_and_date_objects_skips_check(self):
        """17. UI-style save: an existing Pending Approval request is reloaded, from_date and to_date
        are set to the same dates as STRINGS, nothing else changed, and doc is saved while employee
        is over limit (2 approved + pending p) (T5). The check must be skipped.
        """
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_1, docstatus=1)
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_2, docstatus=1)
        p = self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_3, docstatus=0, workflow_state="Pending Approval")

        # T3 Precondition check
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "docstatus": 1}), 2)
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "workflow_state": "Pending Approval"}), 1)

        # Set same dates as STRINGS
        frappe.set_user(EMP_USER)
        doc_str = frappe.get_doc("Attendance Request", p.name)
        doc_str.from_date = str(CYCLE_DATE_3)
        doc_str.to_date = str(CYCLE_DATE_3)
        doc_str.save()
        self.assertEqual(doc_str.name, p.name)

    def test_18_bypass_matrix_report_only(self):
        """18. Bypass matrix, REPORT ONLY (T8). For an over-limit employee with Administrator as session user,
        try each of:
          (a) doc.submit() -> BLOCKED by approval check ('Monthly limit exceeded')
          (b) doc.flags.ignore_validate = True then doc.submit() -> RECORDED (bypasses run_before_save_methods)
          (c) frappe.db.set_value on docstatus and workflow_state -> RECORDED (direct DB write)
          (d) frappe.model.workflow.apply_workflow(doc, "Approve") -> BLOCKED by approval check
          (e) Approver submitting locked date (2026-10-10) with ignore_validate=True -> test if Group 1 lock blocks it.
        Records and prints observed behavior.
        """
        frappe.set_user("Administrator")
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_1, docstatus=1)
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_2, docstatus=1)

        # T3 Precondition check
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "docstatus": 1}), 2)

        # (a) doc.submit() on a 3rd request
        doc_a = self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_3, docstatus=0, workflow_state="Pending Approval")
        blocked_a = False
        msg_a = ""
        try:
            doc_a.submit()
        except frappe.ValidationError as e:
            blocked_a = True
            msg_a = str(e)

        # (b) doc.flags.ignore_validate = True then doc.submit()
        doc_b = self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_4, docstatus=0, workflow_state="Pending Approval")
        blocked_b = False
        msg_b = ""
        try:
            doc_b.flags.ignore_validate = True
            doc_b.submit()
        except frappe.ValidationError as e:
            blocked_b = True
            msg_b = str(e)

        # (c) frappe.db.set_value on docstatus and workflow_state
        doc_c = self._seed_attendance_request(self.test_emp, "Work From Home", "2026-11-01", docstatus=0, workflow_state="Pending Approval")
        blocked_c = False
        msg_c = ""
        try:
            frappe.db.set_value("Attendance Request", doc_c.name, {"docstatus": 1, "workflow_state": "Approved"})
        except Exception as e:
            blocked_c = True
            msg_c = str(e)

        # (d) frappe.model.workflow.apply_workflow(doc, "Approve")
        doc_d = self._seed_attendance_request(self.test_emp, "Work From Home", "2026-11-02", docstatus=0, workflow_state="Pending Approval")
        blocked_d = False
        msg_d = ""
        try:
            frappe.model.workflow.apply_workflow(doc_d, "Approve")
        except frappe.ValidationError as e:
            blocked_d = True
            msg_d = str(e)

        # (e) Approver submitting locked date (2026-10-10) with ignore_validate=True
        doc_e = self._seed_attendance_request(self.test_emp, "Work From Home", "2026-10-10", docstatus=0, workflow_state="Pending Approval")
        frappe.set_user(APPROVER_USER)
        blocked_e = False
        msg_e = ""
        try:
            doc_e.flags.ignore_validate = True
            doc_e.submit()
        except frappe.ValidationError as e:
            blocked_e = True
            msg_e = str(e)

        print("\n=== [Bypass Matrix Observed Results] ===")
        print(f"  (a) doc.submit(): blocked={blocked_a} (msg: {msg_a})")
        print(f"  (b) ignore_validate submit: blocked={blocked_b} (msg: {msg_b})")
        print(f"  (c) db.set_value: blocked={blocked_c} (msg: {msg_c})")
        print(f"  (d) apply_workflow: blocked={blocked_d} (msg: {msg_d})")
        print(f"  (e) approver ignore_validate submit on locked date (2026-10-10): blocked={blocked_e} (msg: {msg_e})")
        print("========================================")

        self.assertTrue(blocked_a, "doc.submit() must be blocked by approval check")
        self.assertIn("Monthly limit exceeded", msg_a)
        self.assertFalse(blocked_b, "doc.flags.ignore_validate=True bypasses before_submit in Frappe framework")
        self.assertFalse(blocked_c, "frappe.db.set_value bypasses all validations")
        self.assertTrue(blocked_d, "apply_workflow('Approve') must be blocked by approval check")
        self.assertIn("Monthly limit exceeded", msg_d)

    def test_19_new_request_workflow_state_observed_after_insert(self):
        """19. A brand new request's workflow_state observed after insert equals the workflow's initial state (T9)."""
        frappe.set_user(EMP_USER)
        doc = frappe.get_doc({
            "doctype": "Attendance Request",
            "employee": self.test_emp,
            "reason": "Work From Home",
            "from_date": CYCLE_DATE_1,
            "to_date": CYCLE_DATE_1,
            "company": TEST_COMPANY,
        })
        doc.insert()
        print(f"\n[Observed workflow_state after insert]: {doc.workflow_state}")
        self.assertEqual(doc.workflow_state, "Pending Approval")

    def test_20_permission_type_request_exceeding_allocation_is_blocked_on_insert(self):
        """20. A Permission-type request (reason mapped to Permission reason type via Late In or Early Out)
        that would exceed Permission allocation of 2 is blocked on insert.
        Proves the check also covers the permission branch.
        """
        fake_window = {"from_time": "2026-11-10 09:00:00", "to_time": "2026-11-10 09:30:00", "hours": 0.5, "checkin_found": True}
        with patch("hrms_custom.overrides.attendance_request._get_actual_window", return_value=fake_window):
            self._seed_attendance_request(self.test_emp, "Late In", CYCLE_DATE_1, docstatus=1)
            self._seed_attendance_request(self.test_emp, "Early Out", CYCLE_DATE_2, docstatus=1)

            # T3 Precondition check
            self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "docstatus": 1}), 2)

            frappe.set_user(EMP_USER)
            doc = frappe.get_doc({
                "doctype": "Attendance Request",
                "employee": self.test_emp,
                "reason": "Late In",
                "from_date": CYCLE_DATE_3,
                "to_date": CYCLE_DATE_3,
                "company": TEST_COMPANY,
            })
            with self.assertRaises(frappe.ValidationError) as cm:
                doc.insert()
            self.assertIn("Limit exceeded", str(cm.exception))

    def test_21_saving_pending_request_with_date_object_does_not_trigger_limit_check(self):
        """21. Saving an existing pending request with date objects while employee is over limit (2 approved + pending p)
        does not re-trigger the limit check.
        """
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_1, docstatus=1)
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_2, docstatus=1)
        p = self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_3, docstatus=0, workflow_state="Pending Approval")

        # T3 Precondition check
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "docstatus": 1}), 2)
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "workflow_state": "Pending Approval"}), 1)

        frappe.set_user(EMP_USER)
        doc_obj = frappe.get_doc("Attendance Request", p.name)
        doc_obj.from_date = getdate(CYCLE_DATE_3)
        doc_obj.to_date = getdate(CYCLE_DATE_3)
        doc_obj.save()
        self.assertEqual(doc_obj.name, p.name)

    def test_22_rejecting_pending_request_works(self):
        """22. Rejecting pending request via apply_workflow('Reject') works (T10)."""
        p = self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_1, docstatus=0, workflow_state="Pending Approval")

        # T3 Precondition check
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "workflow_state": "Pending Approval"}), 1)

        frappe.set_user(APPROVER_USER)
        frappe.model.workflow.apply_workflow(p, "Reject")
        self.assertEqual(p.workflow_state, "Rejected")
        db_state = frappe.db.get_value("Attendance Request", p.name, "workflow_state")
        self.assertEqual(db_state, "Rejected")

    def test_23_cancelling_pending_request_works(self):
        """23. Cancelling own pending request as EMP_USER via apply_workflow('Cancel') works (T10)."""
        p = self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_1, docstatus=0, workflow_state="Pending Approval")

        # T3 Precondition check
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "workflow_state": "Pending Approval"}), 1)

        frappe.set_user(EMP_USER)
        frappe.model.workflow.apply_workflow(p, "Cancel")
        self.assertEqual(p.workflow_state, "Cancelled")
        db_state = frappe.db.get_value("Attendance Request", p.name, "workflow_state")
        self.assertEqual(db_state, "Cancelled")

    def test_24_editing_dates_of_pending_request_within_limit_succeeds(self):
        """24. Changing dates on an existing Pending Approval request while within allocation limit succeeds.
        Self-exclusion ("name != doc.name") ensures the document being edited does not count itself twice.
        """
        self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_1, docstatus=1)
        p = self._seed_attendance_request(self.test_emp, "Work From Home", CYCLE_DATE_2, docstatus=0, workflow_state="Pending Approval")

        # Assert precondition counts
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "docstatus": 1}), 1)
        self.assertEqual(frappe.db.count("Attendance Request", {"employee": self.test_emp, "workflow_state": "Pending Approval"}), 1)

        frappe.set_user(EMP_USER)
        doc = frappe.get_doc("Attendance Request", p.name)
        doc.from_date = CYCLE_DATE_3
        doc.to_date = CYCLE_DATE_3
        doc.save()

        self.assertEqual(doc.name, p.name)
        self.assertEqual(getdate(doc.from_date), getdate(CYCLE_DATE_3))
        self.assertEqual(getdate(doc.to_date), getdate(CYCLE_DATE_3))
        self.assertEqual(doc.workflow_state, "Pending Approval")
        self.assertEqual(doc.docstatus, 0)

