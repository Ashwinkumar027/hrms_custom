import frappe

def execute():
    try:
        script = frappe.db.get_value("Client Script", "Job Requisition Enhancements", "script")
        print("--- Job Requisition Enhancements ---")
        print(script)
    except Exception as e:
        print(f"Error: {e}")
