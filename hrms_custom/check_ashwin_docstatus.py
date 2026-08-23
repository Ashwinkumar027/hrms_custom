import frappe

def execute():
    try:
        onb = frappe.get_doc("Employee Onboarding", "HR-EMP-ONB-2026-00005")
        print(f"Docstatus: {onb.docstatus}, Workflow State: {onb.workflow_state}")
    except Exception as e:
        print(f"Error: {e}")
