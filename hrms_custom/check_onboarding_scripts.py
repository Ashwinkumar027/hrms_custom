import frappe

def execute():
    try:
        ss = frappe.get_all("Server Script", filters={"reference_doctype": "Employee Onboarding"}, fields=["name", "script_type", "doctype_event"])
        print("Employee Onboarding Scripts:")
        for s in ss:
            print(f"- {s.name} ({s.doctype_event})")
            script_doc = frappe.get_doc("Server Script", s.name)
            print("--- Script preview ---")
            print(script_doc.script[:500])
            print("----------------------\n")
    except Exception as e:
        print(f"Error: {e}")
