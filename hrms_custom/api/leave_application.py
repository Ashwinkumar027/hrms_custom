import frappe
from frappe.client import get_doc_permissions as stock_get_doc_permissions


@frappe.whitelist()
def get_doc_permissions(doctype: str, docname: str):
    result = stock_get_doc_permissions(doctype, docname)

    if doctype == "Leave Application":
        state = frappe.db.get_value(
            "Leave Application", docname, ["docstatus", "status", "employee"], as_dict=True
        )
        if state and state.docstatus == 0:
            if state.status == "Open":
                # on_submit() unconditionally rejects submission while status
                # is "Open", regardless of who submits (see
                # hrms/hr/doctype/leave_application/leave_application.py
                # on_submit: "Only Leave Applications with status 'Approved'
                # and 'Rejected' can be submitted"). get_doc_permissions is
                # role/permlevel-based and doesn't know this, so it wrongly
                # reports submit=1 to anyone holding submit rights on the
                # doctype, which shows a Submit button in the PWA that
                # always fails.
                result["permissions"]["submit"] = 0

            employee_user = frappe.db.get_value("Employee", state.employee, "user_id")
            if employee_user == frappe.session.user and frappe.session.user != "Administrator":
                # The applicant should never be the one finalizing their own
                # Leave Application, regardless of status -- normal
                # approvals now auto-submit (see CustomLeaveApplication.
                # on_update), so this only still matters for a record left
                # over from before that existed, and letting the applicant
                # submit it themselves is exactly the self-approval path
                # validate_for_self_approval()/_validate_self_approval_
                # hardening() already reject.
                result["permissions"]["submit"] = 0

    return result
