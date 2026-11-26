from unittest.mock import patch

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
		for emp_name, parent in [
			(self.director_emp, None),
			(self.mgr_emp, self.director_emp),
			(self.sub_emp, self.mgr_emp),
		]:
			frappe.db.set_value(
				"Employee",
				emp_name,
				{"reports_to": parent, "old_parent": parent or ""},
				update_modified=False,
			)
		rebuild_tree("Employee")
		frappe.cache.delete_key("user_permissions")
		frappe.cache.delete_value("employee_tree_unrepairable")
		frappe.cache.delete_value("employee_tree_hook_failed")
		for emp in [self.director_emp, self.mgr_emp, self.sub_emp]:
			frappe.cache.delete_value(f"employee_tree_broken:{emp}")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.cache.delete_value("employee_tree_unrepairable")
		frappe.cache.delete_value("employee_tree_hook_failed")
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
			if not emp.get("custom_roles_responsibilities"):
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
		cls._created_employees.append(doc.name)
		return doc.name

	@classmethod
	def _cleanup_all(cls):
		frappe.db.delete("Attendance Request", {"company": TEST_COMPANY})
		test_users = [
			"_test_loop_b@example.com",
			"_test_loop_a@example.com",
			SUB_USER,
			MGR_USER,
			DIRECTOR_USER,
		]
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

	def test_log_if_tree_broken_via_real_save(self):
		# 1. Corrupt lft/rgt in SQL and save WITHOUT changing reports_to:
		# Employee.on_update runs update_nsm first (which skips when reports_to is unchanged),
		# then doc_events on_update runs log_if_tree_broken and logs the still-broken tree.
		mgr_rgt = frappe.db.get_value("Employee", self.mgr_emp, "rgt")
		frappe.db.sql(
			"UPDATE `tabEmployee` SET lft = %s, rgt = %s WHERE name = %s",
			(mgr_rgt, mgr_rgt + 1, self.sub_emp),
		)

		before_logs = frappe.db.count("Error Log", {"method": "Employee tree broken after save"})
		sub_doc = frappe.get_doc("Employee", self.sub_emp)
		sub_doc.save(ignore_permissions=True)
		after_broken_save_logs = frappe.db.count("Error Log", {"method": "Employee tree broken after save"})
		self.assertEqual(after_broken_save_logs, before_logs + 1)

		# 2. Clear rate-limit key, corrupt again, then save WITH a reports_to change so
		# Employee.on_update -> update_nsm repairs lft/rgt BEFORE log_if_tree_broken runs.
		# Expect NO false "Employee tree broken after save" log.
		frappe.cache.delete_value(f"employee_tree_broken:{self.sub_emp}")
		mgr_rgt = frappe.db.get_value("Employee", self.mgr_emp, "rgt")
		frappe.db.sql(
			"UPDATE `tabEmployee` SET lft = %s, rgt = %s WHERE name = %s",
			(mgr_rgt, mgr_rgt + 1, self.sub_emp),
		)

		sub_doc = frappe.get_doc("Employee", self.sub_emp)
		sub_doc.reports_to = self.director_emp
		sub_doc.save(ignore_permissions=True)
		after_valid_move_logs = frappe.db.count("Error Log", {"method": "Employee tree broken after save"})
		self.assertEqual(after_valid_move_logs, after_broken_save_logs)

	def test_find_tree_problems_reports_loops_missing_manager_and_below_unrepairable(self):
		from hrms_custom.employee_tree import find_tree_problems

		# Self-reporting employee: director_emp -> director_emp
		frappe.db.sql(
			"UPDATE `tabEmployee` SET reports_to = %s WHERE name = %s",
			(self.director_emp, self.director_emp),
		)
		# Missing manager: mgr_emp -> nonexistent employee
		frappe.db.sql(
			"UPDATE `tabEmployee` SET reports_to = %s WHERE name = %s",
			("_MISSING_MANAGER_ID_", self.mgr_emp),
		)
		# sub_emp reports to mgr_emp (below missing_manager)
		problems = find_tree_problems()

		self.assertIn("reporting_loops", problems)
		self.assertIn(self.director_emp, {r["employee"] for r in problems["reporting_loops"]})
		self.assertIn("missing_manager", problems)
		self.assertIn(self.mgr_emp, {r["employee"] for r in problems["missing_manager"]})
		self.assertIn("below_unrepairable", problems)
		self.assertIn(self.sub_emp, {r["employee"] for r in problems["below_unrepairable"]})

		# None of the unrepairable nodes should spill into repairable buckets
		for key in ("outside_manager_range", "invalid_lft_rgt", "duplicate_numbers"):
			self.assertNotIn(key, problems)

	def test_find_tree_problems_ignores_duplicates_shared_with_unrepairable_rows(self):
		from hrms_custom.employee_tree import find_tree_problems

		# Put director_emp into a self-loop and copy sub_emp's lft/rgt onto director_emp
		sub_lft, sub_rgt = frappe.db.get_value("Employee", self.sub_emp, ["lft", "rgt"])
		frappe.db.sql(
			"UPDATE `tabEmployee` SET reports_to = %s, lft = %s, rgt = %s WHERE name = %s",
			(self.director_emp, sub_lft, sub_rgt, self.director_emp),
		)
		# Keep mgr_emp and sub_emp as roots/repairable by pointing mgr_emp to ""
		frappe.db.sql(
			"UPDATE `tabEmployee` SET reports_to = '' WHERE name = %s",
			(self.mgr_emp,),
		)
		rebuild_tree("Employee")
		# Force collision ONLY between unrepairable director_emp and repairable sub_emp
		sub_lft, sub_rgt = frappe.db.get_value("Employee", self.sub_emp, ["lft", "rgt"])
		frappe.db.sql(
			"UPDATE `tabEmployee` SET lft = %s, rgt = %s WHERE name = %s",
			(sub_lft, sub_rgt, self.director_emp),
		)

		problems = find_tree_problems()
		self.assertIn("reporting_loops", problems)
		self.assertNotIn("duplicate_numbers", problems)

	def test_repair_if_broken_repairs_healthy_leaves_loop_and_no_repeat_logs(self):
		from hrms_custom.employee_tree import find_tree_problems, repair_if_broken

		# Create a 2-node loop between two dedicated extra employees (so director/mgr/sub stay repairable)
		emp_a = "_test_loop_a@example.com"
		emp_b = "_test_loop_b@example.com"
		self._ensure_user(emp_a, ["Employee"])
		self._ensure_user(emp_b, ["Employee"])
		loop_a = self._ensure_employee("EMP-LOOP-A", "Loop", "A", emp_a)
		loop_b = self._ensure_employee("EMP-LOOP-B", "Loop", "B", emp_b)
		self._created_employees.extend([loop_a, loop_b])

		try:
			frappe.db.sql(
				"UPDATE `tabEmployee` SET reports_to = %s, lft = 9001, rgt = 9002 WHERE name = %s",
				(loop_b, loop_a),
			)
			frappe.db.sql(
				"UPDATE `tabEmployee` SET reports_to = %s, lft = 9003, rgt = 9004 WHERE name = %s",
				(loop_a, loop_b),
			)

			# Also corrupt repairable subordinate sub_emp
			mgr_rgt = frappe.db.get_value("Employee", self.mgr_emp, "rgt")
			frappe.db.sql(
				"UPDATE `tabEmployee` SET lft = %s, rgt = %s WHERE name = %s",
				(mgr_rgt, mgr_rgt + 1, self.sub_emp),
			)

			repaired_before = frappe.db.count("Error Log", {"method": "Employee tree repaired"})
			unrep_before = frappe.db.count("Error Log", {"method": "Employee tree unrepairable rows"})

			# First repair: fixes sub_emp, leaves loop_a and loop_b lft/rgt unchanged, logs once each
			res1 = repair_if_broken()
			self.assertTrue(res1["repaired"])
			self.assertEqual(
				frappe.db.get_value("Employee", loop_a, ["lft", "rgt"]),
				(9001, 9002),
			)
			self.assertEqual(
				frappe.db.get_value("Employee", loop_b, ["lft", "rgt"]),
				(9003, 9004),
			)

			after_problems = find_tree_problems()
			self.assertNotIn("outside_manager_range", after_problems)
			self.assertNotIn("invalid_lft_rgt", after_problems)
			self.assertNotIn("duplicate_numbers", after_problems)
			self.assertIn("reporting_loops", after_problems)
			self.assertEqual(
				{loop_a, loop_b},
				{r["employee"] for r in after_problems["reporting_loops"]},
			)

			repaired_after_1 = frappe.db.count("Error Log", {"method": "Employee tree repaired"})
			unrep_after_1 = frappe.db.count("Error Log", {"method": "Employee tree unrepairable rows"})
			self.assertEqual(repaired_after_1, repaired_before + 1)
			self.assertEqual(unrep_after_1, unrep_before + 1)

			# Second call when ONLY unrepairable loop remains: must NOT call rebuild_tree or log again
			with patch("hrms_custom.employee_tree.rebuild_tree") as mock_rebuild:
				res2 = repair_if_broken()
			mock_rebuild.assert_not_called()
			self.assertFalse(res2["repaired"])
			self.assertEqual(
				frappe.db.count("Error Log", {"method": "Employee tree repaired"}),
				repaired_after_1,
			)
			self.assertEqual(
				frappe.db.count("Error Log", {"method": "Employee tree unrepairable rows"}),
				unrep_after_1,
			)
		finally:
			for emp_name in [loop_a, loop_b]:
				frappe.db.sql(
					"UPDATE `tabEmployee` SET reports_to = '', old_parent = '' WHERE name = %s",
					(emp_name,),
				)
			rebuild_tree("Employee")
			for user in [emp_a, emp_b]:
				for up in frappe.get_all("User Permission", filters={"user": user}, pluck="name"):
					frappe.delete_doc("User Permission", up, force=1)
				emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
				if emp:
					frappe.delete_doc("Employee", emp, force=1)
				if frappe.db.exists("User", user):
					frappe.delete_doc("User", user, force=1)

	def test_log_if_tree_broken_never_raises(self):
		from hrms_custom.employee_tree import log_if_tree_broken

		sub_doc = frappe.get_doc("Employee", self.sub_emp)
		with patch("hrms_custom.employee_tree.frappe.cache.get_value", side_effect=RuntimeError("Redis down")):
			# Must swallow exception completely and never block Employee save
			log_if_tree_broken(sub_doc)

	def test_log_if_tree_broken_hook_failed_rate_limits_to_once_per_hour(self):
		from hrms_custom.employee_tree import log_if_tree_broken

		sub_doc = frappe.get_doc("Employee", self.sub_emp)
		frappe.cache.delete_value("employee_tree_hook_failed")
		before_logs = frappe.db.count("Error Log", {"method": "Employee tree hook failed"})

		orig_get_value = frappe.db.get_value

		def fail_on_employee(*args, **kwargs):
			if args and args[0] == "Employee":
				raise RuntimeError("DB timeout")
			return orig_get_value(*args, **kwargs)

		with patch("hrms_custom.employee_tree.frappe.db.get_value", side_effect=fail_on_employee):
			log_if_tree_broken(sub_doc)
			log_if_tree_broken(sub_doc)

		after_logs = frappe.db.count("Error Log", {"method": "Employee tree hook failed"})
		self.assertEqual(after_logs, before_logs + 1)

		ttl = frappe.cache.ttl(frappe.cache.make_key("employee_tree_hook_failed"))
		self.assertGreater(ttl, 0)
		self.assertLessEqual(ttl, 3600)
