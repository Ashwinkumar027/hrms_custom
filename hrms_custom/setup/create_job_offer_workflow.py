import frappe

def create_job_offer_workflow():
    print("\n--- Creating Job Offer Workflow ---")

    if frappe.db.exists("Workflow", "Job Offer Approval Workflow"):
        frappe.delete_doc("Workflow", "Job Offer Approval Workflow",
            ignore_permissions=True, force=True)
        print("  Deleted existing workflow")

    states = [
        {"workflow_state_name": "Draft", "style": "Primary"},
        {"workflow_state_name": "Pending BH Approval", "style": "Warning"},
        {"workflow_state_name": "Approved by BH", "style": "Success"},
        {"workflow_state_name": "Rejected", "style": "Danger"},
    ]

    for state in states:
        if not frappe.db.exists("Workflow State", state["workflow_state_name"]):
            ws = frappe.new_doc("Workflow State")
            ws.workflow_state_name = state["workflow_state_name"]
            ws.style = state["style"]
            ws.insert(ignore_permissions=True)
            print("  Created state: " + state["workflow_state_name"])

    actions = ["Send for BH Approval", "BH Approve", "BH Reject"]
    for action in actions:
        if not frappe.db.exists("Workflow Action Master", action):
            wa = frappe.new_doc("Workflow Action Master")
            wa.workflow_action_name = action
            wa.insert(ignore_permissions=True)
            print("  Created action: " + action)

    frappe.db.commit()

    wf = frappe.new_doc("Workflow")
    wf.workflow_name = "Job Offer Approval Workflow"
    wf.document_type = "Job Offer"
    wf.is_active = 1
    wf.override_status = 0
    wf.send_email_alert = 0

    # States — all doc_status 0 (saved, not submitted)
    wf.append("states", {
        "state": "Draft",
        "doc_status": "0",
        "allow_edit": "HR User",
        "update_field": "status",
        "update_value": "Awaiting Response",
        "style": "Primary"
    })
    wf.append("states", {
        "state": "Pending BH Approval",
        "doc_status": "0",
        "allow_edit": "Business Head",
        "update_field": "status",
        "update_value": "Awaiting Response",
        "style": "Warning"
    })
    wf.append("states", {
        "state": "Approved by BH",
        "doc_status": "0",
        "allow_edit": "HR User",
        "update_field": "status",
        "update_value": "Accepted",
        "style": "Success"
    })
    wf.append("states", {
        "state": "Rejected",
        "doc_status": "0",
        "allow_edit": "HR User",
        "update_field": "status",
        "update_value": "Rejected",
        "style": "Danger"
    })

    # Transitions
    wf.append("transitions", {
        "state": "Draft",
        "action": "Send for BH Approval",
        "next_state": "Pending BH Approval",
        "allowed": "HR User",
        "allow_self_approval": 1
    })
    wf.append("transitions", {
        "state": "Pending BH Approval",
        "action": "BH Approve",
        "next_state": "Approved by BH",
        "allowed": "Business Head",
        "allow_self_approval": 1
    })
    wf.append("transitions", {
        "state": "Pending BH Approval",
        "action": "BH Reject",
        "next_state": "Rejected",
        "allowed": "Business Head",
        "allow_self_approval": 1
    })

    wf.insert(ignore_permissions=True)
    frappe.db.commit()
    print("Job Offer Workflow created!")
