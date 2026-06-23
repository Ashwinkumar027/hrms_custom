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
    employee = frappe.db.get_value(
        "Employee", {"user_id": user}, "name"
    )

    if not employee:
        return "1=0"  # Show nothing

    # Only show own record
    return "`tabEmployee`.`name` = '{0}'".format(employee)
