import frappe


def increment_fill_count(doc, method):
    if not getattr(doc, "employee", None):
        return

    if doc.flags.get("_fill_count_incremented"):
        return

    tracker_name = frappe.db.get_value(
        "Form Fill Tracker",
        {"employee": doc.employee, "form_doctype": doc.doctype},
        "name"
    )

    if not tracker_name:
        tracker = frappe.new_doc("Form Fill Tracker")
        tracker.employee = doc.employee
        tracker.form_doctype = doc.doctype
        tracker.record_name = doc.name
        tracker.fill_count = 1
        tracker.insert(ignore_permissions=True)
    else:
        tracker = frappe.get_doc("Form Fill Tracker", tracker_name)
        tracker.fill_count = (tracker.fill_count or 0) + 1
        tracker.record_name = doc.name
        tracker.save(ignore_permissions=True)

    frappe.db.commit()
    doc.flags._fill_count_incremented = True
