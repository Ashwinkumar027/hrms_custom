import frappe

def execute():
    try:
        scripts = frappe.get_all("Client Script", filters={"dt": "Job Requisition"}, fields=["name"])
        if scripts:
            print("Existing Client Scripts for Job Requisition:")
            for s in scripts:
                print(f"- {s.name}")
        else:
            print("No existing Client Scripts for Job Requisition.")
    except Exception as e:
        print(f"Error: {e}")
