import frappe

def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    if "System Manager" in frappe.get_roles(user) or "HR Manager" in frappe.get_roles(user):
        return ""

    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return "1=0"

    # Employee sees their own claims; Reporting Manager sees claims where they are the RM
    return f"""(`tabTA Reimbursement Claim`.employee = {frappe.db.escape(employee)}
        OR `tabTA Reimbursement Claim`.reporting_manager = {frappe.db.escape(employee)})"""


def has_permission(doc, user):
    if not user:
        user = frappe.session.user

    if "System Manager" in frappe.get_roles(user) or "HR Manager" in frappe.get_roles(user):
        return True

    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return False

    if doc.employee == employee:
        return True

    if doc.reporting_manager == employee:
        return True

    return False
