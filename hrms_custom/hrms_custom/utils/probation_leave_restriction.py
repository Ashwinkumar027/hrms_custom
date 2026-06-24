import frappe


def check_probation_leave_type(doc, method=None):
    """Restrict employees on Probation status to only apply for Probation Leave."""

    employee_status = frappe.db.get_value("Employee", doc.employee, "status")

    if employee_status == "Probation" and doc.leave_type != "Probation Leave":
        frappe.throw(
            f"{doc.employee_name or doc.employee} is on Probation and can only apply for "
            f"<b>Probation Leave</b>. Selected Leave Type: <b>{doc.leave_type}</b>."
        )
