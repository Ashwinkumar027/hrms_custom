import frappe

def execute():
    try:
        ss = frappe.get_doc("Server Script", "Merge Pre-Offer Form")
        print("--- Merge Script Code ---")
        print(ss.script)
    except Exception as e:
        print(f"Error: {e}")
