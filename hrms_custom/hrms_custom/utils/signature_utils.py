import frappe


def validate_single_signature_source(doc, signature_pairs):
    """
    signature_pairs: list of tuples (draw_fieldname, upload_fieldname, label)
    Ensures only ONE of draw/upload is set per pair.
    """
    for draw_field, upload_field, label in signature_pairs:
        draw_val = doc.get(draw_field)
        upload_val = doc.get(upload_field)
        if draw_val and upload_val:
            frappe.throw(
                f"For {label}, please provide only one signature — either draw or upload, not both."
            )


def get_signature_image(doc, draw_field, upload_field):
    """Returns whichever signature source is filled, draw takes priority if somehow both exist."""
    return doc.get(draw_field) or doc.get(upload_field) or None
def merge_or_allow_insert(doc, route):
    """
    Called from before_insert(). If a tracked record already exists for this
    employee+doctype, merge the new submission's data into it instead of
    creating a duplicate, then redirect the browser there.
    Returns True if it handled a merge (caller should stop further insert).
    """
    if not getattr(doc, "employee", None):
        return False

    tracker = frappe.db.get_value(
        "Form Fill Tracker",
        {"employee": doc.employee, "form_doctype": doc.doctype},
        ["name", "record_name", "fill_count"],
        as_dict=True
    )

    if not tracker or not tracker.record_name or not frappe.db.exists(doc.doctype, tracker.record_name):
        return False

    if tracker.fill_count >= 2:
        frappe.throw("You have already submitted this form the maximum number of times (2). Please contact HR.")

    existing = frappe.get_doc(doc.doctype, tracker.record_name)
    for df in doc.meta.fields:
        if df.fieldtype in ("Section Break", "Column Break", "HTML"):
            continue
        existing.set(df.fieldname, doc.get(df.fieldname))

    existing.flags.ignore_permissions = True
    existing.save()
    frappe.db.commit()

    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = f"/{route}/{existing.name}"
    frappe.local.flags.redirect_location = frappe.local.response["location"]

    raise frappe.Redirect
