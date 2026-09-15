import frappe
from frappe import _
from frappe.client import get_doc_permissions as stock_get_doc_permissions


@frappe.whitelist()
def get_doc_permissions(doctype: str, docname: str):
	result = stock_get_doc_permissions(doctype, docname)

	if doctype in ("Leave Application", "Attendance Request"):
		result["permissions"]["delete"] = 0

	if doctype == "Leave Application":
		state = frappe.db.get_value(
			"Leave Application", docname, ["docstatus", "status", "employee"], as_dict=True
		)
		if state and state.docstatus == 0:
			if state.status == "Open":
				# on_submit() unconditionally rejects submission while status
				# is "Open", regardless of who submits (see
				# hrms/hr/doctype/leave_application/leave_application.py
				# on_submit: "Only Leave Applications with status 'Approved'
				# and 'Rejected' can be submitted"). get_doc_permissions is
				# role/permlevel-based and doesn't know this, so it wrongly
				# reports submit=1 to anyone holding submit rights on the
				# doctype, which shows a Submit button in the PWA that
				# always fails.
				result["permissions"]["submit"] = 0

			employee_user = frappe.db.get_value("Employee", state.employee, "user_id")
			if employee_user == frappe.session.user and frappe.session.user != "Administrator":
				# The applicant should never be the one finalizing their own
				# Leave Application, regardless of status -- normal
				# approvals now auto-submit (see CustomLeaveApplication.
				# on_update), so this only still matters for a record left
				# over from before that existed, and letting the applicant
				# submit it themselves is exactly the self-approval path
				# validate_for_self_approval()/_validate_self_approval_
				# hardening() already reject.
				result["permissions"]["submit"] = 0

	return result


@frappe.whitelist()
def cancel_pending_leave(name: str):
	if not name or not isinstance(name, str):
		frappe.throw(_("Invalid Leave Application"))

	doc = frappe.get_doc("Leave Application", name)

	if doc.docstatus != 0:
		frappe.throw(_("Only pending Leave Applications can be cancelled."))

	if doc.status not in ("Open", "Draft"):
		frappe.throw(_("Cannot cancel Leave Application with status '{0}'.").format(doc.status))

	user = frappe.session.user
	roles = frappe.get_roles(user)
	employee_user = frappe.db.get_value("Employee", doc.employee, "user_id")

	is_applicant = (user == employee_user or user == doc.owner)
	is_approver = (user == doc.leave_approver)
	is_admin_or_hr = any(r in roles for r in ("System Manager", "HR Manager", "HR User"))

	if not (is_applicant or is_approver or is_admin_or_hr):
		frappe.throw(_("You are not authorized to cancel this Leave Application."), frappe.PermissionError)

	doc.db_set("status", "Cancelled")
	doc.add_comment("Comment", text=_("Cancelled by {0}").format(user))
	frappe.clear_document_cache("Leave Application", doc.name)
	return {"name": doc.name, "status": "Cancelled"}
