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
    Called from before_insert(). If a tracked record already exists in Draft for this
    employee+doctype, merge into it. If already submitted, preserve it and allow new insert.
    Enforces dynamic submission limit configured in Offer Letter Print Settings.
    """
    if not getattr(doc, "employee", None):
        return False

    # 1. Fetch dynamic max limit from Offer Letter Print Settings for company
    company = doc.get("company")
    if not company:
        company = frappe.db.get_value("Employee", doc.employee, "company")

    max_limit = 0
    if company and frappe.db.exists("Offer Letter Print Settings", company):
        try:
            max_limit = frappe.db.get_value("Offer Letter Print Settings", company, "max_agreement_submissions") or 0
            max_limit = int(max_limit)
        except Exception:
            max_limit = 0

    # 2. Check submitted agreements count
    submitted_count = frappe.db.count(doc.doctype, {"employee": doc.employee, "docstatus": 1})
    if max_limit > 0 and submitted_count >= max_limit:
        frappe.throw(
            f"You have already submitted the maximum allowed number of agreements ({max_limit}). Please contact HR."
        )

    # 3. Check tracking for existing record
    tracker = frappe.db.get_value(
        "Form Fill Tracker",
        {"employee": doc.employee, "form_doctype": doc.doctype},
        ["name", "record_name", "fill_count"],
        as_dict=True
    )

    if not tracker or not tracker.record_name or not frappe.db.exists(doc.doctype, tracker.record_name):
        return False

    existing_status = frappe.db.get_value(doc.doctype, tracker.record_name, "docstatus")
    # NEVER overwrite an already submitted agreement (docstatus == 1)! Preserve old historical records.
    if existing_status == 1:
        return False

    existing = frappe.get_doc(doc.doctype, tracker.record_name)
    for df in doc.meta.fields:
        if df.fieldtype in ("Section Break", "Column Break", "HTML"):
            continue
        existing.set(df.fieldname, doc.get(df.fieldname))

    existing.flags.ignore_permissions = True
    existing.save()
    frappe.db.commit()

    if route:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = f"/{route}/{existing.name}"
        frappe.local.flags.redirect_location = frappe.local.response["location"]
        raise frappe.Redirect

    return True
