import frappe

def execute():
    try:
        scripts = frappe.get_all("Client Script", filters={"dt": "Employee Onboarding"}, fields=["name", "script"])
        print(f"Found {len(scripts)} client scripts for Employee Onboarding")
        for s in scripts:
            print(f"--- {s.name} ---")
            print(s.script)
            print("------\n")
    except Exception as e:
        print(f"Error: {e}")
