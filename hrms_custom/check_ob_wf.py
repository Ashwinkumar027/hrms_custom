import frappe

def execute():
    try:
        wf = frappe.get_doc("Workflow", "Employee Onboarding Workflow")
        for t in wf.transitions:
            print(f"Action: {t.action} -> Next State: {t.next_state}")
    except Exception as e:
        print(f"Error: {e}")
