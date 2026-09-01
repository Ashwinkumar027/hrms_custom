import frappe
from frappe.client import get_doc_permissions as stock_get_doc_permissions


@frappe.whitelist()
def get_doc_permissions(doctype: str, docname: str):
    result = stock_get_doc_permissions(doctype, docname)

    if doctype == "Leave Application":
        state = frappe.db.get_value(
            "Leave Application", docname, ["docstatus", "status"], as_dict=True
        )
        if state and state.docstatus == 0 and state.status == "Open":
            # on_submit() unconditionally rejects submission while status is
            # "Open", regardless of who submits (see
            # hrms/hr/doctype/leave_application/leave_application.py on_submit:
            # "Only Leave Applications with status 'Approved' and 'Rejected'
            # can be submitted"). get_doc_permissions is role/permlevel-based
            # and doesn't know this, so it wrongly reports submit=1 to anyone
            # holding submit rights on the doctype, which shows a Submit
            # button in the PWA that always fails.
            result["permissions"]["submit"] = 0

    return result
