import frappe

def create_onboarding_workflow():
    print("\n--- Creating Employee Onboarding Workflow ---")

    # Create Workflow States
    states = [
        {"workflow_state_name": "Pending Manager Input", "style": "Warning"},
        {"workflow_state_name": "Pending HR Review", "style": "Warning"},
        {"workflow_state_name": "Onboarding In Progress", "style": "Primary"},
        {"workflow_state_name": "Completed", "style": "Success"},
    ]
    for state in states:
        if not frappe.db.exists("Workflow State", state["workflow_state_name"]):
            ws = frappe.new_doc("Workflow State")
            ws.workflow_state_name = state["workflow_state_name"]
            ws.style = state["style"]
            ws.insert(ignore_permissions=True)
            print("  State: " + state["workflow_state_name"])

    # Create Actions
    actions = ["Assign to Manager", "Submit Activities", "HR Approve & Start", "Complete"]
    for action in actions:
        if not frappe.db.exists("Workflow Action Master", action):
            wa = frappe.new_doc("Workflow Action Master")
            wa.workflow_action_name = action
            wa.insert(ignore_permissions=True)
            print("  Action: " + action)

    frappe.db.commit()

    # Delete existing
    if frappe.db.exists("Workflow", "Employee Onboarding Workflow"):
        frappe.delete_doc("Workflow", "Employee Onboarding Workflow",
            ignore_permissions=True, force=True)

    wf = frappe.new_doc("Workflow")
    wf.workflow_name = "Employee Onboarding Workflow"
    wf.document_type = "Employee Onboarding"
    wf.is_active = 1
    wf.override_status = 0
    wf.send_email_alert = 0

    wf.append("states", {"state": "Draft", "doc_status": "0",
        "allow_edit": "HR User", "style": "Primary"})
    wf.append("states", {"state": "Pending Manager Input", "doc_status": "0",
        "allow_edit": "HR Manager", "style": "Warning"})
    wf.append("states", {"state": "Pending HR Review", "doc_status": "0",
        "allow_edit": "HR User", "style": "Warning"})
    wf.append("states", {"state": "Onboarding In Progress", "doc_status": "1",
        "allow_edit": "HR User", "style": "Primary"})

    wf.append("transitions", {"state": "Draft",
        "action": "Assign to Manager", "next_state": "Pending Manager Input",
        "allowed": "HR User", "allow_self_approval": 1})
    wf.append("transitions", {"state": "Pending Manager Input",
        "action": "Submit Activities", "next_state": "Pending HR Review",
        "allowed": "HR Manager", "allow_self_approval": 1})
    wf.append("transitions", {"state": "Pending HR Review",
        "action": "HR Approve & Start", "next_state": "Onboarding In Progress",
        "allowed": "HR User", "allow_self_approval": 1})

    wf.insert(ignore_permissions=True)
    frappe.db.commit()
    print("Workflow created!")
