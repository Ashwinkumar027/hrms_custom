import frappe

def execute():
    try:
        scripts = frappe.get_all("Server Script", filters={"script": ["like", "%Employee Referral%"]}, fields=["name", "script_type", "reference_doctype"])
        for s in scripts:
            print(f"Script: {s.name}, Type: {s.script_type}, DocType: {s.reference_doctype}")
    except Exception as e:
        print(f"Error: {e}")
