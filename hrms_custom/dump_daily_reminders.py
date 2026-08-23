import frappe

def execute():
    try:
        script = frappe.db.get_value("Server Script", "Job Requisition Daily Reminders", "script")
        print("--- Job Requisition Daily Reminders ---")
        print(script)
    except Exception as e:
        print(f"Error: {e}")
