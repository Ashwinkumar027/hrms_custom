import frappe

def execute():
    try:
        # Check if REQ-Analyst-00001 has rejection reason
        req = frappe.db.get_value("Job Requisition", "REQ-Analyst-00001", "custom_rejection_reason")
        print(f"custom_rejection_reason for REQ-Analyst-00001: '{req}'")
    except Exception as e:
        print(f"Error: {e}")
