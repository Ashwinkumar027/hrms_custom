import frappe

def execute():
    try:
        scripts = frappe.db.sql("SELECT name, script FROM `tabServer Script` WHERE name LIKE '%job_requisition_workflow_emails%'", as_dict=True)
        for s in scripts:
            print(f"--- {s.name} ---")
            print(s.script)
    except Exception as e:
        print(f"Error: {e}")
