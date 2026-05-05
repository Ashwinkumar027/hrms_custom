import frappe

def create_job_requisition_workflow():
    print("--- Creating Job Requisition Workflow ---")

    states = [
        {"workflow_state_name": "Draft", "style": "Warning"},
        {"workflow_state_name": "Pending HR Approval", "style": "Primary"},
        {"workflow_state_name": "Pending Final Approval", "style": "Primary"},
        {"workflow_state_name": "Approved", "style": "Success"},
        {"workflow_state_name": "Rejected", "style": "Danger"},
    ]

    for state in states:
        if not frappe.db.exists("Workflow State", state["workflow_state_name"]):
            s = frappe.new_doc("Workflow State")
            s.workflow_state_name = state["workflow_state_name"]
            s.style = state["style"]
            s.insert(ignore_permissions=True)
            print("  Created state: " + state["workflow_state_name"])
        else:
            print("  State exists: " + state["workflow_state_name"])
    frappe.db.commit()

    actions = [
        "Submit for HR Approval",
        "HR Approve",
        "HR Reject",
        "Final Approve",
        "Final Reject",
    ]

    for action in actions:
        if not frappe.db.exists("Workflow Action Master", action):
            a = frappe.new_doc("Workflow Action Master")
            a.workflow_action_name = action
            a.insert(ignore_permissions=True)
            print("  Created action: " + action)
        else:
            print("  Action exists: " + action)
    frappe.db.commit()

    if frappe.db.exists("Workflow", "Manpower Requisition Flow"):
        frappe.delete_doc("Workflow", "Manpower Requisition Flow", force=True)
        frappe.db.commit()
        print("  Deleted old workflow")

    doc = frappe.new_doc("Workflow")
    doc.workflow_name = "Manpower Requisition Flow"
    doc.document_type = "Job Requisition"
    doc.workflow_state_field = "workflow_state"
    doc.is_active = 1
    doc.send_email_alert = 1

    doc.set("states", [])
    doc.append("states", {"state": "Draft", "doc_status": "0", "allow_edit": "Hiring Manager"})
    doc.append("states", {"state": "Pending HR Approval", "doc_status": "0", "allow_edit": "HR Manager"})
    doc.append("states", {"state": "Pending Final Approval", "doc_status": "0", "allow_edit": "Final Approver"})
    doc.append("states", {"state": "Approved", "doc_status": "1", "allow_edit": "Final Approver"})
    doc.append("states", {"state": "Rejected", "doc_status": "0", "allow_edit": "Hiring Manager"})

    doc.set("transitions", [])
    doc.append("transitions", {"state": "Draft", "action": "Submit for HR Approval", "next_state": "Pending HR Approval", "allowed": "Hiring Manager", "allow_self_approval": 1})
    doc.append("transitions", {"state": "Pending HR Approval", "action": "HR Approve", "next_state": "Pending Final Approval", "allowed": "HR Manager", "allow_self_approval": 1})
    doc.append("transitions", {"state": "Pending HR Approval", "action": "HR Reject", "next_state": "Rejected", "allowed": "HR Manager", "allow_self_approval": 1})
    doc.append("transitions", {"state": "Pending Final Approval", "action": "Final Approve", "next_state": "Approved", "allowed": "Final Approver", "allow_self_approval": 1})
    doc.append("transitions", {"state": "Pending Final Approval", "action": "Final Reject", "next_state": "Rejected", "allowed": "Final Approver", "allow_self_approval": 1})

    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    print("  Created: Manpower Requisition Flow")
    print("Workflow created successfully!")
