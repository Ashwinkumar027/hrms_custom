import frappe

def execute():
    try:
        wf = frappe.get_doc("Workflow", "Employee Onboarding Workflow")
        for s in wf.states:
            if s.state == "Onboarding In Progress":
                print(f"State: {s.state}, DocStatus: {s.doc_status}, Update Field: {s.update_field}")
    except Exception as e:
        print(f"Error: {e}")
