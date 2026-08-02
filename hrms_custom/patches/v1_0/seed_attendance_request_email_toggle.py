import frappe


def execute():
    """Seed custom_enable_attendance_request_email to enabled by default.

    HR Settings is a Single doctype. In this Frappe version, a Custom
    Field's `default` is not retroactively written into the Singles data
    row when the field is added - frappe.db.get_single_value() reads back
    0 until a row actually exists, so all three Attendance Request
    notifications (which all gate on this field) would silently never
    fire on any site that hasn't opened HR Settings and saved since this
    field was introduced.

    Only seeds when the field has never been set at all. A stored 0 is a
    deliberate choice (someone turned the emails off) and must not be
    overwritten - so this checks for row existence in the Singles table
    directly, not a falsy value read. frappe.db.exists()/get_value() are
    not usable here: the Singles table has no `name`/`creation` columns,
    so the standard doctype-filter query path errors on it. This uses the
    same low-level query frappe.db.get_single_value() itself uses.
    """
    doctype = "HR Settings"
    fieldname = "custom_enable_attendance_request_email"

    existing_rows = frappe.qb.get_query(
        table="Singles",
        filters={"doctype": doctype, "field": fieldname},
        fields="value",
    ).run()

    if existing_rows:
        return

    frappe.db.set_single_value(doctype, fieldname, 1)
