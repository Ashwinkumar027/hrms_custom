import frappe

def execute():
    try:
        wf = frappe.get_doc("Workflow", "Manpower Requisition Flow")
        for s in wf.states:
            if s.state == "Pending Final Approval":
                print(f"State: {s.state}, Allow Edit: {s.allow_edit}")
                
    except Exception as e:
        print(f"Error: {e}")
