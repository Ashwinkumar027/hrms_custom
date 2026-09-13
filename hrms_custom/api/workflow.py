import json
import frappe
from frappe.model.workflow import get_transitions as stock_get_transitions


@frappe.whitelist()
def get_transitions(doc, workflow=None, raise_exception=False):
    transitions = stock_get_transitions(doc, workflow=workflow, raise_exception=raise_exception)

    if isinstance(doc, str):
        try:
            doc = json.loads(doc)
        except Exception:
            pass

    doctype = doc.get("doctype") if isinstance(doc, dict) else getattr(doc, "doctype", None)

    if doctype == "Attendance Request":
        docname = doc.get("name") if isinstance(doc, dict) else getattr(doc, "name", None)
        employee = doc.get("employee") if isinstance(doc, dict) else getattr(doc, "employee", None)

        if not employee and docname:
            employee = frappe.db.get_value("Attendance Request", docname, "employee")

        user = frappe.session.user
        if user and user != "Administrator":
            employee_user = frappe.db.get_value("Employee", employee, "user_id") if employee else None
            owner = doc.get("owner") if isinstance(doc, dict) else getattr(doc, "owner", None)
            if not owner and docname:
                owner = frappe.db.get_value("Attendance Request", docname, "owner")

            if (employee_user and employee_user == user) or (owner and owner == user):
                transitions = [t for t in transitions if t.get("action") not in ("Approve", "Reject")]

    return transitions
