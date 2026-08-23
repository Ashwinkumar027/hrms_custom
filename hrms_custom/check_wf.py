import frappe

def execute():
    try:
        wf = frappe.get_doc("Workflow", "Manpower Requisition Flow")
        for t in wf.transitions:
            print(f"Action: '{t.action}' -> State: '{t.next_state}'")
    except Exception as e:
        print(f"Error: {e}")
