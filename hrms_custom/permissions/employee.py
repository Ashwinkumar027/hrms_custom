import frappe


def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    # These roles see all employees
    allowed_roles = ["HR Manager", "HR User", "System Manager", "Administrator"]
    user_roles = frappe.get_roles(user)

    if any(role in user_roles for role in allowed_roles):
        return ""

    # Get employee linked to this user
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")

    if not employee:
        return "1=0"  # Show nothing

    user_escaped = frappe.db.escape(user)
    employee_escaped = frappe.db.escape(employee)

    # Allow own record, direct reportees, or employees where user is assigned approver
    return f"""(
        `tabEmployee`.`name` = {employee_escaped}
        OR `tabEmployee`.`reports_to` = {employee_escaped}
        OR `tabEmployee`.`leave_approver` = {user_escaped}
        OR `tabEmployee`.`expense_approver` = {user_escaped}
        OR EXISTS (
            SELECT 1 FROM `tabDepartment Approver` da
            WHERE da.parent = `tabEmployee`.`department`
            AND da.approver = {user_escaped}
        )
    )"""
