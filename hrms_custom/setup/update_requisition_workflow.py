import frappe

def update_requisition_workflow():
    print("\n--- Updating Manpower Requisition Workflow ---")

    wf = frappe.get_doc("Workflow", "Manpower Requisition Flow")

    # Clear existing states and transitions
    wf.states = []
    wf.transitions = []

    # New States
    wf.append("states", {
        "state": "Draft",
        "doc_status": "0",
        "allow_edit": "Hiring Manager",
        "style": "Primary"
    })
    wf.append("states", {
        "state": "Pending HR Approval",
        "doc_status": "0",
        "allow_edit": "HR Manager",
        "style": "Warning"
    })
    wf.append("states", {
        "state": "Pending Final Approval",
        "doc_status": "0",
        "allow_edit": "Final Approver",
        "style": "Warning"
    })
    wf.append("states", {
        "state": "Approved",
        "doc_status": "1",
        "allow_edit": "HR Manager",
        "style": "Success"
    })
    wf.append("states", {
        "state": "Rejected",
        "doc_status": "0",
        "allow_edit": "HR Manager",
        "style": "Danger"
    })

    # New Transitions
    wf.append("transitions", {
        "state": "Draft",
        "action": "Submit for HR Approval",
        "next_state": "Pending HR Approval",
        "allowed": "Hiring Manager",
        "allow_self_approval": 1
    })
    wf.append("transitions", {
        "state": "Pending HR Approval",
        "action": "HR Approve",
        "next_state": "Pending Final Approval",
        "allowed": "HR Manager",
        "allow_self_approval": 1
    })
    wf.append("transitions", {
        "state": "Pending HR Approval",
        "action": "HR Reject",
        "next_state": "Rejected",
        "allowed": "HR Manager",
        "allow_self_approval": 1
    })
    wf.append("transitions", {
        "state": "Pending Final Approval",
        "action": "Final Approve",
        "next_state": "Approved",
        "allowed": "Final Approver",
        "allow_self_approval": 1
    })
    wf.append("transitions", {
        "state": "Pending Final Approval",
        "action": "Final Reject",
        "next_state": "Rejected",
        "allowed": "Final Approver",
        "allow_self_approval": 1
    })

    wf.save(ignore_permissions=True)
    frappe.db.commit()
    print("Workflow updated successfully!")
    print("New flow: Draft → Pending HR Approval → Pending Final Approval → Approved")
