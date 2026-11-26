import frappe
from frappe.tests.classes.integration_test_case import IntegrationTestCase
from frappe.utils.nestedset import rebuild_tree

TEST_COMPANY = "_Test Employee Tree Company"
HOLIDAY_LIST = "_Test Employee Tree Holiday List"

DIRECTOR_USER = "_test_tree_director@example.com"
MGR_USER = "_test_tree_mgr@example.com"
SUB_USER = "_test_tree_sub@example.com"


class TestEmployeeTree(IntegrationTestCase):
	_created_users = []
	_created_employees = []

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_users = []
		cls._created_employees = []
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

		cls._ensure_user(DIRECTOR_USER, ["Employee", "Leave Approver", "Employee Self Service"])
		cls._ensure_user(MGR_USER, ["Employee", "Leave Approver", "Employee Self Service"])
		cls._ensure_user(SUB_USER, ["Employee", "Employee Self Service"])

		cls.director_emp = cls._ensure_employee(
			"EMP-TREE-DIR", "Tree", "Director", DIRECTOR_USER, reports_to=None, leave_approver=None
		)
		cls.mgr_emp = cls._ensure_employee(
			"EMP-TREE-MGR",
			"Tree",
			"Manager",
			MGR_USER,
			reports_to=cls.director_emp,
			leave_approver=DIRECTOR_USER,
		)
		cls.sub_emp = cls._ensure_employee(
			"EMP-TREE-SUB",
			"Tree",
			"Subordinate",
			SUB_USER,
			reports_to=cls.mgr_emp,
			leave_approver=MGR_USER,
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
		rebuild_tree("Employee")
		frappe.cache.delete_key("user_permissions")
		for emp in [self.director_emp, self.mgr_emp, self.sub_emp]:
			frappe.cache.delete_value(f"employee_tree_broken:{emp}")

	def tearDown(self):
		frappe.set_user("Administrator")
		for emp in [self.director_emp, self.mgr_emp, self.sub_emp]:
			frappe.cache.delete_value(f"employee_tree_broken:{emp}")
		super().tearDown()

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
				"create_user_permission": 1,
			}
		)
		doc.insert(ignore_permissions=True, ignore_mandatory=True)
		cls._created_employees.append(doc.name)
		return doc.name

	@classmethod
	def _cleanup_all(cls):
		frappe.db.delete("Attendance Request", {"company": TEST_COMPANY})
		for user in [SUB_USER, MGR_USER, DIRECTOR_USER]:
			for up in frappe.get_all("User Permission", filters={"user": user}, pluck="name"):
				frappe.delete_doc("User Permission", up, force=1)
			emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
			if emp:
				frappe.delete_doc("Employee", emp, force=1)
		for user in cls._created_users:
			if frappe.db.exists("User", user):
				frappe.delete_doc("User", user, force=1)
		if frappe.db.exists("Company", TEST_COMPANY):
			frappe.delete_doc("Company", TEST_COMPANY, force=1)
		if frappe.db.exists("Holiday List", HOLIDAY_LIST):
			frappe.delete_doc("Holiday List", HOLIDAY_LIST, force=1)

	def _create_pending_attendance_request(self, employee, owner_user, req_date="2026-11-10"):
		doc = frappe.get_doc(
			{
				"doctype": "Attendance Request",
				"employee": employee,
				"from_date": req_date,
				"to_date": req_date,
				"reason": "Work From Home",
				"company": TEST_COMPANY,
				"workflow_state": "Pending Approval",
				"docstatus": 0,
			}
		)
		doc.flags.ignore_validate = True
		prev_user = frappe.session.user
		try:
			frappe.set_user(owner_user)
			doc.insert(ignore_permissions=True)
		finally:
			frappe.set_user(prev_user)
		return doc.name

	def test_find_tree_problems_detects_outside_manager_range(self):
		from hrms_custom.employee_tree import find_tree_problems

		mgr_lft, mgr_rgt = frappe.db.get_value("Employee", self.mgr_emp, ["lft", "rgt"])
		# Reproduce production symptom: subordinate's lft equals manager's rgt
		frappe.db.sql(
			"UPDATE `tabEmployee` SET lft = %s, rgt = %s WHERE name = %s",
			(mgr_rgt, mgr_rgt + 1, self.sub_emp),
		)

		problems = find_tree_problems()
		self.assertIn("outside_manager_range", problems)
		reported_employees = {row["employee"] for row in problems["outside_manager_range"]}
		self.assertIn(self.sub_emp, reported_employees)

	def test_find_tree_problems_detects_duplicate_numbers(self):
		from hrms_custom.employee_tree import find_tree_problems

		mgr_lft, mgr_rgt = frappe.db.get_value("Employee", self.mgr_emp, ["lft", "rgt"])
		frappe.db.sql(
			"UPDATE `tabEmployee` SET lft = %s, rgt = %s WHERE name = %s",
			(mgr_lft, mgr_rgt, self.sub_emp),
		)

		problems = find_tree_problems()
		self.assertIn("duplicate_numbers", problems)
		dups = problems["duplicate_numbers"]
		dup_values = {row["value"] for row in dups}
		self.assertTrue({mgr_lft, mgr_rgt}.intersection(dup_values))

	def test_find_tree_problems_detects_invalid_values(self):
		from hrms_custom.employee_tree import find_tree_problems

		# Case 1: lft/rgt = 0 (uninitialized NOT NULL default, lft <= 0 and lft >= rgt)
		frappe.db.sql(
			"UPDATE `tabEmployee` SET lft = 0, rgt = 0 WHERE name = %s",
			(self.sub_emp,),
		)
		problems = find_tree_problems()
		self.assertIn("invalid_lft_rgt", problems)
		self.assertIn(self.sub_emp, {r["employee"] for r in problems["invalid_lft_rgt"]})

		# Case 2: lft >= rgt (non-zero)
		frappe.db.sql(
			"UPDATE `tabEmployee` SET lft = 500, rgt = 500 WHERE name = %s",
			(self.sub_emp,),
		)
		problems = find_tree_problems()
		self.assertIn("invalid_lft_rgt", problems)
		self.assertIn(self.sub_emp, {r["employee"] for r in problems["invalid_lft_rgt"]})

	def test_repair_restores_healthy_tree(self):
		from hrms_custom.employee_tree import find_tree_problems, repair_if_broken

		mgr_rgt = frappe.db.get_value("Employee", self.mgr_emp, "rgt")
		frappe.db.sql(
			"UPDATE `tabEmployee` SET lft = %s, rgt = %s WHERE name = %s",
			(mgr_rgt, mgr_rgt + 1, self.sub_emp),
		)
		self.assertTrue(find_tree_problems())

		before_logs = frappe.db.count("Error Log", {"method": "Employee tree repaired"})
		repair_if_broken()

		self.assertEqual(find_tree_problems(), {})
		after_logs = frappe.db.count("Error Log", {"method": "Employee tree repaired"})
		self.assertEqual(after_logs, before_logs + 1)

	def test_repair_does_nothing_when_healthy(self):
		from hrms_custom.employee_tree import find_tree_problems, repair_if_broken

		self.assertEqual(find_tree_problems(), {})
		before_snapshot = frappe.db.sql(
			"SELECT name, lft, rgt FROM `tabEmployee` ORDER BY name",
			as_dict=True,
		)
		before_logs = frappe.db.count("Error Log", {"method": "Employee tree repaired"})

		repair_if_broken()

		after_snapshot = frappe.db.sql(
			"SELECT name, lft, rgt FROM `tabEmployee` ORDER BY name",
			as_dict=True,
		)
		after_logs = frappe.db.count("Error Log", {"method": "Employee tree repaired"})
		self.assertEqual(after_snapshot, before_snapshot)
		self.assertEqual(after_logs, before_logs)

	def test_team_visibility(self):
		from hrms.api import get_attendance_requests
		from hrms_custom.employee_tree import find_tree_problems, repair_if_broken

		req_name = self._create_pending_attendance_request(self.sub_emp, SUB_USER)

		# Corrupt subordinate's lft/rgt so it falls outside manager's range
		mgr_rgt = frappe.db.get_value("Employee", self.mgr_emp, "rgt")
		frappe.db.sql(
			"UPDATE `tabEmployee` SET lft = %s, rgt = %s WHERE name = %s",
			(mgr_rgt, mgr_rgt + 1, self.sub_emp),
		)
		frappe.cache.delete_key("user_permissions")

		frappe.set_user(MGR_USER)
		hidden_results = get_attendance_requests(employee=self.mgr_emp, for_approval=True)
		self.assertNotIn(req_name, [r["name"] for r in hidden_results])

		frappe.set_user("Administrator")
		repair_if_broken()
		self.assertEqual(find_tree_problems(), {})

		frappe.set_user(MGR_USER)
		visible_results = get_attendance_requests(employee=self.mgr_emp, for_approval=True)
		self.assertIn(req_name, [r["name"] for r in visible_results])

	def test_attendance_request_permission_query_conditions(self):
		from hrms.api import get_attendance_requests
		from hrms_custom.employee_tree import find_tree_problems

		# Intact tree: director_emp is above mgr_emp, so sub_emp is within director's lft/rgt range
		self.assertEqual(find_tree_problems(), {})

		req_name = self._create_pending_attendance_request(self.sub_emp, SUB_USER)

		# Director has User Permission covering sub_emp via intact nested set,
		# but is neither owner (SUB_USER) nor sub_emp.leave_approver (MGR_USER).
		frappe.set_user(DIRECTOR_USER)
		director_results = get_attendance_requests(employee=self.director_emp, for_approval=True)
		self.assertNotIn(req_name, [r["name"] for r in director_results])

		# Manager IS sub_emp.leave_approver and has an intact tree covering sub_emp.
		frappe.set_user(MGR_USER)
		mgr_results = get_attendance_requests(employee=self.mgr_emp, for_approval=True)
		self.assertIn(req_name, [r["name"] for r in mgr_results])

	def test_log_if_tree_broken_logs_when_outside_manager_range(self):
		from hrms_custom.employee_tree import log_if_tree_broken

		sub_doc = frappe.get_doc("Employee", self.sub_emp)
		mgr_rgt = frappe.db.get_value("Employee", self.mgr_emp, "rgt")
		frappe.db.sql(
			"UPDATE `tabEmployee` SET lft = %s, rgt = %s WHERE name = %s",
			(mgr_rgt, mgr_rgt + 1, self.sub_emp),
		)
		sub_doc.reload()

		before_logs = frappe.db.count("Error Log", {"method": "Employee tree broken after save"})
		log_if_tree_broken(sub_doc)
		after_logs = frappe.db.count("Error Log", {"method": "Employee tree broken after save"})
		self.assertEqual(after_logs, before_logs + 1)

	def test_log_if_tree_broken_rate_limits_to_once_per_24_hours(self):
		from hrms_custom.employee_tree import log_if_tree_broken

		sub_doc = frappe.get_doc("Employee", self.sub_emp)
		mgr_rgt = frappe.db.get_value("Employee", self.mgr_emp, "rgt")
		frappe.db.sql(
			"UPDATE `tabEmployee` SET lft = %s, rgt = %s WHERE name = %s",
			(mgr_rgt, mgr_rgt + 1, self.sub_emp),
		)
		sub_doc.reload()

		cache_key = f"employee_tree_broken:{self.sub_emp}"
		frappe.cache.delete_value(cache_key)

		before_logs = frappe.db.count("Error Log", {"method": "Employee tree broken after save"})
		log_if_tree_broken(sub_doc)
		log_if_tree_broken(sub_doc)
		after_logs = frappe.db.count("Error Log", {"method": "Employee tree broken after save"})
		self.assertEqual(after_logs, before_logs + 1)

		ttl = frappe.cache.ttl(frappe.cache.make_key(cache_key))
		self.assertGreater(ttl, 0)
		self.assertLessEqual(ttl, 86400)
