import frappe

def execute():
    try:
        cf = frappe.get_all("Custom Field", filters={"dt": "Job Requisition"}, fields=["name", "fieldname", "depends_on"])
        print(cf)
    except Exception as e:
        print(f"Error: {e}")
