import frappe
from frappe import _
from frappe.utils import cint


def _get_employee_for_user(user: str | None = None) -> str | None:
	if not user:
		user = frappe.session.user
	return frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")


def is_authorized_approver(employee: str, user: str | None = None) -> bool:
	if not user:
		user = frappe.session.user

	if user == "Administrator":
		return True

	user_roles = frappe.get_roles(user)
	current_employee = _get_employee_for_user(user)

	# Self-approval strictly forbidden
	if current_employee and current_employee == employee:
		return False

	# Company-wide approvers
	if "HR Manager" in user_roles or "HR User" in user_roles:
		return True

	emp_doc = frappe.db.get_value(
		"Employee", employee, ["leave_approver", "reports_to"], as_dict=True
	)
	if not emp_doc:
		return False

	# Direct leave approver or direct reporting manager
	if emp_doc.leave_approver == user:
		return True
	if current_employee and emp_doc.reports_to == current_employee:
		return True

	return False


def get_authorized_employees(user: str | None = None) -> list[str]:
	"""
	Returns a list of employee IDs the user is authorized to approve for.
	Always excludes the user's own employee record.
	"""
	if not user:
		user = frappe.session.user

	user_roles = frappe.get_roles(user)
	current_employee = _get_employee_for_user(user)

	if user == "Administrator" or "HR Manager" in user_roles or "HR User" in user_roles:
		employees = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name")
		if current_employee and current_employee in employees:
			employees.remove(current_employee)
		return employees

	Employee = frappe.qb.DocType("Employee")
	query = (
		frappe.qb.from_(Employee)
		.select(Employee.name)
		.where(Employee.status == "Active")
	)

	conditions = (Employee.leave_approver == user)
	if current_employee:
		query = query.where(Employee.name != current_employee)
		conditions = conditions | (Employee.reports_to == current_employee)

	query = query.where(conditions)
	rows = query.run(as_dict=True)
	return [r.name for r in rows]


@frappe.whitelist()
def get_compensatory_leave_requests(
	for_approval: int | str | bool = False,
	limit: int | None = 10,
) -> list[dict]:
	for_approval = cint(for_approval)
	current_employee = _get_employee_for_user()
	limit = cint(limit) or 10

	fields = [
		"name",
		"employee",
		"employee_name",
		"department",
		"leave_type",
		"work_from_date",
		"work_end_date",
		"half_day",
		"half_day_date",
		"reason",
		"docstatus",
		"creation",
	]

	if for_approval:
		authorized_employees = get_authorized_employees()
		if not authorized_employees:
			return []

		return frappe.get_list(
			"Compensatory Leave Request",
			fields=fields,
			filters=[
				["docstatus", "=", 0],
				["employee", "in", authorized_employees],
			],
			order_by="creation desc",
			limit=limit,
		)
	else:
		if not current_employee:
			return []

		return frappe.get_list(
			"Compensatory Leave Request",
			fields=fields,
			filters=[
				["employee", "=", current_employee],
				["docstatus", "!=", 2],
			],
			order_by="creation desc",
			limit=limit,
		)


@frappe.whitelist()
def approve_compensatory_leave_request(docname: str) -> dict:
	if not docname:
		frappe.throw(_("Document name is mandatory"))

	doc = frappe.get_doc("Compensatory Leave Request", docname)

	# 1. Authorization check first (prevents state leak to unauthorized users)
	if not is_authorized_approver(doc.employee):
		frappe.throw(_("You are not permitted to approve this request."), frappe.PermissionError)

	# 2. Idempotency / state check second
	if doc.docstatus != 0:
		frappe.throw(_("This Compensatory Leave Request has already been submitted or processed."))

	# 3. Bypass submit=0 role check for Leave Approver, then call doc.submit()
	doc.flags.ignore_permissions = True
	doc.submit()

	return {
		"status": "Approved",
		"docname": doc.name,
		"employee": doc.employee,
	}


@frappe.whitelist()
def reject_compensatory_leave_request(docname: str, reason: str | None = None) -> dict:
	if not docname:
		frappe.throw(_("Document name is mandatory"))

	doc = frappe.get_doc("Compensatory Leave Request", docname)

	# 1. Authorization check first
	if not is_authorized_approver(doc.employee):
		frappe.throw(_("You are not permitted to reject this request."), frappe.PermissionError)

	# 2. State check second
	if doc.docstatus != 0:
		frappe.throw(_("This Compensatory Leave Request has already been processed."))

	# 3. Draft requests are deleted on rejection
	frappe.delete_doc("Compensatory Leave Request", docname, ignore_permissions=True)

	return {
		"status": "Rejected",
		"docname": docname,
	}
