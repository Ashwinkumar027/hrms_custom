import frappe


def execute():
    """Copy custom_permission_type into reason for existing Permission-type
    Attendance Requests, before custom_request_type/custom_permission_type
    are hidden from the Attendance Request form.

    Historically, custom_request_type == "Permission Request" always left
    reason blank (see CustomAttendanceRequest._clean_request_type_fields,
    now removed). Once the flattened single-reason form ships, reason is the
    only field the app reads, so this data needs to move before it's
    effectively unreachable.
    """
    if not frappe.db.has_column("Attendance Request", "custom_request_type"):
        return
    if not frappe.db.has_column("Attendance Request", "custom_permission_type"):
        return

    rows = frappe.get_all(
        "Attendance Request",
        filters={
            "custom_request_type": "Permission Request",
            "custom_permission_type": ["!=", ""],
        },
        fields=["name", "reason", "custom_permission_type"],
    )

    for row in rows:
        if row.reason:
            continue
        frappe.db.set_value(
            "Attendance Request",
            row.name,
            "reason",
            row.custom_permission_type,
            update_modified=False,
        )
