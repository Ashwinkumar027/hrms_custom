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
			"Leave Application", docname, ["docstatus", "status", "employee", "owner"], as_dict=True
		)
		if state:
			employee_user = frappe.db.get_value("Employee", state.employee, "user_id")
			is_applicant = bool(
				(employee_user and employee_user == frappe.session.user)
				or (state.owner and state.owner == frappe.session.user)
			)
			result["is_applicant"] = 1 if is_applicant else 0

			# Leave approver / non-applicant must NEVER have cancel permission on Leave Application.
			# Only the applied person can cancel the leave.
			# Also when status is not pending (e.g. Rejected/Approved/Cancelled), cancel is disabled.
			if not is_applicant or state.status not in ("Open", "Draft"):
				result["permissions"]["cancel"] = 0

			if state.docstatus == 0:
				if state.status == "Open":
					result["permissions"]["submit"] = 0

				if is_applicant and frappe.session.user != "Administrator":
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
	employee_user = frappe.db.get_value("Employee", doc.employee, "user_id")
	is_applicant = (user == employee_user or user == doc.owner)

	# Only the applied person can cancel the leave
	if not (is_applicant or user == "Administrator"):
		frappe.throw(_("Only the applied person can cancel the leave application."), frappe.PermissionError)

	doc.db_set("status", "Cancelled")
	doc.add_comment("Comment", text=_("Cancelled by {0}").format(user))
	frappe.clear_document_cache("Leave Application", doc.name)
	return {"name": doc.name, "status": "Cancelled"}
