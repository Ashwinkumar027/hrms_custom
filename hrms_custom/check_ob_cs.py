import frappe

def execute():
    try:
        cs = frappe.get_doc("Client Script", "Employee Onboarding Enhancements")
        print(f"Client Script Name: {cs.name}")
        print("\n--- Script Content ---")
        print(cs.script)
    except Exception as e:
        print(f"Error: {e}")
