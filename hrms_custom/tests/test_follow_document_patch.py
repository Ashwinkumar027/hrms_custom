# Copyright (c) 2026, ASHWIN and Contributors
# See license.txt
"""Tests for hrms_custom.monkey_patches -- the follow_document doc_name-type
workaround. See hrms_custom/monkey_patches.py for the full explanation of the
bug this patch works around.

Two things worth knowing before reading these tests:

1. Whether Document.insert() calls follow_document() at all is gated by
   User.follow_created_documents. Whether that call actually creates a
   Document Follow record is gated separately, inside follow_document itself,
   by (a) User.document_follow_notify and (b) the target doctype's own
   track_changes meta flag. Both PWA Notification and Leave Application have
   track_changes = 0 in this codebase, so a real Document Follow record can
   never be created for them regardless of this patch -- that's an existing,
   unrelated doctype configuration choice, not something this patch changes
   or could change. Attendance Request has track_changes = 1, so it's used
   here for the "the feature actually still works end-to-end" assertions.

2. Administrator can never follow anything (frappe.desk.form.document_follow
   hard-codes `if user == "Administrator": return False`), so all tests here
   use a real non-Administrator test user.
"""

import frappe
from frappe.tests import IntegrationTestCase

import hrms_custom.monkey_patches as monkey_patches

TEST_EMPLOYEE = "HR-EMP-00003"
TEST_USER = "kishore.k@aionioncapital.com"


class IntegrationTestFollowDocumentPatch(IntegrationTestCase):
	"""Integration tests for the follow_document monkey patch."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		monkey_patches.apply()

	def setUp(self):
		self._original_user = frappe.session.user
		self._user_doc = frappe.get_doc("User", TEST_USER)
		self._original_flags = {
			"follow_created_documents": self._user_doc.follow_created_documents,
			"document_follow_notify": self._user_doc.document_follow_notify,
		}

	def tearDown(self):
		frappe.set_user("Administrator")
		user_doc = frappe.get_doc("User", TEST_USER)
		user_doc.follow_created_documents = self._original_flags["follow_created_documents"]
		user_doc.document_follow_notify = self._original_flags["document_follow_notify"]
		user_doc.save(ignore_permissions=True)
		frappe.clear_cache(user=TEST_USER)
		frappe.set_user(self._original_user)

	def _enable_follow_flags(self):
		user_doc = frappe.get_doc("User", TEST_USER)
		user_doc.follow_created_documents = 1
		user_doc.document_follow_notify = 1
		user_doc.save(ignore_permissions=True)
		frappe.clear_cache(user=TEST_USER)

	def test_pwa_notification_insert_does_not_raise(self):
		"""The actual bug: inserting an autoincrement-named doctype (PWA
		Notification) as a user with follow_created_documents=1 must not
		raise FrappeTypeError. PWA Notification has track_changes=0, so no
		Document Follow record is expected here regardless of the patch --
		this test only asserts the crash is gone."""
		self._enable_follow_flags()
		frappe.set_user(TEST_USER)

		notification = frappe.new_doc("PWA Notification")
		notification.from_user = TEST_USER
		notification.to_user = TEST_USER
		notification.message = "test_follow_document_patch"

		try:
			notification.insert(ignore_permissions=True)
		except frappe.exceptions.FrappeTypeError:
			self.fail(
				"follow_document raised FrappeTypeError on an autoincrement "
				"doc_name -- the monkey patch did not take effect."
			)

		self.assertIsInstance(notification.name, int)

	def test_patched_follow_document_is_whitelisted(self):
		"""Regression guard: losing the @frappe.whitelist() on the
		replacement would silently break the Desk 'Follow' button."""
		import frappe.desk.form.document_follow as document_follow_module

		self.assertIn(document_follow_module.follow_document, frappe.whitelisted)

	def test_apply_is_idempotent(self):
		import frappe.desk.form.document_follow as document_follow_module

		monkey_patches.apply()
		fn_after_first = document_follow_module.follow_document

		monkey_patches.apply()
		fn_after_second = document_follow_module.follow_document

		self.assertIs(
			fn_after_first,
			fn_after_second,
			"apply() wrapped follow_document again instead of being a no-op on the second call.",
		)

	def test_leave_application_saves_and_attendance_request_follow_works_end_to_end(self):
		"""End-to-end via the real Document.insert() call site (not calling
		follow_document directly): both doctypes must save without raising.
		Attendance Request additionally has track_changes=1, so it must also
		produce a real Document Follow record -- proving the patched
		follow_document doesn't just swallow the error, it still does its job."""
		self._enable_follow_flags()
		frappe.set_user(TEST_USER)

		leave_application = frappe.new_doc("Leave Application")
		leave_application.employee = TEST_EMPLOYEE
		leave_application.leave_type = "Leave Without Pay"
		leave_application.from_date = "2026-11-10"
		leave_application.to_date = "2026-11-10"
		leave_application.half_day = 0
		leave_application.insert(ignore_permissions=True)
		self.assertTrue(leave_application.name)

		attendance_request = frappe.new_doc("Attendance Request")
		attendance_request.employee = TEST_EMPLOYEE
		attendance_request.reason = "Regularization"
		attendance_request.from_date = frappe.utils.today()
		attendance_request.to_date = frappe.utils.today()
		attendance_request.insert(ignore_permissions=True)
		self.assertTrue(attendance_request.name)

		is_following = frappe.db.exists(
			"Document Follow",
			{
				"ref_doctype": "Attendance Request",
				"ref_docname": attendance_request.name,
				"user": TEST_USER,
			},
		)
		self.assertTrue(
			is_following,
			"Expected a real Document Follow record for the Attendance Request "
			"(track_changes=1) -- the follow feature itself, not just crash-avoidance.",
		)
