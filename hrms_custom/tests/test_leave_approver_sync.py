from unittest.mock import patch

import frappe
from frappe.tests.classes.integration_test_case import IntegrationTestCase
from frappe.utils.nestedset import rebuild_tree

TEST_COMPANY = "_Test Leave Sync Company"
HOLIDAY_LIST = "_Test Leave Sync Holiday List"
LEAVE_TYPE = "_Test Leave Sync LWP"

MGR1_USER = "_test_leave_sync_mgr1@example.com"
MGR2_USER = "_test_leave_sync_mgr2@example.com"
EMP_USER = "_test_leave_sync_emp@example.com"


class TestLeaveApproverSync(IntegrationTestCase):
	_created_users = []

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_users = []
		cls._cleanup_all()

		if not frappe.db.exists("Company", TEST_COMPANY):
			frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": TEST_COMPANY,
					"default_currency": "INR",
					"country": "India",
				}
			).insert(ignore_permissions=True)

		if not frappe.db.exists("Holiday List", HOLIDAY_LIST):
			frappe.get_doc(
				{
					"doctype": "Holiday List",
					"holiday_list_name": HOLIDAY_LIST,
					"from_date": "2026-01-01",
					"to_date": "2026-12-31",
				}
			).insert(ignore_permissions=True)

		if not frappe.db.exists(
			"Holiday List Assignment",
			{"applicable_for": "Company", "assigned_to": TEST_COMPANY, "docstatus": 1},
		):
			frappe.get_doc(
				{
					"doctype": "Holiday List Assignment",
					"applicable_for": "Company",
					"assigned_to": TEST_COMPANY,
					"holiday_list": HOLIDAY_LIST,
					"from_date": "2026-01-01",
					"docstatus": 1,
				}
			).insert(ignore_permissions=True)

		if not frappe.db.exists("Leave Type", LEAVE_TYPE):
			frappe.get_doc(
				{
					"doctype": "Leave Type",
					"leave_type_name": LEAVE_TYPE,
					"is_lwp": 1,
					"include_holiday": 0,
				}
			).insert(ignore_permissions=True)

		cls._ensure_user(MGR1_USER, ["Employee", "Leave Approver", "Employee Self Service"])
		cls._ensure_user(MGR2_USER, ["Employee", "Leave Approver", "Employee Self Service"])
		cls._ensure_user(EMP_USER, ["Employee", "Employee Self Service"])

		cls.mgr1_emp = cls._ensure_employee(
			"EMP-LSYNC-MGR1", "LeaveSync", "MgrOne", MGR1_USER, reports_to=None, leave_approver=None
		)
		cls.mgr2_emp = cls._ensure_employee(
			"EMP-LSYNC-MGR2", "LeaveSync", "MgrTwo", MGR2_USER, reports_to=None, leave_approver=None
		)
		cls.sub_emp = cls._ensure_employee(
			"EMP-LSYNC-SUB",
			"LeaveSync",
			"Employee",
			EMP_USER,
			reports_to=cls.mgr1_emp,
			leave_approver=MGR1_USER,
		)

		rebuild_tree("Employee")
		frappe.cache.delete_key("user_permissions")
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		cls._cleanup_all()
		rebuild_tree("Employee")
		frappe.cache.delete_key("user_permissions")
		frappe.db.commit()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		frappe.db.set_value(
			"Employee",
			self.sub_emp,
			{"reports_to": self.mgr1_emp, "old_parent": self.mgr1_emp, "leave_approver": MGR1_USER},
			update_modified=False,
		)
		rebuild_tree("Employee")
		frappe.cache.delete_key("user_permissions")

	@classmethod
	def _ensure_user(cls, email, roles):
		if not frappe.db.exists("User", email):
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": email.split("@")[0],
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)
			cls._created_users.append(email)
		else:
			user = frappe.get_doc("User", email)
		existing_roles = {r.role for r in user.roles}
		for role in roles:
			if role not in existing_roles:
				user.append("roles", {"role": role})
		user.save(ignore_permissions=True)

	@classmethod
	def _ensure_employee(cls, emp_id, first_name, last_name, user_id, reports_to=None, leave_approver=None):
		existing = frappe.db.get_value("Employee", {"user_id": user_id}, "name")
		if existing:
			emp = frappe.get_doc("Employee", existing)
			emp.reports_to = reports_to
			emp.leave_approver = leave_approver
			emp.company = TEST_COMPANY
			emp.status = "Active"
			emp.custom_roles_responsibilities = "Test roles and responsibilities"
			emp.save(ignore_permissions=True)
			return emp.name

		doc = frappe.get_doc(
			{
				"doctype": "Employee",
				"employee": emp_id,
				"employee_number": emp_id,
				"employee_name": f"{first_name} {last_name}",
				"first_name": first_name,
				"last_name": last_name,
				"company": TEST_COMPANY,
				"user_id": user_id,
				"reports_to": reports_to,
				"leave_approver": leave_approver,
				"date_of_joining": "2026-01-01",
				"status": "Active",
				"holiday_list": HOLIDAY_LIST,
				"gender": "Female",
				"custom_roles_responsibilities": "Test roles and responsibilities",
				"create_user_permission": 1,
			}
		)
		doc.insert(ignore_permissions=True, ignore_mandatory=True)
		return doc.name

	@classmethod
	def _cleanup_all(cls):
		frappe.db.delete("Leave Application", {"company": TEST_COMPANY})
		test_users = [EMP_USER, MGR2_USER, MGR1_USER]
		for user in test_users:
			emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
			if emp:
				frappe.db.sql(
					"UPDATE `tabEmployee` SET reports_to = '', old_parent = '' WHERE name = %s",
					(emp,),
				)
		for user in test_users:
			for up in frappe.get_all("User Permission", filters={"user": user}, pluck="name"):
				frappe.delete_doc("User Permission", up, force=1)
			emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
			if emp:
				frappe.delete_doc("Employee", emp, force=1)
		for user in set(cls._created_users + test_users):
			if frappe.db.exists("User", user):
				frappe.delete_doc("User", user, force=1)
		if frappe.db.exists("Leave Type", LEAVE_TYPE):
			frappe.delete_doc("Leave Type", LEAVE_TYPE, force=1)
		if frappe.db.exists("Company", TEST_COMPANY):
			frappe.db.delete("Holiday List Assignment", {"assigned_to": TEST_COMPANY})
			frappe.delete_doc("Company", TEST_COMPANY, force=1)
		if frappe.db.exists("Holiday List", HOLIDAY_LIST):
			frappe.delete_doc("Holiday List", HOLIDAY_LIST, force=1)

	def _insert_leave_application(self, from_date="2026-12-01", to_date="2026-12-01", leave_approver=None):
		doc = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": self.sub_emp,
				"leave_type": LEAVE_TYPE,
				"company": TEST_COMPANY,
				"from_date": from_date,
				"to_date": to_date,
				"status": "Open",
				"leave_approver": leave_approver,
				"follow_via_email": 1,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc

	def test_new_leave_application_populates_missing_leave_approver(self):
		from hrms.api import get_leave_applications

		doc = self._insert_leave_application(from_date="2026-12-02", to_date="2026-12-02", leave_approver=None)
		self.assertEqual(doc.leave_approver, MGR1_USER)

		frappe.set_user(MGR1_USER)
		team_leaves = get_leave_applications(
			employee=self.mgr1_emp, approver_id=MGR1_USER, for_approval=True
		)
		self.assertIn(doc.name, [row["name"] for row in team_leaves])

	def test_new_leave_application_sends_email_when_not_muted(self):
		prev_mute = frappe.flags.mute_emails
		prev_send = frappe.db.get_single_value("HR Settings", "send_leave_notification")
		prev_template = frappe.db.get_single_value("HR Settings", "leave_approval_notification_template")
		try:
			frappe.db.set_single_value("HR Settings", "send_leave_notification", 1)
			if not prev_template:
				tpl_name = frappe.db.get_value("Email Template", {}, "name")
				if not tpl_name:
					tpl = frappe.get_doc(
						{
							"doctype": "Email Template",
							"name": "_Test Leave Sync Template",
							"subject": "Leave Notification",
							"response": "Leave from {{ employee_name }}",
						}
					).insert(ignore_permissions=True)
					tpl_name = tpl.name
				frappe.db.set_single_value("HR Settings", "leave_approval_notification_template", tpl_name)

			frappe.flags.mute_emails = False
			with patch("hrms_custom.overrides.leave_application.frappe.sendmail") as mock_sendmail:
				self._insert_leave_application(
					from_date="2026-12-03", to_date="2026-12-03", leave_approver=MGR1_USER
				)
			mock_sendmail.assert_called_once()
			self.assertEqual(mock_sendmail.call_args.kwargs["recipients"], MGR1_USER)
		finally:
			frappe.flags.mute_emails = prev_mute
			frappe.db.set_single_value("HR Settings", "send_leave_notification", prev_send)
			frappe.db.set_single_value("HR Settings", "leave_approval_notification_template", prev_template)

	def test_sync_pending_leave_approver_dry_run_and_sync_without_emails(self):
		from hrms.api import get_leave_applications
		from hrms_custom.scripts.sync_pending_leave_approver import sync_pending_leave_approver

		doc = self._insert_leave_application(
			from_date="2026-12-04", to_date="2026-12-04", leave_approver=MGR1_USER
		)

		# Reassign employee's leave_approver and reporting line to Mgr2
		frappe.db.set_value(
			"Employee",
			self.sub_emp,
			{"reports_to": self.mgr2_emp, "leave_approver": MGR2_USER},
			update_modified=False,
		)
		rebuild_tree("Employee")
		frappe.cache.delete_key("user_permissions")

		# Before sync: Mgr2 does not see pending request
		frappe.set_user(MGR2_USER)
		before_mgr2 = get_leave_applications(
			employee=self.mgr2_emp, approver_id=MGR2_USER, for_approval=True
		)
		self.assertNotIn(doc.name, [r["name"] for r in before_mgr2])
		frappe.set_user("Administrator")

		# Default call is dry_run=True and must not mutate DB
		dry_res = sync_pending_leave_approver()
		self.assertTrue(dry_res["dry_run"])
		self.assertEqual(dry_res["updated"], 0)
		self.assertIn(doc.name, [c["name"] for c in dry_res["changes"]])
		self.assertEqual(frappe.db.get_value("Leave Application", doc.name, "leave_approver"), MGR1_USER)

		# Non-dry run with unmuted emails & notifications enabled must NOT send or queue any email
		prev_mute = frappe.flags.mute_emails
		prev_in_import = frappe.flags.in_import
		prev_mute_msg = frappe.flags.mute_messages
		prev_send = frappe.db.get_single_value("HR Settings", "send_leave_notification")
		prev_template = frappe.db.get_single_value("HR Settings", "leave_approval_notification_template")
		try:
			frappe.db.set_single_value("HR Settings", "send_leave_notification", 1)
			if not prev_template:
				tpl_name = frappe.db.get_value("Email Template", {}, "name")
				if not tpl_name:
					tpl = frappe.get_doc(
						{
							"doctype": "Email Template",
							"name": "_Test Leave Sync Template",
							"subject": "Leave Notification",
							"response": "Leave from {{ employee_name }}",
						}
					).insert(ignore_permissions=True)
					tpl_name = tpl.name
				frappe.db.set_single_value("HR Settings", "leave_approval_notification_template", tpl_name)

			frappe.flags.mute_emails = False
			frappe.flags.in_import = False
			frappe.flags.mute_messages = False
			email_queue_before = frappe.db.count("Email Queue")

			with patch("hrms_custom.overrides.leave_application.frappe.sendmail") as mock_sendmail:
				sync_res = sync_pending_leave_approver(dry_run=False)

			mock_sendmail.assert_not_called()
			self.assertEqual(frappe.db.count("Email Queue"), email_queue_before)
			self.assertFalse(frappe.flags.mute_emails)
			self.assertFalse(frappe.flags.in_import)
			self.assertFalse(frappe.flags.mute_messages)
			self.assertFalse(sync_res["dry_run"])
			self.assertGreaterEqual(sync_res["updated"], 1)
			self.assertEqual(
				frappe.db.get_value("Leave Application", doc.name, "leave_approver"), MGR2_USER
			)
		finally:
			frappe.flags.mute_emails = prev_mute
			frappe.flags.in_import = prev_in_import
			frappe.flags.mute_messages = prev_mute_msg
			frappe.db.set_single_value("HR Settings", "send_leave_notification", prev_send)
			frappe.db.set_single_value("HR Settings", "leave_approval_notification_template", prev_template)

		# After sync: Mgr2 sees the pending request, Mgr1 no longer sees it
		frappe.set_user(MGR2_USER)
		after_mgr2 = get_leave_applications(
			employee=self.mgr2_emp, approver_id=MGR2_USER, for_approval=True
		)
		self.assertIn(doc.name, [r["name"] for r in after_mgr2])

		frappe.set_user(MGR1_USER)
		after_mgr1 = get_leave_applications(
			employee=self.mgr1_emp, approver_id=MGR1_USER, for_approval=True
		)
		self.assertNotIn(doc.name, [r["name"] for r in after_mgr1])

	def test_sync_refuses_to_run_outside_mysite_local(self):
		from hrms_custom.scripts.sync_pending_leave_approver import sync_pending_leave_approver

		prev_site = frappe.local.site
		try:
			frappe.local.site = "production.example.com"
			with self.assertRaises(frappe.ValidationError):
				sync_pending_leave_approver(dry_run=True)
		finally:
			frappe.local.site = prev_site
