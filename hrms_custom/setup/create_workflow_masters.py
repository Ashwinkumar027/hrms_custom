import frappe

def create_workflow_masters():
    print("\n--- Fixing Workflow States and Action Masters ---")

    # Create "Pending HR Approval" with capital HR if not exists
    if not frappe.db.exists("Workflow State", "Pending HR Approval"):
        ws = frappe.new_doc("Workflow State")
        ws.workflow_state_name = "Pending HR Approval"
        ws.style = "Warning"
        ws.insert(ignore_permissions=True)
        print("  Created State: Pending HR Approval")
    else:
        print("  Already exists: Pending HR Approval")

    # All other needed states
    states = [
        {"workflow_state_name": "Draft", "style": "Primary"},
        {"workflow_state_name": "Pending Final Approval", "style": "Warning"},
        {"workflow_state_name": "Approved", "style": "Success"},
        {"workflow_state_name": "Rejected", "style": "Danger"},
    ]

    for state in states:
        if not frappe.db.exists("Workflow State", state["workflow_state_name"]):
            ws = frappe.new_doc("Workflow State")
            ws.workflow_state_name = state["workflow_state_name"]
            ws.style = state["style"]
            ws.insert(ignore_permissions=True)
            print("  Created State: " + state["workflow_state_name"])
        else:
            print("  Already exists: " + state["workflow_state_name"])

    # All needed actions
    actions = [
        "Submit for HR Approval",
        "HR Approve",
        "HR Reject",
        "Final Approve",
        "Final Reject",
    ]

    for action in actions:
        if not frappe.db.exists("Workflow Action Master", action):
            wa = frappe.new_doc("Workflow Action Master")
            wa.workflow_action_name = action
            wa.insert(ignore_permissions=True)
            print("  Created Action: " + action)
        else:
            print("  Already exists: " + action)

    frappe.db.commit()
    print("\nDone!")
