import frappe


def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return None

    user_escaped = frappe.db.escape(user)

    return f"""
        (
            `tabAttendance Request`.owner = {user_escaped}
            OR (
                `tabAttendance Request`.workflow_state = 'Pending Approval'
                AND EXISTS (
                    SELECT 1
                    FROM `tabEmployee`
                    WHERE `tabEmployee`.name = `tabAttendance Request`.employee
                    AND `tabEmployee`.leave_approver = {user_escaped}
                )
            )
        )
    """
