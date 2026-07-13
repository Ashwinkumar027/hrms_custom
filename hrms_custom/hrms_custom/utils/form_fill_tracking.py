import frappe


def increment_fill_count(doc, method):
    if not getattr(doc, "employee", None):
        return

    tracker_name = frappe.db.get_value(
        "Form Fill Tracker",
        {"employee": doc.employee, "form_doctype": doc.doctype},
        "name"
    )

    if not tracker_name:
        return

    tracker = frappe.get_doc("Form Fill Tracker", tracker_name)
    if not doc.flags.get("_fill_count_incremented"):
        tracker.fill_count = (tracker.fill_count or 0) + 1
        tracker.record_name = doc.name
        tracker.save(ignore_permissions=True)
        doc.flags._fill_count_incremented = True
