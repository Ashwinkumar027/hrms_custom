import frappe


def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    # These roles get full unrestricted access via DocPerm — no extra filter needed
    if (
        user == "Administrator"
        or "System Manager" in roles
        or "HR Manager" in roles
        or "HR User" in roles
    ):
        return None

    user_escaped = frappe.db.escape(user)

    return f"""
        (
            `tabAttendance Request`.owner = {user_escaped}
            OR EXISTS (
                SELECT 1
                FROM `tabEmployee`
                WHERE `tabEmployee`.name = `tabAttendance Request`.employee
                AND `tabEmployee`.leave_approver = {user_escaped}
            )
        )
    """
