import frappe

def execute():
    try:
        ss = frappe.get_all("Server Script", fields=["name", "script_type", "reference_doctype", "module"])
        print("Server Scripts:")
        for s in ss:
            print(f"- {s.name} ({s.reference_doctype}, {s.script_type})")
            
        cs = frappe.get_all("Client Script", fields=["name", "dt"])
        print("\nClient Scripts:")
        for c in cs:
            if c.dt == "Job Requisition":
                print(f"- {c.name}")
    except Exception as e:
        print(f"Error: {e}")
