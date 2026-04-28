import frappe


def create_id_card_workflow():
    """
    Creates ID Card Approval workflow on Employee Onboarding.
    Run with:
    bench --site hrms.local execute hrms_custom.setup.create_id_card_workflow.create_id_card_workflow
    """

    # Step 1 — Create Workflow States first
    states = [
        {"workflow_state_name": "Pending",           "style": "Warning"},
        {"workflow_state_name": "ID Card Submitted",  "style": "Primary"},
        {"workflow_state_name": "ID Card Approved",   "style": "Success"},
        {"workflow_state_name": "ID Card Rejected",   "style": "Danger"},
    ]

    for state in states:
        if not frappe.db.exists("Workflow State", state["workflow_state_name"]):
            s = frappe.new_doc("Workflow State")
            s.workflow_state_name = state["workflow_state_name"]
            s.style = state["style"]
            s.insert(ignore_permissions=True)
            print(f"  Created state: {state['workflow_state_name']}")
        else:
            print(f"  State already exists: {state['workflow_state_name']}")

    frappe.db.commit()

    # Step 2 — Create Workflow Actions
    actions = [
        "Submit for ID Card Approval",
        "ID Card Approved",
        "ID Card Rejected",
        "Resubmit ID Card",
    ]

    for action in actions:
        if not frappe.db.exists("Workflow Action Master", action):
            a = frappe.new_doc("Workflow Action Master")
            a.workflow_action_name = action
            a.insert(ignore_permissions=True)
            print(f"  Created action: {action}")
        else:
            print(f"  Action already exists: {action}")

    frappe.db.commit()

    # Step 3 — Create the Workflow
    workflow_name = "ID Card Approval"

    if frappe.db.exists("Workflow", workflow_name):
        frappe.delete_doc("Workflow", workflow_name, force=True)
        frappe.db.commit()
        print(f"  Deleted existing workflow: {workflow_name}")

    doc = frappe.new_doc("Workflow")
    doc.workflow_name = workflow_name
    doc.document_type = "Employee Onboarding"
    doc.workflow_state_field = "workflow_state"
    doc.is_active = 1
    doc.send_email_alert = 1
    doc.dont_override_status = 0
    doc.enable_action_confirmation = 0

    # States
    doc.set("states", [])
    doc.append("states", {
        "state": "Pending",
        "doc_status": "0",
        "allow_edit": "All",
        "send_email_on_state": 1
    })
    doc.append("states", {
        "state": "ID Card Submitted",
        "doc_status": "0",
        "allow_edit": "All",
        "send_email_on_state": 1
    })
    doc.append("states", {
        "state": "ID Card Approved",
        "doc_status": "1",
        "allow_edit": "All",
        "send_email_on_state": 1
    })
    doc.append("states", {
        "state": "ID Card Rejected",
        "doc_status": "0",
        "allow_edit": "All",
        "send_email_on_state": 1
    })

    # Transitions
    doc.set("transitions", [])
    doc.append("transitions", {
        "state": "Pending",
        "action": "Submit for ID Card Approval",
        "next_state": "ID Card Submitted",
        "allowed": "All",
        "allow_self_approval": 1,
        "send_email_to_creator": 0
    })
    doc.append("transitions", {
        "state": "ID Card Submitted",
        "action": "ID Card Approved",
        "next_state": "ID Card Approved",
        "allowed": "HR Manager",
        "allow_self_approval": 1,
        "send_email_to_creator": 0
    })
    doc.append("transitions", {
        "state": "ID Card Submitted",
        "action": "ID Card Rejected",
        "next_state": "ID Card Rejected",
        "allowed": "HR Manager",
        "allow_self_approval": 1,
        "send_email_to_creator": 0
    })
    doc.append("transitions", {
        "state": "ID Card Rejected",
        "action": "Resubmit ID Card",
        "next_state": "ID Card Submitted",
        "allowed": "All",
        "allow_self_approval": 1,
        "send_email_to_creator": 0
    })

    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    print("  Created: ID Card Approval workflow")
    print("  States: Pending, ID Card Submitted, ID Card Approved, ID Card Rejected")
    print("  Transitions: 4 transitions added")
    print("\nID Card Approval workflow created successfully!")
